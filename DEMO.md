# NGO-InvoiceFiler Demo Guide

This guide demonstrates the complete capabilities of the NGO-InvoiceFiler system with practical examples.

---

## Quick Start Demo

### 1. Run the Test Suite

```bash
python test_suite.py
```

**Expected Output:**
```
======================================================================
NGO-InvoiceFiler Test Suite
======================================================================

test_parse_invoice_with_vat (__main__.TestDocumentParser) ... ok
test_parse_receipt_no_invoice_number (__main__.TestDocumentParser) ... ok
test_parse_invoice_with_discount_shipping (__main__.TestDocumentParser) ... ok
test_currency_detection (__main__.TestDocumentParser) ... ok
test_math_validation_pass (__main__.TestValidationEngine) ... ok
test_math_validation_fail (__main__.TestValidationEngine) ... ok
test_date_validation_suspicious (__main__.TestValidationEngine) ... ok
test_deterministic_file_naming (__main__.TestFilingSystem) ... ok
test_vendor_name_sanitization (__main__.TestFilingSystem) ... ok
test_status_transitions (__main__.TestApprovalWorkflow) ... ok
test_approval_requires_approver (__main__.TestApprovalWorkflow) ... ok
test_iban_redaction (__main__.TestSecurity) ... ok
test_email_redaction (__main__.TestSecurity) ... ok
test_access_control (__main__.TestSecurity) ... ok
test_filename_sanitization (__main__.TestSecurity) ... ok
test_duplicate_by_checksum (__main__.TestDuplication) ... ok
test_full_processing_pipeline (__main__.TestIntegration) ... ok

======================================================================
Test Summary
======================================================================
Tests run: 17
Successes: 17
Failures: 0
Errors: 0
======================================================================
```

---

## CLI Demo Scenarios

### Scenario 1: Process an Invoice

**Command:**
```bash
python cli.py process sample_invoice.pdf --project EDU001 --grant GR2023 --verbose
```

**Sample Output:**
```
╔══════════════════════════════════════════════════════════════╗
║            NGO-InvoiceFiler v1.0                             ║
║   Invoice & Receipt Processing System for NGOs               ║
║   OCR • Validation • Filing • Ledger Management              ║
╚══════════════════════════════════════════════════════════════╝

📥 Processing: sample_invoice.pdf

✅ PROCESSING COMPLETE
Document ID: 550e8400-e29b-41d4-a716-446655440000

📄 Summary:
   Invoice from Acme Corporation dated 2024-03-15 for 1755.00 ILS,
   status: draft, project: EDU001, grant: GR2023.

📁 Filing:
   Folder: 2023-2024/EDU001-Education/GR2023-UNICEF/acme_corporation/Invoice
   File:   2024-03-15__acme_corporation__INV001__EDU001__GR2023__1755ILS__draft.pdf

🔧 Developer Log:
   [SECURITY] Validating upload for user role: contributor
   [SECURITY] Upload validated, sanitized filename: sample_invoice.pdf
   [HASH] Computing SHA-256 checksum and fingerprint
   [OCR] Extracting text from sample_invoice.pdf
   [OCR] Complete. Confidence=95.00%, Language=en
   [PARSE] Parsing structured data from OCR text
   [PARSE] Fingerprint=a1b2c3d4...
   [VALIDATE] Running validation checks
   [VALIDATE] Complete. Flags: 0 (High=0, Medium=0)
   [CLASSIFY] Applying NGO-specific classifications
   [CLASSIFY] Project=EDU001, Grant=GR2023, Fund=restricted
   [FILE] Generating folder path and file name
   [FILE] Path=2023-2024/EDU001-Education/GR2023-UNICEF/..., Status=draft
   [ASSEMBLE] Building ProcessedDocument object
   [LEDGER] Adding entry to ledger
   [AUDIT] Logged to audit trail
   [EXPORT] Preparing final outputs
   [COMPLETE] Processing finished for doc_id=550e8400...
```

---

### Scenario 2: Query Ledger

**Command:**
```bash
python cli.py query --project EDU001 --status approved
```

**Sample Output:**
```
🔍 Querying ledger...

📊 Results: 3 document(s)

Date         Vendor                    Amount          Project    Status
--------------------------------------------------------------------------------
2024-03-15   Acme Corporation          1755.00 ILS     EDU001     approved
2024-03-20   Jerusalem Restaurant      150.00 ILS      EDU001     approved
2024-04-01   Tech Company Ltd.         6435.00 ILS     EDU001     approved
```

---

### Scenario 3: Export Ledger

**Command:**
```bash
python cli.py export --format csv --fiscal-year 2023-2024 --output ledger_2024.csv
```

