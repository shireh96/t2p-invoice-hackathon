// NGO-InvoiceFiler - Frontend JavaScript Application

const API_BASE = 'http://localhost:5000/api';

// State
let appState = {
    config: null,
    currentPage: 'dashboard',
    currentRole: 'contributor',
    selectedFile: null,
    currentDocId: null
};

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
    setupEventListeners();
    loadConfig();
});

function initializeApp() {
    // Load dashboard by default
    showPage('dashboard');
    loadDashboard();
}

function setupEventListeners() {
    // Navigation
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const page = e.currentTarget.dataset.page;
            showPage(page);
        });
    });

    // User role selector
    document.getElementById('userRole').addEventListener('change', (e) => {
        appState.currentRole = e.target.value;
        showToast(`Switched to ${e.target.value} role`, 'info');
    });

    // Upload page
    const uploadZone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('fileInput');

    uploadZone.addEventListener('click', () => fileInput.click());
    uploadZone.addEventListener('dragover', handleDragOver);
    uploadZone.addEventListener('dragleave', handleDragLeave);
    uploadZone.addEventListener('drop', handleDrop);

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });

    document.getElementById('uploadBtn').addEventListener('click', uploadDocument);

    // Documents page
    document.getElementById('searchBtn').addEventListener('click', searchDocuments);
    document.getElementById('applyFilters').addEventListener('click', loadDocuments);
    document.getElementById('clearFilters').addEventListener('click', clearFilters);

    // Reports page
    document.getElementById('generateFYReport').addEventListener('click', generateFiscalYearReport);
    document.getElementById('generateProjectReport').addEventListener('click', generateProjectReport);

    // Export page
    document.getElementById('exportBtn').addEventListener('click', exportLedger);

    // Modal
    document.querySelectorAll('.close, .close-modal').forEach(el => {
        el.addEventListener('click', closeModal);
    });

    document.getElementById('approveDocBtn').addEventListener('click', approveDocument);

    // Close modal on outside click
    document.getElementById('docModal').addEventListener('click', (e) => {
        if (e.target.id === 'docModal') closeModal();
    });
}

// Page Navigation
function showPage(pageName) {
    // Update nav
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
        if (link.dataset.page === pageName) {
            link.classList.add('active');
        }
    });

    // Update pages
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    document.getElementById(`${pageName}-page`).classList.add('active');

    appState.currentPage = pageName;

    // Load page data
    switch(pageName) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'upload':
            // Already initialized
            break;
        case 'documents':
            loadDocuments();
            break;
        case 'reports':
            // Reports load on button click
            break;
        case 'export':
            // Export loads on button click
            break;
    }
}

// Load Configuration
async function loadConfig() {
    try {
        const response = await fetch(`${API_BASE}/config`);
        const data = await response.json();
        appState.config = data;

        // Populate dropdowns
        populateProjectDropdowns(data.projects);
        populateGrantDropdowns(data.grants);
    } catch (error) {
        console.error('Error loading config:', error);
    }
}

function populateProjectDropdowns(projects) {
    const dropdowns = [
        'projectCode', 'filterProject', 'exportProject', 'projectReportSelect'
    ];

    dropdowns.forEach(id => {
        const select = document.getElementById(id);
        if (!select) return;

        Object.entries(projects).forEach(([code, name]) => {
            const option = document.createElement('option');
            option.value = code;
            option.textContent = `${code} - ${name}`;
            select.appendChild(option);
        });
    });
}

function populateGrantDropdowns(grants) {
    const dropdowns = ['grantCode', 'filterGrant', 'exportGrant'];

    dropdowns.forEach(id => {
        const select = document.getElementById(id);
        if (!select) return;

        grants.forEach(grant => {
            const option = document.createElement('option');
            option.value = grant;
            option.textContent = grant;
            select.appendChild(option);
        });
    });
}

