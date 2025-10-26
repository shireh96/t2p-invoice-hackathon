"""
NGO-InvoiceFiler: Filing System with Deterministic Naming
Creates folder structures and file names following NGO best practices.
"""

import re
import unicodedata
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import date

from schemas import Status, DocType, AuditLogEntry


class FilingSystem:
    """Generate deterministic folder paths and file names for NGO document filing"""

    def __init__(self, org_profile, base_storage_path: str = "invoice_storage"):
        self.org_profile = org_profile
        self.base_path = Path(base_storage_path)
        self.audit_entries = []

    def generate_filing_info(self, parsed_data: Dict, ngo_context: Dict,
                            classification: Dict, validation: Dict) -> Dict[str, Any]:
        """
        Generate complete filing information: folder path, file name, initial status

        Returns: Dict with folder_path, file_name, status, approver, approved_at
        """
        self.audit_entries = []

        # Extract required fields
        fiscal_year = ngo_context['fiscal_year']
        project_code = ngo_context.get('project_code')
        grant_code = ngo_context.get('grant_code')
        vendor_name = parsed_data['vendor']['display_name']
        doc_type = parsed_data['doc_type']
        issue_date = parsed_data['dates'].get('issue_date') or date.today()
        invoice_num = parsed_data['invoice'].get('number')
        grand_total = parsed_data['amounts']['grand_total']
        currency = parsed_data['currency']

        # Determine initial status based on validation flags
        initial_status = self._determine_initial_status(validation['flags'])

        # Build folder path
        folder_path = self._build_folder_path(
            fiscal_year, project_code, grant_code, vendor_name, doc_type
        )

        # Build file name
        file_name = self._build_file_name(
            issue_date, vendor_name, invoice_num, project_code,
            grant_code, grand_total, currency, initial_status,
            original_extension=".pdf"  # Default, would be detected from input
        )

        self.audit_entries.append(AuditLogEntry(
            step="file",
            detail=f"path={folder_path}, name={file_name}, status={initial_status.value}"
        ))

        return {
            'folder_path': folder_path,
            'file_name': file_name,
            'status': initial_status,
            'approver': None,
            'approved_at': None,
            'audit_log': self.audit_entries
        }

    def _build_folder_path(self, fiscal_year: str, project_code: Optional[str],
                          grant_code: Optional[str], vendor_name: str,
                          doc_type: DocType) -> str:
        """
        Build folder path: FiscalYear/Project/Grant/Vendor/DocType/

        Format:
        - FiscalYear: YYYY-YYYY (e.g., 2023-2024)
        - Project: <ProjectCode>-<ShortName> (e.g., EDU001-Education)
        - Grant: <GrantCode>-<DonorShort> (e.g., GR2023-UNICEF)
        - Vendor: <CanonicalVendorName> (e.g., Acme_Corp)
        - DocType: Invoice | Receipt | CreditNote
        """
        parts = []

        # Fiscal year
        parts.append(fiscal_year)

        # Project
        if project_code:
            project_name = self.org_profile.project_codes.get(project_code, "Unknown")
            project_short = self._truncate_name(project_name, 20)
            parts.append(f"{project_code}-{project_short}")
        else:
            parts.append("NoProject")

        # Grant
        if grant_code:
            grant_info = self.org_profile.grant_dictionary.get(grant_code, {})
            donor_name = grant_info.get('donor', 'Unknown')
            donor_short = self._truncate_name(donor_name, 15)
            parts.append(f"{grant_code}-{donor_short}")
        else:
            parts.append("NoGrant")

        # Vendor
        vendor_safe = self._sanitize_name(vendor_name)
        parts.append(vendor_safe)

        # DocType
        doc_type_map = {
            DocType.INVOICE: "Invoice",
            DocType.RECEIPT: "Receipt",
            DocType.CREDIT_NOTE: "CreditNote",
            DocType.PROFORMA: "Proforma",
            DocType.OTHER: "Other"
        }
        parts.append(doc_type_map.get(doc_type, "Other"))

        # Join with OS-appropriate separator
        folder_path = "/".join(parts)
        return folder_path

    def _build_file_name(self, issue_date: date, vendor_name: str,
                        invoice_num: Optional[str], project_code: Optional[str],
                        grant_code: Optional[str], amount: float, currency: str,
                        status: Status, original_extension: str = ".pdf") -> str:
        """
        Build deterministic file name:
        YYYY-MM-DD__Vendor__InvoiceNumber__Project__Grant__AmountCurrency__Status.ext

        Example: 2024-03-15__Acme_Corp__INV001__EDU001__GR2023__1500USD__draft.pdf
        """
        parts = []

        # Date
        parts.append(issue_date.strftime('%Y-%m-%d'))

        # Vendor
        vendor_safe = self._sanitize_name(vendor_name)
        parts.append(self._truncate_name(vendor_safe, 30))

        # Invoice/reference number
        if invoice_num:
            inv_safe = self._sanitize_name(invoice_num)
            parts.append(self._truncate_name(inv_safe, 20))
        else:
            parts.append("NOREF")

        # Project code
        parts.append(project_code or "NOPROJ")

        # Grant code
        parts.append(grant_code or "NOGRANT")

        # Amount + Currency
        amount_str = f"{int(amount)}{currency}"
        parts.append(amount_str)

        # Status
        parts.append(status.value)

        # Join parts
        file_name = "__".join(parts) + original_extension
        return file_name

    def _sanitize_name(self, name: str) -> str:
        """
        Sanitize name for file system:
        - Remove diacritics
        - Replace spaces with underscores
        - Remove special characters
        - Lowercase
        """
        # Normalize Unicode (remove diacritics)
        normalized = unicodedata.normalize('NFD', name)
        without_accents = ''.join(
            c for c in normalized
            if unicodedata.category(c) != 'Mn'
        )

        # Replace spaces with underscores
        no_spaces = without_accents.replace(' ', '_')

        # Keep only alphanumeric and underscores
        safe = re.sub(r'[^\w]', '', no_spaces)

        # Convert to lowercase for consistency
        return safe.lower()

    def _truncate_name(self, name: str, max_len: int) -> str:
        """Truncate name to max length"""
        if len(name) <= max_len:
            return name
        return name[:max_len]

    def _determine_initial_status(self, flags: list) -> Status:
        """
        Determine initial document status based on validation flags:
        - If high severity flags: needs_review
        - If medium severity flags: needs_review
        - Otherwise: draft
        """
        from schemas import FlagSeverity

        if not flags:
            return Status.DRAFT

        severities = [flag.severity for flag in flags]

        if FlagSeverity.HIGH in severities:
            return Status.NEEDS_REVIEW
        elif FlagSeverity.MEDIUM in severities:
            return Status.NEEDS_REVIEW
        else:
            return Status.DRAFT

    def create_folder_structure(self, folder_path: str) -> Path:
        """Create the folder structure if it doesn't exist"""
        full_path = self.base_path / folder_path
        full_path.mkdir(parents=True, exist_ok=True)
        return full_path

    def get_full_file_path(self, folder_path: str, file_name: str) -> str:
        """Get complete file path for storage"""
        return str(self.base_path / folder_path / file_name)

    def file_exists(self, folder_path: str, file_name: str) -> bool:
        """Check if file already exists"""
        full_path = Path(self.get_full_file_path(folder_path, file_name))
        return full_path.exists()