**Sample Output:**
```
📤 Exporting ledger to CSV...
✅ Ledger exported to: ledger_2024.csv
   Records: 15
```

**ledger_2024.csv contents:**
```csv
doc_id,issue_date,due_date,vendor,invoice_number,currency,subtotal,tax_amount,grand_total,project_code,grant_code,fund_type,category_primary,status,fiscal_year,file_path,file_name,dedupe_status,approver,approved_at
550e8400-e29b-41d4-a716-446655440000,2024-03-15,2024-04-15,Acme Corporation,INV-2024-001,ILS,1500.00,255.00,1755.00,EDU001,GR2023,restricted,Consulting,approved,2023-2024,2023-2024/EDU001-Education/GR2023-UNICEF/acme_corporation/Invoice,2024-03-15__acme_corporation__INV001__EDU001__GR2023__1755ILS__approved.pdf,unique,Jane Doe,2024-03-16T10:30:00
```

---

### Scenario 4: View Statistics

**Command:**
```bash
python cli.py stats
```

**Sample Output:**
```
📈 Ledger Statistics

Total Documents: 25
Total Amount:    $125,450.75

By Status:
   draft           5 documents
   needs_review    8 documents
   approved        10 documents
   posted          2 documents

By Project:
   EDU001          $45,230.50
   HLTH001         $62,100.25
   WASH001         $18,120.00

By Fiscal Year:
   2023-2024       $95,340.75
   2024-2025       $30,110.00
```

---

### Scenario 5: Generate Report

**Command:**
```bash
python cli.py report --fiscal-year 2023-2024
```

**Sample Output:**
```
📊 Fiscal Year Report: 2023-2024

Summary:
   Total Documents: 20
   Total Amount:    $95,340.75
   Average Amount:  $4,767.04

By Project:
   EDU001          $45,230.50
   HLTH001         $42,100.25
   WASH001         $8,010.00

By Grant:
   GR2023          $62,340.75
   GR2024          $33,000.00

Top 10 Vendors:
   Acme Corporation               $15,450.00
   Tech Company Ltd.              $12,300.50
   Jerusalem Restaurant           $8,650.25
   Office Supplies Inc.           $6,200.00
   Travel Agency XYZ              $5,800.00
   Consultant Group               $5,250.00
   Medical Equipment Co.          $4,890.00
   Training Institute             $3,750.00
   IT Services Ltd.               $2,950.00
   Printing Services              $1,800.00
```

---

### Scenario 6: Approve Document

**Command:**
```bash
python cli.py approve 550e8400-e29b-41d4-a716-446655440000 --approver "Jane Doe" --role approver
```

**Sample Output:**
```
✅ Approving document: 550e8400-e29b-41d4-a716-446655440000
✅ Document approved by Jane Doe
   Status: approved
```

---

## Python API Demo

### Example 1: Basic Processing

```python
from main import InvoiceFilerOrchestrator, create_default_org_profile

# Initialize
org = create_default_org_profile()
filer = InvoiceFilerOrchestrator(org)

# Process
with open('invoice.pdf', 'rb') as f:
    result = filer.process_document(
        file_bytes=f.read(),
        file_name='invoice.pdf',
        user_hints={'project_code': 'EDU001'},
        user_role='contributor'
    )

# Results
print(result['summary'])
# Output: Invoice from Acme Corp dated 2024-03-15 for 1755.00 ILS...

print(f"Confidence: {result['processed_document']['validation']['score_confidence']}")
# Output: Confidence: 0.92

print(f"Filed to: {result['folder_path']}/{result['file_name']}")
# Output: Filed to: 2023-2024/EDU001-Education/.../2024-03-15__acme_corp__...
```

---

### Example 2: Query and Filter

```python
from ledger import LedgerManager

ledger = LedgerManager()

# Query by project and date range
results = ledger.query({
    'project_code': 'EDU001',
    'start_date': '2024-01-01',
    'end_date': '2024-03-31',
    'min_amount': 1000.0
})

for doc in results:
    print(f"{doc['vendor']}: ${doc['grand_total']:.2f}")
```

---

### Example 3: Security and Redaction

```python
from security import PIIRedactor, AccessControl

# Redact PII
vendor = {
    'display_name': 'Acme Corp',
    'tax_id_vat': '123-45-6789',
    'email': 'billing@acme.com',
    'iban': 'IL620108000000099999999'
}

redacted = PIIRedactor.redact_vendor(vendor, for_ui=True)
print(redacted['tax_id_vat'])   # Output: *****6789
print(redacted['email'])        # Output: b***@acme.com
print(redacted['iban'])         # Output: IL6201******9999

# Check permissions
can_approve = AccessControl.check_permission('contributor', 'approve')
print(can_approve)  # Output: False

can_read = AccessControl.check_permission('viewer', 'read')
print(can_read)  # Output: True
```

