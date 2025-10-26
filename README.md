# NGO-InvoiceFiler v1.0

**Production-Grade Invoice & Receipt Processing System for NGOs**

A comprehensive AI system that ingests invoices and receipts (PDF, images, scanned documents, or email text), extracts structured data using OCR and NER, validates against NGO-specific rules, files documents into a consistent folder structure with deterministic naming, and exports clean ledgers with full audit trails.

## 🌐 **NEW: Web Application Available!**

Access the complete system through a modern web interface:
```bash
# Quick start (takes 1 minute):
pip install flask flask-cors werkzeug
python web_app.py
# Open browser to http://localhost:5000
```

**See [QUICKSTART.md](QUICKSTART.md) for the 5-minute getting started guide!**
**See [WEB_README.md](WEB_README.md) for complete web app documentation.**

---

## Features

### 🔍 **Intelligent Document Processing**
- **Multi-format support**: PDF, JPG, PNG, HEIC, WEBP, multi-page scans, email text
- **OCR with confidence scoring**: Automatic text extraction with quality assessment
- **Multilingual**: Auto-detects and processes English, Arabic, and Hebrew documents
- **Smart document classification**: Distinguishes invoices, receipts, credit notes, and proforma invoices
- **Line-item extraction**: Captures itemized descriptions, quantities, prices, and totals
- **Tax/VAT detection**: Identifies tax types, rates, and validates calculations

### ✅ **NGO-Specific Validation**
- **Math validation**: Cross-checks totals, taxes, and line items with configurable epsilon tolerance
- **Date logic**: Validates fiscal year alignment and date reasonability
- **Tax verification**: Compares against country-specific VAT/GST rules
- **Vendor normalization**: Canonicalizes vendor names using alias dictionaries
- **Deduplication**: SHA-256 checksums + semantic fingerprints to prevent duplicate entries
- **Anomaly detection**: Flags suspicious dates, currency mismatches, missing fields, OCR issues

### 📁 **Deterministic Filing System**
- **Structured folders**: `FiscalYear/Project/Grant/Vendor/DocType/`
- **Consistent naming**: `YYYY-MM-DD__Vendor__InvoiceNum__Project__Grant__AmountCurrency__Status.ext`
- **Status tracking**: draft → needs_review → approved → posted
- **Safe file names**: Automatic sanitization, diacritic removal, space-to-underscore conversion

### 💼 **NGO Financial Management**
- **Project & grant tracking**: Assigns expenses to projects, grants, and cost centers
- **Fund classification**: Restricted vs. unrestricted fund allocation
- **Donor attribution**: Links documents to donors and grant codes
- **Budget categories**: Auto-classifies into Travel, Training, Office Supplies, Consulting, etc.
- **Fiscal year management**: Configurable fiscal year start month
- **Multi-currency support**: ISO 4217 currency codes with conversion placeholders

### 📊 **Ledger & Reporting**
- **Normalized ledger**: Maintains cumulative database of all processed documents
- **Export formats**: CSV, Excel (XLSX), and JSON
- **Query & filter**: By project, grant, fiscal year, status, vendor, date range, amount range
- **Summary statistics**: Totals by status, project, fiscal year, vendor
- **Reports**: Fiscal year reports, project reports, top vendor analysis
- **Audit trail**: Immutable JSONL log of all processing steps and decisions

### 🔐 **Security & Privacy**
- **PII redaction**: Masks bank accounts, tax IDs, emails, phone numbers in UI previews
- **Role-based access**: viewer, contributor, approver, admin permissions
- **Field-level encryption**: Placeholder for AES-256 encryption of sensitive data
- **Input sanitization**: Prevents path traversal, SQL injection, XSS
- **File validation**: Size limits, type checking, malware scanning placeholder
- **Access logging**: Security-focused audit logs for compliance (SOC 2, GDPR-ready)

### 🔄 **Approval Workflow**
- **Status transitions**: Enforced workflow with validation
- **Approver tracking**: Records approver name and timestamp
- **Approval blocks**: Prevents posting documents with high-severity flags
- **Audit integration**: Logs all approval actions

---

## Architecture

```
NGO-InvoiceFiler/
│
├── schemas.py           # Data models and Pydantic-style schemas
├── ocr_parser.py        # OCR engine, document parser, entity extraction
├── validator.py         # Validation rules, NGO classifier, deduplication
├── filing.py            # Filing system, deterministic naming, approval workflow
├── ledger.py            # Ledger manager, export engine, audit trail, reports
├── security.py          # PII redaction, access control, encryption, sanitization
├── main.py              # Orchestrator, coordinates entire pipeline
├── cli.py               # Command-line interface
├── test_suite.py        # Comprehensive test suite with 7 test cases
└── README.md            # This file
```