// Dashboard
async function loadDashboard() {
    try {
        // Load statistics
        const statsResponse = await fetch(`${API_BASE}/stats`);
        const statsData = await statsResponse.json();

        if (statsData.success) {
            const stats = statsData.stats;

            document.getElementById('totalDocs').textContent = stats.total_documents;
            document.getElementById('totalAmount').textContent = `$${stats.total_amount.toLocaleString()}`;
            document.getElementById('needsReview').textContent = stats.by_status.needs_review || 0;
            document.getElementById('approved').textContent = stats.by_status.approved || 0;

            // Render charts
            renderProjectChart(stats.by_project);
            renderStatusChart(stats.by_status);
        }

        // Load recent documents
        const docsResponse = await fetch(`${API_BASE}/documents?limit=10`);
        const docsData = await docsResponse.json();

        if (docsData.success) {
            renderRecentDocuments(docsData.documents);
        }
    } catch (error) {
        console.error('Error loading dashboard:', error);
        showToast('Error loading dashboard', 'error');
    }
}

function renderProjectChart(data) {
    const container = document.getElementById('projectChart');
    container.innerHTML = '';

    if (!data || Object.keys(data).length === 0) {
        container.innerHTML = '<p class="loading">No data available</p>';
        return;
    }

    const sorted = Object.entries(data).sort((a, b) => b[1] - a[1]);

    sorted.forEach(([project, amount]) => {
        const bar = document.createElement('div');
        bar.style.cssText = `
            margin-bottom: 1rem;
        `;

        const maxAmount = sorted[0][1];
        const percentage = (amount / maxAmount) * 100;

        bar.innerHTML = `
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                <span style="font-weight: 600;">${project}</span>
                <span>$${amount.toLocaleString()}</span>
            </div>
            <div style="background: #e2e8f0; border-radius: 4px; height: 10px;">
                <div style="background: linear-gradient(90deg, #3b82f6, #2563eb);
                           height: 100%; width: ${percentage}%; border-radius: 4px;"></div>
            </div>
        `;

        container.appendChild(bar);
    });
}

function renderStatusChart(data) {
    const container = document.getElementById('statusChart');
    container.innerHTML = '';

    if (!data || Object.keys(data).length === 0) {
        container.innerHTML = '<p class="loading">No data available</p>';
        return;
    }

    const statusColors = {
        draft: '#64748b',
        needs_review: '#f59e0b',
        approved: '#10b981',
        posted: '#3b82f6'
    };

    const total = Object.values(data).reduce((sum, val) => sum + val, 0);

    Object.entries(data).forEach(([status, count]) => {
        const percentage = ((count / total) * 100).toFixed(1);

        const item = document.createElement('div');
        item.style.cssText = `
            margin-bottom: 1rem;
        `;

        item.innerHTML = `
            <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem;">
                <span style="font-weight: 600; text-transform: capitalize;">
                    ${status.replace('_', ' ')}
                </span>
                <span>${count} (${percentage}%)</span>
            </div>
            <div style="background: #e2e8f0; border-radius: 4px; height: 10px;">
                <div style="background: ${statusColors[status]};
                           height: 100%; width: ${percentage}%; border-radius: 4px;"></div>
            </div>
        `;

        container.appendChild(item);
    });
}

