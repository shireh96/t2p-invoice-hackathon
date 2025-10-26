"""
NGO-InvoiceFiler: Enhanced OCR and Document Parsing Engine
Supports Tesseract OCR + AI-based document understanding (Claude/GPT-4 Vision)
"""

import re
import hashlib
import io
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, date
from pathlib import Path
import unicodedata

from schemas import (
    DocType, Language, PaymentMethod, LineItem,
    AuditLogEntry, FlagType, FlagSeverity, ValidationFlag
)

# Try importing OCR dependencies
try:
    from PIL import Image
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("Warning: Tesseract OCR not available. Install: pip install pytesseract Pillow")

try:
    from pdf2image import convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    print("Warning: pdf2image not available. Install: pip install pdf2image")

# Try importing AI APIs
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class EnhancedOCREngine:
    """
    Enhanced OCR engine with multiple backends:
    1. Tesseract OCR (local, free)
    2. AI-based understanding (Claude/GPT-4 Vision)
    """

    def __init__(self, ocr_backend='tesseract', ai_backend=None, api_key=None):
        """
        Args:
            ocr_backend: 'tesseract' or 'simulation'
            ai_backend: 'claude' or 'openai' or None
            api_key: API key for AI backend
        """
        self.ocr_backend = ocr_backend
        self.ai_backend = ai_backend
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY') or os.getenv('OPENAI_API_KEY')
        self.supported_langs = ['en', 'ar', 'he', 'fr', 'es', 'de']

        # Initialize AI client if available
        self.ai_client = None
        if ai_backend == 'claude' and ANTHROPIC_AVAILABLE and self.api_key:
            self.ai_client = anthropic.Anthropic(api_key=self.api_key)
        elif ai_backend == 'openai' and OPENAI_AVAILABLE and self.api_key:
            openai.api_key = self.api_key
            self.ai_client = openai

    def extract_text(self, file_bytes: bytes, language: str = 'auto') -> Tuple[str, float, str]:
        """
        Extract text from document using selected OCR backend
        Returns: (extracted_text, confidence, detected_language)
        """
        if self.ocr_backend == 'tesseract' and TESSERACT_AVAILABLE:
            return self._extract_with_tesseract(file_bytes, language)
        else:
            return self._extract_simulated(file_bytes, language)

    def _extract_with_tesseract(self, file_bytes: bytes, language: str = 'auto') -> Tuple[str, float, str]:
        """Extract text using Tesseract OCR"""
        try:
            # Detect file type and convert to images
            images = self._convert_to_images(file_bytes)

            if not images:
                return "[ERROR] Could not convert document to images", 0.0, 'en'

            # Perform OCR on all pages
            all_text = []
            total_confidence = 0.0

            for img in images:
                # Preprocess image for better OCR
                processed_img = self._preprocess_image(img)

                # Configure Tesseract for multilingual support
                lang_code = self._map_language_code(language)

                # Tesseract configuration for better accuracy
                custom_config = r'--oem 3 --psm 6'  # OEM 3 = LSTM, PSM 6 = Uniform text block

                # Extract text with confidence data
                ocr_data = pytesseract.image_to_data(
                    processed_img,
                    lang=lang_code,
                    config=custom_config,
                    output_type=pytesseract.Output.DICT
                )

                # Calculate average confidence
                confidences = [int(conf) for conf in ocr_data['conf'] if int(conf) > 0]
                page_confidence = sum(confidences) / len(confidences) if confidences else 0
                total_confidence += page_confidence

                # Extract text
                page_text = pytesseract.image_to_string(
                    processed_img,
                    lang=lang_code,
                    config=custom_config
                )
                all_text.append(page_text)

            # Combine all pages
            full_text = "\n\n".join(all_text)
            avg_confidence = total_confidence / len(images) if images else 0

            # Detect language from text
            detected_lang = self._detect_language_from_text(full_text) if language == 'auto' else language

            return full_text, avg_confidence / 100.0, detected_lang

        except Exception as e:
            print(f"Tesseract OCR error: {e}")
            import traceback
            traceback.print_exc()
            return f"[OCR ERROR] {str(e)}", 0.0, 'en'

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """Preprocess image for better OCR accuracy"""
        try:
            from PIL import ImageEnhance, ImageFilter

            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Resize if too small (min 1200px width for good OCR)
            width, height = image.size
            if width < 1200:
                ratio = 1200 / width
                new_size = (int(width * ratio), int(height * ratio))
                image = image.resize(new_size, Image.Resampling.LANCZOS)

            # Enhance contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(1.5)

            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(2.0)

            # Convert to grayscale
            image = image.convert('L')

            # Apply threshold to get binary image (helps with text clarity)
            threshold = 128
            image = image.point(lambda p: 255 if p > threshold else 0)

            # Slight blur to reduce noise
            image = image.filter(ImageFilter.MedianFilter(size=1))

            return image

        except Exception as e:
            print(f"Image preprocessing warning: {e}")
            # Return original if preprocessing fails
            return image

    def _convert_to_images(self, file_bytes: bytes) -> List[Image.Image]:
        """Convert PDF or image bytes to PIL Images with high DPI for better OCR"""
        images = []

        try:
            # Try to open as image first
            img = Image.open(io.BytesIO(file_bytes))
            images.append(img)
        except:
            # Try to convert from PDF with higher DPI for better OCR
            if PDF2IMAGE_AVAILABLE:
                try:
                    # Use 400 DPI for better OCR quality (was 300)
                    images = convert_from_bytes(file_bytes, dpi=400)
                except Exception as e:
                    print(f"PDF conversion error: {e}")
            else:
                print("pdf2image not available. Cannot process PDFs.")

        return images

    def _map_language_code(self, lang: str) -> str:
        """Map internal language codes to Tesseract language codes"""
        lang_map = {
            'en': 'eng',
            'ar': 'ara',
            'he': 'heb',
            'fr': 'fra',
            'es': 'spa',
            'de': 'deu',
            'auto': 'eng+ara+heb'  # Multi-language detection
        }
        return lang_map.get(lang, 'eng')

    def _detect_language_from_text(self, text: str) -> str:
        """Detect language from extracted text"""
        # Simple heuristic: check for Arabic/Hebrew characters
        arabic_count = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
        hebrew_count = sum(1 for c in text if '\u0590' <= c <= '\u05FF')

        if arabic_count > 10:
            return 'ar'
        elif hebrew_count > 10:
            return 'he'
        else:
            return 'en'

    def _extract_simulated(self, file_bytes: bytes, language: str = 'auto') -> Tuple[str, float, str]:
        """Fallback: Simulated OCR for testing without dependencies"""
        detected_lang = 'en'
        confidence = 0.85
        text = """
[SIMULATED OCR OUTPUT]
This is placeholder text for demonstration purposes.
In production, install Tesseract: pip install pytesseract Pillow pdf2image

INVOICE
Date: 2024-10-26
Vendor: Demo Supplier Ltd.
Invoice #: INV-2024-001

Amount: $1,234.56
Tax: $123.45
Total: $1,358.01

Thank you for your business!
"""
        return text, confidence, detected_lang

    def enhance_with_ai(self, text: str, file_bytes: bytes) -> Dict[str, Any]:
        """
        Use AI (Claude or GPT-4) to extract structured data from document
        This is more accurate than regex parsing
        """
        if not self.ai_client:
            return {'error': 'AI backend not configured'}

        if self.ai_backend == 'claude':
            return self._enhance_with_claude(text, file_bytes)
        elif self.ai_backend == 'openai':
            return self._enhance_with_openai(text, file_bytes)
        else:
            return {'error': 'Invalid AI backend'}

    def _enhance_with_claude(self, text: str, file_bytes: bytes) -> Dict[str, Any]:
        """Use Claude to extract structured invoice data"""
        try:
            # Prepare prompt for Claude
            prompt = f"""You are an expert at extracting structured data from invoices and receipts.

Analyze this document text and extract the following information in JSON format:

{{
    "vendor_name": "vendor/supplier name",
    "vendor_tax_id": "tax ID or VAT number if available",
    "vendor_email": "email if available",
    "vendor_phone": "phone if available",
    "vendor_address": "address if available",
    "invoice_number": "invoice/receipt number",
    "invoice_date": "date in YYYY-MM-DD format",
    "due_date": "due date in YYYY-MM-DD format if available",
    "currency": "3-letter currency code (USD, EUR, ILS, etc.)",
    "subtotal": numeric value without currency symbol,
    "tax_amount": numeric tax amount,
    "tax_rate": numeric tax rate percentage,
    "grand_total": numeric total amount,
    "line_items": [
        {{
            "description": "item description",
            "quantity": numeric quantity,
            "unit_price": numeric price per unit,
            "total": numeric line total
        }}
    ],
    "payment_method": "cash/transfer/card/check if mentioned",
    "notes": "any important notes or special instructions"
}}

Document text:
{text}

Respond ONLY with the JSON object, no other text."""

            # Call Claude API
            response = self.ai_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            # Parse response
            response_text = response.content[0].text

            # Extract JSON from response
            import json
            # Try to find JSON in the response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                parsed_data = json.loads(json_match.group())
                return {'success': True, 'data': parsed_data}
            else:
                return {'success': False, 'error': 'Could not parse AI response'}

        except Exception as e:
            print(f"Claude API error: {e}")
            return {'success': False, 'error': str(e)}

    def _enhance_with_openai(self, text: str, file_bytes: bytes) -> Dict[str, Any]:
        """Use OpenAI GPT-4 Vision to extract structured invoice data"""
        try:
            import base64
            import json

            # Convert file bytes to base64 for API
            base64_image = base64.b64encode(file_bytes).decode('utf-8')

            # Determine image format
            image_format = "jpeg"
            if file_bytes[:4] == b'\x89PNG':
                image_format = "png"
            elif file_bytes[:4] == b'%PDF':
                image_format = "pdf"
                # For PDFs, we'll use the OCR text instead of image
                return self._enhance_with_openai_text(text)

            # Prepare enhanced prompt for GPT-4
            prompt = """You are an expert invoice data extraction AI. Analyze this document image carefully and extract ALL information with high accuracy.

CRITICAL INSTRUCTIONS:
1. Extract EXACT values - do not estimate or guess
2. If a field is not visible, use null (not empty string)
3. For dates, use YYYY-MM-DD format
4. For numbers, provide numeric values only (no currency symbols, no commas)
5. Double-check all line items match the totals
6. Look for vendor details at the TOP of the invoice
7. Look for amounts at the BOTTOM of the invoice

Return ONLY valid JSON in this exact format:

{
    "vendor_name": "exact vendor/company name as shown",
    "vendor_tax_id": "tax ID, VAT, EIN, or similar (or null)",
    "vendor_email": "email address (or null)",
    "vendor_phone": "phone number with country code if available (or null)",
    "vendor_address": "complete address (or null)",
    "invoice_number": "invoice/receipt/reference number",
    "invoice_date": "YYYY-MM-DD format (or null)",
    "due_date": "YYYY-MM-DD format (or null)",
    "currency": "3-letter code: USD, EUR, GBP, ILS, etc.",
    "subtotal": 0.00,
    "tax_amount": 0.00,
    "tax_rate": 0.00,
    "grand_total": 0.00,
    "line_items": [
        {
            "description": "exact item/service description",
            "quantity": 0.00,
            "unit_price": 0.00,
            "total": 0.00
        }
    ],
    "payment_method": "cash/transfer/card/check/other (or null)",
    "notes": "payment terms, notes, or special instructions (or null)"
}

VALIDATION:
- Ensure subtotal + tax_amount = grand_total (approximately)
- Ensure sum of line_items totals = subtotal (approximately)
- If math doesn't match, prioritize the clearly printed grand_total

Respond with ONLY the JSON object. No explanations, no markdown, just pure JSON."""

            # Call OpenAI API
            response = self.ai_client.chat.completions.create(
                model="gpt-4o",  # GPT-4 with vision
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/{image_format};base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000
            )

            # Parse response
            response_text = response.choices[0].message.content

            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                parsed_data = json.loads(json_match.group())
                return {'success': True, 'data': parsed_data}
            else:
                return {'success': False, 'error': 'Could not parse AI response'}

        except Exception as e:
            print(f"OpenAI API error: {e}")
            return {'success': False, 'error': str(e)}

    def _enhance_with_openai_text(self, text: str) -> Dict[str, Any]:
        """Use OpenAI GPT-4 to extract structured data from OCR text (for PDFs)"""
        try:
            import json

            prompt = f"""You are an expert invoice data extraction AI. Analyze this OCR-extracted text carefully and extract ALL information with high accuracy.

CRITICAL INSTRUCTIONS:
1. Extract EXACT values - do not estimate or guess
2. If a field is not clearly present, use null
3. For dates, convert to YYYY-MM-DD format
4. For numbers, extract numeric values only (no currency symbols, commas)
5. Double-check math: subtotal + tax = grand_total
6. Vendor info is usually at the start of the document
7. Totals are usually at the end

Return ONLY valid JSON in this exact format:

{{
    "vendor_name": "exact vendor/company name",
    "vendor_tax_id": "tax ID/VAT/EIN (or null)",
    "vendor_email": "email (or null)",
    "vendor_phone": "phone number (or null)",
    "vendor_address": "complete address (or null)",
    "invoice_number": "invoice/reference number",
    "invoice_date": "YYYY-MM-DD (or null)",
    "due_date": "YYYY-MM-DD (or null)",
    "currency": "USD/EUR/GBP/ILS etc.",
    "subtotal": 0.00,
    "tax_amount": 0.00,
    "tax_rate": 0.00,
    "grand_total": 0.00,
    "line_items": [
        {{
            "description": "item description",
            "quantity": 0.00,
            "unit_price": 0.00,
            "total": 0.00
        }}
    ],
    "payment_method": "cash/transfer/card/check/other (or null)",
    "notes": "payment terms or notes (or null)"
}}

VALIDATION:
- Verify subtotal + tax_amount = grand_total
- Verify sum of line_items totals = subtotal
- If OCR text has errors, use context to correct them
- Prioritize clearly stated grand_total

Document OCR Text:
{text}

Respond with ONLY the JSON object. No markdown, no explanations."""

            response = self.ai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=2000
            )

            response_text = response.choices[0].message.content

            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                parsed_data = json.loads(json_match.group())
                return {'success': True, 'data': parsed_data}
            else:
                return {'success': False, 'error': 'Could not parse AI response'}

        except Exception as e:
            print(f"OpenAI text parsing error: {e}")
            return {'success': False, 'error': str(e)}


class DocumentHasher:
    """Generate checksums and fingerprints for deduplication"""

    @staticmethod
    def compute_sha256(file_bytes: bytes) -> str:
        """Compute SHA-256 hash of file"""
        return hashlib.sha256(file_bytes).hexdigest()

    @staticmethod
    def compute_fingerprint(vendor: str, date: Optional[date],
                          invoice_num: Optional[str], amount: float) -> str:
        """
        Generate semantic fingerprint for duplicate detection
        Format: vendor_YYYYMMDD_invoicenum_amount
        """
        vendor_clean = re.sub(r'[^\w]', '', vendor.lower())[:20]
        date_str = date.strftime('%Y%m%d') if date else 'nodate'
        invoice_clean = re.sub(r'[^\w]', '', invoice_num.lower())[:15] if invoice_num else 'noinv'
        amount_str = f"{int(amount)}"

        fingerprint_str = f"{vendor_clean}_{date_str}_{invoice_clean}_{amount_str}"
        return hashlib.md5(fingerprint_str.encode()).hexdigest()[:16]
