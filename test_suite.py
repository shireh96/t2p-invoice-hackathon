"""
NGO-InvoiceFiler: Test Suite
Comprehensive tests for all components with sample documents.
"""

import unittest
from datetime import date, datetime
from pathlib import Path

from schemas import (
    DocType, Language, Status, FundType, FlagType, FlagSeverity,
    OrganizationProfile
)
from ocr_parser import DocumentParser, DocumentHasher
from validator import ValidationEngine, NGOClassifier
from filing import FilingSystem, ApprovalWorkflow
from ledger import LedgerManager
from security import PIIRedactor, AccessControl, InputSanitizer
from main import InvoiceFilerOrchestrator, create_default_org_profile


class TestDocumentParser(unittest.TestCase):
    """Test OCR and parsing functionality"""

    def setUp(self):
        self.org_profile = create_default_org_profile()
        self.parser = DocumentParser(self.org_profile)

    def test_parse_invoice_with_vat(self):
        """Test Case 1: EN Invoice with VAT 17%, 2 line items, correct math"""
        sample_text = """
        Acme Corporation
        123 Main Street, Tel Aviv, Israel
        VAT: IL123456789
        Email: billing@acme.com

        INVOICE #INV-2024-001
        Date: 2024-03-15
        Due Date: 2024-04-15

        Description          Qty    Unit Price    Total
        Consulting Services  10     100.00        1000.00
        Software License     1      500.00        500.00

        Subtotal:                               1500.00
        VAT (17%):                               255.00
        Grand Total:                            1755.00
        """

        parsed = self.parser.parse_document(sample_text, "invoice.pdf", confidence=0.95)

        self.assertEqual(parsed['doc_type'], DocType.INVOICE)
        self.assertEqual(parsed['vendor']['display_name'], 'Acme Corporation')
        self.assertEqual(parsed['invoice']['number'], 'INV-2024-001')
        self.assertEqual(parsed['amounts']['subtotal'], 1500.00)
        self.assertEqual(parsed['amounts']['tax_amount'], 255.00)
        self.assertEqual(parsed['amounts']['grand_total'], 1755.00)
        self.assertEqual(len(parsed['line_items']), 2)

    def test_parse_receipt_no_invoice_number(self):
        """Test Case 2: AR Receipt (no invoice number), cash payment, total only"""
        sample_text = """
        مطعم القدس
        Jerusalem Restaurant

        إيصال / RECEIPT
        التاريخ: 2024-03-20
        Date: 2024-03-20

        المبلغ الإجمالي: 150.00 ILS
        Total Amount: 150.00 ILS

        الدفع نقداً / Cash Payment
        شكراً لزيارتكم / Thank you
        """

        parsed = self.parser.parse_document(sample_text, "receipt.pdf", confidence=0.90)

        self.assertEqual(parsed['doc_type'], DocType.RECEIPT)
        self.assertIsNone(parsed['invoice']['number'])
        # Would infer cash payment
        self.assertEqual(parsed['amounts']['grand_total'], 150.00)

    def test_parse_invoice_with_discount_shipping(self):
        """Test Case 3: HE Invoice with discount and shipping; due_date before issue_date"""
        sample_text = """
        חברת טכנולוגיה בע"מ
        Tech Company Ltd.

        חשבונית מס / Tax Invoice #2024-HE-100

        תאריך הנפקה: 2024-04-01
        Issue Date: 2024-04-01
        תאריך פירעון: 2024-03-25
        Due Date: 2024-03-25

        פריט                    כמות    מחיר    סה"כ
        מחשב נייד               2       3000    6000.00

        סכום ביניים:                           6000.00
        הנחה:                                   600.00
        משלוח:                                  100.00
        מע"מ (17%):                             935.00
        סה"כ לתשלום:                           6435.00 ILS
        """

        parsed = self.parser.parse_document(sample_text, "invoice_he.pdf", confidence=0.88)

        self.assertEqual(parsed['doc_type'], DocType.INVOICE)
        self.assertEqual(parsed['amounts']['discount'], 600.00)
        self.assertEqual(parsed['amounts']['shipping'], 100.00)

        # Dates should trigger flag in validation
        issue = parsed['dates']['issue_date']
        due = parsed['dates']['due_date']
        if issue and due:
            self.assertLess(due, issue)  # Suspicious!

    def test_currency_detection(self):
        """Test Case 5: Currency symbol $ with vendor in EU and tax as VAT"""
        sample_text = """
        European Supplier GmbH
        Berlin, Germany
        VAT: DE987654321

        Invoice #EU-2024-500
        Date: 2024-03-10

        Item                    Amount
        Consulting              $2,500.00

        Subtotal:               $2,500.00
        VAT (20%):              $500.00
        Total:                  $3,000.00
        """

        parsed = self.parser.parse_document(sample_text, "invoice_eu.pdf", confidence=0.92)

        # Should detect $ symbol -> USD
        self.assertEqual(parsed['currency'], 'USD')
        # But might flag currency mismatch in validation