---

### Example 4: Generate Reports

```python
from ledger import LedgerManager, ReportGenerator

ledger = LedgerManager()
reporter = ReportGenerator(ledger)

# Fiscal year report
report = reporter.generate_fiscal_year_report('2023-2024')

print(f"Total: ${report['summary']['total_amount']:,.2f}")
print("\nTop Vendors:")
for vendor, amount in report['top_vendors'][:5]:
    print(f"  {vendor}: ${amount:,.2f}")

# Project report
proj_report = reporter.generate_project_report('EDU001')
print(f"\nProject EDU001: ${proj_report['total_amount']:,.2f}")
print("Categories:")
for cat, amt in proj_report['by_category'].items():
    print(f"  {cat}: ${amt:,.2f}")
```

---

## Validation Flags Demo

### Example: Document with Flags

When processing a document with validation issues:

```python
result = filer.process_document(...)

if result['processed_document']['validation']['flags']:
    print("\n⚠ Validation Flags:")
    for flag in result['processed_document']['validation']['flags']:
        print(f"  [{flag['severity'].upper()}] {flag['type']}: {flag['message']}")
```

**Sample Output:**
```
⚠ Validation Flags:
  [HIGH] math_mismatch: Grand total 2000.00 != computed 1755.00 (diff: 245.00)
  [HIGH] suspicious_date: Due date 2024-03-25 before issue date 2024-04-01
  [MEDIUM] ocr_low_confidence: OCR confidence 72% below threshold
  [LOW] missing_field: Vendor missing contact information
```

---

## Audit Trail Demo

The system maintains a complete audit trail in `audit_trail.jsonl`:

```json
{"timestamp": "2024-03-15T14:30:00Z", "doc_id": "550e8400...", "event_type": "process_complete", "user": "contributor", "details": {"file_name": "invoice.pdf", "vendor": "Acme Corp", "amount": 1755.0, "status": "draft", "flags": 0}}
{"timestamp": "2024-03-16T10:30:00Z", "doc_id": "550e8400...", "event_type": "approve", "user": "Jane Doe", "details": {"approver": "Jane Doe"}}
```

---

## File Structure Demo

After processing, documents are organized as:

```
invoice_storage/
├── 2023-2024/
│   ├── EDU001-Education/
│   │   ├── GR2023-UNICEF/
│   │   │   ├── acme_corporation/
│   │   │   │   ├── Invoice/
│   │   │   │   │   └── 2024-03-15__acme_corporation__INV001__EDU001__GR2023__1755ILS__approved.pdf
│   │   │   │   └── Receipt/
│   │   │   └── jerusalem_restaurant/
│   │   │       └── Receipt/
│   │   │           └── 2024-03-20__jerusalem_restaurant__NOREF__EDU001__GR2023__150ILS__draft.pdf
│   │   └── NoGrant/
│   └── HLTH001-Healthcare/
└── 2024-2025/
```

---

## Performance Demo

The system handles:
- **Processing speed**: ~1-2 seconds per document (with simulated OCR)
- **Batch processing**: Process multiple documents concurrently
- **Ledger queries**: O(n) linear scan, sub-second for <10,000 documents
- **Export**: CSV generation ~100ms for 1,000 records

---

## Error Handling Demo

### Invalid File Type

```bash
python cli.py process malicious.exe
```

**Output:**
```
❌ PROCESSING FAILED
Error: Invalid file type. Only PDF and images are allowed.
```

### Missing Permissions

```python
result = filer.approve_document(doc_id, approver="John", user_role='viewer')
# Output: {'success': False, 'error': 'User does not have approval permission'}
```

### Math Mismatch

When totals don't match:
```
⚠ Validation Flags:
  [HIGH] math_mismatch: Grand total 2000.00 != computed 1755.00 (diff: 245.00)
Status: needs_review (requires manual review before approval)
```

---

## Next Steps

1. **Customize Configuration**: Edit `create_default_org_profile()` in [main.py](main.py)
2. **Integrate Real OCR**: Replace simulated OCR with Tesseract/Cloud OCR
3. **Add Database**: Replace JSON with PostgreSQL/MongoDB
4. **Deploy API**: Use FastAPI to create REST endpoints
5. **Add UI**: Build web interface with React/Vue for document upload and review
6. **Scale**: Use Celery for async processing of large batches

---

**Ready to process your NGO's invoices with confidence!**
