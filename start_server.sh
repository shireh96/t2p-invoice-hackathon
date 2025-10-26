#!/bin/bash

echo "================================================================"
echo "  NGO-InvoiceFiler - Web Application Launcher"
echo "================================================================"
echo ""
echo "Starting Flask server on http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo "================================================================"
echo ""

# Install dependencies if needed
pip install flask flask-cors werkzeug --quiet

# Start the Flask server
python3 web_app.py
