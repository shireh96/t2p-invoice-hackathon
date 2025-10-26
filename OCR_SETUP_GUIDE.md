# OCR Setup Guide for NGO-InvoiceFiler

This guide will help you set up OCR (Optical Character Recognition) and AI-based document understanding for the NGO-InvoiceFiler system.

## Overview

The system now supports three levels of document processing:

1. **Simulation Mode** (Default, no dependencies) - For testing only
2. **Tesseract OCR** (Local, free) - Good accuracy for typed documents
3. **AI-Enhanced** (Claude/GPT-4) - Best accuracy, understands context

## Quick Start

### Option 1: Tesseract OCR Only (Recommended for Getting Started)

#### Step 1: Install Tesseract

**Windows:**
```bash
# Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
# Run the installer (tesseract-ocr-w64-setup-v5.3.3.exe or newer)
# During installation, note the installation path (usually C:\Program Files\Tesseract-OCR)
```

**Mac:**
```bash
brew install tesseract
```

**Linux:**
```bash
sudo apt-get install tesseract-ocr
# For additional languages:
sudo apt-get install tesseract-ocr-ara  # Arabic
sudo apt-get install tesseract-ocr-heb  # Hebrew
```

#### Step 2: Install Python Dependencies
```bash
pip install pytesseract Pillow pdf2image
```

**Windows users also need poppler:**
- Download poppler from: https://github.com/oschwartz10612/poppler-windows/releases/
- Extract to a folder (e.g., `C:\poppler`)
- Add `C:\poppler\Library\bin` to your PATH environment variable

#### Step 3: Configure Tesseract Path (Windows only, if needed)
```bash
# Create a .env file from the example
copy .env.example .env

# Edit .env and add (if Tesseract is not in PATH):
# TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe
```

#### Step 4: Set OCR Backend
In your `.env` file:
```bash
OCR_BACKEND=tesseract
AI_BACKEND=
```

### Option 2: AI-Enhanced (Best Accuracy)

#### For Claude (Recommended)

1. Get your Claude API key from: https://console.anthropic.com/
2. Create or edit `.env` file:
```bash
OCR_BACKEND=tesseract
AI_BACKEND=claude
ANTHROPIC_API_KEY=your_api_key_here
```

3. Install dependencies:
```bash
pip install anthropic pytesseract Pillow pdf2image
```

#### For OpenAI GPT-4 Vision

1. Get your OpenAI API key from: https://platform.openai.com/
2. Create or edit `.env` file:
```bash
OCR_BACKEND=tesseract
AI_BACKEND=openai
OPENAI_API_KEY=your_api_key_here
```

3. Install dependencies:
```bash
pip install openai pytesseract Pillow pdf2image
```

## Testing Your Setup

### Test 1: Verify Tesseract Installation
```bash
# Open command prompt / terminal
tesseract --version
# Should show: tesseract v5.x.x
```

### Test 2: Test Python Integration
```python
# Create test_ocr.py
from PIL import Image
import pytesseract

# Windows users may need:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

print("Tesseract version:", pytesseract.get_tesseract_version())
print("Available languages:", pytesseract.get_languages())
```

Run: `python test_ocr.py`

### Test 3: Upload a Test Invoice
1. Start the server: `start_server.bat` (Windows) or `./start_server.sh` (Linux/Mac)
2. Open browser: http://localhost:5000
3. Upload a test invoice
4. Check the console output for OCR results

## Troubleshooting

### Tesseract Not Found
**Windows:**
```bash
# Add to .env:
TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe
```

Or add Tesseract to PATH:
- Right-click "This PC" → Properties → Advanced System Settings
- Environment Variables → System Variables → Path → Edit
- Add: `C:\Program Files\Tesseract-OCR`

**Mac/Linux:**
```bash
which tesseract
# Should show: /usr/local/bin/tesseract or similar
```

### PDF Conversion Fails
You need poppler-utils:

**Windows:**
- Download: https://github.com/oschwartz10612/poppler-windows/releases/
- Extract and add `bin` folder to PATH

**Mac:**
```bash
brew install poppler
```

**Linux:**
```bash
sudo apt-get install poppler-utils
```

### Poor OCR Quality
1. **Use higher DPI**: Edit `ocr_parser_enhanced.py` line with `dpi=300` → change to `dpi=600`
2. **Ensure good image quality**: Scan at 300 DPI minimum
3. **Enable AI backend**: Claude/GPT-4 Vision will correct OCR errors
4. **Try different languages**: Edit language detection in `_map_language_code()`

### AI API Errors
- **Rate limiting**: Add delays between requests
- **Invalid API key**: Check `.env` file for correct key
- **Quota exceeded**: Check your API billing/usage

## Language Support

Tesseract supports 100+ languages. To add languages:

**Windows:**
During Tesseract installation, select additional language packs

**Mac:**
```bash
brew install tesseract-lang
```

**Linux:**
```bash
# Arabic
sudo apt-get install tesseract-ocr-ara

# Hebrew
sudo apt-get install tesseract-ocr-heb

# French
sudo apt-get install tesseract-ocr-fra

# Spanish
sudo apt-get install tesseract-ocr-spa
```

## Performance Tips

### Speed Optimization
1. **Reduce DPI** for faster processing (300 DPI is usually sufficient)
2. **Disable AI** if processing many documents (use only for critical docs)
3. **Process in batches** during off-hours

### Accuracy Optimization
1. **Increase DPI** to 600 for small text
2. **Enable AI backend** for complex documents
3. **Pre-process images**: remove noise, increase contrast
4. **Use correct language** in OCR settings

## Cost Considerations

### Free Options
- **Tesseract**: Completely free, unlimited
- **Simulation**: Free, but doesn't actually read documents

### Paid Options (Pay-per-use)
- **Claude API**: ~$0.003 per image (very affordable)
- **OpenAI GPT-4 Vision**: ~$0.01-0.02 per image
- **Google Cloud Vision**: ~$1.50 per 1000 images
- **AWS Textract**: ~$1.50 per 1000 pages

### Recommended Setup by Use Case

**Small NGO (<100 invoices/month):**
- Tesseract OCR + Claude AI for verification
- Cost: ~$1-5/month

**Medium NGO (100-1000 invoices/month):**
- Tesseract OCR + selective AI for complex documents
- Cost: ~$10-30/month

**Large NGO (>1000 invoices/month):**
- Tesseract OCR + batch AI processing
- Consider Google Cloud Vision or AWS Textract
- Cost: ~$50-200/month

## Next Steps

1. ✅ Install Tesseract
2. ✅ Install Python dependencies: `pip install -r requirements.txt`
3. ✅ Create `.env` file from `.env.example`
4. ✅ Configure OCR settings in `.env`
5. ✅ Restart server: `start_server.bat`
6. ✅ Test with a real invoice
7. ✅ (Optional) Add Claude API key for AI enhancement

## Support

If you encounter issues:
1. Check this guide's Troubleshooting section
2. Review console output for error messages
3. Test Tesseract independently: `tesseract --version`
4. Verify Python packages: `pip list | grep tesseract`

For additional help, check the project documentation or GitHub issues.