class TestValidationEngine(unittest.TestCase):
    """Test validation rules"""

    def setUp(self):
        self.org_profile = create_default_org_profile()
        self.org_profile.vat_rules['ILS'] = 17.0
        self.validator = ValidationEngine(self.org_profile)

    def test_math_validation_pass(self):
        """Test correct math validation"""
        parsed_data = {
            'amounts': {
                'subtotal': 1500.00,
                'tax_amount': 255.00,
                'shipping': 0.0,
                'discount': 0.0,
                'grand_total': 1755.00,
                'tax_rate': 17.0
            },
            'line_items': [
                {'total': 1000.00},
                {'total': 500.00}
            ],
            'dates': {'issue_date': date(2024, 3, 15), 'due_date': date(2024, 4, 15)},
            'vendor': {'display_name': 'Test Vendor'},
            'currency': 'ILS',
            'confidence': 0.95
        }

        result = self.validator.validate(parsed_data, 'checksum123', 'fingerprint123')

        # Should have no math mismatch flags
        math_flags = [f for f in result['flags'] if f.type == FlagType.MATH_MISMATCH]
        self.assertEqual(len(math_flags), 0)

    def test_math_validation_fail(self):
        """Test math mismatch detection"""
        parsed_data = {
            'amounts': {
                'subtotal': 1500.00,
                'tax_amount': 255.00,
                'shipping': 0.0,
                'discount': 0.0,
                'grand_total': 2000.00,  # Wrong!
                'tax_rate': 17.0
            },
            'line_items': [],
            'dates': {'issue_date': date(2024, 3, 15), 'due_date': date(2024, 4, 15)},
            'vendor': {'display_name': 'Test Vendor'},
            'currency': 'ILS',
            'confidence': 0.95
        }

        result = self.validator.validate(parsed_data, 'checksum123', 'fingerprint123')

        # Should have math mismatch flag
        math_flags = [f for f in result['flags'] if f.type == FlagType.MATH_MISMATCH]
        self.assertGreater(len(math_flags), 0)
        self.assertEqual(math_flags[0].severity, FlagSeverity.HIGH)

    def test_date_validation_suspicious(self):
        """Test suspicious date detection (due before issue)"""
        parsed_data = {
            'amounts': {
                'subtotal': 100.00,
                'tax_amount': 0.0,
                'shipping': 0.0,
                'discount': 0.0,
                'grand_total': 100.00
            },
            'line_items': [],
            'dates': {
                'issue_date': date(2024, 4, 1),
                'due_date': date(2024, 3, 25)  # Before issue date!
            },
            'vendor': {'display_name': 'Test Vendor'},
            'currency': 'USD',
            'confidence': 0.95
        }

        result = self.validator.validate(parsed_data, 'checksum456', 'fingerprint456')

        # Should have suspicious date flag
        date_flags = [f for f in result['flags'] if f.type == FlagType.SUSPICIOUS_DATE]
        self.assertGreater(len(date_flags), 0)
        self.assertEqual(date_flags[0].severity, FlagSeverity.HIGH)


