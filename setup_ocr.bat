@echo off
echo ============================================================
echo NGO-InvoiceFiler: OCR Setup Script
echo ============================================================
echo.

echo Step 1: Installing Python dependencies...
pip install flask flask-cors werkzeug pytesseract Pillow pdf2image anthropic
echo.

echo Step 2: Creating .env configuration file...
if not exist .env (
    copy .env.example .env
    echo ✓ Created .env file - Please edit it to add your API keys
) else (
    echo ℹ .env file already exists - skipping
)
echo.

echo ============================================================
echo Setup Complete!
echo ============================================================
echo.
echo Next steps:
echo 1. Install Tesseract OCR:
echo    Download from: https://github.com/UB-Mannheim/tesseract/wiki
echo    Run installer and note the installation path
echo.
echo 2. Install Poppler (for PDF support):
echo    Download from: https://github.com/oschwartz10612/poppler-windows/releases/
echo    Extract and add bin folder to PATH
echo.
echo 3. Edit .env file:
echo    - Set OCR_BACKEND=tesseract
echo    - (Optional) Add ANTHROPIC_API_KEY for AI enhancement
echo.
echo 4. Start the server:
echo    start_server.bat
echo.
echo For detailed instructions, see: OCR_SETUP_GUIDE.md
echo ============================================================
pause
