"""
NGO-InvoiceFiler: Interactive Chat Assistant
Conversational invoice upload with GPT-4 powered Q&A for missing data
"""

import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import openai


class InvoiceChatAssistant:
    """
    Interactive chat assistant for invoice processing
    Uses GPT-4 to have conversations about missing invoice data
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.client = openai.OpenAI(api_key=self.api_key) if self.api_key else None

        # Conversation state
        self.sessions = {}  # session_id -> session_data

    def create_session(self, session_id: str, extracted_data: Dict[str, Any],
                      file_name: str, ocr_text: str) -> Dict[str, Any]:
        """
        Create a new chat session for an invoice

        Args:
            session_id: Unique session identifier
            extracted_data: Data extracted from OCR/AI
            file_name: Name of uploaded file
            ocr_text: Raw OCR text for reference

        Returns:
            Initial session state with first message
        """
        # Identify missing or uncertain fields
        missing_fields = self._identify_missing_fields(extracted_data)

        # Create session
        session = {
            'session_id': session_id,
            'file_name': file_name,
            'extracted_data': extracted_data,
            'ocr_text': ocr_text,
            'missing_fields': missing_fields,
            'conversation_history': [],
            'collected_data': {},
            'current_question': None,
            'state': 'collecting',  # collecting, confirming, complete
            'created_at': datetime.now().isoformat()
        }

        self.sessions[session_id] = session

        # Generate first message
        first_message = self._generate_initial_message(session)
        session['conversation_history'].append({
            'role': 'assistant',
            'content': first_message,
            'timestamp': datetime.now().isoformat()
        })

        return {
            'session_id': session_id,
            'message': first_message,
            'missing_fields': missing_fields,
            'progress': self._calculate_progress(session)
        }

    def send_message(self, session_id: str, user_message: str) -> Dict[str, Any]:
        """
        Process user message and return assistant response

        Args:
            session_id: Session identifier
            user_message: User's message/answer

        Returns:
            Assistant response with updated state
        """
        if session_id not in self.sessions:
            return {'error': 'Session not found'}

        session = self.sessions[session_id]

        # Add user message to history
        session['conversation_history'].append({
            'role': 'user',
            'content': user_message,
            'timestamp': datetime.now().isoformat()
        })

        # Process message based on state
        if session['state'] == 'collecting':
            response = self._handle_data_collection(session, user_message)
        elif session['state'] == 'confirming':
            response = self._handle_confirmation(session, user_message)
        else:
            response = "Session is complete. Ready to process invoice!"

        # Add assistant response to history
        session['conversation_history'].append({
            'role': 'assistant',
            'content': response,
            'timestamp': datetime.now().isoformat()
        })

        return {
            'session_id': session_id,
            'message': response,
            'state': session['state'],
            'progress': self._calculate_progress(session),
            'is_complete': session['state'] == 'complete',
            'final_data': self._get_final_data(session) if session['state'] == 'complete' else None
        }

    def _identify_missing_fields(self, extracted_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Identify which fields are missing or uncertain"""
        missing = []

        # Check vendor name
        if not extracted_data.get('vendor_name') or extracted_data['vendor_name'] == 'Unknown Vendor':
            missing.append({
                'field': 'vendor_name',
                'question': 'What is the vendor/supplier name?',
                'type': 'text',
                'required': True
            })

        # Check invoice number
        if not extracted_data.get('invoice_number'):
            missing.append({
                'field': 'invoice_number',
                'question': 'What is the invoice or receipt number?',
                'type': 'text',
                'required': True
            })

        # Check invoice date
        if not extracted_data.get('invoice_date'):
            missing.append({
                'field': 'invoice_date',
                'question': 'What is the invoice date? (format: YYYY-MM-DD or tell me the date)',
                'type': 'date',
                'required': True
            })

        # Check grand total
        if not extracted_data.get('grand_total') or extracted_data['grand_total'] == 0:
            missing.append({
                'field': 'grand_total',
                'question': 'What is the total amount on the invoice?',
                'type': 'number',
                'required': True
            })

        # Check currency
        if not extracted_data.get('currency') or extracted_data['currency'] == 'USD':
            missing.append({
                'field': 'currency',
                'question': 'What currency is this invoice in? (USD, EUR, GBP, ILS, etc.)',
                'type': 'text',
                'required': False
            })

        # Check subtotal
        if not extracted_data.get('subtotal') or extracted_data['subtotal'] == 0:
            missing.append({
                'field': 'subtotal',
                'question': 'What is the subtotal amount (before tax)?',
                'type': 'number',
                'required': False
            })

        # Check tax amount
        if not extracted_data.get('tax_amount') or extracted_data['tax_amount'] == 0:
            missing.append({
                'field': 'tax_amount',
                'question': 'What is the tax amount?',
                'type': 'number',
                'required': False
            })

        return missing

    def _generate_initial_message(self, session: Dict[str, Any]) -> str:
        """Generate welcoming message with context"""
        file_name = session['file_name']
        extracted = session['extracted_data']
        missing = session['missing_fields']

        message = f"Hi! I received your invoice: **{file_name}**\n\n"

        # Show what was extracted
        if extracted.get('vendor_name') and extracted['vendor_name'] != 'Unknown Vendor':
            message += f"I can see this is from **{extracted['vendor_name']}**. "

        if extracted.get('grand_total') and extracted['grand_total'] > 0:
            currency = extracted.get('currency', 'USD')
            message += f"The total is **{currency} {extracted['grand_total']:.2f}**. "

        message += "\n\n"

        # Explain what's needed
        if missing:
            required_count = sum(1 for f in missing if f['required'])
            optional_count = len(missing) - required_count

            if required_count > 0:
                message += f"I need **{required_count} more details** to process this invoice. "
            if optional_count > 0:
                message += f"There are also {optional_count} optional fields I couldn't extract. "

            message += "\n\nLet me ask you a few quick questions:\n\n"

            # Ask first question
            first_missing = missing[0]
            message += f"**1.** {first_missing['question']}"
            session['current_question'] = first_missing
        else:
            message += "Great! I have all the information I need. Let me confirm the details with you..."
            session['state'] = 'confirming'

        return message

    def _handle_data_collection(self, session: Dict[str, Any], user_message: str) -> str:
        """Handle collecting missing data from user"""
        if not session.get('current_question'):
            return "Something went wrong. Please start over."

        current_q = session['current_question']
        field_name = current_q['field']

        # Use GPT-4 to extract and validate the answer
        extracted_value = self._extract_value_from_message(
            user_message,
            current_q['type'],
            session['ocr_text']
        )

        if extracted_value is None:
            return f"I didn't quite understand that. {current_q['question']}"

        # Store the collected data
        session['collected_data'][field_name] = extracted_value

        # Remove this field from missing list
        session['missing_fields'] = [f for f in session['missing_fields']
                                     if f['field'] != field_name]

        # Check if more fields needed
        if session['missing_fields']:
            next_field = session['missing_fields'][0]
            session['current_question'] = next_field

            response = f"Got it! **{extracted_value}** ✓\n\n"
            response += f"**Next:** {next_field['question']}"
            return response
        else:
            # All data collected, move to confirmation
            session['state'] = 'confirming'
            session['current_question'] = None
            return self._generate_confirmation_message(session)

    def _handle_confirmation(self, session: Dict[str, Any], user_message: str) -> str:
        """Handle confirmation of collected data"""
        user_msg_lower = user_message.lower().strip()

        # Check for affirmative responses
        affirmative = ['yes', 'y', 'correct', 'looks good', 'ok', 'okay', 'confirm',
                      'yep', 'yeah', 'yup', 'sure', 'absolutely', 'perfect']

        # Check for negative responses
        negative = ['no', 'n', 'wrong', 'incorrect', 'fix', 'change', 'edit']

        if any(word in user_msg_lower for word in affirmative):
            session['state'] = 'complete'
            return ("Perfect! ✓ Your invoice is ready to be processed.\n\n"
                   "Click the **'Process Invoice'** button below to complete the upload!")

        elif any(word in user_msg_lower for word in negative):
            # Ask what needs to be changed
            return ("No problem! What would you like to change?\n\n"
                   "Tell me which field and the correct value.\n"
                   "(Example: 'The vendor name should be Acme Corp' or 'Change total to 1500')")

        else:
            # Use GPT-4 to understand if they're making corrections
            correction = self._detect_correction(user_message, session)
            if correction:
                field, value = correction
                session['collected_data'][field] = value
                return (f"Updated! Changed **{field}** to **{value}**\n\n"
                       + self._generate_confirmation_message(session))
            else:
                return ("I'm not sure what you mean. Please say:\n"
                       "- **'Yes'** if everything looks correct\n"
                       "- **'No'** or tell me what to change")

    def _extract_value_from_message(self, message: str, field_type: str,
                                    ocr_text: str) -> Optional[Any]:
        """Use GPT-4 to extract and validate value from user message"""
        if not self.client:
            # Fallback without GPT
            return message.strip()

        try:
            system_prompt = f"""You are a data extraction assistant. Extract the {field_type} value from the user's message.

Rules:
- For dates: Convert to YYYY-MM-DD format (if they say "today" use {datetime.now().strftime('%Y-%m-%d')})
- For numbers: Extract numeric value only (no currency symbols, no commas)
- For text: Extract the clean text value
- If unclear or invalid, return null

Return ONLY the extracted value or null. No explanations."""

            user_prompt = f"User message: {message}\n\nExtract the {field_type} value:"

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Use mini for speed and cost
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=50,
                temperature=0
            )

            value = response.choices[0].message.content.strip()

            # Parse based on type
            if value.lower() == 'null':
                return None

            if field_type == 'number':
                try:
                    return float(value.replace(',', ''))
                except:
                    return None

            return value

        except Exception as e:
            print(f"GPT extraction error: {e}")
            # Fallback to simple extraction
            if field_type == 'number':
                try:
                    import re
                    numbers = re.findall(r'\d+\.?\d*', message)
                    return float(numbers[0]) if numbers else None
                except:
                    return None
            return message.strip()

    def _detect_correction(self, message: str, session: Dict[str, Any]) -> Optional[tuple]:
        """Detect if user is making a correction to a field"""
        if not self.client:
            return None

        try:
            fields_str = ", ".join(session['collected_data'].keys())

            system_prompt = f"""You are a correction detector. The user is reviewing invoice data.

Available fields: {fields_str}

If the user is correcting a field, return: field_name|new_value
If not a correction, return: null

Examples:
- "The vendor name should be Acme Corp" → vendor_name|Acme Corp
- "Change total to 1500" → grand_total|1500
- "Date is 2024-10-26" → invoice_date|2024-10-26"""

            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                max_tokens=50,
                temperature=0
            )

            result = response.choices[0].message.content.strip()

            if result.lower() == 'null' or '|' not in result:
                return None

            field, value = result.split('|', 1)
            return (field.strip(), value.strip())

        except Exception as e:
            print(f"Correction detection error: {e}")
            return None

    def _generate_confirmation_message(self, session: Dict[str, Any]) -> str:
        """Generate confirmation message showing all collected data"""
        extracted = session['extracted_data']
        collected = session['collected_data']

        # Merge data
        final_data = {**extracted, **collected}

        message = "Perfect! Here's what I have:\n\n"
        message += "**Invoice Details:**\n"

        if final_data.get('vendor_name'):
            message += f"• Vendor: **{final_data['vendor_name']}**\n"

        if final_data.get('invoice_number'):
            message += f"• Invoice #: **{final_data['invoice_number']}**\n"

        if final_data.get('invoice_date'):
            message += f"• Date: **{final_data['invoice_date']}**\n"

        if final_data.get('grand_total'):
            currency = final_data.get('currency', 'USD')
            message += f"• Total: **{currency} {final_data['grand_total']:.2f}**\n"

        if final_data.get('subtotal'):
            message += f"• Subtotal: **{final_data['subtotal']:.2f}**\n"

        if final_data.get('tax_amount'):
            message += f"• Tax: **{final_data['tax_amount']:.2f}**\n"

        message += "\n**Is this correct?** (Yes/No)"

        return message

    def _calculate_progress(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate completion progress"""
        total_fields = len(session.get('missing_fields', [])) + len(session.get('collected_data', {}))
        collected_fields = len(session.get('collected_data', {}))

        if total_fields == 0:
            return {'percent': 100, 'collected': 0, 'total': 0}

        percent = int((collected_fields / total_fields) * 100)

        return {
            'percent': percent,
            'collected': collected_fields,
            'total': total_fields
        }

    def _get_final_data(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Get final merged data for processing"""
        return {**session['extracted_data'], **session['collected_data']}

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        return self.sessions.get(session_id)

    def delete_session(self, session_id: str):
        """Delete a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