function renderRecentDocuments(documents) {
    const container = document.getElementById('recentDocs');

    if (!documents || documents.length === 0) {
        container.innerHTML = '<p class="loading">No documents found</p>';
        return;
    }

    let html = `
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Vendor</th>
                    <th>Invoice #</th>
                    <th>Amount</th>
                    <th>Project</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
    `;

    documents.forEach(doc => {
        html += `
            <tr onclick="showDocumentDetails('${doc.doc_id}')">
                <td>${doc.issue_date || 'N/A'}</td>
                <td>${doc.vendor}</td>
                <td>${doc.invoice_number || 'N/A'}</td>
                <td>${doc.grand_total.toFixed(2)} ${doc.currency}</td>
                <td>${doc.project_code || 'N/A'}</td>
                <td><span class="status-badge status-${doc.status}">${doc.status.replace('_', ' ')}</span></td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

// Upload Handling
function handleDragOver(e) {
    e.preventDefault();
    e.currentTarget.classList.add('dragover');
}

function handleDragLeave(e) {
    e.currentTarget.classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('dragover');

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFileSelect(files[0]);
    }
}

function handleFileSelect(file) {
    appState.selectedFile = file;

    document.getElementById('uploadZone').innerHTML = `
        <i class="fas fa-file-alt"></i>
        <h3>${file.name}</h3>
        <p>${(file.size / 1024 / 1024).toFixed(2)} MB</p>
    `;

    document.getElementById('uploadBtn').disabled = false;
}

async function uploadDocument() {
    if (!appState.selectedFile) {
        showToast('Please select a file', 'warning');
        return;
    }

    const formData = new FormData();
    formData.append('file', appState.selectedFile);
    formData.append('user_role', appState.currentRole);

    const projectCodeEl = document.getElementById('projectCode');
    const grantCodeEl = document.getElementById('grantCode');

    const projectCode = projectCodeEl ? projectCodeEl.value : '';
    const grantCode = grantCodeEl ? grantCodeEl.value : '';

    if (projectCode) formData.append('project_code', projectCode);
    if (grantCode) formData.append('grant_code', grantCode);

    const uploadBtn = document.getElementById('uploadBtn');
    if (!uploadBtn) {
        console.error('Upload button not found');
        return;
    }
    uploadBtn.disabled = true;
    uploadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';

    try {
        const response = await fetch(`${API_BASE}/upload`, {
            method: 'POST',
            body: formData
        });

        // Check if response is OK
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: 'Server error' }));
            showToast(errorData.error || 'Upload failed', 'error');
            console.error('Upload error:', errorData);
            return;
        }

        const data = await response.json();

        if (data.success) {
            showToast('Document processed successfully!', 'success');
            displayUploadResult(data);
            resetUploadForm();
        } else {
            showToast(data.error || 'Upload failed', 'error');
            console.error('Upload error:', data);
        }
    } catch (error) {
        console.error('Upload error:', error);
        showToast('Upload failed: ' + error.message, 'error');
    } finally {
        const btn = document.getElementById('uploadBtn');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-upload"></i> Process Document';
        }
    }
}

function displayUploadResult(data) {
    const resultDiv = document.getElementById('uploadResult');
    const contentDiv = document.getElementById('resultContent');

    if (!resultDiv || !contentDiv) {
        console.error('Upload result elements not found');
        return;
    }

    let flagsHtml = '';
    if (data.document && data.document.validation && data.document.validation.flags.length > 0) {
        flagsHtml = '<div style="margin-top: 1rem; padding: 1rem; background: #fef3c7; border-radius: 8px;">';
        flagsHtml += '<h4>⚠ Validation Flags:</h4><ul style="margin-left: 1.5rem;">';
        data.document.validation.flags.forEach(flag => {
            flagsHtml += `<li><strong>${flag.severity}:</strong> ${flag.message}</li>`;
        });
        flagsHtml += '</ul></div>';
    }

    contentDiv.innerHTML = `
        <div style="background: #f8fafc; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
            <p><strong>Document ID:</strong> ${data.doc_id}</p>
            <p><strong>Summary:</strong> ${data.summary}</p>
        </div>
        <div style="background: #f8fafc; padding: 1rem; border-radius: 8px;">
            <p><strong>Filed to:</strong></p>
            <p style="font-family: monospace; word-break: break-all;">${data.folder_path}/${data.file_name}</p>
        </div>
        ${flagsHtml}
    `;

    resultDiv.style.display = 'block';
}

function resetUploadForm() {
    const uploadZone = document.getElementById('uploadZone');
    if (uploadZone) {
        uploadZone.innerHTML = `
            <i class="fas fa-cloud-upload-alt"></i>
            <h3>Drag & Drop or Click to Upload</h3>
            <p>PDF, PNG, JPG, JPEG (Max 50MB)</p>
        `;
    }

    const fileInput = document.getElementById('fileInput');
    if (fileInput) fileInput.value = '';

    const projectCode = document.getElementById('projectCode');
    if (projectCode) projectCode.value = '';

    const grantCode = document.getElementById('grantCode');
    if (grantCode) grantCode.value = '';

    appState.selectedFile = null;

    const uploadBtn = document.getElementById('uploadBtn');
    if (uploadBtn) uploadBtn.disabled = true;
}

// Documents Page
async function loadDocuments() {
    const container = document.getElementById('documentsTable');
    container.innerHTML = '<div class="spinner"></div>';

    try {
        const project = document.getElementById('filterProject')?.value || '';
        const grant = document.getElementById('filterGrant')?.value || '';
        const status = document.getElementById('filterStatus')?.value || '';
        const currency = document.getElementById('filterCurrency')?.value || '';
        const user = document.getElementById('filterUser')?.value || '';
        const dateFrom = document.getElementById('filterDateFrom')?.value || '';
        const dateTo = document.getElementById('filterDateTo')?.value || '';
        const amountMin = document.getElementById('filterAmountMin')?.value || '';
        const amountMax = document.getElementById('filterAmountMax')?.value || '';
        const searchQuery = document.getElementById('searchQuery')?.value || '';

        let url = `${API_BASE}/documents?limit=100`;
        if (project) url += `&project=${project}`;
        if (grant) url += `&grant=${grant}`;
        if (status) url += `&status=${status}`;

        const response = await fetch(url);
        const data = await response.json();

        if (data.success) {
            // Apply client-side filters
            let filteredDocs = data.documents;

            // Currency filter
            if (currency) {
                filteredDocs = filteredDocs.filter(doc => doc.currency === currency);
            }

            // Date range filter
            if (dateFrom) {
                filteredDocs = filteredDocs.filter(doc => {
                    const docDate = doc.issue_date || '';
                    return docDate >= dateFrom;
                });
            }
            if (dateTo) {
                filteredDocs = filteredDocs.filter(doc => {
                    const docDate = doc.issue_date || '';
                    return docDate <= dateTo;
                });
            }

            // Amount range filter
            if (amountMin) {
                filteredDocs = filteredDocs.filter(doc => doc.grand_total >= parseFloat(amountMin));
            }
            if (amountMax) {
                filteredDocs = filteredDocs.filter(doc => doc.grand_total <= parseFloat(amountMax));
            }

            // User filter (if user field exists)
            if (user) {
                filteredDocs = filteredDocs.filter(doc =>
                    (doc.user || 'system').toLowerCase() === user.toLowerCase()
                );
            }

            // Search query filter
            if (searchQuery) {
                const query = searchQuery.toLowerCase();
                filteredDocs = filteredDocs.filter(doc =>
                    (doc.vendor || '').toLowerCase().includes(query) ||
                    (doc.invoice_number || '').toLowerCase().includes(query)
                );
            }

            renderDocumentsTable(filteredDocs);
        } else {
            container.innerHTML = '<p class="loading">Error loading documents</p>';
        }
    } catch (error) {
        console.error('Error loading documents:', error);
        container.innerHTML = '<p class="loading">Error loading documents</p>';
    }
}

function renderDocumentsTable(documents) {
    const container = document.getElementById('documentsTable');

    if (!documents || documents.length === 0) {
        container.innerHTML = '<p class="loading">No documents found</p>';
        return;
    }

    let html = `
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Vendor</th>
                    <th>Invoice #</th>
                    <th>Amount</th>
                    <th>Project</th>
                    <th>Grant</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
    `;

    documents.forEach(doc => {
        html += `
            <tr>
                <td>${doc.issue_date || 'N/A'}</td>
                <td>${doc.vendor}</td>
                <td>${doc.invoice_number || 'N/A'}</td>
                <td>${doc.grand_total.toFixed(2)} ${doc.currency}</td>
                <td>${doc.project_code || 'N/A'}</td>
                <td>${doc.grant_code || 'N/A'}</td>
                <td><span class="status-badge status-${doc.status}">${doc.status.replace('_', ' ')}</span></td>
                <td>
                    <button class="btn btn-secondary" style="padding: 0.5rem 1rem;"
                            onclick="showDocumentDetails('${doc.doc_id}')">
                        <i class="fas fa-eye"></i> View
                    </button>
                </td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

async function searchDocuments() {
    const query = document.getElementById('searchQuery').value;

    if (!query) {
        showToast('Please enter a search term', 'warning');
        return;
    }

    const container = document.getElementById('documentsTable');
    container.innerHTML = '<div class="spinner"></div>';

    try {
        const response = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        if (data.success) {
            renderDocumentsTable(data.results);
        } else {
            container.innerHTML = '<p class="loading">Error searching documents</p>';
        }
    } catch (error) {
        console.error('Search error:', error);
        container.innerHTML = '<p class="loading">Error searching documents</p>';
    }
}

function clearFilters() {
    const searchQuery = document.getElementById('searchQuery');
    if (searchQuery) searchQuery.value = '';

    const filterProject = document.getElementById('filterProject');
    if (filterProject) filterProject.value = '';

    const filterGrant = document.getElementById('filterGrant');
    if (filterGrant) filterGrant.value = '';

    const filterStatus = document.getElementById('filterStatus');
    if (filterStatus) filterStatus.value = '';

    const filterCurrency = document.getElementById('filterCurrency');
    if (filterCurrency) filterCurrency.value = '';

    const filterUser = document.getElementById('filterUser');
    if (filterUser) filterUser.value = '';

    const filterDateFrom = document.getElementById('filterDateFrom');
    if (filterDateFrom) filterDateFrom.value = '';

    const filterDateTo = document.getElementById('filterDateTo');
    if (filterDateTo) filterDateTo.value = '';

    const filterAmountMin = document.getElementById('filterAmountMin');
    if (filterAmountMin) filterAmountMin.value = '';

    const filterAmountMax = document.getElementById('filterAmountMax');
    if (filterAmountMax) filterAmountMax.value = '';

    loadDocuments();
}

// Document Details Modal
async function showDocumentDetails(docId) {
    appState.currentDocId = docId;

    const modal = document.getElementById('docModal');
    const modalBody = document.getElementById('modalBody');

    modalBody.innerHTML = '<div class="spinner"></div>';
    modal.classList.add('active');

    try {
        const response = await fetch(`${API_BASE}/documents/${docId}?role=${appState.currentRole}`);
        const data = await response.json();

        if (data.success) {
            renderDocumentDetails(data.document);

            // Show approve button if user is approver/admin and doc needs review
            const approveBtn = document.getElementById('approveDocBtn');
            if (['approver', 'admin'].includes(appState.currentRole) &&
                data.document.status === 'needs_review') {
                approveBtn.style.display = 'inline-flex';
            } else {
                approveBtn.style.display = 'none';
            }
        } else {
            modalBody.innerHTML = '<p class="loading">Error loading document</p>';
        }
    } catch (error) {
        console.error('Error loading document:', error);
        modalBody.innerHTML = '<p class="loading">Error loading document</p>';
    }
}

function renderDocumentDetails(doc) {
    const modalBody = document.getElementById('modalBody');

    let flagsHtml = '';
    if (doc.validation && doc.validation.flags && doc.validation.flags.length > 0) {
        flagsHtml = '<div style="margin-top: 1.5rem; padding: 1rem; background: #fef3c7; border-radius: 8px;">';
        flagsHtml += '<h3 style="margin-bottom: 0.5rem;">⚠ Validation Flags:</h3><ul style="margin-left: 1.5rem;">';
        doc.validation.flags.forEach(flag => {
            flagsHtml += `<li><strong>[${flag.severity.toUpperCase()}]</strong> ${flag.message}</li>`;
        });
        flagsHtml += '</ul></div>';
    }

    // Determine file type and create viewer HTML
    const fileName = doc.filing.file_name || '';
    const fileExt = fileName.toLowerCase().split('.').pop();
    const isPdf = fileExt === 'pdf';
    const isImage = ['jpg', 'jpeg', 'png', 'gif', 'bmp'].includes(fileExt);

    let viewerHtml = '';
    if (doc.document_id) {
        viewerHtml = `
            <div style="margin-bottom: 1.5rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0;">Original Document</h3>
                    <div>
                        <a href="${API_BASE}/documents/${doc.document_id}/download"
                           class="btn btn-secondary"
                           style="padding: 0.5rem 1rem; text-decoration: none; display: inline-flex; align-items: center; gap: 0.5rem;">
                            <i class="fas fa-download"></i> Download
                        </a>
                    </div>
                </div>
                <div style="border: 2px solid #e2e8f0; border-radius: 8px; overflow: hidden; background: #f8fafc;">
                    ${isPdf ? `
                        <embed src="${API_BASE}/documents/${doc.document_id}/file"
                               type="application/pdf"
                               width="100%"
                               height="600px"
                               style="display: block;" />
                    ` : isImage ? `
                        <img src="${API_BASE}/documents/${doc.document_id}/file"
                             alt="Invoice"
                             style="width: 100%; height: auto; display: block; max-height: 600px; object-fit: contain;" />
                    ` : `
                        <div style="padding: 2rem; text-align: center; color: #64748b;">
                            <i class="fas fa-file" style="font-size: 3rem; margin-bottom: 1rem; opacity: 0.5;"></i>
                            <p><strong>File: ${fileName}</strong></p>
                            <p>Preview not available for this file type.</p>
                            <a href="${API_BASE}/documents/${doc.document_id}/download"
                               class="btn btn-primary"
                               style="margin-top: 1rem; text-decoration: none;">
                                <i class="fas fa-download"></i> Download to View
                            </a>
                        </div>
                    `}
                </div>
            </div>
        `;
    }

    modalBody.innerHTML = `
        <div style="display: grid; gap: 1.5rem;">
            ${viewerHtml}

            <div>
                <h3 style="margin-bottom: 0.5rem;">Basic Information</h3>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.75rem;
                           background: #f8fafc; padding: 1rem; border-radius: 8px;">
                    <div><strong>Document Type:</strong> ${doc.doc_type}</div>
                    <div><strong>Currency:</strong> ${doc.currency}</div>
                    <div><strong>Issue Date:</strong> ${doc.dates.issue_date || 'N/A'}</div>
                    <div><strong>Due Date:</strong> ${doc.dates.due_date || 'N/A'}</div>
                    <div><strong>Status:</strong> <span class="status-badge status-${doc.filing.status}">${doc.filing.status}</span></div>
                    <div><strong>Confidence:</strong> ${(doc.validation.score_confidence * 100).toFixed(0)}%</div>
                </div>
            </div>

            <div>
                <h3 style="margin-bottom: 0.5rem;">Vendor Information</h3>
                <div style="background: #f8fafc; padding: 1rem; border-radius: 8px;">
                    <p><strong>Name:</strong> ${doc.vendor.display_name}</p>
                    ${doc.vendor.email ? `<p><strong>Email:</strong> ${doc.vendor.email}</p>` : ''}
                    ${doc.vendor.tax_id_vat ? `<p><strong>Tax ID:</strong> ${doc.vendor.tax_id_vat}</p>` : ''}
                </div>
            </div>

            <div>
                <h3 style="margin-bottom: 0.5rem;">Amounts</h3>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.75rem;
                           background: #f8fafc; padding: 1rem; border-radius: 8px;">
                    <div><strong>Subtotal:</strong> ${doc.totals.subtotal.toFixed(2)} ${doc.currency}</div>
                    <div><strong>Tax:</strong> ${doc.totals.tax_amount.toFixed(2)} ${doc.currency}</div>
                    <div><strong>Grand Total:</strong> <strong style="font-size: 1.2em; color: #2563eb;">${doc.totals.grand_total.toFixed(2)} ${doc.currency}</strong></div>
                    ${doc.totals.discount ? `<div><strong>Discount:</strong> ${doc.totals.discount.toFixed(2)} ${doc.currency}</div>` : ''}
                </div>
            </div>

            <div>
                <h3 style="margin-bottom: 0.5rem;">NGO Context</h3>
                <div style="background: #f8fafc; padding: 1rem; border-radius: 8px;">
                    <p><strong>Fiscal Year:</strong> ${doc.ngo_context.fiscal_year}</p>
                    <p><strong>Project:</strong> ${doc.ngo_context.project_code || 'N/A'}</p>
                    <p><strong>Grant:</strong> ${doc.ngo_context.grant_code || 'N/A'}</p>
                    <p><strong>Fund Type:</strong> ${doc.classification.fund_type || 'N/A'}</p>
                </div>
            </div>

            ${flagsHtml}
        </div>
    `;
}

async function approveDocument() {
    // Show confirmation modal instead of prompt
    try {
        // Get current document data from the modal
        const response = await fetch(`${API_BASE}/documents/${appState.currentDocId}?role=${appState.currentRole}`);
        const data = await response.json();

        if (data.success) {
            const doc = data.document;

            // Populate confirmation modal
            document.getElementById('confirmDocType').textContent = doc.doc_type || 'N/A';
            document.getElementById('confirmVendor').textContent = doc.vendor?.display_name || 'N/A';
            document.getElementById('confirmAmount').textContent = `${doc.totals?.grand_total?.toFixed(2) || '0.00'} ${doc.currency || ''}`;
            document.getElementById('confirmDate').textContent = doc.dates?.issue_date || 'N/A';

            // Clear previous input
            document.getElementById('approverName').value = '';
            document.getElementById('approverComments').value = '';

            // Show confirmation modal
            document.getElementById('confirmModal').classList.add('active');
        }
    } catch (error) {
        console.error('Error loading document for approval:', error);
        showToast('Error loading document details', 'error');
    }
}

async function confirmApproval() {
    const approverName = document.getElementById('approverName')?.value.trim();
    const comments = document.getElementById('approverComments')?.value.trim();

    if (!approverName) {
        showToast('Please enter your name', 'error');
        document.getElementById('approverName').focus();
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/documents/${appState.currentDocId}/approve`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                approver: approverName,
                user_role: appState.currentRole,
                comments: comments || ''
            })
        });

        const data = await response.json();

        if (data.success) {
            showToast('Document approved successfully!', 'success');
            closeConfirmModal();
            closeModal();
            loadDocuments();
            loadDashboard();
        } else {
            showToast(data.error || 'Approval failed', 'error');
        }
    } catch (error) {
        console.error('Approval error:', error);
        showToast('Approval failed', 'error');
    }
}

function closeConfirmModal() {
    document.getElementById('confirmModal').classList.remove('active');
}

function closeModal() {
    document.getElementById('docModal').classList.remove('active');
}

function printDocument() {
    // Get the modal body content
    const modalBody = document.getElementById('modalBody');
    if (!modalBody) return;

    // Create a new window for printing
    const printWindow = window.open('', '_blank', 'width=800,height=600');

    // Write print-friendly HTML
    printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>Print Document</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    padding: 20px;
                    color: #333;
                }
                h3 {
                    color: #2563eb;
                    margin-top: 20px;
                    margin-bottom: 10px;
                    border-bottom: 2px solid #e2e8f0;
                    padding-bottom: 5px;
                }
                .status-badge {
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-size: 0.875rem;
                    font-weight: 600;
                }
                .status-draft { background: #e5e7eb; color: #374151; }
                .status-needs_review { background: #fef3c7; color: #92400e; }
                .status-approved { background: #d1fae5; color: #065f46; }
                .status-posted { background: #dbeafe; color: #1e40af; }
                embed, img {
                    max-width: 100%;
                    page-break-inside: avoid;
                }
                @media print {
                    body { padding: 0; }
                    .no-print { display: none; }
                }
            </style>
        </head>
        <body>
            ${modalBody.innerHTML}
        </body>
        </html>
    `);

    printWindow.document.close();

    // Wait for content to load, then print
    printWindow.onload = function() {
        setTimeout(() => {
            printWindow.print();
            // Close the window after printing (user can cancel)
            printWindow.onafterprint = function() {
                printWindow.close();
            };
        }, 250);
    };
}

// Reports
async function generateFiscalYearReport() {
    const fiscalYear = document.getElementById('fiscalYearSelect').value;
    const resultDiv = document.getElementById('fyReportResult');

    resultDiv.innerHTML = '<div class="spinner"></div>';

    try {
        const response = await fetch(`${API_BASE}/reports/fiscal-year/${fiscalYear}`);
        const data = await response.json();

        if (data.success) {
            renderFiscalYearReport(data.report, resultDiv);
        } else {
            resultDiv.innerHTML = '<p class="loading">Error generating report</p>';
        }
    } catch (error) {
        console.error('Report error:', error);
        resultDiv.innerHTML = '<p class="loading">Error generating report</p>';
    }
}

function renderFiscalYearReport(report, container) {
    let html = `
        <div style="background: #f8fafc; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
            <h4>Summary</h4>
            <p><strong>Total Documents:</strong> ${report.summary.total_documents}</p>
            <p><strong>Total Amount:</strong> $${report.summary.total_amount.toLocaleString()}</p>
            <p><strong>Average Amount:</strong> $${report.summary.average_amount.toLocaleString()}</p>
        </div>

        <div style="background: #f8fafc; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
            <h4>By Project</h4>
            <ul style="margin-left: 1.5rem;">
    `;

    Object.entries(report.by_project).forEach(([proj, amt]) => {
        html += `<li>${proj}: $${amt.toLocaleString()}</li>`;
    });

    html += `
            </ul>
        </div>

        <div style="background: #f8fafc; padding: 1rem; border-radius: 8px;">
            <h4>Top Vendors</h4>
            <ul style="margin-left: 1.5rem;">
    `;

    report.top_vendors.forEach(([vendor, amt]) => {
        html += `<li>${vendor}: $${amt.toLocaleString()}</li>`;
    });

    html += '</ul></div>';
    container.innerHTML = html;
}

async function generateProjectReport() {
    const projectCode = document.getElementById('projectReportSelect').value;

    if (!projectCode) {
        showToast('Please select a project', 'warning');
        return;
    }

    const resultDiv = document.getElementById('projectReportResult');
    resultDiv.innerHTML = '<div class="spinner"></div>';

    try {
        const response = await fetch(`${API_BASE}/reports/project/${projectCode}`);
        const data = await response.json();

        if (data.success) {
            renderProjectReport(data.report, resultDiv);
        } else {
            resultDiv.innerHTML = '<p class="loading">Error generating report</p>';
        }
    } catch (error) {
        console.error('Report error:', error);
        resultDiv.innerHTML = '<p class="loading">Error generating report</p>';
    }
}

function renderProjectReport(report, container) {
    let html = `
        <div style="background: #f8fafc; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
            <p><strong>Total Documents:</strong> ${report.total_documents}</p>
            <p><strong>Total Amount:</strong> $${report.total_amount.toLocaleString()}</p>
        </div>

        <div style="background: #f8fafc; padding: 1rem; border-radius: 8px;">
            <h4>By Category</h4>
            <ul style="margin-left: 1.5rem;">
    `;

    Object.entries(report.by_category).forEach(([cat, amt]) => {
        html += `<li>${cat}: $${amt.toLocaleString()}</li>`;
    });

    html += '</ul></div>';
    container.innerHTML = html;
}

// Export
async function exportLedger() {
    const format = document.getElementById('exportFormat').value;
    const project = document.getElementById('exportProject').value;
    const grant = document.getElementById('exportGrant').value;
    const fiscalYear = document.getElementById('exportFiscalYear').value;
    const status = document.getElementById('exportStatus').value;

    let url = `${API_BASE}/export?format=${format}`;
    if (project) url += `&project=${project}`;
    if (grant) url += `&grant=${grant}`;
    if (fiscalYear) url += `&fiscal_year=${fiscalYear}`;
    if (status) url += `&status=${status}`;

    try {
        showToast('Generating export...', 'info');

        // Open in new window to trigger download
        window.open(url, '_blank');

        showToast('Export started! Check your downloads.', 'success');
    } catch (error) {
        console.error('Export error:', error);
        showToast('Export failed', 'error');
    }
}

// Toast Notifications
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}
