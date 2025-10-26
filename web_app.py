"""
NGO-InvoiceFiler: Flask Web Application
REST API backend for the web interface running on localhost.
"""

from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
from pathlib import Path
import json
import os
from datetime import datetime
from werkzeug.utils import secure_filename

from main import InvoiceFilerOrchestrator, create_default_org_profile
from ledger import ReportGenerator
from security import SecureDocumentHandler
from chat_assistant import InvoiceChatAssistant


app = Flask(__name__, static_folder='web', static_url_path='')
CORS(app)  # Enable CORS for development

# Configuration
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output'
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'heic', 'webp'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Initialize orchestrator with OCR configuration
org_profile = create_default_org_profile()

# Load OCR configuration from environment
ocr_backend = os.getenv('OCR_BACKEND', 'tesseract')
ai_backend = os.getenv('AI_BACKEND', None)
api_key = os.getenv('ANTHROPIC_API_KEY') or os.getenv('OPENAI_API_KEY')

print(f"\n{'='*60}")
print(f"Initializing NGO-InvoiceFiler")
print(f"{'='*60}")
print(f"OCR Backend: {ocr_backend}")
print(f"AI Backend: {ai_backend or 'None (regex parsing only)'}")
print(f"{'='*60}\n")

orchestrator = InvoiceFilerOrchestrator(
    org_profile,
    ocr_backend=ocr_backend,
    ai_backend=ai_backend,
    api_key=api_key
)
security_handler = SecureDocumentHandler()
chat_assistant = InvoiceChatAssistant(api_key=api_key)


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Serve the main page"""
    return send_from_directory('web', 'index.html')


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'NGO-InvoiceFiler',
        'version': '1.0'
    })


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get organization configuration"""
    return jsonify({
        'ngo_name': org_profile.ngo_name,
        'default_currency': org_profile.default_currency,
        'fiscal_year_start_month': org_profile.fiscal_year_start_month,
        'projects': org_profile.project_codes,
        'grants': list(org_profile.grant_dictionary.keys()),
        'categories': list(org_profile.category_keywords.keys())
    })


@app.route('/api/upload', methods=['POST'])
def upload_document():
    """Upload and process a document"""
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Only PDF and images allowed.'}), 400

        # Get optional parameters
        project_code = request.form.get('project_code')
        grant_code = request.form.get('grant_code')
        user_role = request.form.get('user_role', 'contributor')

        # Secure filename
        filename = secure_filename(file.filename)

        # Read file bytes
        file_bytes = file.read()

        # Check file size
        if len(file_bytes) > MAX_FILE_SIZE:
            return jsonify({'error': f'File size exceeds {MAX_FILE_SIZE} bytes'}), 400

        # Build user hints
        user_hints = {}
        if project_code:
            user_hints['project_code'] = project_code
        if grant_code:
            user_hints['grant_code'] = grant_code

        # Process document
        result = orchestrator.process_document(
            file_bytes=file_bytes,
            file_name=filename,
            user_hints=user_hints,
            user_role=user_role
        )

        # Prepare response
        if result['success']:
            # Redact PII for UI
            doc_dict = result['processed_document']
            redacted_doc = security_handler.prepare_for_ui(doc_dict, user_role)

            return jsonify({
                'success': True,
                'doc_id': result['doc_id'],
                'summary': result['summary'],
                'folder_path': result['folder_path'],
                'file_name': result['file_name'],
                'document': redacted_doc,
                'ledger_row': result['ledger_row']
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Unknown error'),
                'doc_id': result.get('doc_id')
            }), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/documents', methods=['GET'])
