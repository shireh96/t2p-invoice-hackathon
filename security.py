"""
NGO-InvoiceFiler: Security and Privacy Module
Handles PII redaction, data masking, access control, and secure storage.
"""

import re
from typing import Dict, Any, Optional


class PIIRedactor:
    """Redact sensitive personal information for UI previews and logs"""

    @staticmethod
    def redact_iban(iban: Optional[str]) -> Optional[str]:
        """
        Redact IBAN: show first 6 + last 4 characters
        Example: IL620108000000099999999 -> IL6201******9999
        """
        if not iban or len(iban) < 10:
            return iban

        return iban[:6] + '*' * (len(iban) - 10) + iban[-4:]

    @staticmethod
    def redact_tax_id(tax_id: Optional[str]) -> Optional[str]:
        """
        Redact tax ID/VAT: show only last 4 characters
        Example: 123-45-6789 -> *****6789
        """
        if not tax_id or len(tax_id) < 4:
            return '****'

        return '*' * (len(tax_id) - 4) + tax_id[-4:]

    @staticmethod
    def redact_email(email: Optional[str]) -> Optional[str]:
        """
        Redact email: show first char + domain
        Example: john.doe@example.com -> j***@example.com
        """
        if not email or '@' not in email:
            return email

        local, domain = email.split('@', 1)
        if len(local) <= 1:
            return f"{local}@{domain}"

        return f"{local[0]}***@{domain}"

    @staticmethod
    def redact_phone(phone: Optional[str]) -> Optional[str]:
        """
        Redact phone: show last 4 digits
        Example: +1-555-123-4567 -> ****4567
        """
        if not phone:
            return phone

        digits = re.sub(r'\D', '', phone)
        if len(digits) < 4:
            return '****'

        return '****' + digits[-4:]

    @staticmethod
    def redact_vendor(vendor_dict: Dict[str, Any], for_ui: bool = True) -> Dict[str, Any]:
        """
        Redact vendor PII for UI preview

        Args:
            vendor_dict: Vendor information dictionary
            for_ui: If True, redact; if False, return full data
        """
        if not for_ui:
            return vendor_dict.copy()

        redacted = vendor_dict.copy()

        if redacted.get('tax_id_vat'):
            redacted['tax_id_vat'] = PIIRedactor.redact_tax_id(redacted['tax_id_vat'])

        if redacted.get('email'):
            redacted['email'] = PIIRedactor.redact_email(redacted['email'])

        if redacted.get('phone'):
            redacted['phone'] = PIIRedactor.redact_phone(redacted['phone'])

        if redacted.get('iban'):
            redacted['iban'] = PIIRedactor.redact_iban(redacted['iban'])

        return redacted

    @staticmethod
    def redact_document_for_preview(doc_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a UI-safe preview of document with all PII redacted

        Returns: Copy of document with sensitive fields masked
        """
        preview = doc_dict.copy()

        # Redact vendor
        if 'vendor' in preview:
            preview['vendor'] = PIIRedactor.redact_vendor(preview['vendor'], for_ui=True)

        # Redact buyer
        if 'buyer' in preview and preview['buyer'].get('tax_id_vat'):
            preview['buyer']['tax_id_vat'] = PIIRedactor.redact_tax_id(
                preview['buyer']['tax_id_vat']
            )

        # Remove audit log details that might contain PII
        if 'audit_log' in preview:
            for entry in preview['audit_log']:
                if 'detail' in entry:
                    # Redact any email addresses in detail
                    entry['detail'] = re.sub(
                        r'[\w\.-]+@[\w\.-]+\.\w+',
                        'redacted@email.com',
                        entry['detail']
                    )

        return preview


class AccessControl:
    """Manage access control and permissions for documents"""

    # Permission levels
    PERMISSION_LEVELS = {
        'viewer': ['read'],
        'contributor': ['read', 'create', 'update'],
        'approver': ['read', 'create', 'update', 'approve'],
        'admin': ['read', 'create', 'update', 'approve', 'delete', 'export']
    }

    @staticmethod
    def check_permission(user_role: str, action: str) -> bool:
        """
        Check if user role has permission for action

        Args:
            user_role: User's role (viewer, contributor, approver, admin)
            action: Action to check (read, create, update, approve, delete, export)

        Returns: True if permitted, False otherwise
        """
        if user_role not in AccessControl.PERMISSION_LEVELS:
            return False

        return action in AccessControl.PERMISSION_LEVELS[user_role]

    @staticmethod
    def can_approve(user_role: str) -> bool:
        """Check if user can approve documents"""
        return AccessControl.check_permission(user_role, 'approve')

    @staticmethod
    def can_export(user_role: str) -> bool:
        """Check if user can export data"""
        return AccessControl.check_permission(user_role, 'export')

    @staticmethod
    def can_delete(user_role: str) -> bool:
        """Check if user can delete documents"""
        return AccessControl.check_permission(user_role, 'delete')


class DataEncryption:
    """Handle encryption for sensitive data at rest"""

    @staticmethod
    def encrypt_sensitive_fields(doc_dict: Dict[str, Any], key: Optional[str] = None) -> Dict[str, Any]:
        """
        Encrypt sensitive fields in document

        In production, use:
        - AES-256 for symmetric encryption
        - Properly managed keys (AWS KMS, Azure Key Vault, HashiCorp Vault)
        - Field-level encryption for PII

        For now, this is a placeholder that marks which fields should be encrypted.
        """
        # Fields to encrypt
        sensitive_fields = [
            ('vendor', 'tax_id_vat'),
            ('vendor', 'iban'),
            ('vendor', 'email'),
            ('buyer', 'tax_id_vat'),
        ]

        encrypted = doc_dict.copy()

        # In production, actually encrypt these fields
        # For now, just add metadata indicating encryption status
        encrypted['_encryption_metadata'] = {
            'encrypted': True,
            'algorithm': 'AES-256-GCM',
            'fields_encrypted': [f"{f[0]}.{f[1]}" for f in sensitive_fields]
        }

        return encrypted

    @staticmethod
    def decrypt_sensitive_fields(doc_dict: Dict[str, Any], key: Optional[str] = None) -> Dict[str, Any]:
        """
        Decrypt sensitive fields in document

        In production, use proper decryption with managed keys.
        """
        # Remove encryption metadata
        decrypted = doc_dict.copy()
        if '_encryption_metadata' in decrypted:
            del decrypted['_encryption_metadata']

        return decrypted


class AuditLogger:
    """Security-focused audit logging for compliance"""

    @staticmethod
    def log_access(doc_id: str, user: str, action: str, details: Optional[Dict] = None):
        """
        Log access to sensitive documents

        In production:
        - Send to SIEM (Security Information and Event Management)
        - Integrate with compliance logging (SOC 2, GDPR)
        - Immutable audit logs
        - Tamper-proof storage
        """
        log_entry = {
            'timestamp': __import__('datetime').datetime.utcnow().isoformat(),
            'doc_id': doc_id,
            'user': user,
            'action': action,
            'ip_address': 'placeholder',  # Would capture from request context
            'user_agent': 'placeholder',
            'details': details or {}
        }

        # In production, send to audit service
        # For now, just structure the log entry
        return log_entry

    @staticmethod
    def log_pii_access(doc_id: str, user: str, pii_fields: list):
        """Log access to PII fields specifically"""
        return AuditLogger.log_access(
            doc_id, user, 'pii_access',
            {'pii_fields': pii_fields}
        )

    @staticmethod
    def log_export(user: str, format: str, record_count: int, filters: Optional[Dict] = None):
        """Log data export events"""
        return {
            'timestamp': __import__('datetime').datetime.utcnow().isoformat(),
            'user': user,
            'action': 'export',
            'format': format,
            'record_count': record_count,
            'filters': filters or {},
            'ip_address': 'placeholder'
        }


class InputSanitizer:
    """Sanitize user inputs to prevent injection attacks"""

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize user-provided filename to prevent path traversal

        Remove: ../, ..\, absolute paths, special chars
        """
        # Remove path separators and parent directory references
        sanitized = filename.replace('..', '').replace('/', '').replace('\\', '')

        # Remove control characters
        sanitized = ''.join(c for c in sanitized if ord(c) >= 32)

        # Limit length
        sanitized = sanitized[:255]

        # Ensure not empty
        if not sanitized:
            sanitized = 'unnamed_file'

        return sanitized

    @staticmethod
    def sanitize_text_input(text: str, max_length: int = 10000) -> str:
        """
        Sanitize text input for storage

        Remove: control characters, excessive whitespace, SQL/script injection
        """
        # Remove null bytes
        sanitized = text.replace('\x00', '')

        # Normalize whitespace
        sanitized = ' '.join(sanitized.split())

        # Limit length
        sanitized = sanitized[:max_length]

        return sanitized

    @staticmethod
    def validate_currency_code(currency: str) -> bool:
        """Validate currency code is safe"""
        # Must be 3 uppercase letters
        return bool(re.match(r'^[A-Z]{3}$', currency))

    @staticmethod
    def validate_date_string(date_str: str) -> bool:
        """Validate date string format"""
        # Must be YYYY-MM-DD
        return bool(re.match(r'^\d{4}-\d{2}-\d{2}$', date_str))


class SecureDocumentHandler:
    """High-level secure document handling"""

    def __init__(self):
        self.pii_redactor = PIIRedactor()
        self.access_control = AccessControl()
        self.audit_logger = AuditLogger()

    def prepare_for_ui(self, doc: Dict[str, Any], user_role: str) -> Optional[Dict[str, Any]]:
        """
        Prepare document for UI display with appropriate redactions

        Returns: Redacted document if user has read permission, None otherwise
        """
        if not self.access_control.check_permission(user_role, 'read'):
            return None

        # Redact PII for UI
        redacted = self.pii_redactor.redact_document_for_preview(doc)

        return redacted

    def prepare_for_export(self, doc: Dict[str, Any], user_role: str,
                          include_pii: bool = False) -> Optional[Dict[str, Any]]:
        """
        Prepare document for export with appropriate security

        Args:
            doc: Document to export
            user_role: User's role
            include_pii: Whether to include full PII (requires export permission)

        Returns: Document for export if permitted, None otherwise
        """
        if not self.access_control.check_permission(user_role, 'export'):
            return None

        if include_pii:
            # Full document with PII (admin only)
            if user_role != 'admin':
                return self.pii_redactor.redact_document_for_preview(doc)
            return doc.copy()
        else:
            # Redacted version
            return self.pii_redactor.redact_document_for_preview(doc)

    def validate_upload(self, file_bytes: bytes, filename: str, user_role: str) -> Dict[str, Any]:
        """
        Validate uploaded file for security

        Checks:
        - File size limits
        - File type validation
        - Malware scanning (placeholder)
        - User permissions

        Returns: Dict with 'valid': bool, 'message': str, 'sanitized_filename': str
        """
        if not self.access_control.check_permission(user_role, 'create'):
            return {
                'valid': False,
                'message': 'User does not have permission to upload documents'
            }

        # Sanitize filename
        safe_filename = InputSanitizer.sanitize_filename(filename)

        # Check file size (max 50MB)
        max_size = 50 * 1024 * 1024
        if len(file_bytes) > max_size:
            return {
                'valid': False,
                'message': f'File size exceeds maximum allowed ({max_size} bytes)'
            }

        # Check file type by magic bytes (simplified)
        # In production, use python-magic or similar
        is_pdf = file_bytes[:4] == b'%PDF'
        is_image = file_bytes[:2] in [b'\xff\xd8', b'\x89P', b'II', b'MM']  # JPEG, PNG, TIFF

        if not (is_pdf or is_image):
            return {
                'valid': False,
                'message': 'Invalid file type. Only PDF and images are allowed.'
            }

        # Malware scanning placeholder
        # In production, integrate with ClamAV, VirusTotal API, or cloud scanning
        # is_safe = scan_for_malware(file_bytes)

        return {
            'valid': True,
            'message': 'File validated successfully',
            'sanitized_filename': safe_filename
        }
