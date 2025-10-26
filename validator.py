"""
NGO-InvoiceFiler: Validation and Rule Engine
Validates extracted data against NGO-specific rules, detects anomalies, checks math, deduplicates.
"""

from typing import List, Dict, Any, Optional
from datetime import date, datetime, timedelta
import re

from schemas import (
    ValidationFlag, FlagType, FlagSeverity, DedupeStatus,
    AuditLogEntry, Status, FundType
)


class ValidationEngine:
    """Comprehensive validation of parsed document data"""

    EPSILON = 0.02  # Acceptable rounding error in currency units

    def __init__(self, org_profile, existing_docs: Optional[List[Dict]] = None):
        self.org_profile = org_profile
        self.existing_docs = existing_docs or []
        self.flags: List[ValidationFlag] = []
        self.audit_entries: List[AuditLogEntry] = []

    def validate(self, parsed_data: Dict[str, Any], checksum: str, fingerprint: str) -> Dict[str, Any]:
        """Run all validation checks and return validation results"""
        self.flags = []
        self.audit_entries = []

        # Math validation
        self._validate_math(parsed_data['amounts'], parsed_data['line_items'])

        # Date validation
        self._validate_dates(parsed_data['dates'])

        # Tax validation
        self._validate_tax(parsed_data['amounts'], parsed_data['currency'])

        # Currency validation
        self._validate_currency(parsed_data['currency'])

        # Vendor validation
        self._validate_vendor(parsed_data['vendor'])

        # Deduplication
        dedupe_status = self._check_duplicate(checksum, fingerprint, parsed_data)

        # OCR confidence check
        if parsed_data.get('confidence', 1.0) < 0.75:
            self.flags.append(ValidationFlag(
                type=FlagType.OCR_LOW_CONFIDENCE,
                severity=FlagSeverity.MEDIUM,
                message=f"OCR confidence {parsed_data['confidence']:.2%} below threshold",
                field="confidence"
            ))

        # Compute overall confidence
        score = self._compute_confidence_score(parsed_data)

        self.audit_entries.append(AuditLogEntry(
            step="validate",
            detail=f"checks=5, flags={len(self.flags)}, "
                   f"high={sum(1 for f in self.flags if f.severity == FlagSeverity.HIGH)}, "
                   f"dedupe={dedupe_status.value}, score={score:.2f}"
        ))

        return {
            'checksum_sha256': checksum,
            'doc_fingerprint': fingerprint,
            'dedupe_status': dedupe_status,
            'score_confidence': score,
            'flags': self.flags,
            'audit_log': self.audit_entries
        }

    def _validate_math(self, amounts: Dict[str, float], line_items: List[Dict]) -> None:
        """Validate totals = sum(lines) + tax + shipping - discount"""
        subtotal = amounts.get('subtotal', 0.0)
        tax = amounts.get('tax_amount', 0.0)
        shipping = amounts.get('shipping') or 0.0
        discount = amounts.get('discount') or 0.0
        grand_total = amounts.get('grand_total', 0.0)

        # Recompute grand total
        computed_total = subtotal + tax + shipping - discount

        # Check if within epsilon
        diff = abs(computed_total - grand_total)
        if diff > self.EPSILON:
            self.flags.append(ValidationFlag(
                type=FlagType.MATH_MISMATCH,
                severity=FlagSeverity.HIGH,
                message=f"Grand total {grand_total:.2f} != computed {computed_total:.2f} (diff: {diff:.2f})",
                field="totals.grand_total"
            ))

        # Validate line items sum to subtotal (if available)
        if line_items:
            line_totals = [item.get('total') or 0.0 for item in line_items]
            lines_sum = sum(line_totals)
            if lines_sum > 0:
                line_diff = abs(lines_sum - subtotal)
                if line_diff > self.EPSILON:
                    self.flags.append(ValidationFlag(
                        type=FlagType.MATH_MISMATCH,
                        severity=FlagSeverity.MEDIUM,
                        message=f"Line items sum {lines_sum:.2f} != subtotal {subtotal:.2f}",
                        field="totals.subtotal"
                    ))

        self.audit_entries.append(AuditLogEntry(
            step="validate_math",
            detail=f"grand_total={grand_total:.2f}, computed={computed_total:.2f}, diff={diff:.4f}"
        ))

    def _validate_dates(self, dates: Dict[str, Optional[date]]) -> None:
        """Validate date logic and fiscal year alignment"""
        issue_date = dates.get('issue_date')
        due_date = dates.get('due_date')

        # Check issue_date <= due_date
        if issue_date and due_date:
            if due_date < issue_date:
                self.flags.append(ValidationFlag(
                    type=FlagType.SUSPICIOUS_DATE,
                    severity=FlagSeverity.HIGH,
                    message=f"Due date {due_date} before issue date {issue_date}",
                    field="dates.due_date"
                ))

        # Check fiscal year alignment
        if issue_date:
            fy_start_month = self.org_profile.fiscal_year_start_month
            fiscal_year = self._get_fiscal_year(issue_date, fy_start_month)

            # Check if date is reasonable (not too far in past/future)
            today = date.today()
            days_diff = abs((issue_date - today).days)
            if days_diff > 730:  # More than 2 years
                self.flags.append(ValidationFlag(
                    type=FlagType.SUSPICIOUS_DATE,
                    severity=FlagSeverity.MEDIUM,
                    message=f"Issue date {issue_date} is {days_diff} days from today",
                    field="dates.issue_date"
                ))

            self.audit_entries.append(AuditLogEntry(
                step="validate_dates",
                detail=f"issue={issue_date}, due={due_date}, fiscal_year={fiscal_year}"
            ))
        else:
            self.flags.append(ValidationFlag(
                type=FlagType.MISSING_FIELD,
                severity=FlagSeverity.MEDIUM,
                message="Issue date not found",
                field="dates.issue_date"
            ))

    def _validate_tax(self, amounts: Dict[str, float], currency: str) -> None:
        """Validate tax calculations against known rates"""
        subtotal = amounts.get('subtotal', 0.0)
        tax_amount = amounts.get('tax_amount', 0.0)
        tax_rate = amounts.get('tax_rate')

        if tax_amount > 0 and subtotal > 0:
            # Compute effective rate
            effective_rate = (tax_amount / subtotal) * 100

            # If tax_rate is provided, check consistency
            if tax_rate:
                rate_diff = abs(effective_rate - tax_rate)
                if rate_diff > 0.5:  # Allow 0.5% tolerance
                    self.flags.append(ValidationFlag(
                        type=FlagType.TAX_ANOMALY,
                        severity=FlagSeverity.MEDIUM,
                        message=f"Stated tax rate {tax_rate}% != effective {effective_rate:.1f}%",
                        field="totals.tax_rate"
                    ))

            # Check against known VAT rules for currency/country
            if currency in self.org_profile.vat_rules:
                expected_rate = self.org_profile.vat_rules[currency]
                if abs(effective_rate - expected_rate) > 1.0:
                    self.flags.append(ValidationFlag(
                        type=FlagType.TAX_ANOMALY,
                        severity=FlagSeverity.LOW,
                        message=f"Tax rate {effective_rate:.1f}% differs from expected {expected_rate}% for {currency}",
                        field="totals.tax_amount"
                    ))

            self.audit_entries.append(AuditLogEntry(
                step="validate_tax",
                detail=f"tax={tax_amount:.2f}, subtotal={subtotal:.2f}, "
                       f"effective_rate={effective_rate:.2f}%, stated_rate={tax_rate}"
            ))

    def _validate_currency(self, currency: str) -> None:
        """Validate currency code is valid ISO 4217"""
        # List of common ISO 4217 codes
        valid_currencies = {
            'USD', 'EUR', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD', 'NZD',
            'ILS', 'INR', 'CNY', 'KRW', 'SGD', 'HKD', 'THB', 'MXN',
            'BRL', 'ZAR', 'RUB', 'TRY', 'SEK', 'NOK', 'DKK', 'PLN'
        }

        if currency not in valid_currencies:
            self.flags.append(ValidationFlag(
                type=FlagType.CURRENCY_MISMATCH,
                severity=FlagSeverity.MEDIUM,
                message=f"Currency '{currency}' not recognized or invalid",
                field="currency"
            ))

        self.audit_entries.append(AuditLogEntry(
            step="validate_currency",
            detail=f"currency={currency}, valid={currency in valid_currencies}"
        ))

    def _validate_vendor(self, vendor: Dict[str, Any]) -> None:
        """Validate vendor information completeness"""
        vendor_name = vendor.get('display_name', '')

        if not vendor_name or vendor_name == 'Unknown Vendor':
            self.flags.append(ValidationFlag(
                type=FlagType.MISSING_FIELD,
                severity=FlagSeverity.HIGH,
                message="Vendor name not found",
                field="vendor.display_name"
            ))

        # Check for minimal vendor info
        if not any([vendor.get('tax_id_vat'), vendor.get('email'), vendor.get('phone')]):
            self.flags.append(ValidationFlag(
                type=FlagType.VENDOR_MISMATCH,
                severity=FlagSeverity.LOW,
                message="Vendor missing contact information (tax ID, email, or phone)",
                field="vendor"
            ))

    def _check_duplicate(self, checksum: str, fingerprint: str, parsed_data: Dict) -> DedupeStatus:
        """Check for duplicate documents by hash and fingerprint"""
        # Check exact file duplicate (SHA-256)
        for doc in self.existing_docs:
            if doc.get('checksum_sha256') == checksum:
                self.flags.append(ValidationFlag(
                    type=FlagType.DUPLICATE,
                    severity=FlagSeverity.HIGH,
                    message=f"Exact duplicate found (SHA-256 match): {doc.get('doc_id')}",
                    field="validation.checksum_sha256"
                ))
                return DedupeStatus.DUPLICATE

        # Check semantic duplicate (fingerprint)
        for doc in self.existing_docs:
            if doc.get('doc_fingerprint') == fingerprint:
                self.flags.append(ValidationFlag(
                    type=FlagType.DUPLICATE,
                    severity=FlagSeverity.HIGH,
                    message=f"Suspected duplicate (fingerprint match): {doc.get('doc_id')}",
                    field="validation.doc_fingerprint"
                ))
                return DedupeStatus.SUSPECTED_DUPLICATE

        return DedupeStatus.UNIQUE

    def _compute_confidence_score(self, parsed_data: Dict) -> float:
        """Compute overall confidence score based on completeness and flags"""
        base_score = parsed_data.get('confidence', 0.9)

        # Deduct points for missing fields
        required_fields = [
            parsed_data['vendor'].get('display_name'),
            parsed_data['dates'].get('issue_date'),
            parsed_data['amounts'].get('grand_total'),
            parsed_data['currency']
        ]
        completeness = sum(1 for f in required_fields if f) / len(required_fields)

        # Deduct points for flags
        high_flags = sum(1 for f in self.flags if f.severity == FlagSeverity.HIGH)
        medium_flags = sum(1 for f in self.flags if f.severity == FlagSeverity.MEDIUM)

        penalty = (high_flags * 0.15) + (medium_flags * 0.05)

        final_score = max(0.0, min(1.0, base_score * completeness - penalty))
        return round(final_score, 2)

    @staticmethod
    def _get_fiscal_year(date_obj: date, fy_start_month: int) -> str:
        """
        Compute fiscal year string (YYYY-YYYY) based on date and FY start month
        Example: if FY starts in April, March 2024 is FY2023-2024
        """
        if date_obj.month < fy_start_month:
            fy_start = date_obj.year - 1
            fy_end = date_obj.year
        else:
            fy_start = date_obj.year
            fy_end = date_obj.year + 1

        return f"{fy_start}-{fy_end}"


