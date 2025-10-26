"""
NGO-InvoiceFiler: OCR and Document Parsing Engine
Handles OCR extraction, language detection, entity recognition, and structured parsing.
"""

import re
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date
from pathlib import Path
import unicodedata

from schemas import (
    DocType, Language, PaymentMethod, LineItem,
    AuditLogEntry, FlagType, FlagSeverity, ValidationFlag
)


class OCREngine:
    """Simulated OCR engine with multilingual support"""

    def __init__(self):
        self.supported_langs = ['en', 'ar', 'he']

    def extract_text(self, file_bytes: bytes, language: str = 'auto') -> Tuple[str, float, str]:
        """
        Simulate OCR text extraction
        Returns: (extracted_text, confidence, detected_language)
        """
        # In production, integrate with Tesseract, Google Vision, AWS Textract, or Azure Computer Vision
        # For now, simulate with placeholder

        detected_lang = self._detect_language(file_bytes) if language == 'auto' else language
        confidence = 0.95  # Simulated high confidence

        # Placeholder text - in production this would be actual OCR output
        text = "[OCR_SIMULATION] Document text would appear here after real OCR processing"

        return text, confidence, detected_lang

    def _detect_language(self, file_bytes: bytes) -> str:
        """Auto-detect document language"""
        # In production: analyze script types, common words, character frequencies
        # Check for RTL markers, Arabic/Hebrew Unicode ranges
        return 'en'  # Default for simulation