class TestFilingSystem(unittest.TestCase):
    """Test filing and naming"""

    def setUp(self):
        self.org_profile = create_default_org_profile()
        self.filing_system = FilingSystem(self.org_profile)

    def test_deterministic_file_naming(self):
        """Test deterministic file name generation"""
        parsed_data = {
            'doc_type': DocType.INVOICE,
            'vendor': {'display_name': 'Acme Corp'},
            'invoice': {'number': 'INV-001'},
            'dates': {'issue_date': date(2024, 3, 15)},
            'amounts': {'grand_total': 1500.00},
            'currency': 'USD'
        }

        ngo_context = {
            'fiscal_year': '2023-2024',
            'project_code': 'EDU001',
            'grant_code': 'GR2023'
        }

        classification = {
            'is_invoice': True,
            'fund_type': FundType.RESTRICTED
        }

        validation = {
            'flags': []
        }

        filing_info = self.filing_system.generate_filing_info(
            parsed_data, ngo_context, classification, validation
        )

        # Check folder path structure
        self.assertIn('2023-2024', filing_info['folder_path'])
        self.assertIn('EDU001', filing_info['folder_path'])
        self.assertIn('GR2023', filing_info['folder_path'])

        # Check file name format
        file_name = filing_info['file_name']
        self.assertTrue(file_name.startswith('2024-03-15'))
        self.assertIn('acme_corp', file_name.lower())
        self.assertIn('inv001', file_name.lower())
        self.assertIn('1500USD', file_name)

    def test_vendor_name_sanitization(self):
        """Test vendor name sanitization for file system"""
        test_name = "Tel-Aviv Med. Ctr. / Healthcare"
        sanitized = self.filing_system._sanitize_name(test_name)

        # Should remove special chars, lowercase, no spaces
        self.assertNotIn('/', sanitized)
        self.assertNotIn('.', sanitized)
        self.assertNotIn(' ', sanitized)
        self.assertEqual(sanitized, sanitized.lower())


class TestApprovalWorkflow(unittest.TestCase):
    """Test approval workflow"""

    def test_status_transitions(self):
        """Test valid status transitions"""
        self.assertTrue(ApprovalWorkflow.can_transition(Status.DRAFT, Status.NEEDS_REVIEW))
        self.assertTrue(ApprovalWorkflow.can_transition(Status.NEEDS_REVIEW, Status.APPROVED))
        self.assertTrue(ApprovalWorkflow.can_transition(Status.APPROVED, Status.POSTED))

        # Invalid transitions
        self.assertFalse(ApprovalWorkflow.can_transition(Status.POSTED, Status.DRAFT))
        self.assertFalse(ApprovalWorkflow.can_transition(Status.DRAFT, Status.POSTED))

    def test_approval_requires_approver(self):
        """Test that approval requires approver name"""
        filing_info = {
            'status': Status.NEEDS_REVIEW,
            'file_name': '2024-03-15__vendor__inv__proj__grant__100USD__needs_review.pdf'
        }

        # Should raise error without approver
        with self.assertRaises(ValueError):
            ApprovalWorkflow.transition(filing_info, Status.APPROVED, approver=None)

        # Should succeed with approver
        updated = ApprovalWorkflow.transition(filing_info, Status.APPROVED, approver="John Doe")
        self.assertEqual(updated['status'], Status.APPROVED)
        self.assertEqual(updated['approver'], "John Doe")
        self.assertIsNotNone(updated['approved_at'])


