@echo off
echo ============================================================
echo NGO-InvoiceFiler: Fixed Installation Script
echo ============================================================
echo.

echo Checking Python installation...
python --version
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)
echo.

echo Installing packages using python -m pip...
echo.

python -m pip install --upgrade pip
python -m pip install openai
python -m pip install pytesseract
python -m pip install Pillow
python -m pip install pdf2image
python -m pip install flask
python -m pip install flask-cors
python -m pip install werkzeug
python -m pip install python-dotenv

echo.
echo ============================================================
echo Testing installation...
echo ============================================================
echo.

python -c "import openai; print('✓ OpenAI installed')"
python -c "import PIL; print('✓ Pillow installed')"
python -c "import flask; print('✓ Flask installed')"
python -c "from dotenv import load_dotenv; print('✓ python-dotenv installed')"

echo.
echo ============================================================
echo Installation Complete!
echo ============================================================
echo.
echo Next steps:
echo.
echo 1. Install Tesseract OCR:
echo    https://github.com/UB-Mannheim/tesseract/wiki
echo    Download and run: tesseract-ocr-w64-setup-v5.3.3.exe
echo.
echo 2. (Optional) Install Poppler for PDF support:
echo    https://github.com/oschwartz10612/poppler-windows/releases/
echo.
echo 3. Start the server:
echo    start_server.bat
echo.
echo 4. Open browser:
echo    http://localhost:5000
echo.
echo ============================================================
pause
