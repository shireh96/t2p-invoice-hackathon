// Chat Upload Functionality
let chatState = {
    sessionId: null,
    isProcessing: false,
    file: null
};

// Initialize chat upload
function initChatUpload() {
    const uploadZone = document.getElementById('chatUploadZone');
    const fileInput = document.getElementById('chatFileInput');
    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('chatSendBtn');
    const processBtn = document.getElementById('chatProcessBtn');
    const resetBtn = document.getElementById('chatResetBtn');

    if (!uploadZone || !fileInput) return;

    // Click to upload
    uploadZone.addEventListener('click', () => fileInput.click());

    // File selected
    fileInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (file) {
            await startChatSession(file);
        }
    });

    // Drag and drop
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.style.borderColor = '#3b82f6';
        uploadZone.style.background = '#eff6ff';
    });

    uploadZone.addEventListener('dragleave', () => {
        uploadZone.style.borderColor = '#e5e7eb';
        uploadZone.style.background = '#f9fafb';
    });

    uploadZone.addEventListener('drop', async (e) => {
        e.preventDefault();
        uploadZone.style.borderColor = '#e5e7eb';
        uploadZone.style.background = '#f9fafb';

        const file = e.dataTransfer.files[0];
        if (file) {
            await startChatSession(file);
        }
    });

    // Send message on Enter key
    if (chatInput) {
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !chatInput.disabled) {
                sendChatMessage();
            }
        });
    }

    // Send button
    if (sendBtn) {
        sendBtn.addEventListener('click', sendChatMessage);
    }

    // Process button
    if (processBtn) {
        processBtn.addEventListener('click', processChatInvoice);
    }

    // Reset button
    if (resetBtn) {
        resetBtn.addEventListener('click', resetChat);
    }
}

async function startChatSession(file) {
    try {
        chatState.file = file;
        chatState.isProcessing = true;

        // Show uploading state
        const uploadZone = document.getElementById('chatUploadZone');
        const messagesContainer = document.getElementById('chatMessages');

        uploadZone.innerHTML = '<div class="spinner"></div><p>Analyzing invoice...</p>';

        // Prepare form data
        const formData = new FormData();
        formData.append('file', file);
        formData.append('user_role', appState.currentRole);

        // Start chat session
        const response = await fetch(`${API_BASE}/chat/upload`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            chatState.sessionId = data.session_id;

            // Hide upload zone, show chat
            uploadZone.style.display = 'none';
            messagesContainer.style.display = 'block';

            // Set file name
            document.getElementById('chatFileName').textContent = file.name;

            // Add first message
            addChatMessage('assistant', data.message);

            // Update progress
            updateChatProgress(data.progress);

            // Enable input
            document.getElementById('chatInput').disabled = false;
            document.getElementById('chatSendBtn').disabled = false;

            // Focus input
            document.getElementById('chatInput').focus();

        } else {
            showToast(data.error || 'Failed to start chat session', 'error');
            resetChat();
        }

    } catch (error) {
        console.error('Chat upload error:', error);
        showToast('Upload failed: ' + error.message, 'error');
        resetChat();
    } finally {
        chatState.isProcessing = false;
    }
}