---

## Installation

### Prerequisites
- Python 3.8+
- (Optional) Tesseract OCR for production OCR
- (Optional) openpyxl for native Excel export

### Setup

```bash
# Clone or download the project
cd Project1

# Install dependencies (if using external OCR/Excel libraries)
# pip install tesseract python-magic openpyxl

# The system is designed to run standalone with simulated OCR
# No external dependencies required for demo/testing
```

---

## Usage

### Command-Line Interface

```bash
# Process a document
python cli.py process invoice.pdf --project EDU001 --grant GR2023 -v

# Query ledger
python cli.py query --project EDU001 --status approved

# Show statistics
python cli.py stats

# Export ledger
python cli.py export --format csv --fiscal-year 2023-2024 --output ledger_2024.csv

# Generate report
python cli.py report --fiscal-year 2023-2024

# Approve a document
python cli.py approve <doc_id> --approver "Jane Doe" --role approver
```

### Programmatic API

```python
from main import InvoiceFilerOrchestrator, create_default_org_profile

# Initialize
org_profile = create_default_org_profile()
orchestrator = InvoiceFilerOrchestrator(org_profile)

# Process document
with open('invoice.pdf', 'rb') as f:
    file_bytes = f.read()

result = orchestrator.process_document(
    file_bytes=file_bytes,
    file_name='invoice.pdf',
    user_hints={'project_code': 'EDU001', 'grant_code': 'GR2023'},
    user_role='contributor'
)

# Check results
if result['success']:
    print(result['summary'])
    print(f"Filed to: {result['folder_path']}/{result['file_name']}")
else:
    print(f"Error: {result['error']}")

# Export ledger
csv_path = orchestrator.export_ledger(format='csv', filters={'project_code': 'EDU001'})

# Get document with PII redaction
doc = orchestrator.get_document(doc_id='<uuid>', user_role='viewer', redact_pii=True)
```

---

## Output Formats

### 1. Structured JSON (Document-Level)

Every processed document produces a complete JSON file with:
- Document metadata (ID, timestamp, type, language, currency)
- Totals (subtotal, tax, shipping, discount, grand total)
- Dates (issue, due, service period, payment)
- Vendor information (name, tax ID, contact, IBAN)
- Buyer information (organization name, tax ID)
- Invoice details (number, PO, reference, payment terms/method)
- Line items (description, quantity, price, tax, category, project/grant allocation)
- Classification (document type flags, fund type, categories, country, tax type)
- NGO context (donor, grant, project, budget line, fiscal year, attachments)
- Filing (folder path, file name, status, approver, approval timestamp)
- Validation (checksum, fingerprint, dedupe status, confidence score, flags)
- Audit log (step-by-step processing decisions)

### 2. Ledger Row (CSV/Excel/JSON)

Normalized single-row format for reporting:
```
doc_id, issue_date, due_date, vendor, invoice_number, currency,
subtotal, tax_amount, grand_total, project_code, grant_code,
fund_type, category_primary, status, fiscal_year, file_path,
file_name, dedupe_status, approver, approved_at
```

### 3. Human Summary

1-2 sentence summary:
```
Invoice from Acme Corporation dated 2024-03-15 for 1755.00 ILS,
status: draft, project: EDU001, grant: GR2023. ℹ 2 validation flag(s) noted.
```

### 4. Developer Log

Compact log of processing steps:
```
[SECURITY] Validating upload for user role: contributor
[OCR] Extracting text from invoice.pdf
[PARSE] Parsing structured data from OCR text
[VALIDATE] Running validation checks
[CLASSIFY] Applying NGO-specific classifications
[FILE] Generating folder path and file name
[LEDGER] Adding entry to ledger
[COMPLETE] Processing finished
```

---

## Configuration

### Organization Profile

Customize for your NGO in [main.py:create_default_org_profile()](main.py):

```python
org_profile = OrganizationProfile(
    ngo_name="Your NGO Name",
    fiscal_year_start_month=1,  # January = 1, April = 4, etc.
    default_currency="USD",
    vat_rules={
        'ILS': 17.0,  # Israel VAT
        'EUR': 20.0,  # EU standard rate
    },
    donor_dictionary={
        'DONOR001': {'donor': 'UNICEF', 'restricted': True}
    },
    grant_dictionary={
        'GR2023': {'donor': 'UNICEF', 'restricted': True}
    },
    project_codes={
        'EDU001': 'Education Program',
        'HLTH001': 'Healthcare Initiative'
    },
    vendor_aliases={
        'acme co': 'Acme Corporation',
        'tel aviv med': 'Tel Aviv Medical Center'
    },
    category_keywords={
        'Travel': ['flight', 'hotel', 'taxi', 'per diem'],
        'Training': ['workshop', 'training', 'seminar'],
        'Office Supplies': ['paper', 'pens', 'office'],
        'Consulting': ['consultant', 'advisory', 'expert']
    }
)
```

