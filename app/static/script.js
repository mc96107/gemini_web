document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatContainer = document.getElementById('chat-container');
    const fileUpload = document.getElementById('file-upload');
    const filePreviewArea = document.getElementById('file-preview-area');
    const fileNameDisplay = document.getElementById('file-name');
    const clearFileBtn = document.getElementById('clear-file-btn');
    const resetBtn = document.getElementById('reset-btn');
    const modelLinks = document.querySelectorAll('[data-model]');
    const modelInput = document.getElementById('model-input');
    const modelLabel = document.getElementById('model-label');
    const patternsList = document.getElementById('patterns-list');
    const patternSearch = document.getElementById('pattern-search');
    const patternsModal = document.getElementById('patternsModal');
    const sessionsList = document.getElementById('sessions-list');
    const newChatBtn = document.getElementById('new-chat-btn');
    const historySidebar = document.getElementById('historySidebar');
    const toolsModal = document.getElementById('toolsModal');
    const toolsStatus = document.getElementById('tools-status');
    const btnApplyTools = document.getElementById('btn-apply-tools');
    const btnDeselectAllTools = document.getElementById('btn-deselect-all-tools');
    const toolToggles = document.querySelectorAll('.tool-toggle');

    let currentFile = null;
    let allPatterns = [];

    // Handle Tools Modal show
    toolsModal.addEventListener('show.bs.modal', async () => {
        // Find the active session UUID
        const activeSessionItem = document.querySelector('.session-item.active-session');
        let uuid = "pending";
        if (activeSessionItem) {
            uuid = activeSessionItem.dataset.uuid;
        }

        toolsStatus.textContent = 'Loading settings...';
        toolsStatus.className = 'mt-2 small text-muted';

        // Reset toggles first
        toolToggles.forEach(t => t.checked = false);

        try {
            const response = await fetch(`/sessions/${uuid}/tools`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            
            if (data.tools) {
                data.tools.forEach(toolName => {
                    const toggle = document.querySelector(`.tool-toggle[value="${toolName}"]`);
                    if (toggle) toggle.checked = true;
                });
            }
            toolsStatus.textContent = '';
        } catch (error) {
            console.error('Error loading tool settings:', error);
            toolsStatus.textContent = 'Failed to load settings.';
            toolsStatus.className = 'mt-2 small text-danger';
        }
    });

    btnApplyTools.addEventListener('click', async () => {
        const activeSessionItem = document.querySelector('.session-item.active-session');
        let uuid = "pending";
        if (activeSessionItem) {
            uuid = activeSessionItem.dataset.uuid;
        }

        const selectedTools = Array.from(toolToggles)
            .filter(t => t.checked)
            .map(t => t.value);

        toolsStatus.textContent = 'Saving settings...';
        toolsStatus.className = 'mt-2 small text-muted';

        try {
            const response = await fetch(`/sessions/${uuid}/tools`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tools: selectedTools })
            });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            if (data.success) {
                toolsStatus.textContent = 'Settings applied successfully!';
                toolsStatus.className = 'mt-2 small text-success';
                setTimeout(() => {
                    const modal = bootstrap.Modal.getInstance(toolsModal);
                    if (modal) modal.hide();
                }, 1000);
            }
        } catch (error) {
            console.error('Error saving tool settings:', error);
            toolsStatus.textContent = 'Failed to save settings.';
            toolsStatus.className = 'mt-2 small text-danger';
        }
    });

    btnDeselectAllTools.addEventListener('click', () => {
        toolToggles.forEach(t => t.checked = false);
    });

    // Load sessions when sidebar is shown
    historySidebar.addEventListener('show.bs.offcanvas', loadSessions);

    
    async function loadMessages(uuid) {
        try {
            const response = await fetch(`/sessions/${uuid}/messages`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const messages = await response.json();
            chatContainer.innerHTML = ''; // Clear current chat
            if (messages.length === 0) {
                chatContainer.innerHTML = '<div class="text-center text-muted mt-5"><p>Start a conversation with Gemini.</p><p class="small">Try <code>/help</code> to see available commands.</p></div>';
            } else {
                messages.forEach(msg => appendMessage(msg.role, msg.content));
            }
        } catch (error) {
            console.error('Error loading messages:', error);
        }
    }

    async function loadSessions() {
        try {
            const response = await fetch('/sessions');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const sessions = await response.json();
            renderSessions(sessions);
            const activeSession = sessions.find(s => s.active);
            if (activeSession && chatContainer.querySelectorAll('.message').length === 0) {
                 loadMessages(activeSession.uuid);
            }
        } catch (error) {
            console.error('Error loading sessions:', error);
            sessionsList.innerHTML = `<div class="alert alert-danger mx-3 mt-3">Failed to load history: ${error.message}</div>`;
        }
    }

    // Load patterns when modal is shown
    patternsModal.addEventListener('show.bs.modal', async () => {
        if (allPatterns.length === 0) {
            try {
                const response = await fetch('/patterns');
                if (!response.ok) throw new Error(`HTTP ${response.status}`);
                const data = await response.json();
                allPatterns = data; // data is already the list
                renderPatterns(allPatterns);
            } catch (error) {
                console.error('Error loading patterns:', error);
                patternsList.innerHTML = `<div class="alert alert-danger">Failed to load patterns: ${error.message}</div>`;
            }
        }
    });

    function renderSessions(sessions) {
        if (sessions.length === 0) {
            sessionsList.innerHTML = '<div class="text-center p-3 text-muted">No history found.</div>';
            return;
        }
        sessionsList.innerHTML = sessions.map(s => `
            <div class="list-group-item list-group-item-action bg-dark text-light session-item ${s.active ? 'active-session' : ''}" data-uuid="${s.uuid}">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1 overflow-hidden">
                        <span class="session-title text-truncate">${s.title || 'Untitled Chat'}</span>
                        <span class="session-time">${s.time || ''}</span>
                    </div>
                    <div class="d-flex align-items-center gap-2">
                        ${s.active ? '<span class="badge bg-primary rounded-pill small">Active</span>' : ''}
                        <button class="btn btn-sm btn-outline-danger border-0 delete-session-btn" data-uuid="${s.uuid}" title="Delete Chat">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `).join('');

        // Add click listeners to items
        document.querySelectorAll('.session-item').forEach(item => {
            item.addEventListener('click', async (e) => {
                // If clicked on delete button, don't switch session
                if (e.target.closest('.delete-session-btn')) return;

                const uuid = item.dataset.uuid;
                if (item.classList.contains('active-session')) {
                    bootstrap.Offcanvas.getInstance(historySidebar).hide();
                    return;
                }
                
                try {
                    const formData = new FormData();
                    formData.append('session_uuid', uuid);
                    const response = await fetch('/sessions/switch', {
                        method: 'POST',
                        body: formData
                    });
                    const data = await response.json();
                    if (data.success) {
                        chatContainer.innerHTML = '<div class="text-center text-muted mt-5"><p>Loading conversation...</p></div>';
                        await loadMessages(uuid);
                        bootstrap.Offcanvas.getInstance(historySidebar).hide();
                        loadSessions();
                    }
                } catch (error) {
                    console.error('Error switching session:', error);
                    alert('Failed to switch session.');
                }
            });
        });

        // Delete buttons
        document.querySelectorAll('.delete-session-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const uuid = btn.dataset.uuid;
                if (confirm('Are you sure you want to delete this conversation?')) {
                    try {
                        const formData = new FormData();
                        formData.append('session_uuid', uuid);
                        const response = await fetch('/sessions/delete', {
                            method: 'POST',
                            body: formData
                        });
                        const data = await response.json();
                        if (data.success) {
                            loadSessions();
                            // If deleted the active one, clear the chat
                            const item = btn.closest('.session-item');
                            if (item.classList.contains('active-session')) {
                                chatContainer.innerHTML = '<div class="text-center text-muted mt-5"><p>Conversation deleted. Start a new one!</p></div>';
                            }
                        }
                    } catch (error) {
                        console.error('Error deleting session:', error);
                        alert('Failed to delete session.');
                    }
                }
            });
        });
    }

    // New Chat
    newChatBtn.addEventListener('click', async () => {
        try {
            const response = await fetch('/sessions/new', { method: 'POST' });
            const data = await response.json();
            if (data.success) {
                chatContainer.innerHTML = '<div class="text-center text-muted mt-5"><p>New conversation started.</p></div>';
                bootstrap.Offcanvas.getInstance(historySidebar).hide();
                loadSessions();
            }
        } catch (error) {
            console.error('Error starting new chat:', error);
            alert('Failed to start new chat.');
        }
    });

    // Load patterns when modal is shown
    patternsModal.addEventListener('show.bs.modal', async () => {
        if (allPatterns.length === 0) {
            try {
                const response = await fetch('/patterns');
                const data = await response.json();
                allPatterns = data; // data is already the list
                renderPatterns(allPatterns);
            } catch (error) {
                console.error('Error loading patterns:', error);
                patternsList.innerHTML = '<div class="alert alert-danger">Failed to load patterns.</div>';
            }
        }
    });

    // Search patterns
    patternSearch.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        const filtered = allPatterns.filter(p => 
            (p.name && p.name.toLowerCase().includes(query)) || 
            (p.description && p.description.toLowerCase().includes(query))
        );
        renderPatterns(filtered);
    });

    function renderPatterns(patterns) {
        if (patterns.length === 0) {
            patternsList.innerHTML = '<div class="text-center p-3 text-muted">No patterns found.</div>';
            return;
        }
        patternsList.innerHTML = patterns.map(p => `
            <button type="button" class="list-group-item list-group-item-action bg-dark text-light border-secondary pattern-item" data-pattern="${p.name}">
                <div class="d-flex w-100 justify-content-between">
                    <h6 class="mb-1"><i class="bi bi-magic"></i> ${p.name}</h6>
                </div>
                <small class="text-muted">${p.description || ''}</small>
            </button>
        `).join('');

        // Add click listeners to items
        document.querySelectorAll('.pattern-item').forEach(item => {
            item.addEventListener('click', () => {
                const pattern = item.dataset.pattern;
                messageInput.value = `/p ${pattern} ${messageInput.value}`;
                bootstrap.Modal.getInstance(patternsModal).hide();
                messageInput.focus();
                // Trigger auto-resize
                messageInput.dispatchEvent(new Event('input'));
            });
        });
    }

    // Auto-resize textarea
    messageInput.addEventListener('keydown', function(event) {
        if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
            event.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });

    messageInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        if (this.value === '') {
            this.style.height = '';
        }
    });

    // Model selection
    modelLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetLink = e.currentTarget; // The <a> tag
            const model = targetLink.dataset.model;
            
            modelInput.value = model;
            // Get text without the badge if possible, or just full text
            let modelName = targetLink.innerText;
            // Clean up "Fast"/"Smart" badges from text if present (simple hack)
            modelName = modelName.replace('Fast', '').replace('Smart', '').trim();
            
            modelLabel.textContent = modelName;
            
            modelLinks.forEach(l => l.classList.remove('active'));
            targetLink.classList.add('active');
        });
    });

    // File handling
    fileUpload.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            currentFile = e.target.files[0];
            fileNameDisplay.textContent = currentFile.name;
            filePreviewArea.classList.remove('d-none');
        }
    });

    clearFileBtn.addEventListener('click', () => {
        fileUpload.value = '';
        currentFile = null;
        filePreviewArea.classList.add('d-none');
    });

    // Reset Chat
    if (resetBtn) {
        resetBtn.addEventListener('click', async () => {
            if (confirm('Are you sure you want to clear the conversation history?')) {
                try {
                    const response = await fetch('/reset', { method: 'POST' });
                    const data = await response.json();
                    chatContainer.innerHTML = `<div class="text-center text-muted mt-5"><p>${data.response}</p></div>`;
                } catch (error) {
                    console.error('Error resetting chat:', error);
                    alert('Failed to reset chat.');
                }
            }
        });
    }

    // Send Message
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const message = messageInput.value.trim();
        if (!message && !currentFile) return;

        // Add user message to chat
        appendMessage('user', message, currentFile ? `[Attachment: ${currentFile.name}]` : null);
        
        // Clear inputs immediately
        messageInput.value = '';
        messageInput.style.height = '';
        fileUpload.value = '';
        filePreviewArea.classList.add('d-none');
        const fileToSend = currentFile; // Keep ref for sending
        currentFile = null;

        // Show loading state
        const loadingId = appendLoading();

        try {
            const formData = new FormData();
            formData.append('message', message);
            if (fileToSend) {
                formData.append('file', fileToSend);
            }
            formData.append('model', modelInput.value);

            const response = await fetch('/chat', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                let errorMessage = `Server Error: ${response.status}`;
                try {
                    const text = await response.text();
                    try {
                        const errorData = JSON.parse(text);
                        if (errorData.error) {
                            errorMessage = `Error: ${errorData.error}`;
                        } else if (errorData.response) {
                            errorMessage = errorData.response;
                        }
                    } catch (parseError) {
                        // Not JSON, use the raw text if short, or just the status
                        if (text && text.length < 100) {
                            errorMessage = `Error ${response.status}: ${text}`;
                        } else {
                            errorMessage = `Error ${response.status}: Failed to get valid response from server.`;
                        }
                    }
                } catch (e) {
                    console.error('Could not read error response:', e);
                }
                throw new Error(errorMessage);
            }

            const data = await response.json();
            
            // Remove loading and add bot response
            removeLoading(loadingId);
            appendMessage('bot', data.response);

        } catch (error) {
            removeLoading(loadingId);
            console.error('Detailed Chat Error:', error);
            let displayError = error.message || 'Unknown Error';
            if (error instanceof TypeError && error.message === 'Failed to fetch') {
                displayError = 'Network Error: Could not connect to the server. Check if the service is running and accessible.';
            }
            appendMessage('bot', `Error: ${displayError}`);
        }
    });

    function appendMessage(sender, text, attachmentInfo = null) {
        try {
            const messageDiv = document.createElement('div');
            messageDiv.classList.add('message', sender);
            
            let contentHtml = '';
            if (attachmentInfo) {
                contentHtml += `<div class="text-muted small mb-1"><i class="bi bi-paperclip"></i> ${attachmentInfo}</div>`;
            }
            
            // Use marked to parse markdown safely
            let parsedText = text;
            try {
                if (typeof marked !== 'undefined') {
                    // Check if it's the newer marked.parse or the older marked()
                    if (typeof marked.parse === 'function') {
                        parsedText = marked.parse(text);
                    } else if (typeof marked === 'function') {
                        parsedText = marked(text);
                    }
                }
            } catch (e) {
                console.error('Error parsing markdown:', e);
            }
            
            contentHtml += parsedText;

            messageDiv.innerHTML = contentHtml;
            // Add copy button
            const copyBtn = document.createElement('button');
            copyBtn.className = 'copy-btn';
            copyBtn.innerHTML = '<i class="bi bi-clipboard"></i>';
            copyBtn.onclick = (e) => {
                e.stopPropagation();
                navigator.clipboard.writeText(text).then(() => {
                    const icon = copyBtn.querySelector('i');
                    icon.className = 'bi bi-check2';
                    setTimeout(() => { icon.className = 'bi bi-clipboard'; }, 2000);
                });
            };
            messageDiv.appendChild(copyBtn);

            chatContainer.appendChild(messageDiv);
            
            // Highlight code blocks safely
            try {
                if (typeof hljs !== 'undefined') {
                    messageDiv.querySelectorAll('pre code').forEach((block) => {
                        hljs.highlightElement(block);
                    });
                }
            } catch (e) {
                console.error('Error highlighting code:', e);
            }

            chatContainer.scrollTop = chatContainer.scrollHeight;
        } catch (e) {
            console.error('Error in appendMessage:', e);
        }
    }

    function appendLoading() {
        const id = 'loading-' + Date.now();
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', 'bot');
        messageDiv.id = id;
        messageDiv.innerHTML = '<div class="spinner-border spinner-border-sm text-light" role="status"><span class="visually-hidden">Loading...</span></div> Thinking...';
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        return id;
    }

    function removeLoading(id) {
        const element = document.getElementById(id);
        if (element) {
            element.remove();
        }
    }
});
