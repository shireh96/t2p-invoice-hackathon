"""
NGO-InvoiceFiler: Data Schemas and Models
Production-grade data structures for invoice processing, validation, and filing.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime, date
from enum import Enum
import json


class DocType(str, Enum):
    INVOICE = "invoice"
    RECEIPT = "receipt"
    CREDIT_NOTE = "credit_note"
    PROFORMA = "proforma"
    OTHER = "other"


class Language(str, Enum):
    EN = "en"
    AR = "ar"
    HE = "he"
    AUTO = "auto"


class FundType(str, Enum):
    RESTRICTED = "restricted"
    UNRESTRICTED = "unrestricted"


class Status(str, Enum):
    DRAFT = "draft"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    POSTED = "posted"


class PaymentMethod(str, Enum):
    CASH = "cash"
    TRANSFER = "transfer"
    CARD = "card"
    CHECK = "check"
    OTHER = "other"


class FlagSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FlagType(str, Enum):
    MATH_MISMATCH = "math_mismatch"
    MISSING_FIELD = "missing_field"
    SUSPICIOUS_DATE = "suspicious_date"
    CURRENCY_MISMATCH = "currency_mismatch"
    TAX_ANOMALY = "tax_anomaly"
    DUPLICATE = "duplicate"
    VENDOR_MISMATCH = "vendor_mismatch"
    OCR_LOW_CONFIDENCE = "ocr_low_confidence"
    PARSE_FAILED = "parse_failed"


class DedupeStatus(str, Enum):
    UNIQUE = "unique"
    DUPLICATE = "duplicate"
    SUSPECTED_DUPLICATE = "suspected_duplicate"


@dataclass
class Totals:
    subtotal: float
    tax_amount: float
    grand_total: float
    tax_rate: Optional[float] = None
    shipping: Optional[float] = None
    discount: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subtotal": self.subtotal,
            "tax_amount": self.tax_amount,
            "tax_rate": self.tax_rate,
            "shipping": self.shipping,
            "discount": self.discount,
            "grand_total": self.grand_total
        }


@dataclass
class Dates:
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    service_period_start: Optional[date] = None
    service_period_end: Optional[date] = None
    payment_date: Optional[date] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_date": self.issue_date.isoformat() if self.issue_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "service_period_start": self.service_period_start.isoformat() if self.service_period_start else None,
            "service_period_end": self.service_period_end.isoformat() if self.service_period_end else None,
            "payment_date": self.payment_date.isoformat() if self.payment_date else None
        }


@dataclass
class Vendor:
    display_name: str
    legal_name: Optional[str] = None
    tax_id_vat: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    iban: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "display_name": self.display_name,
            "legal_name": self.legal_name,
            "tax_id_vat": self.tax_id_vat,
            "email": self.email,
            "phone": self.phone,
            "address": self.address,
            "iban": self.iban
        }


@dataclass
class Buyer:
    org_name: str
    tax_id_vat: Optional[str] = None
    address: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "org_name": self.org_name,
            "tax_id_vat": self.tax_id_vat,
            "address": self.address
        }


@dataclass
class Invoice:
    number: Optional[str] = None
    po_number: Optional[str] = None
    reference: Optional[str] = None
    payment_terms: Optional[str] = None
    payment_method: Optional[PaymentMethod] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "number": self.number,
            "po_number": self.po_number,
            "reference": self.reference,
            "payment_terms": self.payment_terms,
            "payment_method": self.payment_method.value if self.payment_method else None
        }


@dataclass
class LineItem:
    description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    tax_rate: Optional[float] = None
    total: Optional[float] = None
    project_code: Optional[str] = None
    grant_code: Optional[str] = None
    cost_center: Optional[str] = None
    category: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "description": self.description,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "tax_rate": self.tax_rate,
            "total": self.total,
            "project_code": self.project_code,
            "grant_code": self.grant_code,
            "cost_center": self.cost_center,
            "category": self.category
        }


@dataclass
class Classification:
    is_receipt: bool = False
    is_invoice: bool = False
    is_credit_note: bool = False
    fund_type: Optional[FundType] = None
    spend_categories: List[str] = field(default_factory=list)
    country: Optional[str] = None
    tax_type: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_receipt": self.is_receipt,
            "is_invoice": self.is_invoice,
            "is_credit_note": self.is_credit_note,
            "fund_type": self.fund_type.value if self.fund_type else None,
            "spend_categories": self.spend_categories,
            "country": self.country,
            "tax_type": self.tax_type
        }


@dataclass
class NGOContext:
    fiscal_year: str
    donor: Optional[str] = None
    grant_code: Optional[str] = None
    project_code: Optional[str] = None
    budget_line: Optional[str] = None
    attachments: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "donor": self.donor,
            "grant_code": self.grant_code,
            "project_code": self.project_code,
            "budget_line": self.budget_line,
            "fiscal_year": self.fiscal_year,
            "attachments": self.attachments
        }


@dataclass
class Filing:
    folder_path: str
    file_name: str
    status: Status
    approver: Optional[str] = None
    approved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "folder_path": self.folder_path,
            "file_name": self.file_name,
            "status": self.status.value,
            "approver": self.approver,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None
        }


@dataclass
class ValidationFlag:
    type: FlagType
    severity: FlagSeverity
    message: str
    field: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "severity": self.severity.value,
            "message": self.message,
            "field": self.field
        }


@dataclass
class Validation:
    checksum_sha256: str
    doc_fingerprint: str
    dedupe_status: DedupeStatus
    score_confidence: float
    flags: List[ValidationFlag] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checksum_sha256": self.checksum_sha256,
            "doc_fingerprint": self.doc_fingerprint,
            "dedupe_status": self.dedupe_status.value,
            "score_confidence": self.score_confidence,
            "flags": [f.to_dict() for f in self.flags]
        }


@dataclass
class AuditLogEntry:
    step: str
    detail: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "detail": self.detail
        }


@dataclass
class ProcessedDocument:
    """Complete structured document output"""
    doc_id: str
    ingest_timestamp: datetime
    doc_type: DocType
    language: Language
    currency: str
    totals: Totals
    dates: Dates
    vendor: Vendor
    buyer: Buyer
    invoice: Invoice
    line_items: List[LineItem]
    classification: Classification
    ngo_context: NGOContext
    filing: Filing
    validation: Validation
    audit_log: List[AuditLogEntry]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "ingest_timestamp": self.ingest_timestamp.isoformat(),
            "doc_type": self.doc_type.value,
            "language": self.language.value,
            "currency": self.currency,
            "totals": self.totals.to_dict(),
            "dates": self.dates.to_dict(),
            "vendor": self.vendor.to_dict(),
            "buyer": self.buyer.to_dict(),
            "invoice": self.invoice.to_dict(),
            "line_items": [item.to_dict() for item in self.line_items],
            "classification": self.classification.to_dict(),
            "ngo_context": self.ngo_context.to_dict(),
            "filing": self.filing.to_dict(),
            "validation": self.validation.to_dict(),
            "audit_log": [entry.to_dict() for entry in self.audit_log]
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


@dataclass
class OrganizationProfile:
    """NGO organization configuration"""
    ngo_name: str
    fiscal_year_start_month: int = 1  # January
    default_currency: str = "USD"
    vat_rules: Dict[str, float] = field(default_factory=dict)  # country -> rate
    donor_dictionary: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    grant_dictionary: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    project_codes: Dict[str, str] = field(default_factory=dict)  # code -> name
    cost_centers: List[str] = field(default_factory=list)
    vendor_aliases: Dict[str, str] = field(default_factory=dict)  # alias -> canonical
    category_keywords: Dict[str, List[str]] = field(default_factory=dict)  # category -> keywords


@dataclass
class LedgerRow:
    """Normalized ledger entry for CSV/Excel export"""
    doc_id: str
    issue_date: Optional[str]
    due_date: Optional[str]
    vendor: str
    invoice_number: Optional[str]
    currency: str
    subtotal: float
    tax_amount: float
    grand_total: float
    project_code: Optional[str]
    grant_code: Optional[str]
    fund_type: Optional[str]
    category_primary: Optional[str]
    status: str
    fiscal_year: str
    file_path: str
    file_name: str
    dedupe_status: str
    approver: Optional[str]
    approved_at: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "issue_date": self.issue_date,
            "due_date": self.due_date,
            "vendor": self.vendor,
            "invoice_number": self.invoice_number,
            "currency": self.currency,
            "subtotal": self.subtotal,
            "tax_amount": self.tax_amount,
            "grand_total": self.grand_total,
            "project_code": self.project_code,
            "grant_code": self.grant_code,
            "fund_type": self.fund_type,
            "category_primary": self.category_primary,
            "status": self.status,
            "fiscal_year": self.fiscal_year,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "dedupe_status": self.dedupe_status,
            "approver": self.approver,
            "approved_at": self.approved_at
        }

    @staticmethod
    def csv_headers() -> List[str]:
        return [
            "doc_id", "issue_date", "due_date", "vendor", "invoice_number",
            "currency", "subtotal", "tax_amount", "grand_total",
            "project_code", "grant_code", "fund_type", "category_primary",
            "status", "fiscal_year", "file_path", "file_name",
            "dedupe_status", "approver", "approved_at"
        ]