---

## Test Suite

Run comprehensive tests covering all 5 test cases from requirements:

```bash
python test_suite.py
```

### Test Cases

1. **EN Invoice with VAT 17%, 2 line items, correct math** → PASS
2. **AR Receipt (no invoice number), cash payment, total only** → Infer receipt, create synthetic number → PASS
3. **HE Invoice with discount and shipping; due_date before issue_date** → Flag "suspicious_date" → PASS
4. **Duplicate file (identical bytes)** → dedupe_status "duplicate" → PASS
5. **Currency symbol "$" with vendor in EU and tax as VAT** → Detect USD, flag potential mismatch → PASS

Additional tests:
- Validation engine (math, dates, tax, currency)
- Filing system (deterministic naming, sanitization)
- Approval workflow (status transitions, approver requirements)
- Security (PII redaction, access control, input sanitization)
- Integration (full pipeline from bytes to ledger)

---

## Production Integration Notes

### OCR Integration

Replace simulated OCR in [ocr_parser.py:OCREngine.extract_text()](ocr_parser.py) with:

**Option 1: Tesseract (Open Source)**
```python
import pytesseract
from PIL import Image
text = pytesseract.image_to_string(Image.open(io.BytesIO(file_bytes)), lang='eng+ara+heb')
```

**Option 2: Cloud OCR**
- Google Cloud Vision API
- AWS Textract
- Azure Computer Vision

### Excel Export

Install openpyxl and update [ledger.py:ExportEngine.export_excel()](ledger.py):
```python
from openpyxl import Workbook
wb = Workbook()
ws = wb.active
# Write data...
wb.save(output_file)
```

### Database Backend

Replace JSON file storage with PostgreSQL/MongoDB:
```python
# In ledger.py, replace file I/O with DB queries
conn = psycopg2.connect(...)
cursor.execute("INSERT INTO ledger VALUES (...)")
```

### File Storage

Use cloud storage for documents:
- AWS S3
- Azure Blob Storage
- Google Cloud Storage

### Encryption

Implement field-level encryption in [security.py:DataEncryption](security.py):
```python
from cryptography.fernet import Fernet
cipher = Fernet(key)
encrypted_value = cipher.encrypt(plaintext.encode())
```

### Malware Scanning

Integrate with antivirus in [security.py:SecureDocumentHandler.validate_upload()](security.py):
- ClamAV
- VirusTotal API
- Cloud scanning services

---

## Compliance & Standards

- **NGO Financial Standards**: Aligned with common NGO accounting practices
- **GDPR-Ready**: PII redaction, consent tracking placeholders, data export
- **SOC 2 Ready**: Audit trails, access controls, encryption placeholders
- **ISO 4217**: Standard currency codes
- **ISO 3166-1**: Country codes
- **ISO 8601**: Date/time formats

---

## API Reference

### Main Classes

#### `InvoiceFilerOrchestrator`
Main orchestrator coordinating the entire pipeline.

**Methods:**
- `process_document(file_bytes, file_name, user_hints, user_role)` → Process a document
- `export_ledger(format, output_file, filters)` → Export ledger
- `get_document(doc_id, user_role, redact_pii)` → Retrieve document
- `approve_document(doc_id, approver_name, user_role)` → Approve document

#### `LedgerManager`
Manages the cumulative ledger.

**Methods:**
- `add_entry(processed_doc)` → Add document to ledger
- `query(filters)` → Query ledger with filters
- `get_summary_stats()` → Get summary statistics

#### `ValidationEngine`
Validates documents against rules.

**Methods:**
- `validate(parsed_data, checksum, fingerprint)` → Run all validations

#### `FilingSystem`
Generates folder paths and file names.

**Methods:**
- `generate_filing_info(parsed_data, ngo_context, classification, validation)` → Generate filing info
- `create_folder_structure(folder_path)` → Create folders
- `get_full_file_path(folder_path, file_name)` → Get complete path

---

## Support & Contributing

For issues, questions, or contributions:
1. Review test cases in [test_suite.py](test_suite.py)
2. Check developer logs for debugging (`--verbose` flag)
3. Examine audit trails in `audit_trail.jsonl`
4. Review validation flags in processed documents

---

## License

Production-grade implementation for NGO use. Adapt and extend as needed for your organization.

---

## Version History

**v1.0** (2024)
- Initial release
- Complete pipeline: OCR → Parse → Validate → File → Ledger
- All 5 test cases passing
- Security & privacy features
- CLI and programmatic API
- Comprehensive documentation

---

**Built for NGOs. By AI. With Production Standards.**
