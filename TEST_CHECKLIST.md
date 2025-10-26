# Testing Checklist - Verify Improvements

Use this checklist to verify all improvements are working correctly.

---

## 🔧 Pre-Test Setup

- [ ] Server is running (`start_server.bat`)
- [ ] Console shows: `✓ Enhanced OCR initialized: backend=tesseract, AI=openai`
- [ ] Browser open to: http://localhost:5000
- [ ] Have test invoices ready (1 good quality, 1 poor quality)

---

## ✅ Test 1: Basic Upload (Good Quality Invoice)

**Steps:**
1. [ ] Click "Upload" tab
2. [ ] Select a clear, high-quality invoice (PDF or image)
3. [ ] Optionally select Project/Grant codes
4. [ ] Click "Process Document"

**Expected Results:**
- [ ] Upload progress indicator shows
- [ ] Success message appears
- [ ] Console shows:
  ```
  [OCR] Complete. Confidence=90%+
  [AI] AI extraction successful
  [VALIDATE] Flags: 0
  [COMPLETE] Processing finished
  ```
- [ ] Results panel displays:
  - Document ID
  - Summary
  - Filed path
  - No validation flags (or only informational)

**Pass/Fail:** ___________

---

## ✅ Test 2: View Document

**Steps:**
1. [ ] Click "Documents" tab
2. [ ] Wait for documents to load
3. [ ] Click on the document you just uploaded
4. [ ] Modal opens with document details

**Expected Results:**
- [ ] Modal opens successfully (not "Error loading document")
- [ ] All sections visible:
  - Basic Information (doc type, currency, dates)
  - Vendor Information (name, contact details)
  - Invoice Details (number, payment info)
  - Financial Information (subtotal, tax, total)
  - Line Items (if any)
  - NGO Classification (project, grant, fiscal year)
  - Filing Information (path, status)
- [ ] Vendor name is correct
- [ ] Invoice number is correct
- [ ] Amounts match the invoice
- [ ] Dates are correct

**Pass/Fail:** ___________

---

## ✅ Test 3: Extraction Accuracy (Good Image)

**Compare extracted data with actual invoice:**

| Field | Expected | Extracted | Match? |
|-------|----------|-----------|--------|
| Vendor Name | _________ | _________ | [ ] |
| Invoice Number | _________ | _________ | [ ] |
| Invoice Date | _________ | _________ | [ ] |
| Subtotal | _________ | _________ | [ ] |
| Tax Amount | _________ | _________ | [ ] |
| Grand Total | _________ | _________ | [ ] |

**Accuracy Score:** ___/6 fields correct

**Expected:** 5-6 fields correct (83-100%)

**Pass/Fail:** ___________

---

## ✅ Test 4: Poor Quality Invoice

**Steps:**
1. [ ] Upload a poor quality invoice (blurry, low res, or photo)
2. [ ] Watch console output
3. [ ] Review extraction results