async function sendChatMessage() {
    const chatInput = document.getElementById('chatInput');
    const message = chatInput.value.trim();

    if (!message || chatState.isProcessing || !chatState.sessionId) {
        return;
    }

    try {
        chatState.isProcessing = true;

        // Add user message to chat
        addChatMessage('user', message);

        // Clear input
        chatInput.value = '';
        chatInput.disabled = true;
        document.getElementById('chatSendBtn').disabled = true;

        // Send to backend
        const response = await fetch(`${API_BASE}/chat/message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: chatState.sessionId,
                message: message
            })
        });

        const data = await response.json();

        if (data.success) {
            // Add assistant response
            addChatMessage('assistant', data.message);

            // Update progress
            updateChatProgress(data.progress);

            // Check if complete
            if (data.is_complete) {
                // Show process button
                document.getElementById('chatActions').style.display = 'flex';
                document.getElementById('chatInput').disabled = true;
                document.getElementById('chatSendBtn').disabled = true;
            } else {
                // Re-enable input
                chatInput.disabled = false;
                document.getElementById('chatSendBtn').disabled = false;
                chatInput.focus();
            }

        } else {
            showToast(data.error || 'Failed to send message', 'error');
            chatInput.disabled = false;
            document.getElementById('chatSendBtn').disabled = false;
        }

    } catch (error) {
        console.error('Chat message error:', error);
        showToast('Failed to send message', 'error');
        chatInput.disabled = false;
        document.getElementById('chatSendBtn').disabled = false;
    } finally {
        chatState.isProcessing = false;
    }
}

async function processChatInvoice() {
    if (!chatState.sessionId || chatState.isProcessing) {
        return;
    }

    try {
        chatState.isProcessing = true;

        const processBtn = document.getElementById('chatProcessBtn');
        processBtn.disabled = true;
        processBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';

        // Process invoice
        const response = await fetch(`${API_BASE}/chat/process`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: chatState.sessionId
            })
        });

        const data = await response.json();

        if (data.success) {
            showToast('Invoice processed successfully!', 'success');

            // Show success message in chat
            addChatMessage('assistant',
                `✓ Success! Invoice processed and filed.\n\n` +
                `**Document ID:** ${data.doc_id}\n` +
                `**Summary:** ${data.summary}\n\n` +
                `You can view it in the Documents tab.`
            );

            // Disable everything
            document.getElementById('chatInput').disabled = true;
            document.getElementById('chatSendBtn').disabled = true;
            processBtn.style.display = 'none';

            // Show reset button more prominently
            document.getElementById('chatResetBtn').innerHTML =
                '<i class="fas fa-plus"></i> Upload Another Invoice';

        } else {
            showToast(data.error || 'Processing failed', 'error');
            processBtn.disabled = false;
            processBtn.innerHTML = '<i class="fas fa-check-circle"></i> Process Invoice';
        }

    } catch (error) {
        console.error('Process error:', error);
        showToast('Processing failed: ' + error.message, 'error');
        const processBtn = document.getElementById('chatProcessBtn');
        processBtn.disabled = false;
        processBtn.innerHTML = '<i class="fas fa-check-circle"></i> Process Invoice';
    } finally {
        chatState.isProcessing = false;
    }
}

function addChatMessage(role, content) {
    const messagesArea = document.getElementById('messagesArea');
    if (!messagesArea) return;

    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}-message`;

    // Parse markdown-style bold
    const formattedContent = content
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>');

    messageDiv.innerHTML = `
        <div class="message-content">${formattedContent}</div>
        <div class="message-time">${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
    `;

    messagesArea.appendChild(messageDiv);

    // Scroll to bottom
    messagesArea.scrollTop = messagesArea.scrollHeight;
}

function updateChatProgress(progress) {
    if (!progress) return;

    const progressEl = document.getElementById('chatProgress');
    if (progressEl) {
        if (progress.percent === 100) {
            progressEl.textContent = 'All information collected ✓';
            progressEl.style.color = '#10b981';
        } else {
            progressEl.textContent = `Progress: ${progress.collected}/${progress.total} fields (${progress.percent}%)`;
        }
    }
}

function resetChat() {
    // Reset state
    chatState = {
        sessionId: null,
        isProcessing: false,
        file: null
    };

    // Hide chat, show upload zone
    document.getElementById('chatMessages').style.display = 'none';
    const uploadZone = document.getElementById('chatUploadZone');
    uploadZone.style.display = 'flex';
    uploadZone.innerHTML = `
        <i class="fas fa-cloud-upload-alt"></i>
        <h3>Drop Invoice or Click to Upload</h3>
        <p>AI will extract what it can, then ask you for missing details</p>
    `;

    // Clear messages
    document.getElementById('messagesArea').innerHTML = '';

    // Hide actions
    document.getElementById('chatActions').style.display = 'none';

    // Reset input
    document.getElementById('chatInput').value = '';
    document.getElementById('chatInput').disabled = true;
    document.getElementById('chatSendBtn').disabled = true;

    // Reset file input
    document.getElementById('chatFileInput').value = '';
}

// Initialize when page loads
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initChatUpload);
} else {
    initChatUpload();
}