class ApprovalWorkflow:
    """Manage document approval workflow and status transitions"""

    # Valid status transitions
    TRANSITIONS = {
        Status.DRAFT: [Status.NEEDS_REVIEW, Status.APPROVED],
        Status.NEEDS_REVIEW: [Status.DRAFT, Status.APPROVED],
        Status.APPROVED: [Status.POSTED],
        Status.POSTED: []  # Terminal state
    }

    @staticmethod
    def can_transition(current: Status, target: Status) -> bool:
        """Check if status transition is valid"""
        return target in ApprovalWorkflow.TRANSITIONS.get(current, [])

    @staticmethod
    def transition(filing_info: Dict, new_status: Status, approver: Optional[str] = None) -> Dict[str, Any]:
        """
        Transition document to new status

        Returns: Updated filing_info with new status, approver, and timestamp
        Raises: ValueError if transition is invalid
        """
        from datetime import datetime

        current_status = filing_info['status']

        if not ApprovalWorkflow.can_transition(current_status, new_status):
            raise ValueError(
                f"Invalid transition from {current_status.value} to {new_status.value}"
            )

        # Check for high-severity flags if transitioning to POSTED
        if new_status == Status.POSTED:
            if filing_info.get('has_high_severity_flags'):
                raise ValueError("Cannot post document with high-severity validation flags")

        # Update filing info
        filing_info['status'] = new_status

        # Record approver and timestamp for APPROVED status
        if new_status == Status.APPROVED:
            if not approver:
                raise ValueError("Approver name required for approval")
            filing_info['approver'] = approver
            filing_info['approved_at'] = datetime.utcnow()

        # Update file name to reflect new status
        old_name = filing_info['file_name']
        new_name = ApprovalWorkflow._update_filename_status(old_name, new_status)
        filing_info['file_name'] = new_name

        return filing_info

    @staticmethod
    def _update_filename_status(file_name: str, new_status: Status) -> str:
        """Update status in file name"""
        # Pattern: ...Status.ext
        # Replace the status part (second to last component before extension)
        parts = file_name.rsplit('.', 1)
        name_parts = parts[0].split('__')

        # Last part is status
        if len(name_parts) >= 2:
            name_parts[-1] = new_status.value

        new_name = '__'.join(name_parts)
        if len(parts) > 1:
            new_name += '.' + parts[1]

        return new_name

    @staticmethod
    def get_available_transitions(current: Status) -> list:
        """Get list of available status transitions from current state"""
        return ApprovalWorkflow.TRANSITIONS.get(current, [])
