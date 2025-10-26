"""
NGO-InvoiceFiler: Main Orchestrator
Coordinates the entire document processing pipeline from ingestion to export.
"""

import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from schemas import (
    ProcessedDocument, OrganizationProfile, DocType, Language,
    Totals, Dates, Vendor, Buyer, Invoice, LineItem,
    Classification, NGOContext, Filing, Validation,
    AuditLogEntry, FlagSeverity, DedupeStatus
)
from ocr_parser import DocumentParser, DocumentHasher
from validator import ValidationEngine, NGOClassifier
from filing import FilingSystem, ApprovalWorkflow
from ledger import LedgerManager, ExportEngine, AuditTrailManager
from security import SecureDocumentHandler, InputSanitizer

# Try to import enhanced OCR, fallback to basic OCR
try:
    from ocr_parser_enhanced import EnhancedOCREngine as OCREngine
    ENHANCED_OCR_AVAILABLE = True
except ImportError:
    from ocr_parser import OCREngine
    ENHANCED_OCR_AVAILABLE = False


class InvoiceFilerOrchestrator:
    """
    Main orchestrator that coordinates the entire invoice processing pipeline
    """

    def __init__(self, org_profile: OrganizationProfile, storage_path: str = "invoice_storage",
                 ocr_backend: str = 'tesseract', ai_backend: str = None, api_key: str = None):
        self.org_profile = org_profile
        self.storage_path = storage_path

        # Initialize OCR engine with configuration
        if ENHANCED_OCR_AVAILABLE:
            self.ocr_engine = OCREngine(
                ocr_backend=ocr_backend,
                ai_backend=ai_backend,
                api_key=api_key
            )
            print(f"✓ Enhanced OCR initialized: backend={ocr_backend}, AI={ai_backend or 'none'}")
        else:
            self.ocr_engine = OCREngine()
            print("⚠ Using simulated OCR (enhanced OCR not available)")

        # Initialize other components
        self.parser = DocumentParser(org_profile)
        self.validator = ValidationEngine(org_profile)
        self.classifier = NGOClassifier(org_profile)
        self.filing_system = FilingSystem(org_profile, storage_path)
        self.ledger_manager = LedgerManager("ledger.json")
        self.audit_trail = AuditTrailManager("audit_trail.jsonl")
        self.security_handler = SecureDocumentHandler()

    def process_document(self, file_bytes: bytes, file_name: str,
                        user_hints: Optional[Dict[str, Any]] = None,
                        user_role: str = 'contributor') -> Dict[str, Any]:
        """
        Complete document processing pipeline

        Args:
            file_bytes: Raw file bytes
            file_name: Original file name
            user_hints: Optional hints (project_code, grant_code, etc.)
            user_role: User role for permissions

        Returns: Dict with processed_document, ledger_row, summary, dev_log
        """
        doc_id = str(uuid.uuid4())
        ingest_timestamp = datetime.utcnow()
        user_hints = user_hints or {}

        dev_log = []

        try:
            # Step 1: Security validation
            dev_log.append(f"[SECURITY] Validating upload for user role: {user_role}")
            upload_validation = self.security_handler.validate_upload(
                file_bytes, file_name, user_role
            )

            if not upload_validation['valid']:
                return self._create_error_response(
                    doc_id, ingest_timestamp, upload_validation['message'], dev_log
                )

            safe_filename = upload_validation['sanitized_filename']
            dev_log.append(f"[SECURITY] Upload validated, sanitized filename: {safe_filename}")

            # Step 2: Compute checksums
            dev_log.append("[HASH] Computing SHA-256 checksum and fingerprint")
            checksum = DocumentHasher.compute_sha256(file_bytes)

            # Step 3: OCR extraction
            dev_log.append(f"[OCR] Extracting text from {safe_filename}")
            ocr_text, ocr_confidence, detected_lang = self.ocr_engine.extract_text(
                file_bytes, language='auto'
            )
            dev_log.append(
                f"[OCR] Complete. Confidence={ocr_confidence:.2%}, Language={detected_lang}"
            )

            # Step 3.5: AI Enhancement (if configured)
            ai_data = None
            if ENHANCED_OCR_AVAILABLE and hasattr(self.ocr_engine, 'enhance_with_ai'):
                if self.ocr_engine.ai_client:
                    dev_log.append("[AI] Enhancing extraction with AI...")
                    ai_data = self.ocr_engine.enhance_with_ai(ocr_text, file_bytes)
                    if ai_data.get('success'):
                        dev_log.append("[AI] AI extraction successful, using AI-parsed data")
                    else:
                        dev_log.append(f"[AI] AI extraction failed: {ai_data.get('error')}, using regex parsing")
                        ai_data = None

            # Step 4: Parse document (with AI data if available)
            dev_log.append("[PARSE] Parsing structured data from OCR text")
            parsed_data = self.parser.parse_document(ocr_text, safe_filename, ocr_confidence, ai_data)
            parsed_data['file_name'] = safe_filename

            # Compute semantic fingerprint
            fingerprint = DocumentHasher.compute_fingerprint(
                vendor=parsed_data['vendor']['display_name'],
                date=parsed_data['dates'].get('issue_date'),
                invoice_num=parsed_data['invoice'].get('number'),
                amount=parsed_data['amounts']['grand_total']
            )
            dev_log.append(f"[PARSE] Fingerprint={fingerprint[:8]}...")

            # Step 5: Validate
            dev_log.append("[VALIDATE] Running validation checks")
            existing_docs = self.ledger_manager.get_all_entries()
            validation_results = self.validator.validate(
                parsed_data, checksum, fingerprint
            )

            high_flags = sum(
                1 for f in validation_results['flags']
                if f.severity == FlagSeverity.HIGH
            )
            medium_flags = sum(
                1 for f in validation_results['flags']
                if f.severity == FlagSeverity.MEDIUM
            )
            dev_log.append(
                f"[VALIDATE] Complete. Flags: {len(validation_results['flags'])} "
                f"(High={high_flags}, Medium={medium_flags})"
            )

            # Step 6: Classify (NGO-specific)
            dev_log.append("[CLASSIFY] Applying NGO-specific classifications")
            classification_results = self.classifier.classify(parsed_data, user_hints)
            dev_log.append(
                f"[CLASSIFY] Project={classification_results['ngo_context']['project_code']}, "
                f"Grant={classification_results['ngo_context']['grant_code']}, "
                f"Fund={classification_results['classification']['fund_type']}"
            )

            # Step 7: Filing
            dev_log.append("[FILE] Generating folder path and file name")
            filing_info = self.filing_system.generate_filing_info(
                parsed_data,
                classification_results['ngo_context'],
                classification_results['classification'],
                validation_results
            )
            dev_log.append(
                f"[FILE] Path={filing_info['folder_path'][:50]}..., "
                f"Status={filing_info['status'].value}"
            )

            # Step 8: Assemble complete document
            dev_log.append("[ASSEMBLE] Building ProcessedDocument object")
            processed_doc = self._assemble_processed_document(
                doc_id, ingest_timestamp, parsed_data, classification_results,
                filing_info, validation_results
            )

            # Step 9: Update ledger
            dev_log.append("[LEDGER] Adding entry to ledger")
            ledger_row = self.ledger_manager.add_entry(processed_doc)

            # Step 10: Audit trail
            self.audit_trail.log_event(
                doc_id=doc_id,
                event_type='process_complete',
                details={
                    'file_name': safe_filename,
                    'vendor': parsed_data['vendor']['display_name'],
                    'amount': parsed_data['amounts']['grand_total'],
                    'status': filing_info['status'].value,
                    'flags': len(validation_results['flags'])
                },
                user=user_role
            )
            dev_log.append("[AUDIT] Logged to audit trail")

            # Step 11: Generate outputs
            dev_log.append("[EXPORT] Preparing final outputs")

            # Save document JSON
            doc_json_path = f"output/{doc_id}.json"
            Path("output").mkdir(exist_ok=True)
            ExportEngine.export_document_json(processed_doc, doc_json_path)

            # Generate human summary
            summary = self._generate_human_summary(processed_doc)

            dev_log.append(f"[COMPLETE] Processing finished for doc_id={doc_id}")

            return {
                'success': True,
                'doc_id': doc_id,
                'processed_document': processed_doc.to_dict(),
                'ledger_row': ledger_row.to_dict(),
                'folder_path': filing_info['folder_path'],
                'file_name': filing_info['file_name'],
                'summary': summary,
                'dev_log': dev_log
            }

        except Exception as e:
            dev_log.append(f"[ERROR] Processing failed: {str(e)}")
            return self._create_error_response(doc_id, ingest_timestamp, str(e), dev_log)

    def _assemble_processed_document(self, doc_id: str, ingest_timestamp: datetime,
                                    parsed_data: Dict, classification_results: Dict,
                                    filing_info: Dict, validation_results: Dict) -> ProcessedDocument:
        """Assemble all components into ProcessedDocument"""

        # Build all sub-components
        totals = Totals(**parsed_data['amounts'])

        dates = Dates(**parsed_data['dates'])

        vendor = Vendor(**parsed_data['vendor'])

        buyer = Buyer(
            org_name=self.org_profile.ngo_name,
            tax_id_vat=None,
            address=None
        )

        invoice = Invoice(**parsed_data['invoice'])

        line_items = [LineItem(**item) for item in parsed_data['line_items']]

        classification = Classification(**classification_results['classification'])

        ngo_context = NGOContext(**classification_results['ngo_context'])

        # Extract audit_log before creating Filing object (Filing doesn't accept audit_log)
        filing_info_copy = {k: v for k, v in filing_info.items() if k != 'audit_log'}
        filing = Filing(**filing_info_copy)

        # Extract audit_log before creating Validation object (Validation doesn't accept audit_log)
        validation_results_copy = {k: v for k, v in validation_results.items() if k != 'audit_log'}
        validation = Validation(**validation_results_copy)

        # Collect all audit entries
        audit_log = []
        audit_log.extend(parsed_data.get('audit_log', []))
        audit_log.extend(validation_results.get('audit_log', []))
        audit_log.extend(filing_info.get('audit_log', []))

        return ProcessedDocument(
            doc_id=doc_id,
            ingest_timestamp=ingest_timestamp,
            doc_type=parsed_data['doc_type'],
            language=Language.EN,  # Would use detected language
            currency=parsed_data['currency'],
            totals=totals,
            dates=dates,
            vendor=vendor,
            buyer=buyer,
            invoice=invoice,
            line_items=line_items,
            classification=classification,
            ngo_context=ngo_context,
            filing=filing,
            validation=validation,
            audit_log=audit_log
        )

    def _generate_human_summary(self, doc: ProcessedDocument) -> str:
        """Generate 1-2 sentence human-readable summary"""
        vendor = doc.vendor.display_name
        amount = f"{doc.totals.grand_total:.2f} {doc.currency}"
        date_str = doc.dates.issue_date.strftime('%Y-%m-%d') if doc.dates.issue_date else 'unknown date'
        status = doc.filing.status.value
        project = doc.ngo_context.project_code or 'unassigned'
        grant = doc.ngo_context.grant_code or 'unassigned'

        flag_count = len(doc.validation.flags)
        flag_note = ""
        if flag_count > 0:
            high_count = sum(1 for f in doc.validation.flags if f.severity == FlagSeverity.HIGH)
            if high_count > 0:
                flag_note = f" ⚠ {high_count} high-priority flag(s) require attention."
            else:
                flag_note = f" ℹ {flag_count} validation flag(s) noted."

        summary = (
            f"{doc.doc_type.value.title()} from {vendor} dated {date_str} "
            f"for {amount}, status: {status}, project: {project}, grant: {grant}.{flag_note}"
        )

        return summary

    def _create_error_response(self, doc_id: str, ingest_timestamp: datetime,
                              error_msg: str, dev_log: List[str]) -> Dict[str, Any]:
        """Create error response when processing fails"""
        from schemas import FlagType, FlagSeverity, ValidationFlag, Status

        # Create minimal failed document
        error_doc = ProcessedDocument(
            doc_id=doc_id,
            ingest_timestamp=ingest_timestamp,
            doc_type=DocType.OTHER,
            language=Language.AUTO,
            currency=self.org_profile.default_currency,
            totals=Totals(subtotal=0, tax_amount=0, grand_total=0),
            dates=Dates(),
            vendor=Vendor(display_name="Unknown Vendor"),
            buyer=Buyer(org_name=self.org_profile.ngo_name),
            invoice=Invoice(),
            line_items=[],
            classification=Classification(),
            ngo_context=NGOContext(fiscal_year="Unknown"),
            filing=Filing(
                folder_path="Errors",
                file_name=f"ERROR_{doc_id}.pdf",
                status=Status.NEEDS_REVIEW
            ),
            validation=Validation(
                checksum_sha256="",
                doc_fingerprint="",
                dedupe_status=DedupeStatus.UNIQUE,
                score_confidence=0.0,
                flags=[ValidationFlag(
                    type=FlagType.PARSE_FAILED,
                    severity=FlagSeverity.HIGH,
                    message=error_msg,
                    field="document"
                )]
            ),
            audit_log=[AuditLogEntry(step="error", detail=error_msg)]
        )

        return {
            'success': False,
            'doc_id': doc_id,
            'error': error_msg,
            'processed_document': error_doc.to_dict(),
            'ledger_row': None,
            'folder_path': "Errors",
            'file_name': f"ERROR_{doc_id}.pdf",
            'summary': f"Processing failed: {error_msg}",
            'dev_log': dev_log
        }

    def export_ledger(self, format: str = 'csv', output_file: Optional[str] = None,
                     filters: Optional[Dict] = None) -> str:
        """
        Export ledger in specified format

        Args:
            format: 'csv', 'xlsx', or 'json'
            output_file: Output file path (auto-generated if None)
            filters: Optional filters for query

        Returns: Path to exported file
        """
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"ledger_export_{timestamp}.{format}"

        entries = self.ledger_manager.query(filters)

        if format == 'csv':
            return ExportEngine.export_csv(entries, output_file)
        elif format == 'xlsx':
            return ExportEngine.export_excel(entries, output_file)
        elif format == 'json':
            return ExportEngine.export_json(entries, output_file)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def get_document(self, doc_id: str, user_role: str = 'viewer',
                    redact_pii: bool = True) -> Optional[Dict[str, Any]]:
        """
        Retrieve document by ID with appropriate security

        Args:
            doc_id: Document ID
            user_role: User's role
            redact_pii: Whether to redact PII for UI

        Returns: Document dict or None if not found/unauthorized
        """
        # Check if document exists in ledger
        entry = self.ledger_manager.get_entry_by_id(doc_id)
        if not entry:
            return None

        # Try to load full document from JSON file
        doc_json_path = Path(f"output/{doc_id}.json")
        if doc_json_path.exists():
            try:
                with open(doc_json_path, 'r', encoding='utf-8') as f:
                    full_doc = json.load(f)

                if redact_pii:
                    return self.security_handler.prepare_for_ui(full_doc, user_role)
                else:
                    return self.security_handler.prepare_for_export(
                        full_doc, user_role, include_pii=True
                    )
            except Exception as e:
                print(f"Error loading document JSON: {e}")
                # Fall back to ledger entry
                pass

        # Fallback to ledger entry if JSON not available
        if redact_pii:
            return self.security_handler.prepare_for_ui(entry, user_role)
        else:
            return self.security_handler.prepare_for_export(
                entry, user_role, include_pii=True
            )

    def approve_document(self, doc_id: str, approver_name: str,
                        user_role: str = 'approver') -> Dict[str, Any]:
        """
        Approve a document

        Args:
            doc_id: Document ID
            approver_name: Name of approver
            user_role: User's role

        Returns: Updated document or error
        """
        from security import AccessControl

        if not AccessControl.can_approve(user_role):
            return {
                'success': False,
                'error': 'User does not have approval permission'
            }

        # Get document
        entry = self.ledger_manager.get_entry_by_id(doc_id)
        if not entry:
            return {
                'success': False,
                'error': 'Document not found'
            }

        # Transition status
        try:
            from schemas import Status
            # Simplified - would need to reload full ProcessedDocument
            # For now, just update ledger entry
            entry['status'] = Status.APPROVED.value
            entry['approver'] = approver_name
            entry['approved_at'] = datetime.utcnow().isoformat()

            # Log audit event
            self.audit_trail.log_event(
                doc_id=doc_id,
                event_type='approve',
                details={'approver': approver_name},
                user=approver_name
            )

            return {
                'success': True,
                'doc_id': doc_id,
                'status': entry['status'],
                'approver': approver_name
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


def create_default_org_profile() -> OrganizationProfile:
    """Create a default organization profile for demo/testing"""
    return OrganizationProfile(
        ngo_name="Demo NGO",
        fiscal_year_start_month=1,
        default_currency="USD",
        vat_rules={
            'ILS': 17.0,
            'EUR': 20.0,
            'GBP': 20.0
        },
        donor_dictionary={
            'GR2023': {'donor': 'UNICEF', 'restricted': True},
            'GR2024': {'donor': 'World Bank', 'restricted': True}
        },
        grant_dictionary={
            'GR2023': {'donor': 'UNICEF', 'restricted': True},
            'GR2024': {'donor': 'World Bank', 'restricted': True}
        },
        project_codes={
            'EDU001': 'Education Program',
            'HLTH001': 'Healthcare Initiative',
            'WASH001': 'Water and Sanitation'
        },
        cost_centers=['Admin', 'Programs', 'Operations'],
        vendor_aliases={
            'tel aviv med ctr': 'Tel Aviv Medical Center',
            'acme co': 'Acme Corporation'
        },
        category_keywords={
            'Travel': ['flight', 'hotel', 'taxi', 'transportation', 'per diem'],
            'Training': ['workshop', 'training', 'seminar', 'course'],
            'Office Supplies': ['paper', 'pens', 'office', 'supplies', 'stationery'],
            'Consulting': ['consultant', 'consulting', 'advisory', 'expert'],
            'Equipment': ['computer', 'laptop', 'equipment', 'hardware'],
        }
    )