class DocumentParser:
    """Extract structured data from OCR text using NER and pattern matching"""

    # Currency symbols and codes
    CURRENCY_SYMBOLS = {
        '$': 'USD', '€': 'EUR', '£': 'GBP', '₪': 'ILS',
        '¥': 'JPY', '₹': 'INR', 'CHF': 'CHF', 'C$': 'CAD'
    }

    # Date patterns for multiple formats
    DATE_PATTERNS = [
        r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})',  # DD/MM/YYYY or MM/DD/YYYY
        r'(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})',    # YYYY-MM-DD
        r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(\d{2,4})',  # DD Mon YYYY
    ]

    # Amount patterns
    AMOUNT_PATTERN = r'[\$€£₪¥₹]?\s*(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?|\d+(?:\.\d{2})?)'

    def __init__(self, org_profile):
        self.org_profile = org_profile
        self.audit_entries = []

    def parse_document(self, text: str, file_name: str, confidence: float,
                      ai_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main parsing orchestrator
        Args:
            text: OCR extracted text
            file_name: Original file name
            confidence: OCR confidence score
            ai_data: Optional AI-extracted structured data
        """
        self.audit_entries = []

        # If AI data is provided, use it (it's more accurate)
        if ai_data and ai_data.get('success'):
            return self._parse_from_ai_data(ai_data['data'], text, confidence)

        # Otherwise, use regex-based parsing
        # Detect document type
        doc_type = self._classify_document_type(text)
        self.audit_entries.append(AuditLogEntry(
            step="classify",
            detail=f"doc_type={doc_type.value}, confidence={confidence:.2f}"
        ))

        # Extract core fields
        vendor_info = self._extract_vendor(text)
        invoice_info = self._extract_invoice_details(text)
        dates_info = self._extract_dates(text)
        amounts = self._extract_amounts(text)
        line_items = self._extract_line_items(text)
        currency = self._detect_currency(text)

        self.audit_entries.append(AuditLogEntry(
            step="parse",
            detail=f"vendor={vendor_info.get('display_name', 'unknown')}, "
                   f"invoice={invoice_info.get('number', 'N/A')}, "
                   f"currency={currency}, items={len(line_items)}"
        ))

        # Build structured output
        parsed = {
            'doc_type': doc_type,
            'vendor': vendor_info,
            'invoice': invoice_info,
            'dates': dates_info,
            'amounts': amounts,
            'line_items': line_items,
            'currency': currency,
            'confidence': confidence,
            'audit_log': self.audit_entries
        }

        return parsed

    def _parse_from_ai_data(self, ai_data: Dict[str, Any], text: str, confidence: float) -> Dict[str, Any]:
        """Parse document using AI-extracted data"""
        from datetime import datetime

        self.audit_entries.append(AuditLogEntry(
            step="parse_ai",
            detail="Using AI-extracted structured data"
        ))

        # Parse dates
        issue_date = None
        due_date = None
        if ai_data.get('invoice_date'):
            try:
                issue_date = datetime.strptime(ai_data['invoice_date'], '%Y-%m-%d').date()
            except:
                pass
        if ai_data.get('due_date'):
            try:
                due_date = datetime.strptime(ai_data['due_date'], '%Y-%m-%d').date()
            except:
                pass

        # Build vendor info
        vendor_info = {
            'display_name': ai_data.get('vendor_name', 'Unknown Vendor'),
            'legal_name': ai_data.get('vendor_name'),
            'tax_id_vat': ai_data.get('vendor_tax_id'),
            'email': ai_data.get('vendor_email'),
            'phone': ai_data.get('vendor_phone'),
            'address': ai_data.get('vendor_address'),
            'iban': None
        }

        # Build invoice info
        invoice_info = {
            'number': ai_data.get('invoice_number'),
            'po_number': None,
            'reference': None,
            'payment_terms': None,
            'payment_method': self._map_payment_method(ai_data.get('payment_method'))
        }

        # Build dates
        dates_info = {
            'issue_date': issue_date,
            'due_date': due_date,
            'service_period_start': None,
            'service_period_end': None,
            'payment_date': None
        }

        # Build amounts
        amounts = {
            'subtotal': float(ai_data.get('subtotal', 0)),
            'tax_amount': float(ai_data.get('tax_amount', 0)),
            'tax_rate': float(ai_data.get('tax_rate', 0)) if ai_data.get('tax_rate') else None,
            'grand_total': float(ai_data.get('grand_total', 0)),
            'shipping': None,
            'discount': None
        }

        # Build line items
        line_items = []
        for item in ai_data.get('line_items', []):
            line_items.append({
                'description': item.get('description', ''),
                'quantity': float(item.get('quantity', 0)) if item.get('quantity') else None,
                'unit_price': float(item.get('unit_price', 0)) if item.get('unit_price') else None,
                'tax_rate': None,
                'total': float(item.get('total', 0)) if item.get('total') else None,
                'project_code': None,
                'grant_code': None,
                'cost_center': None,
                'category': None
            })

        # Detect document type
        doc_type = self._classify_document_type(text)

        currency = ai_data.get('currency', 'USD')

        self.audit_entries.append(AuditLogEntry(
            step="parse_complete",
            detail=f"AI parsing: vendor={vendor_info['display_name']}, "
                   f"invoice={invoice_info.get('number')}, "
                   f"total={amounts['grand_total']} {currency}"
        ))

        return {
            'doc_type': doc_type,
            'vendor': vendor_info,
            'invoice': invoice_info,
            'dates': dates_info,
            'amounts': amounts,
            'line_items': line_items,
            'currency': currency,
            'confidence': 0.95,  # AI parsing has high confidence
            'audit_log': self.audit_entries
        }

    def _map_payment_method(self, method_str: Optional[str]) -> Optional[PaymentMethod]:
        """Map string payment method to enum"""
        if not method_str:
            return None
        method_lower = method_str.lower()
        if 'cash' in method_lower:
            return PaymentMethod.CASH
        elif 'transfer' in method_lower or 'bank' in method_lower:
            return PaymentMethod.TRANSFER
        elif 'card' in method_lower or 'credit' in method_lower:
            return PaymentMethod.CARD
        elif 'check' in method_lower or 'cheque' in method_lower:
            return PaymentMethod.CHECK
        else:
            return PaymentMethod.OTHER

    def _classify_document_type(self, text: str) -> DocType:
        """Detect if invoice, receipt, credit note, etc."""
        text_lower = text.lower()

        if any(kw in text_lower for kw in ['credit note', 'credit memo', 'refund']):
            return DocType.CREDIT_NOTE
        elif any(kw in text_lower for kw in ['proforma', 'pro forma', 'quotation']):
            return DocType.PROFORMA
        elif any(kw in text_lower for kw in ['receipt', 'paid receipt', 'payment received']):
            return DocType.RECEIPT
        elif any(kw in text_lower for kw in ['invoice', 'bill', 'tax invoice', 'vat invoice']):
            return DocType.INVOICE
        else:
            return DocType.OTHER

    def _extract_vendor(self, text: str) -> Dict[str, Any]:
        """Extract vendor name, tax ID, contact info"""
        lines = text.split('\n')

        # Heuristic: vendor name often in first 5 lines
        vendor_name = "Unknown Vendor"
        for line in lines[:5]:
            if len(line.strip()) > 3 and not any(kw in line.lower() for kw in ['invoice', 'receipt', 'date']):
                vendor_name = line.strip()
                break

        # Normalize vendor name using aliases
        canonical_name = self._normalize_vendor_name(vendor_name)

        # Extract tax ID / VAT
        tax_id = None
        tax_patterns = [
            r'VAT[:\s]*([A-Z0-9\-]+)',
            r'Tax\s*ID[:\s]*([A-Z0-9\-]+)',
            r'EIN[:\s]*(\d{2}-\d{7})',
        ]
        for pattern in tax_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                tax_id = match.group(1)
                break

        # Extract email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        email = email_match.group(0) if email_match else None

        # Extract phone
        phone_match = re.search(r'[\+]?[\d\s\(\)\-]{10,20}', text)
        phone = phone_match.group(0).strip() if phone_match else None

        # Extract IBAN
        iban_match = re.search(r'IBAN[:\s]*([A-Z]{2}\d{2}[A-Z0-9]+)', text, re.IGNORECASE)
        iban = iban_match.group(1) if iban_match else None

        return {
            'display_name': canonical_name,
            'legal_name': vendor_name if vendor_name != canonical_name else None,
            'tax_id_vat': tax_id,
            'email': email,
            'phone': phone,
            'address': None,  # Complex extraction - would need NER
            'iban': iban
        }

    def _normalize_vendor_name(self, name: str) -> str:
        """Canonicalize vendor name using alias dictionary"""
        normalized = name.lower().strip()

        # Remove diacritics
        normalized = ''.join(
            c for c in unicodedata.normalize('NFD', normalized)
            if unicodedata.category(c) != 'Mn'
        )

        # Strip punctuation except spaces
        normalized = re.sub(r'[^\w\s]', '', normalized)

        # Check aliases
        if normalized in self.org_profile.vendor_aliases:
            return self.org_profile.vendor_aliases[normalized]

        # Title case for display
        return ' '.join(word.capitalize() for word in normalized.split())

    def _extract_invoice_details(self, text: str) -> Dict[str, Any]:
        """Extract invoice number, PO, payment terms"""
        invoice_num = None
        po_num = None
        payment_terms = None
        payment_method = None

        # Invoice number
        inv_patterns = [
            r'Invoice\s*#?\s*:?\s*([A-Z0-9\-]+)',
            r'Bill\s*#?\s*:?\s*([A-Z0-9\-]+)',
            r'Ref(?:erence)?\s*#?\s*:?\s*([A-Z0-9\-]+)',
        ]
        for pattern in inv_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                invoice_num = match.group(1)
                break

        # PO number
        po_match = re.search(r'P\.?O\.?\s*#?\s*:?\s*([A-Z0-9\-]+)', text, re.IGNORECASE)
        if po_match:
            po_num = po_match.group(1)

        # Payment terms
        terms_match = re.search(r'Payment\s*Terms?\s*:?\s*(.{5,30})', text, re.IGNORECASE)
        if terms_match:
            payment_terms = terms_match.group(1).strip()

        # Payment method
        text_lower = text.lower()
        if 'cash' in text_lower:
            payment_method = PaymentMethod.CASH
        elif any(kw in text_lower for kw in ['wire', 'transfer', 'bank']):
            payment_method = PaymentMethod.TRANSFER
        elif any(kw in text_lower for kw in ['card', 'credit card', 'visa', 'mastercard']):
            payment_method = PaymentMethod.CARD
        elif any(kw in text_lower for kw in ['check', 'cheque']):
            payment_method = PaymentMethod.CHECK

        return {
            'number': invoice_num,
            'po_number': po_num,
            'reference': None,
            'payment_terms': payment_terms,
            'payment_method': payment_method
        }

    def _extract_dates(self, text: str) -> Dict[str, Optional[date]]:
        """Extract issue date, due date, service period"""
        dates = {}

        # Issue date
        issue_patterns = [
            r'(?:Invoice\s*)?Date\s*:?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
            r'Issue(?:d)?\s*(?:Date)?\s*:?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
        ]
        for pattern in issue_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                dates['issue_date'] = self._parse_date(match.group(1))
                break

        # Due date
        due_match = re.search(r'Due\s*Date\s*:?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})', text, re.IGNORECASE)
        if due_match:
            dates['due_date'] = self._parse_date(due_match.group(1))

        return {
            'issue_date': dates.get('issue_date'),
            'due_date': dates.get('due_date'),
            'service_period_start': None,
            'service_period_end': None,
            'payment_date': None
        }

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string to date object"""
        formats = ['%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d.%m.%Y']
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def _detect_currency(self, text: str) -> str:
        """Detect currency from symbols and codes"""
        # Check for currency symbols
        for symbol, code in self.CURRENCY_SYMBOLS.items():
            if symbol in text:
                return code

        # Check for ISO codes
        iso_match = re.search(r'\b(USD|EUR|GBP|ILS|JPY|INR|CHF|CAD)\b', text, re.IGNORECASE)
        if iso_match:
            return iso_match.group(1).upper()

        # Default to org currency
        return self.org_profile.default_currency

    def _extract_amounts(self, text: str) -> Dict[str, float]:
        """Extract subtotal, tax, total, shipping, discount"""
        amounts = {
            'subtotal': 0.0,
            'tax_amount': 0.0,
            'tax_rate': None,
            'shipping': None,
            'discount': None,
            'grand_total': 0.0
        }

        # Total/Grand Total
        total_patterns = [
            r'(?:Grand\s*)?Total\s*:?\s*[\$€£₪¥₹]?\s*([\d,]+\.?\d*)',
            r'Amount\s*Due\s*:?\s*[\$€£₪¥₹]?\s*([\d,]+\.?\d*)',
        ]
        for pattern in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amounts['grand_total'] = self._parse_amount(match.group(1))
                break

        # Subtotal
        subtotal_match = re.search(r'Sub\s*Total\s*:?\s*[\$€£₪¥₹]?\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
        if subtotal_match:
            amounts['subtotal'] = self._parse_amount(subtotal_match.group(1))

        # Tax/VAT
        tax_patterns = [
            r'(?:VAT|Tax|GST)\s*(?:\((\d+)%\))?\s*:?\s*[\$€£₪¥₹]?\s*([\d,]+\.?\d*)',
        ]
        for pattern in tax_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if match.group(1):
                    amounts['tax_rate'] = float(match.group(1))
                amounts['tax_amount'] = self._parse_amount(match.group(2))
                break

        # Shipping
        ship_match = re.search(r'Shipping\s*:?\s*[\$€£₪¥₹]?\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
        if ship_match:
            amounts['shipping'] = self._parse_amount(ship_match.group(1))

        # Discount
        disc_match = re.search(r'Discount\s*:?\s*[\$€£₪¥₹]?\s*([\d,]+\.?\d*)', text, re.IGNORECASE)
        if disc_match:
            amounts['discount'] = self._parse_amount(disc_match.group(1))

        # If no subtotal, infer from total - tax - shipping + discount
        if amounts['subtotal'] == 0.0 and amounts['grand_total'] > 0.0:
            amounts['subtotal'] = (
                amounts['grand_total']
                - amounts['tax_amount']
                - (amounts['shipping'] or 0.0)
                + (amounts['discount'] or 0.0)
            )

        return amounts

    def _parse_amount(self, amount_str: str) -> float:
        """Convert amount string to float"""
        cleaned = amount_str.replace(',', '').replace(' ', '').strip()
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def _extract_line_items(self, text: str) -> List[Dict[str, Any]]:
        """Extract itemized line items"""
        items = []

        # Look for table-like structures
        # This is simplified - production would use table detection
        lines = text.split('\n')
        in_items_section = False

        for line in lines:
            # Detect start of items section
            if any(kw in line.lower() for kw in ['description', 'item', 'quantity', 'amount']):
                in_items_section = True
                continue

            # Detect end of items section
            if in_items_section and any(kw in line.lower() for kw in ['subtotal', 'total', 'tax']):
                break

            # Extract line item (simplified pattern)
            if in_items_section and line.strip():
                # Pattern: description ... quantity ... unit price ... total
                item_match = re.search(
                    r'(.+?)\s+(\d+(?:\.\d+)?)\s+[\$€£₪¥₹]?([\d,]+\.?\d*)\s+[\$€£₪¥₹]?([\d,]+\.?\d*)',
                    line
                )
                if item_match:
                    desc = item_match.group(1).strip()
                    qty = float(item_match.group(2))
                    unit_price = self._parse_amount(item_match.group(3))
                    total = self._parse_amount(item_match.group(4))

                    # Infer category from description
                    category = self._classify_line_item(desc)

                    items.append({
                        'description': desc,
                        'quantity': qty,
                        'unit_price': unit_price,
                        'total': total,
                        'category': category,
                        'tax_rate': None,
                        'project_code': None,
                        'grant_code': None,
                        'cost_center': None
                    })

        # If no items extracted, create a single generic item
        if not items:
            items.append({
                'description': 'General expense',
                'quantity': 1.0,
                'unit_price': None,
                'total': None,
                'category': None,
                'tax_rate': None,
                'project_code': None,
                'grant_code': None,
                'cost_center': None
            })

        return items

    def _classify_line_item(self, description: str) -> Optional[str]:
        """Classify line item into spend category using keyword matching"""
        desc_lower = description.lower()

        for category, keywords in self.org_profile.category_keywords.items():
            if any(kw.lower() in desc_lower for kw in keywords):
                return category

        return None


class DocumentHasher:
    """Generate checksums and fingerprints for deduplication"""

    @staticmethod
    def compute_sha256(file_bytes: bytes) -> str:
        """Compute SHA-256 checksum of file"""
        return hashlib.sha256(file_bytes).hexdigest()

    @staticmethod
    def compute_fingerprint(vendor: str, date: Optional[date], invoice_num: Optional[str],
                          amount: float) -> str:
        """
        Compute semantic fingerprint for deduplication
        Format: vendor_YYYYMMDD_invnum_amount
        """
        vendor_norm = re.sub(r'\W+', '', vendor.lower())
        date_str = date.strftime('%Y%m%d') if date else 'NODATE'
        inv_str = re.sub(r'\W+', '', invoice_num.lower()) if invoice_num else 'NOINV'
        amt_str = f"{amount:.2f}".replace('.', '')

        fingerprint_str = f"{vendor_norm}_{date_str}_{inv_str}_{amt_str}"
        return hashlib.md5(fingerprint_str.encode()).hexdigest()[:16]