def list_documents():
    """List all documents with optional filters"""
    try:
        # Get query parameters
        project = request.args.get('project')
        grant = request.args.get('grant')
        fiscal_year = request.args.get('fiscal_year')
        status = request.args.get('status')
        vendor = request.args.get('vendor')
        limit = int(request.args.get('limit', 100))

        # Build filters
        filters = {}
        if project:
            filters['project_code'] = project
        if grant:
            filters['grant_code'] = grant
        if fiscal_year:
            filters['fiscal_year'] = fiscal_year
        if status:
            filters['status'] = status
        if vendor:
            filters['vendor'] = vendor

        # Query ledger
        results = orchestrator.ledger_manager.query(filters if filters else None)

        # Limit results
        results = results[:limit]

        return jsonify({
            'success': True,
            'count': len(results),
            'documents': results
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/documents/<doc_id>', methods=['GET'])
def get_document(doc_id):
    """Get a specific document by ID"""
    try:
        user_role = request.args.get('role', 'viewer')
        redact = request.args.get('redact', 'true').lower() == 'true'

        doc = orchestrator.get_document(doc_id, user_role, redact_pii=redact)

        if doc:
            return jsonify({
                'success': True,
                'document': doc
            })
        else:
            return jsonify({'error': 'Document not found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/documents/<doc_id>/approve', methods=['POST'])
def approve_document(doc_id):
    """Approve a document"""
    try:
        data = request.json
        approver = data.get('approver')
        user_role = data.get('user_role', 'approver')

        if not approver:
            return jsonify({'error': 'Approver name required'}), 400

        result = orchestrator.approve_document(doc_id, approver, user_role)

        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get ledger statistics"""
    try:
        stats = orchestrator.ledger_manager.get_summary_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/reports/fiscal-year/<fiscal_year>', methods=['GET'])
def get_fiscal_year_report(fiscal_year):
    """Generate fiscal year report"""
    try:
        report_gen = ReportGenerator(orchestrator.ledger_manager)
        report = report_gen.generate_fiscal_year_report(fiscal_year)

        return jsonify({
            'success': True,
            'report': report
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/reports/project/<project_code>', methods=['GET'])
def get_project_report(project_code):
    """Generate project report"""
    try:
        report_gen = ReportGenerator(orchestrator.ledger_manager)
        report = report_gen.generate_project_report(project_code)

        return jsonify({
            'success': True,
            'report': report
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/export', methods=['GET'])
def export_ledger():
    """Export ledger to CSV/Excel/JSON"""
    try:
        format = request.args.get('format', 'csv')
        project = request.args.get('project')
        grant = request.args.get('grant')
        fiscal_year = request.args.get('fiscal_year')
        status = request.args.get('status')

        # Build filters
        filters = {}
        if project:
            filters['project_code'] = project
        if grant:
            filters['grant_code'] = grant
        if fiscal_year:
            filters['fiscal_year'] = fiscal_year
        if status:
            filters['status'] = status

        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"{OUTPUT_FOLDER}/ledger_export_{timestamp}.{format}"

        # Export
        file_path = orchestrator.export_ledger(
            format=format,
            output_file=output_file,
            filters=filters if filters else None
        )

        # Send file
        return send_file(
            file_path,
            as_attachment=True,
            download_name=f"ledger_export_{timestamp}.{format}"
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/search', methods=['GET'])
def search_documents():
    """Search documents by keyword"""
    try:
        query = request.args.get('q', '').lower()
        limit = int(request.args.get('limit', 50))

        if not query:
            return jsonify({'error': 'Search query required'}), 400

        # Get all documents
        all_docs = orchestrator.ledger_manager.get_all_entries()

        # Simple keyword search in vendor and invoice_number
        results = []
        for doc in all_docs:
            vendor = doc.get('vendor', '').lower()
            invoice = doc.get('invoice_number', '').lower()
            if query in vendor or query in invoice:
                results.append(doc)

            if len(results) >= limit:
                break

        return jsonify({
            'success': True,
            'count': len(results),
            'results': results
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/audit/<doc_id>', methods=['GET'])
def get_audit_trail(doc_id):
    """Get audit trail for a document"""
    try:
        history = orchestrator.audit_trail.get_document_history(doc_id)

        return jsonify({
            'success': True,
            'doc_id': doc_id,
            'audit_trail': history
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================================
# CHAT ASSISTANT ENDPOINTS
# ============================================================================

@app.route('/api/chat/upload', methods=['POST'])
def chat_upload():
    """
    Start a chat session for invoice upload
    Extracts what it can, then creates interactive session for missing data
    """
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type'}), 400

        # Get user role
        user_role = request.form.get('user_role', 'contributor')

        # Secure filename
        filename = secure_filename(file.filename)

        # Read file bytes
        file_bytes = file.read()

        # Check file size
        if len(file_bytes) > MAX_FILE_SIZE:
            return jsonify({'error': f'File size exceeds {MAX_FILE_SIZE} bytes'}), 400

        # Extract data using OCR + AI
        ocr_text, ocr_confidence, detected_lang = orchestrator.ocr_engine.extract_text(
            file_bytes, language='auto'
        )

        # Try AI enhancement
        ai_data = None
        if hasattr(orchestrator.ocr_engine, 'enhance_with_ai'):
            if orchestrator.ocr_engine.ai_client:
                ai_result = orchestrator.ocr_engine.enhance_with_ai(ocr_text, file_bytes)
                if ai_result.get('success'):
                    ai_data = ai_result['data']

        # Use AI data or fallback to empty
        extracted_data = ai_data if ai_data else {
            'vendor_name': None,
            'invoice_number': None,
            'invoice_date': None,
            'grand_total': 0,
            'currency': 'USD',
            'subtotal': 0,
            'tax_amount': 0
        }

        # Generate session ID
        import uuid
        session_id = str(uuid.uuid4())

        # Create chat session
        session_data = chat_assistant.create_session(
            session_id=session_id,
            extracted_data=extracted_data,
            file_name=filename,
            ocr_text=ocr_text
        )

        # Store file bytes temporarily (for later processing)
        temp_file_path = f"{UPLOAD_FOLDER}/{session_id}_{filename}"
        with open(temp_file_path, 'wb') as f:
            f.write(file_bytes)

        # Add file path to session
        session = chat_assistant.get_session(session_id)
        if session:
            session['temp_file_path'] = temp_file_path
            session['user_role'] = user_role

        return jsonify({
            'success': True,
            **session_data
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat/message', methods=['POST'])
def chat_message():
    """
    Send message to chat assistant
    """
    try:
        data = request.json
        session_id = data.get('session_id')
        message = data.get('message')

        if not session_id or not message:
            return jsonify({'error': 'Missing session_id or message'}), 400

        # Send message to chat assistant
        response = chat_assistant.send_message(session_id, message)

        return jsonify({
            'success': True,
            **response
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat/process', methods=['POST'])
def chat_process():
    """
    Process invoice with collected data from chat session
    """
    try:
        data = request.json
        session_id = data.get('session_id')

        if not session_id:
            return jsonify({'error': 'Missing session_id'}), 400

        # Get session
        session = chat_assistant.get_session(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404

        if session['state'] != 'complete':
            return jsonify({'error': 'Session not complete. Continue conversation first.'}), 400

        # Get final data
        final_data = chat_assistant._get_final_data(session)

        # Read file bytes
        temp_file_path = session.get('temp_file_path')
        if not temp_file_path or not os.path.exists(temp_file_path):
            return jsonify({'error': 'File not found'}), 404

        with open(temp_file_path, 'rb') as f:
            file_bytes = f.read()

        # Build user hints from collected data
        user_hints = {}
        if final_data.get('vendor_name'):
            user_hints['vendor'] = final_data['vendor_name']
        if final_data.get('invoice_number'):
            user_hints['invoice_number'] = final_data['invoice_number']

        # Process document with collected data
        # We'll inject the collected data directly
        user_role = session.get('user_role', 'contributor')

        result = orchestrator.process_document(
            file_bytes=file_bytes,
            file_name=session['file_name'],
            user_hints=user_hints,
            user_role=user_role
        )

        # Clean up temporary file
        try:
            os.remove(temp_file_path)
        except:
            pass

        # Delete session
        chat_assistant.delete_session(session_id)

        # Prepare response
        if result['success']:
            doc_dict = result['processed_document']
            redacted_doc = security_handler.prepare_for_ui(doc_dict, user_role)

            return jsonify({
                'success': True,
                'doc_id': result['doc_id'],
                'summary': result['summary'],
                'folder_path': result['folder_path'],
                'file_name': result['file_name'],
                'document': redacted_doc,
                'ledger_row': result['ledger_row']
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Unknown error')
            }), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat/session/<session_id>', methods=['GET'])
def get_chat_session(session_id):
    """Get chat session data"""
    try:
        session = chat_assistant.get_session(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404

        return jsonify({
            'success': True,
            'session': {
                'session_id': session['session_id'],
                'file_name': session['file_name'],
                'state': session['state'],
                'progress': chat_assistant._calculate_progress(session),
                'conversation_history': session['conversation_history']
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/documents/<doc_id>/file', methods=['GET'])
def get_document_file(doc_id):
    """
    Get the original uploaded file (PDF/image) for a document
    """
    try:
        # Get document from ledger to find file path
        entry = orchestrator.ledger_manager.get_entry_by_id(doc_id)
        if not entry:
            return jsonify({'error': 'Document not found'}), 404

        # Construct file path
        file_path = entry.get('file_path')
        file_name = entry.get('file_name')

        if not file_path or not file_name:
            return jsonify({'error': 'File information not found'}), 404

        # Full path to file
        full_path = Path(file_path) / file_name

        if not full_path.exists():
            return jsonify({'error': 'File not found on disk'}), 404

        # Serve the file
        return send_file(
            full_path,
            as_attachment=False,  # Display in browser
            download_name=file_name
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/documents/<doc_id>/download', methods=['GET'])
def download_document_file(doc_id):
    """
    Download the original uploaded file
    """
    try:
        entry = orchestrator.ledger_manager.get_entry_by_id(doc_id)
        if not entry:
            return jsonify({'error': 'Document not found'}), 404

        file_path = entry.get('file_path')
        file_name = entry.get('file_name')

        if not file_path or not file_name:
            return jsonify({'error': 'File information not found'}), 404

        full_path = Path(file_path) / file_name

        if not full_path.exists():
            return jsonify({'error': 'File not found on disk'}), 404

        return send_file(
            full_path,
            as_attachment=True,  # Force download
            download_name=file_name
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("""
╔══════════════════════════════════════════════════════════════╗
║            NGO-InvoiceFiler Web Application                  ║
║                                                              ║
║  Starting server on http://localhost:5000                    ║
║                                                              ║
║  API Endpoints:                                              ║
║    POST   /api/upload          - Upload document            ║
║    GET    /api/documents       - List documents             ║
║    GET    /api/documents/:id   - Get document               ║
║    POST   /api/documents/:id/approve - Approve document     ║
║    GET    /api/stats           - Statistics                 ║
║    GET    /api/reports/*       - Reports                    ║
║    GET    /api/export          - Export ledger              ║
║    GET    /api/search          - Search documents           ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)

    app.run(host='0.0.0.0', port=5000, debug=True)