class NGOClassifier:
    """NGO-specific classification: fund type, projects, grants, categories"""

    def __init__(self, org_profile):
        self.org_profile = org_profile

    def classify(self, parsed_data: Dict, user_hints: Optional[Dict] = None) -> Dict[str, Any]:
        """Apply NGO-specific classifications"""
        user_hints = user_hints or {}

        # Determine project and grant from hints or line items
        project_code = user_hints.get('project_code')
        grant_code = user_hints.get('grant_code')

        # If not in hints, try to extract from line items
        if not project_code:
            project_code = self._infer_project_code(parsed_data['line_items'])

        if not grant_code:
            grant_code = self._infer_grant_code(parsed_data['line_items'])

        # Determine fund type (restricted vs unrestricted)
        fund_type = self._determine_fund_type(grant_code)

        # Classify spend categories
        spend_categories = self._classify_spend_categories(parsed_data['line_items'])

        # Primary category (most common)
        category_primary = spend_categories[0] if spend_categories else None

        # Determine donor from grant
        donor = self._get_donor_from_grant(grant_code)

        # Determine country (from vendor address or currency)
        country = self._infer_country(parsed_data['vendor'], parsed_data['currency'])

        # Tax type
        tax_type = self._infer_tax_type(parsed_data['amounts'], country)

        # Fiscal year
        issue_date = parsed_data['dates'].get('issue_date')
        fiscal_year = ValidationEngine._get_fiscal_year(
            issue_date or date.today(),
            self.org_profile.fiscal_year_start_month
        )

        # Document type booleans
        doc_type = parsed_data['doc_type']
        is_invoice = doc_type.value == 'invoice'
        is_receipt = doc_type.value == 'receipt'
        is_credit_note = doc_type.value == 'credit_note'

        return {
            'classification': {
                'is_receipt': is_receipt,
                'is_invoice': is_invoice,
                'is_credit_note': is_credit_note,
                'fund_type': fund_type,
                'spend_categories': spend_categories,
                'country': country,
                'tax_type': tax_type
            },
            'ngo_context': {
                'donor': donor,
                'grant_code': grant_code,
                'project_code': project_code,
                'budget_line': None,  # Would require budget mapping
                'fiscal_year': fiscal_year,
                'attachments': [parsed_data.get('file_name', 'unknown.pdf')]
            },
            'category_primary': category_primary
        }

    def _infer_project_code(self, line_items: List[Dict]) -> Optional[str]:
        """Extract project code from line items if present"""
        for item in line_items:
            if item.get('project_code'):
                return item['project_code']
        return None

    def _infer_grant_code(self, line_items: List[Dict]) -> Optional[str]:
        """Extract grant code from line items if present"""
        for item in line_items:
            if item.get('grant_code'):
                return item['grant_code']
        return None

    def _determine_fund_type(self, grant_code: Optional[str]) -> Optional[FundType]:
        """Determine if restricted or unrestricted based on grant"""
        if not grant_code:
            return FundType.UNRESTRICTED

        # Check grant dictionary
        if grant_code in self.org_profile.grant_dictionary:
            grant_info = self.org_profile.grant_dictionary[grant_code]
            if grant_info.get('restricted'):
                return FundType.RESTRICTED

        return FundType.UNRESTRICTED

    def _classify_spend_categories(self, line_items: List[Dict]) -> List[str]:
        """Extract unique spend categories from line items"""
        categories = set()
        for item in line_items:
            cat = item.get('category')
            if cat:
                categories.add(cat)

        return sorted(list(categories))

    def _get_donor_from_grant(self, grant_code: Optional[str]) -> Optional[str]:
        """Look up donor from grant code"""
        if not grant_code:
            return None

        if grant_code in self.org_profile.grant_dictionary:
            return self.org_profile.grant_dictionary[grant_code].get('donor')

        return None

    def _infer_country(self, vendor: Dict, currency: str) -> Optional[str]:
        """Infer country from vendor address or currency"""
        # Currency to country mapping (simplified)
        currency_country = {
            'USD': 'US', 'EUR': 'EU', 'GBP': 'GB', 'ILS': 'IL',
            'JPY': 'JP', 'CAD': 'CA', 'AUD': 'AU', 'CHF': 'CH',
            'INR': 'IN', 'CNY': 'CN', 'MXN': 'MX', 'BRL': 'BR'
        }

        # Try to extract from vendor address (would need NER in production)
        # For now, use currency
        return currency_country.get(currency)

    def _infer_tax_type(self, amounts: Dict, country: Optional[str]) -> Optional[str]:
        """Infer tax type (VAT, GST, Sales Tax)"""
        if amounts.get('tax_amount', 0) == 0:
            return 'None'

        # Country-specific tax types
        if country in ['EU', 'GB', 'IL']:
            return 'VAT'
        elif country in ['IN', 'AU', 'SG', 'NZ']:
            return 'GST'
        elif country in ['US', 'CA']:
            return 'SalesTax'

        return None
