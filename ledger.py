"""
NGO-InvoiceFiler: Ledger Management and Export System
Maintains normalized ledger, exports to CSV/Excel/JSON, manages audit trail.
"""

import csv
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from schemas import LedgerRow, ProcessedDocument, AuditLogEntry


class LedgerManager:
    """Manage cumulative ledger of all processed documents"""

    def __init__(self, ledger_file: str = "ledger.json"):
        self.ledger_file = Path(ledger_file)
        self.ledger: List[Dict[str, Any]] = []
        self._load_ledger()

    def _load_ledger(self):
        """Load existing ledger from disk"""
        if self.ledger_file.exists():
            with open(self.ledger_file, 'r', encoding='utf-8') as f:
                self.ledger = json.load(f)

    def _save_ledger(self):
        """Save ledger to disk"""
        with open(self.ledger_file, 'w', encoding='utf-8') as f:
            json.dump(self.ledger, f, indent=2, ensure_ascii=False)

    def add_entry(self, processed_doc: ProcessedDocument) -> LedgerRow:
        """
        Add a new document to the ledger

        Returns: LedgerRow object
        """
        # Create ledger row from processed document
        ledger_row = self._create_ledger_row(processed_doc)

        # Check if document already exists (update vs insert)
        existing_idx = None
        for idx, entry in enumerate(self.ledger):
            if entry['doc_id'] == processed_doc.doc_id:
                existing_idx = idx
                break

        row_dict = ledger_row.to_dict()

        if existing_idx is not None:
            # Update existing entry
            self.ledger[existing_idx] = row_dict
        else:
            # Insert new entry
            self.ledger.append(row_dict)

        # Save to disk
        self._save_ledger()

        return ledger_row

    def _create_ledger_row(self, doc: ProcessedDocument) -> LedgerRow:
        """Convert ProcessedDocument to LedgerRow"""
        # Get primary category from line items
        category_primary = None
        if doc.line_items:
            categories = [item.category for item in doc.line_items if item.category]
            if categories:
                # Use most common category
                category_primary = max(set(categories), key=categories.count)

        return LedgerRow(
            doc_id=doc.doc_id,
            issue_date=doc.dates.issue_date.isoformat() if doc.dates.issue_date else None,
            due_date=doc.dates.due_date.isoformat() if doc.dates.due_date else None,
            vendor=doc.vendor.display_name,
            invoice_number=doc.invoice.number,
            currency=doc.currency,
            subtotal=doc.totals.subtotal,
            tax_amount=doc.totals.tax_amount,
            grand_total=doc.totals.grand_total,
            project_code=doc.ngo_context.project_code,
            grant_code=doc.ngo_context.grant_code,
            fund_type=doc.classification.fund_type.value if doc.classification.fund_type else None,
            category_primary=category_primary,
            status=doc.filing.status.value,
            fiscal_year=doc.ngo_context.fiscal_year,
            file_path=doc.filing.folder_path,
            file_name=doc.filing.file_name,
            dedupe_status=doc.validation.dedupe_status.value,
            approver=doc.filing.approver,
            approved_at=doc.filing.approved_at.isoformat() if doc.filing.approved_at else None
        )

    def get_all_entries(self) -> List[Dict[str, Any]]:
        """Get all ledger entries"""
        return self.ledger.copy()

    def get_entry_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get specific ledger entry by document ID"""
        for entry in self.ledger:
            if entry['doc_id'] == doc_id:
                return entry.copy()
        return None

    def query(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Query ledger with filters

        Example filters:
        {
            'fiscal_year': '2023-2024',
            'project_code': 'EDU001',
            'status': 'approved',
            'min_amount': 100.0,
            'max_amount': 5000.0
        }
        """
        if not filters:
            return self.get_all_entries()

        results = []
        for entry in self.ledger:
            match = True

            # String equality filters
            for key in ['fiscal_year', 'project_code', 'grant_code', 'vendor', 'status', 'fund_type']:
                if key in filters and entry.get(key) != filters[key]:
                    match = False
                    break

            # Amount range filters
            if 'min_amount' in filters and entry.get('grand_total', 0) < filters['min_amount']:
                match = False
            if 'max_amount' in filters and entry.get('grand_total', float('inf')) > filters['max_amount']:
                match = False

            # Date range filters
            if 'start_date' in filters:
                entry_date = entry.get('issue_date')
                if not entry_date or entry_date < filters['start_date']:
                    match = False

            if 'end_date' in filters:
                entry_date = entry.get('issue_date')
                if not entry_date or entry_date > filters['end_date']:
                    match = False

            if match:
                results.append(entry.copy())

        return results

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics from ledger"""
        if not self.ledger:
            return {
                'total_documents': 0,
                'total_amount': 0.0,
                'by_status': {},
                'by_project': {},
                'by_fiscal_year': {}
            }

        total_docs = len(self.ledger)
        total_amount = sum(entry.get('grand_total', 0.0) for entry in self.ledger)

        # Count by status
        by_status = {}
        for entry in self.ledger:
            status = entry.get('status', 'unknown')
            by_status[status] = by_status.get(status, 0) + 1

        # Sum by project
        by_project = {}
        for entry in self.ledger:
            project = entry.get('project_code', 'NoProject')
            amount = entry.get('grand_total', 0.0)
            by_project[project] = by_project.get(project, 0.0) + amount

        # Sum by fiscal year
        by_fiscal_year = {}
        for entry in self.ledger:
            fy = entry.get('fiscal_year', 'Unknown')
            amount = entry.get('grand_total', 0.0)
            by_fiscal_year[fy] = by_fiscal_year.get(fy, 0.0) + amount

        return {
            'total_documents': total_docs,
            'total_amount': round(total_amount, 2),
            'by_status': by_status,
            'by_project': {k: round(v, 2) for k, v in by_project.items()},
            'by_fiscal_year': {k: round(v, 2) for k, v in by_fiscal_year.items()}
        }


class ExportEngine:
    """Export ledger and documents to various formats"""

    @staticmethod
    def export_csv(ledger_entries: List[Dict[str, Any]], output_file: str) -> str:
        """
        Export ledger to CSV

        Returns: Path to exported file
        """
        output_path = Path(output_file)

        if not ledger_entries:
            # Create empty file with headers
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=LedgerRow.csv_headers())
                writer.writeheader()
            return str(output_path)

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=LedgerRow.csv_headers())
            writer.writeheader()
            writer.writerows(ledger_entries)

        return str(output_path)

    @staticmethod
    def export_json(ledger_entries: List[Dict[str, Any]], output_file: str) -> str:
        """
        Export ledger to JSON

        Returns: Path to exported file
        """
        output_path = Path(output_file)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(ledger_entries, f, indent=2, ensure_ascii=False)

        return str(output_path)

    @staticmethod
    def export_excel(ledger_entries: List[Dict[str, Any]], output_file: str) -> str:
        """
        Export ledger to Excel (XLSX)

        Note: In production, use openpyxl or xlsxwriter
        For now, fall back to CSV
        """
        # Placeholder - would use openpyxl in production:
        # from openpyxl import Workbook
        # wb = Workbook()
        # ws = wb.active
        # ...

        # For now, export as CSV with .xlsx extension warning
        csv_file = output_file.replace('.xlsx', '.csv')
        ExportEngine.export_csv(ledger_entries, csv_file)

        return csv_file + " (Note: Install openpyxl for native Excel support)"

    @staticmethod
    def export_document_json(processed_doc: ProcessedDocument, output_file: str) -> str:
        """
        Export single processed document to JSON

        Returns: Path to exported file
        """
        output_path = Path(output_file)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(processed_doc.to_json())

        return str(output_path)


class AuditTrailManager:
    """Manage comprehensive audit trail for all processing operations"""

    def __init__(self, audit_file: str = "audit_trail.jsonl"):
        """
        Use JSON Lines format for append-only audit log
        Each line is a complete JSON object
        """
        self.audit_file = Path(audit_file)

    def log_event(self, doc_id: str, event_type: str, details: Dict[str, Any],
                  user: Optional[str] = None):
        """
        Append event to audit trail

        Args:
            doc_id: Document ID
            event_type: Type of event (ingest, parse, validate, file, approve, export)
            details: Event-specific details
            user: Username/email if applicable
        """
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'doc_id': doc_id,
            'event_type': event_type,
            'user': user,
            'details': details
        }

        # Append to JSONL file
        with open(self.audit_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event, ensure_ascii=False) + '\n')

    def get_document_history(self, doc_id: str) -> List[Dict[str, Any]]:
        """Get all audit events for a specific document"""
        if not self.audit_file.exists():
            return []

        events = []
        with open(self.audit_file, 'r', encoding='utf-8') as f:
            for line in f:
                event = json.loads(line.strip())
                if event.get('doc_id') == doc_id:
                    events.append(event)

        return events

    def get_recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get most recent audit events"""
        if not self.audit_file.exists():
            return []

        events = []
        with open(self.audit_file, 'r', encoding='utf-8') as f:
            for line in f:
                events.append(json.loads(line.strip()))

        # Return last N events
        return events[-limit:]

    def export_audit_log(self, output_file: str, doc_id: Optional[str] = None,
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None) -> str:
        """
        Export filtered audit log to JSON file

        Args:
            output_file: Output file path
            doc_id: Filter by document ID
            start_date: Filter by start date (ISO format)
            end_date: Filter by end date (ISO format)
        """
        if not self.audit_file.exists():
            return output_file

        filtered_events = []
        with open(self.audit_file, 'r', encoding='utf-8') as f:
            for line in f:
                event = json.loads(line.strip())

                # Apply filters
                if doc_id and event.get('doc_id') != doc_id:
                    continue

                if start_date and event.get('timestamp', '') < start_date:
                    continue

                if end_date and event.get('timestamp', '') > end_date:
                    continue

                filtered_events.append(event)

        # Export to JSON
        output_path = Path(output_file)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(filtered_events, f, indent=2, ensure_ascii=False)

        return str(output_path)