class TestSecurity(unittest.TestCase):
    """Test security and privacy features"""

    def test_iban_redaction(self):
        """Test IBAN redaction"""
        iban = "IL620108000000099999999"
        redacted = PIIRedactor.redact_iban(iban)

        self.assertTrue(redacted.startswith("IL6201"))
        self.assertTrue(redacted.endswith("9999"))
        self.assertIn("*", redacted)

    def test_email_redaction(self):
        """Test email redaction"""
        email = "john.doe@example.com"
        redacted = PIIRedactor.redact_email(email)

        self.assertTrue(redacted.startswith("j"))
        self.assertIn("@example.com", redacted)
        self.assertIn("*", redacted)

    def test_access_control(self):
        """Test role-based permissions"""
        # Viewer can read only
        self.assertTrue(AccessControl.check_permission('viewer', 'read'))
        self.assertFalse(AccessControl.check_permission('viewer', 'approve'))

        # Approver can approve
        self.assertTrue(AccessControl.check_permission('approver', 'approve'))

        # Admin can do everything
        self.assertTrue(AccessControl.check_permission('admin', 'delete'))
        self.assertTrue(AccessControl.check_permission('admin', 'export'))

    def test_filename_sanitization(self):
        """Test malicious filename sanitization"""
        malicious = "../../../etc/passwd"
        sanitized = InputSanitizer.sanitize_filename(malicious)

        self.assertNotIn("..", sanitized)
        self.assertNotIn("/", sanitized)
        self.assertNotIn("\\", sanitized)


class TestDuplication(unittest.TestCase):
    """Test Case 4: Duplicate detection"""

    def setUp(self):
        self.org_profile = create_default_org_profile()
        self.validator = ValidationEngine(self.org_profile)

    def test_duplicate_by_checksum(self):
        """Test exact duplicate detection by SHA-256"""
        checksum = "abc123"
        fingerprint = "fp123"

        existing_docs = [
            {'checksum_sha256': checksum, 'doc_id': 'doc-001'}
        ]

        validator = ValidationEngine(self.org_profile, existing_docs)

        parsed_data = {
            'amounts': {'subtotal': 100, 'tax_amount': 0, 'grand_total': 100,
                       'shipping': None, 'discount': None},
            'line_items': [],
            'dates': {'issue_date': date.today()},
            'vendor': {'display_name': 'Test'},
            'currency': 'USD',
            'confidence': 0.9
        }

        result = validator.validate(parsed_data, checksum, fingerprint)

        from schemas import DedupeStatus
        self.assertEqual(result['dedupe_status'], DedupeStatus.DUPLICATE)

        # Should have duplicate flag
        dup_flags = [f for f in result['flags'] if f.type == FlagType.DUPLICATE]
        self.assertGreater(len(dup_flags), 0)


class TestIntegration(unittest.TestCase):
    """Integration tests for full pipeline"""

    def setUp(self):
        self.org_profile = create_default_org_profile()
        self.orchestrator = InvoiceFilerOrchestrator(self.org_profile)

    def test_full_processing_pipeline(self):
        """Test complete document processing from bytes to ledger"""
        # Simulate a PDF file (placeholder bytes)
        sample_bytes = b"%PDF-1.4\nSample invoice content"
        file_name = "test_invoice.pdf"

        user_hints = {
            'project_code': 'EDU001',
            'grant_code': 'GR2023'
        }

        result = self.orchestrator.process_document(
            file_bytes=sample_bytes,
            file_name=file_name,
            user_hints=user_hints,
            user_role='contributor'
        )

        # Should succeed (even with simulated OCR)
        self.assertTrue(result['success'])
        self.assertIsNotNone(result['doc_id'])
        self.assertIn('processed_document', result)
        self.assertIn('ledger_row', result)
        self.assertIn('summary', result)
        self.assertIn('dev_log', result)

        # Check ledger was updated
        doc_id = result['doc_id']
        ledger_entry = self.orchestrator.ledger_manager.get_entry_by_id(doc_id)
        self.assertIsNotNone(ledger_entry)


def run_test_suite():
    """Run all tests and print summary"""
    print("\n" + "="*70)
    print("NGO-InvoiceFiler Test Suite")
    print("="*70 + "\n")

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestDocumentParser))
    suite.addTests(loader.loadTestsFromTestCase(TestValidationEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestFilingSystem))
    suite.addTests(loader.loadTestsFromTestCase(TestApprovalWorkflow))
    suite.addTests(loader.loadTestsFromTestCase(TestSecurity))
    suite.addTests(loader.loadTestsFromTestCase(TestDuplication))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*70)
    print("Test Summary")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("="*70 + "\n")

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_test_suite()
    exit(0 if success else 1)