**Expected Results:**
- [ ] System still processes (doesn't crash)
- [ ] Console may show:
  ```
  [OCR] Confidence=65-85% (lower)
  [AI] AI extraction successful (AI corrects errors)
  [VALIDATE] Flags: 1-2 (may have flags)
  ```
- [ ] Most data extracted correctly (80-92% accuracy)
- [ ] May have validation flags warning about low confidence

**Accuracy:** ___% (at least 3/6 fields correct = 50%)

**Pass/Fail:** ___________

---

## ✅ Test 5: Image Preprocessing Verification

**Check console for preprocessing:**

```
Look for in console output:
- Image resizing messages (if image was small)
- No preprocessing errors
- OCR confidence improved
```

- [ ] No preprocessing errors in console
- [ ] OCR confidence is reasonable (70%+)
- [ ] System handled image automatically

**Pass/Fail:** ___________

---

## ✅ Test 6: AI Enhancement Verification

**Check console for AI processing:**

```
Expected console output:
[AI] Enhancing extraction with AI...
[AI] AI extraction successful, using AI-parsed data
[PARSE] AI parsing: vendor=..., invoice=..., total=...
```

- [ ] AI enhancement triggered
- [ ] AI extraction successful
- [ ] AI-parsed data used

**Pass/Fail:** ___________

---

## ✅ Test 7: Math Validation

**Check if system validates calculations:**

Upload invoice and verify:
- [ ] Subtotal + Tax = Grand Total (approximately)
- [ ] Sum of line items = Subtotal (approximately)
- [ ] No high-severity math validation flags (unless actual error)

**Pass/Fail:** ___________

---

## ✅ Test 8: Multiple Documents

**Test viewing multiple documents:**
1. [ ] Upload 2-3 different invoices
2. [ ] Go to Documents tab
3. [ ] All documents listed
4. [ ] Click each document
5. [ ] Each opens correctly with unique data

**Expected Results:**
- [ ] All documents appear in list
- [ ] Each document has unique data
- [ ] No mixing of data between documents

**Pass/Fail:** ___________

---

## ✅ Test 9: Different File Formats

**Test various formats:**
- [ ] PDF → Uploads and extracts
- [ ] JPG → Uploads and extracts
- [ ] PNG → Uploads and extracts

**Pass/Fail:** ___________

---

## ✅ Test 10: Error Handling

**Test system handles errors gracefully:**

**Test A: Invalid file**
1. [ ] Try uploading a text file (.txt)
2. [ ] System rejects with clear error message

**Test B: Empty file**
1. [ ] Try uploading empty/corrupted file
2. [ ] System handles gracefully (error message, no crash)

**Test C: Huge file**
1. [ ] Try uploading very large file (>50MB)
2. [ ] System rejects with size limit message

**Pass/Fail:** ___________

---

## 📊 Overall Results Summary

| Test | Result | Notes |
|------|--------|-------|
| 1. Basic Upload | Pass/Fail | |
| 2. View Document | Pass/Fail | |
| 3. Accuracy (Good) | Pass/Fail | |
| 4. Poor Quality | Pass/Fail | |
| 5. Preprocessing | Pass/Fail | |
| 6. AI Enhancement | Pass/Fail | |
| 7. Math Validation | Pass/Fail | |
| 8. Multiple Docs | Pass/Fail | |
| 9. File Formats | Pass/Fail | |
| 10. Error Handling | Pass/Fail | |

**Tests Passed:** ___/10

**Overall Assessment:** ___________

---

## 🐛 If Tests Fail

### View Document Fails (Test 2):
1. Check console for errors
2. Verify document JSON exists in `output/` folder
3. Check browser console (F12) for JavaScript errors
4. Restart server

### Low Accuracy (Tests 3-4):
1. Check image quality (DPI, clarity)
2. Verify Tesseract installed: `tesseract --version`
3. Check OpenAI API key in `.env`
4. Review console for OCR confidence score
5. Try rescanning invoice with better quality

### AI Not Working (Test 6):
1. Check `.env` file has correct API key
2. Verify OpenAI package installed: `pip list | findstr openai`
3. Check API quota at: https://platform.openai.com/usage
4. Review console for specific error messages

### Preprocessing Not Working (Test 5):
1. Check Pillow package installed: `pip list | findstr Pillow`
2. Review console for image processing errors
3. Verify image format is supported

---

## ✅ Success Criteria

**Minimum for Pass:**
- 8/10 tests pass
- View documents works (Test 2)
- Good image accuracy >80% (Test 3)
- No system crashes

**Excellent Performance:**
- 10/10 tests pass
- Good image accuracy >95% (Test 3)
- Poor image accuracy >85% (Test 4)
- All features working smoothly

---

## 📝 Notes Section

Use this space for any observations or issues:

```
Date: ___________
Tester: ___________

Observations:
_____________________________________________
_____________________________________________
_____________________________________________

Issues Found:
_____________________________________________
_____________________________________________
_____________________________________________

Additional Comments:
_____________________________________________
_____________________________________________
_____________________________________________
```

---

## 🎯 After Testing

If all tests pass:
✅ System is ready for production use!
✅ Start processing real invoices
✅ Monitor accuracy over time

If some tests fail:
⚠️ Review failure notes
⚠️ Check troubleshooting sections
⚠️ Consult EXTRACTION_IMPROVEMENTS.md
⚠️ Review console error messages

---

**Happy Testing!** 🚀