class ReportGenerator:
    """Generate summary reports and dashboards"""

    def __init__(self, ledger_manager: LedgerManager):
        self.ledger = ledger_manager

    def generate_fiscal_year_report(self, fiscal_year: str) -> Dict[str, Any]:
        """Generate comprehensive report for a fiscal year"""
        entries = self.ledger.query({'fiscal_year': fiscal_year})

        total_amount = sum(e.get('grand_total', 0.0) for e in entries)
        total_docs = len(entries)

        # By project
        by_project = {}
        for entry in entries:
            proj = entry.get('project_code', 'NoProject')
            by_project[proj] = by_project.get(proj, 0.0) + entry.get('grand_total', 0.0)

        # By grant
        by_grant = {}
        for entry in entries:
            grant = entry.get('grant_code', 'NoGrant')
            by_grant[grant] = by_grant.get(grant, 0.0) + entry.get('grand_total', 0.0)

        # By status
        by_status = {}
        for entry in entries:
            status = entry.get('status', 'unknown')
            by_status[status] = by_status.get(status, 0) + 1

        # By vendor
        by_vendor = {}
        for entry in entries:
            vendor = entry.get('vendor', 'Unknown')
            by_vendor[vendor] = by_vendor.get(vendor, 0.0) + entry.get('grand_total', 0.0)

        # Top 10 vendors by spend
        top_vendors = sorted(by_vendor.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            'fiscal_year': fiscal_year,
            'summary': {
                'total_documents': total_docs,
                'total_amount': round(total_amount, 2),
                'average_amount': round(total_amount / total_docs, 2) if total_docs > 0 else 0.0
            },
            'by_project': {k: round(v, 2) for k, v in by_project.items()},
            'by_grant': {k: round(v, 2) for k, v in by_grant.items()},
            'by_status': by_status,
            'top_vendors': [(v, round(amt, 2)) for v, amt in top_vendors]
        }

    def generate_project_report(self, project_code: str) -> Dict[str, Any]:
        """Generate report for a specific project"""
        entries = self.ledger.query({'project_code': project_code})

        total_amount = sum(e.get('grand_total', 0.0) for e in entries)
        total_docs = len(entries)

        # By grant
        by_grant = {}
        for entry in entries:
            grant = entry.get('grant_code', 'NoGrant')
            by_grant[grant] = by_grant.get(grant, 0.0) + entry.get('grand_total', 0.0)

        # By category
        by_category = {}
        for entry in entries:
            cat = entry.get('category_primary', 'Uncategorized')
            by_category[cat] = by_category.get(cat, 0.0) + entry.get('grand_total', 0.0)

        return {
            'project_code': project_code,
            'total_documents': total_docs,
            'total_amount': round(total_amount, 2),
            'by_grant': {k: round(v, 2) for k, v in by_grant.items()},
            'by_category': {k: round(v, 2) for k, v in by_category.items()}
        }
