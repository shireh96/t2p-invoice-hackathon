@echo off
echo ============================================================
echo NGO-InvoiceFiler: Installation with OpenAI GPT-4
echo ============================================================
echo.

echo Installing all required packages...
echo.

pip install flask flask-cors werkzeug python-dotenv pytesseract Pillow pdf2image openai

echo.
echo Testing OpenAI API connection...
echo.
python test_openai_connection.py
echo.
echo ============================================================
echo Installation Complete!
echo ============================================================
echo.
echo Your .env file has been configured with your OpenAI API key.
echo.
echo Next steps:
echo.
echo 1. Install Tesseract OCR (required):
echo    Windows: https://github.com/UB-Mannheim/tesseract/wiki
echo    Download and run the installer
echo.
echo 2. (Optional) Install Poppler for PDF support:
echo    Download: https://github.com/oschwartz10612/poppler-windows/releases/
echo    Extract and add bin folder to PATH
echo.
echo 3. Start the server:
echo    start_server.bat
echo.
echo 4. Test by uploading an invoice at:
echo    http://localhost:5000
echo.
echo Your system will use:
echo   - Tesseract OCR for text extraction
echo   - OpenAI GPT-4o for intelligent data parsing
echo   - Hybrid approach for best accuracy
echo.
echo ============================================================
pause
