@echo off
echo ================================================================
echo   NGO-InvoiceFiler - Web Application Launcher
echo ================================================================
echo.
echo Starting Flask server on http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo ================================================================
echo.

REM Install dependencies if needed
python -m pip install flask flask-cors werkzeug --quiet

REM Start the Flask server
python web_app.py

pause
