# 🚀 NGO-InvoiceFiler - Quick Start (5 Minutes)

## Step 1: Install Dependencies (30 seconds)

```bash
pip install flask flask-cors werkzeug
```

## Step 2: Start the Server (10 seconds)

**Windows:**
```bash
start_server.bat
```

**Mac/Linux:**
```bash
chmod +x start_server.sh
./start_server.sh
```

**You should see:**
```
╔══════════════════════════════════════════════════════════════╗
║            NGO-InvoiceFiler Web Application                  ║
║                                                              ║
║  Starting server on http://localhost:5000                    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

 * Running on http://0.0.0.0:5000
```

## Step 3: Open in Browser (5 seconds)

Open your web browser and go to:
```
http://localhost:5000
```

## Step 4: Explore the Interface (2 minutes)

### 📊 Dashboard (Default Page)
- View statistics: total documents, amounts, status counts
- See charts showing spending by project and status
- Browse recent documents

### 📤 Upload a Document (1 minute)
1. Click **"Upload"** in the navigation
2. Drag & drop a PDF/image invoice OR click to browse
3. (Optional) Select project and grant
4. Click **"Process Document"**
5. View results with document ID, summary, and validation flags

### 📁 Browse Documents (1 minute)
1. Click **"Documents"** in navigation
2. See all processed documents in a table
3. Use search or filters to find specific documents
4. Click **"View"** on any document to see full details

### 📈 Generate Reports (30 seconds)
1. Click **"Reports"** in navigation
2. Select fiscal year or project
3. Click **"Generate Report"**
4. View summary, breakdowns, and top vendors

### 💾 Export Data (30 seconds)
1. Click **"Export"** in navigation
2. Choose format: CSV, Excel, or JSON
3. Apply optional filters
4. Click **"Export Ledger"**
5. File downloads automatically

---

## 🎯 First Document Upload Tutorial

### Complete Example (Step-by-Step)

1. **Prepare a test invoice:**
   - Any PDF invoice or receipt
   - Or a photo of a receipt (JPG/PNG)

2. **Go to Upload page**

3. **Upload the file:**
   - Drag file to the upload zone
   - OR click the zone and select file

4. **Configure options (optional):**
   - Select "EDU001 - Education Program"
   - Select "GR2023" grant

5. **Process:**
   - Click blue "Process Document" button
   - Wait 1-2 seconds

6. **View results:**
   - ✅ Document ID: `550e8400-e29b-41d4-a716-446655440000`
   - 📄 Summary: "Invoice from Acme Corp dated 2024-03-15 for 1755.00 ILS..."
   - 📁 Filed to: `2023-2024/EDU001-Education/GR2023-UNICEF/...`
   - ⚠️ Any validation flags (if present)

7. **View in dashboard:**
   - Click "Dashboard" to see updated stats
   - Document appears in "Recent Documents" table

---

## 🎨 Interface Overview

```
┌────────────────────────────────────────────────────────────┐
│  🧭 Navigation Bar                                         │
│  [Dashboard] [Upload] [Documents] [Reports] [Export]       │
│                                       Role: [Contributor ▼] │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  📊 DASHBOARD PAGE (Default)                              │
│  ┌──────────┬──────────┬──────────┬──────────┐           │
│  │ 25 Docs  │ $125K    │ 8 Review │ 10 OK    │           │
│  └──────────┴──────────┴──────────┴──────────┘           │
│                                                            │
│  ┌──────────────────┬──────────────────┐                 │
│  │ By Project Chart │ By Status Chart  │                 │
│  └──────────────────┴──────────────────┘                 │
│                                                            │
│  📜 Recent Documents Table                                │
│  Date | Vendor | Amount | Project | Status                │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 💡 Common Tasks

### Task 1: Find all documents from a specific vendor
1. Go to **Documents** page
2. Type vendor name in search box
3. Click **Search**
4. Results show instantly

### Task 2: See all approved documents for a project
1. Go to **Documents** page
2. Filter by Project: "EDU001"
3. Filter by Status: "approved"
4. Click **Apply**

### Task 3: Export all education project expenses
1. Go to **Export** page
2. Format: CSV
3. Project: "EDU001 - Education Program"
4. Click **Export Ledger**
5. Open downloaded CSV in Excel

### Task 4: Approve a document (Approver role)
1. Switch role to "Approver" (top-right dropdown)
2. Go to **Documents** page
3. Filter by Status: "needs_review"
4. Click **View** on a document
5. Click green **Approve Document** button
6. Enter your name
7. Done! Document status → "approved"

### Task 5: Generate fiscal year report
1. Go to **Reports** page
2. Select "2023-2024" from dropdown
3. Click **Generate Report**
4. View summary, project breakdown, top vendors

---

## 🎭 Role Switching

Use the **Role Selector** (top-right) to test different permissions:

- **Viewer**: Browse only, PII redacted
- **Contributor**: Can upload documents
- **Approver**: Can approve documents
- **Admin**: Full access, can export with PII

---

## 🐛 Troubleshooting

### Server won't start?
```bash
# Make sure Python and pip are installed
python --version

# Install dependencies again
pip install flask flask-cors werkzeug
```

### Page not loading?
- Check server terminal shows "Running on http://0.0.0.0:5000"
- Try http://127.0.0.1:5000 instead
- Clear browser cache (Ctrl+F5)

### Upload fails?
- Check file size < 50MB
- Use only PDF, PNG, JPG, JPEG
- Check server terminal for error messages

### Port 5000 already in use?
Edit `web_app.py` line 273:
```python
app.run(host='0.0.0.0', port=8000, debug=True)
```
Then use http://localhost:8000

---

## 📚 Next Steps

1. **Customize configuration:**
   - Edit `create_default_org_profile()` in `main.py`
   - Add your projects, grants, vendors

2. **Test with real documents:**
   - Process PDF invoices
   - Upload receipt photos
   - Test multilingual documents (Arabic, Hebrew)

3. **Run test suite:**
   ```bash
   python test_suite.py
   ```

4. **Explore CLI:**
   ```bash
   python cli.py --help
   python cli.py stats
   ```

5. **Read full documentation:**
   - `README.md` - Complete system docs
   - `WEB_README.md` - Web app details
   - `DEMO.md` - Detailed examples

---

## 🎉 You're Ready!

Your NGO-InvoiceFiler system is now running with:

✅ Modern web interface
✅ RESTful API backend
✅ Document processing pipeline
✅ Validation engine
✅ Ledger management
✅ Reports and exports
✅ Security features
✅ Audit trail

**Enjoy processing invoices with confidence!** 🚀
