@echo off
echo ============================================================
echo Installing Required Packages
echo ============================================================
echo.

echo Installing OpenAI package...
pip install openai

echo.
echo Installing Tesseract OCR support...
pip install pytesseract Pillow pdf2image

echo.
echo Installing other dependencies...
pip install flask flask-cors werkzeug python-dotenv

echo.
echo ============================================================
echo Installation Complete!
echo ============================================================
echo.
echo Now you need to:
echo 1. Install Tesseract OCR application:
echo    https://github.com/UB-Mannheim/tesseract/wiki
echo.
echo 2. (Optional) Install Poppler for PDF support:
echo    https://github.com/oschwartz10612/poppler-windows/releases/
echo.
echo 3. Restart the server:
echo    start_server.bat
echo.
pause
