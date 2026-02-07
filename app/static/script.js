document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatContainer = document.getElementById('chat-container');
    const fileUpload = document.getElementById('file-upload');
    const filePreviewArea = document.getElementById('file-preview-area');
    const fileNameDisplay = document.getElementById('file-name');
    const clearFileBtn = document.getElementById('clear-file-btn');
    const exportBtn = document.getElementById('export-btn');
    const exportBtnMobile = document.getElementById('export-btn-mobile');
    const resetBtn = document.getElementById('reset-btn');
    const resetBtnMobile = document.getElementById('reset-btn-mobile');

    window.addEventListener('tree-helper-question', (e) => {
        const { question, options, allowMultiple, nodeId, isComplete } = e.detail;
        
        // Append question as a bot message
        appendMessage('bot', question);

        if (options && options.length > 0) {
            const optionsDiv = document.createElement('div');
            optionsDiv.className = 'mt-2';
            
            if (allowMultiple) {
                const selected = new Set();
                const container = document.createElement('div');
                container.className = 'd-flex flex-wrap gap-2 mb-2';
                
                options.forEach(opt => {
                    const btn = document.createElement('button');
                    btn.className = 'btn btn-outline-primary btn-sm';
                    btn.innerText = opt;
                    btn.onclick = () => {
                        if (selected.has(opt)) {
                            selected.delete(opt);
                            btn.classList.remove('active');
                        } else {
                            selected.add(opt);
                            btn.classList.add('active');
                        }
                    };
                    container.appendChild(btn);
                });
                
                const submitBtn = document.createElement('button');
                submitBtn.className = 'btn btn-primary btn-sm';
                submitBtn.innerHTML = '<i class="bi bi-check-lg"></i> Submit';
                submitBtn.onclick = () => {
                    if (selected.size === 0) return;
                    const answer = Array.from(selected).join(', ');
                    appendMessage('user', answer);
                    if (window.promptTreeView) {
                        window.promptTreeView.submitAnswer(nodeId, answer);
                    }
                    optionsDiv.remove();
                };
                
                optionsDiv.appendChild(container);
                optionsDiv.appendChild(submitBtn);
            } else {
                optionsDiv.className = 'd-flex flex-wrap gap-2 mt-2';
                options.forEach(opt => {
                    const btn = document.createElement('button');
                    btn.className = 'btn btn-outline-primary btn-sm';
                    btn.innerText = opt;
                    btn.onclick = () => {
                        appendMessage('user', opt);
                        if (window.promptTreeView) {
                            window.promptTreeView.submitAnswer(nodeId, opt);
                        }
                        optionsDiv.remove();
                    };
                    optionsDiv.appendChild(btn);
                });
            }
            chatContainer.appendChild(optionsDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    });

    window.addEventListener('tree-helper-rewind', (e) => {
        // When rewinding, we might want to clear the chat messages related to the tree
        // For simplicity, let's just show a notification or clear the bottom of chat
        appendMessage('bot', '[System: Session rewound to previous node.]');
    });

    window.addEventListener('tree-helper-save', (e) => {
        const { filename, prompt } = e.detail;
        appendMessage('bot', `Prompt saved to **${filename}**:\n\n\`\`\`markdown\n${prompt}\n\`\`\``);
        // Clear session from tree view to allow starting over
        if (window.promptTreeView) {
            window.promptTreeView.sessionId = null;
            window.promptTreeView.nodes = [];
            window.promptTreeView.render();
        }
    });

    async function handleReset() {
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
    }

    async function handleClone(uuid, messageIndex, showAlert = true) {
        try {
            const response = await fetch(`/sessions/${uuid}/clone`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message_index: messageIndex })
            });
            const data = await response.json();
            if (data.success) {
                if (showAlert) showToast('Conversation forked!');
                
                if (data.new_uuid === "pending") {
                    // For -1 forks, the next message sent will establish the session.
                    // We just need to clear the current chat display.
                    chatContainer.innerHTML = '<div class="text-center text-muted mt-5"><p>Type your edited question to start the branch.</p></div>';
                    currentOffset = 0;
                    window.TOTAL_MESSAGES = 0;
                    loadSessions();
                } else {
                    // The backend sets the new session as active, so we just need to reload.
                    chatContainer.innerHTML = '<div class="text-center text-muted mt-5"><p>Loading forked conversation...</p></div>';
                    await loadMessages(data.new_uuid);
                    loadSessions();
                }
            } else {
                alert('Failed to fork conversation.');
            }
        } catch (error) {
            console.error('Error cloning chat:', error);
            alert('Failed to fork chat.');
        }
    }

    async function handleExport() {
        const uuid = currentActiveUUID;
        if (!uuid) {
            alert('No active session to export.');
            return;
        }

        let title = "chat_export";
        const activeSessionItem = document.querySelector(`.session-item[data-uuid="${uuid}"]`);
        if (activeSessionItem) {
            const titleEl = activeSessionItem.querySelector('.session-title');
            if (titleEl) title = titleEl.textContent.trim();
        }

        try {
            const response = await fetch(`/sessions/${uuid}/messages`);
            if (!response.ok) throw new Error('Network response was not ok');
            const data = await response.json();
            const messages = data.messages || [];

            let markdown = `# Chat Export: ${title}\n\n`;
            messages.forEach(msg => {
                const role = msg.role === 'user' ? 'User' : 'Gemini';
                markdown += `## ${role}\n\n${msg.content}\n\n---\n\n`;
            });

            const blob = new Blob([markdown], { type: 'text/markdown' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            const safeTitle = title.replace(/[^a-z0-9]/gi, '_').substring(0, 50);
            a.download = `${safeTitle}.md`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } catch (e) {
            console.error('Export failed:', e);
            alert('Failed to export chat.');
        }
    }

    if (exportBtn) exportBtn.onclick = handleExport;
    if (exportBtnMobile) exportBtnMobile.onclick = handleExport;
    if (resetBtn) resetBtn.onclick = handleReset;
    if (resetBtnMobile) resetBtnMobile.onclick = handleReset;
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
    
    const liveToast = document.getElementById('liveToast');
    const toastBody = document.getElementById('toast-body');
    const loadMoreContainer = document.getElementById('load-more-container');
    const loadMoreBtn = document.getElementById('load-more-btn');
    const chatWelcome = document.getElementById('chat-welcome');
    const sessionSearch = document.getElementById('session-search');
    const sidebarLoadMoreContainer = document.getElementById('sidebar-load-more-container');
    const sidebarLoadMoreBtn = document.getElementById('sidebar-load-more-btn');
    const sendBtn = document.getElementById('send-btn');
    const stopBtn = document.getElementById('stop-btn');
    const tagFilterContainer = document.getElementById('tag-filter-container');
    const chatTagsHeader = document.getElementById('chat-tags-header');

    const taggingModal = document.getElementById('taggingModal');
    const modalCurrentTags = document.getElementById('modal-current-tags');
    const modalExistingTags = document.getElementById('modal-existing-tags');
    const tagInput = document.getElementById('tag-input');
    const btnAddTag = document.getElementById('btn-add-tag');
    const btnSaveTags = document.getElementById('btn-save-tags');

    const renameModalEl = document.getElementById('renameSessionModal');
    const renameInput = document.getElementById('rename-input');
    const btnSaveRename = document.getElementById('btn-save-rename');
    let renameModal = null;
    let currentRenameUUID = null;
    let currentRenameTitleEl = null; // To update UI immediately

    const treeViewModalEl = document.getElementById('treeViewModal');
    const treeContainer = document.getElementById('tree-container');
    const treeViewBtn = document.getElementById('tree-view-btn');
    const treeViewBtnMobile = document.getElementById('tree-view-btn-mobile');
    let treeViewModal = null;

    // --- Attachment Management ---
    const attachmentQueue = document.getElementById('attachment-queue');
    const dragDropOverlay = document.getElementById('drag-drop-overlay');
    
    // --- Drive Mode ---
    const driveModeBtn = document.getElementById('drive-mode-btn');
    const driveMode = new DriveModeManager();

    const showMicSetting = document.getElementById('setting-show-mic');
    if (showMicSetting && window.USER_SETTINGS) {
        showMicSetting.checked = window.USER_SETTINGS.show_mic !== false;
        
        showMicSetting.onchange = async () => {
            const enabled = showMicSetting.checked;
            try {
                const response = await fetch('/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ show_mic: enabled })
                });
                if (response.ok) {
                    window.USER_SETTINGS.show_mic = enabled;
                    updateDriveModeVisibility();
                }
            } catch (err) {
                console.error('Error saving setting:', err);
            }
        };
    }

    function updateDriveModeVisibility() {
        if (!driveModeBtn) return;
        const isEnabled = window.USER_SETTINGS && window.USER_SETTINGS.show_mic !== false;
        if (driveMode.isSupported() && isEnabled) {
            driveModeBtn.classList.remove('d-none');
        } else {
            driveModeBtn.classList.add('d-none');
        }
    }
    window.updateDriveModeVisibility = updateDriveModeVisibility;

    updateDriveModeVisibility();

    driveModeBtn?.addEventListener('click', () => {
        if (!driveMode.isActive) {
            startDriveMode();
        } else {
            stopDriveMode();
        }
    });

    async function startDriveMode() {
        driveMode.isActive = true;
        driveModeBtn.classList.replace('btn-outline-info', 'btn-info');
        driveModeBtn.innerHTML = '<i class="bi bi-stop-circle-fill"></i>';
        await driveMode.requestWakeLock();
        runDriveModeLoop();
    }

    function stopDriveMode() {
        driveMode.isActive = false;
        driveMode.stopListening();
        driveMode.stopSpeaking();
        driveMode.releaseWakeLock();
        driveModeBtn.classList.replace('btn-info', 'btn-outline-info');
        driveModeBtn.innerHTML = '<i class="bi bi-mic-fill"></i>';
        driveMode.state = 'idle';
        updateDriveModeUI();
    }

    function updateDriveModeUI() {
        const state = driveMode.state;
        const btn = document.getElementById('drive-mode-btn');
        if (!btn) return;

        // Reset icon and animation
        btn.innerHTML = driveMode.isActive ? '<i class="bi bi-stop-circle-fill"></i>' : '<i class="bi bi-mic-fill"></i>';
        btn.classList.remove('pulse-animation');

        if (driveMode.isActive) {
            if (state === 'listening') {
                btn.classList.add('pulse-animation');
                btn.style.color = '#fff';
            } else if (state === 'processing') {
                btn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
            } else if (state === 'speaking') {
                btn.innerHTML = '<i class="bi bi-volume-up-fill"></i>';
            }
        }
    }

    function runDriveModeLoop() {
        if (!driveMode.isActive) return;

        updateDriveModeUI();
        driveMode.state = 'listening';
        updateDriveModeUI();

        driveMode.startListening(
            async (transcript) => {
                const cmd = transcript.toLowerCase().trim();
                // Check for stop words
                if (cmd === 'stop' || cmd === 'σταμάτα' || cmd === 'σταμάτα.') {
                    console.log('Voice Command: Stop detected.');
                    stopDriveMode();
                    driveMode.speak(cmd === 'stop' ? 'Stopping drive mode.' : 'Τερματισμός drive mode.');
                    return;
                }

                // onResult
                driveMode.state = 'processing';
                updateDriveModeUI();
                
                // Add user message to chat UI using standard method
                const userMsgIndex = window.TOTAL_MESSAGES || 0;
                appendMessage('user', transcript, null, null, userMsgIndex);
                window.TOTAL_MESSAGES = userMsgIndex + 1;

                // Send to AI
                try {
                    const loadingObj = appendLoading();
                    toggleStopButton(true);

                    const formData = new FormData();
                    formData.append('message', transcript);
                    formData.append('model', document.getElementById('model-input').value);

                    const response = await fetch('/chat', {
                        method: 'POST',
                        body: formData
                    });

                    if (!response.ok) throw new Error('Chat request failed');

                    // Process stream using NATIVE function for reliability
                    await processStream(response, loadingObj.id);
                    
                    if (!driveMode.isActive) return;

                    // Capture the text from the message we just created
                    const lastBotMsg = chatContainer.querySelector('.message.bot:last-child .message-content');
                    const aiResponse = lastBotMsg ? lastBotMsg.innerText : "";

                    driveMode.state = 'speaking';
                    updateDriveModeUI();

                    driveMode.speak(aiResponse, () => {
                        // onEnd
                        if (driveMode.isActive) {
                            setTimeout(runDriveModeLoop, 500); // Small delay before restart
                        }
                    });
                } catch (err) {
                    console.error('Drive Mode AI Error:', err);
                    if (driveMode.isActive) {
                        driveMode.speak('Σφάλμα επικοινωνίας. Ξαναπροσπαθώ.', () => {
                            setTimeout(runDriveModeLoop, 2000);
                        });
                    }
                } finally {
                    toggleStopButton(false);
                }
            },
            (error) => {
                // onError
                console.warn('Drive Mode STT Error:', error);
                if (driveMode.isActive) {
                    if (error === 'no-speech') {
                        // Silent retry
                        setTimeout(runDriveModeLoop, 1000);
                    } else {
                        driveMode.state = 'idle';
                        updateDriveModeUI();
                        // Possible permanent error, but let's try to recover once
                        setTimeout(runDriveModeLoop, 3000);
                    }
                }
            }
        );
    }

    // Remove the redundant processStreamWithCapture to prevent scope issues
    async function sendToAI(text) {
        // Prepare data
        const formData = new FormData();
        formData.append('message', text);
        formData.append('model', document.getElementById('model-input').value);

        const response = await fetch('/chat', {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error('Chat request failed');

        // Since it's a streaming response usually, we need to handle it.
        // For Drive Mode, we want the FULL text to speak it.
        // We'll use a modified logic or wait for completion.
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            
            // Extract text from SSE format "data: ..."
            const lines = chunk.split('\n');
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.substring(6));
                        if (data.type === 'text') {
                            fullText += data.content;
                        } else if (data.type === 'error') {
                            throw new Error(data.content);
                        }
                    } catch (e) {
                        // Ignore partial JSON or other types
                    }
                }
            }
        }
        return fullText;
    }

    const attachments = new AttachmentManager({
        maxTotalSize: 20 * 1024 * 1024, // 20MB
        onQueueChange: (items) => renderAttachmentQueue(items),
        onSizeLimitExceeded: (fileName) => {
            showToast(`Size limit exceeded: ${fileName} was not added.`);
        }
    });

    function renderAttachmentQueue(items) {
        if (!attachmentQueue) return;
        attachmentQueue.innerHTML = items.map(item => {
            const isImage = item.type.startsWith('image/');
            return `
                <div class="attachment-item position-relative bg-secondary bg-opacity-25 rounded p-1 d-flex align-items-center gap-2" style="max-width: 200px; border: 1px solid rgba(255,255,255,0.1);">
                    ${isImage ? 
                        `<img src="${item.previewUrl}" class="rounded" style="width: 40px; height: 40px; object-fit: cover;">` :
                        `<div class="bg-dark rounded d-flex align-items-center justify-content-center" style="width: 40px; height: 40px;"><i class="bi bi-file-earmark"></i></div>`
                    }
                    <div class="flex-grow-1 overflow-hidden">
                        <div class="small text-truncate" title="${item.name}">${item.name}</div>
                        <div class="text-muted" style="font-size: 0.6rem;">${(item.size / 1024).toFixed(1)} KB</div>
                    </div>
                    <button type="button" class="btn-close btn-close-white small p-1" style="font-size: 0.5rem;" onclick="window.removeAttachment('${item.id}')"></button>
                </div>
            `;
        }).join('');
    }

    window.removeAttachment = (id) => {
        attachments.removeAttachment(id);
    };

    // --- Drag and Drop ---
    if (chatContainer && dragDropOverlay) {
        let dragCounter = 0;

        window.addEventListener('dragenter', (e) => {
            e.preventDefault();
            dragCounter++;
            dragDropOverlay.classList.remove('d-none');
        });

        window.addEventListener('dragleave', (e) => {
            e.preventDefault();
            dragCounter--;
            if (dragCounter === 0) {
                dragDropOverlay.classList.add('d-none');
            }
        });

        window.addEventListener('dragover', (e) => {
            e.preventDefault();
        });

        window.addEventListener('drop', async (e) => {
            e.preventDefault();
            dragCounter = 0;
            dragDropOverlay.classList.add('d-none');
            
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                await attachments.addFiles(e.dataTransfer.files);
                // Auto-switch to Gemini 3 Flash Preview for better vision support
                switchToFlashModel();
            }
        });
    }

    function switchToFlashModel() {
        const flashModel = "gemini-3-flash-preview";
        modelInput.value = flashModel;
        modelLinks.forEach(link => {
            if (link.dataset.model === flashModel) {
                link.classList.add('active');
                let modelName = link.innerText;
                modelName = modelName.replace('Fast', '').replace('Smart', '').trim();
                modelLabel.textContent = modelName + " (Auto-switched)";
            } else {
                link.classList.remove('active');
            }
        });
    }

    if (treeViewModalEl) {
        treeViewModal = new bootstrap.Modal(treeViewModalEl);
        
        const openTree = async () => {
            treeContainer.innerHTML = '<div class="text-center p-5"><div class="spinner-border text-info" role="status"></div><p class="mt-2">Building conversation tree...</p></div>';
            treeViewModal.show();
            
            try {
                // Fetch full fork graph for the user
                const graphRes = await fetch(`/sessions/fork-graph`);
                const graphData = await graphRes.json();
                const graph = graphData.graph; // { uuid: { parent, fork_point, title } }

                renderGraph(graph, currentActiveUUID);

            } catch (error) {
                console.error('Error building tree:', error);
                treeContainer.innerHTML = `<div class="alert alert-danger">Failed to build tree: ${error.message}</div>`;
            }
        };

        if (treeViewBtn) treeViewBtn.onclick = openTree;
        if (treeViewBtnMobile) treeViewBtnMobile.onclick = openTree;
    }

    function renderGraph(graph, activeUUID) {
        treeContainer.innerHTML = '';
        
        if (!activeUUID || !graph[activeUUID]) {
            treeContainer.innerHTML = '<div class="alert alert-info">No related forks found for this conversation.</div>';
            return;
        }

        // Find the root of the current session's tree
        let rootUUID = activeUUID;
        let visited = new Set();
        while (graph[rootUUID] && graph[rootUUID].parent && !visited.has(rootUUID)) {
            visited.add(rootUUID);
            rootUUID = graph[rootUUID].parent;
        }

        const treeRoot = document.createElement('div');
        treeRoot.className = 'tree-view';
        treeRoot.appendChild(createTreeNode(rootUUID, graph, activeUUID));

        treeContainer.appendChild(treeRoot);
    }

    function createTreeNode(uuid, graph, activeUUID) {
        const node = graph[uuid];
        const div = document.createElement('div');
        div.className = 'tree-node-wrapper';
        
        const content = document.createElement('div');
        content.className = `tree-node p-2 mb-3 rounded border ${uuid === activeUUID ? 'bg-primary text-white shadow-lg border-light' : 'bg-dark text-light border-secondary'}`;
        content.style.cursor = 'pointer';
        content.style.maxWidth = '280px';
        content.style.transition = 'all 0.2s';
        content.style.borderRadius = '15px';
        
        const header = document.createElement('div');
        header.className = 'tree-node-header mb-1 small text-info d-flex align-items-center gap-1';
        
        const forkIcon = `<svg width="14" height="14" fill="currentColor" viewBox="0 0 16 16" style="margin-top: -2px;"><path d="M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z"></path></svg>`;
        header.innerHTML = node.parent ? forkIcon : `<i class="bi bi-chat-left-text"></i>`;
        
        const title = document.createElement('div');
        title.className = 'fw-bold text-truncate flex-grow-1';
        title.style.fontSize = '0.85rem';
        title.textContent = node.title || 'Untitled Chat';
        header.appendChild(title);
        
        const meta = document.createElement('div');
        meta.className = `small ${uuid === activeUUID ? 'text-white-50' : 'text-muted'}`;
        meta.style.fontSize = '0.7rem';
        if (node.parent) {
            meta.textContent = `Forked at msg #${node.fork_point + 1}`;
        } else {
            meta.textContent = 'Root Conversation';
        }
        
        content.appendChild(header);
        content.appendChild(meta);
        
        content.onclick = () => {
            if (uuid !== activeUUID) {
                switchSession(uuid);
                treeViewModal.hide();
            }
        };

        // Hover effect
        content.onmouseover = () => { 
            content.style.transform = 'scale(1.02)';
            if (uuid !== activeUUID) content.classList.add('border-primary'); 
        };
        content.onmouseout = () => { 
            content.style.transform = 'scale(1)';
            if (uuid !== activeUUID) content.classList.remove('border-primary'); 
        };

        div.appendChild(content);

        // Children - sort them by fork point
        const children = Object.keys(graph).filter(u => graph[u].parent === uuid);
        children.sort((a, b) => (graph[a].fork_point || 0) - (graph[b].fork_point || 0));

        if (children.length > 0) {
            const childrenContainer = document.createElement('div');
            childrenContainer.className = 'tree-children ms-4 ps-3 border-start border-secondary';
            children.forEach(childUUID => {
                childrenContainer.appendChild(createTreeNode(childUUID, graph, activeUUID));
            });
            div.appendChild(childrenContainer);
        }

        return div;
    }

    if (renameModalEl) {
        renameModal = new bootstrap.Modal(renameModalEl);
        
        renameModalEl.addEventListener('shown.bs.modal', () => {
            renameInput.focus();
        });

        if (btnSaveRename) {
            btnSaveRename.addEventListener('click', async () => {
                const newTitle = renameInput.value.trim();
                if (!newTitle || !currentRenameUUID) return;
                
                try {
                    const response = await fetch(`/sessions/${currentRenameUUID}/title`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ title: newTitle })
                    });
                    const data = await response.json();
                    if (data.success) {
                        if (currentRenameTitleEl) currentRenameTitleEl.textContent = newTitle;
                        showToast('Chat renamed');
                        renameModal.hide();
                    } else {
                        alert('Failed to rename chat: ' + (data.error || 'Unknown error'));
                    }
                } catch (error) {
                    console.error('Error renaming session:', error);
                    alert('Failed to rename chat.');
                }
            });
        }
    }

    let currentFile = null;
    let allPatterns = [];
    let currentOffset = 0;
    let sidebarOffset = 0;
    const PAGE_LIMIT = 20;
    const SIDEBAR_PAGE_LIMIT = 10;
    let isLoadingHistory = false;
    let isLoadingSidebar = false;

    let activeTags = new Set();
    let allUniqueTags = [];
    let currentForkMap = {}; // index -> [uuids]
    let currentActiveUUID = window.ACTIVE_SESSION_UUID || null;

    function toggleStopButton(show) {
        if (show) {
            sendBtn.classList.add('d-none');
            stopBtn.classList.remove('d-none');
        } else {
            sendBtn.classList.remove('d-none');
            stopBtn.classList.add('d-none');
        }
    }

    if (stopBtn) {
        stopBtn.addEventListener('click', async () => {
            if (driveMode.isActive) {
                stopDriveMode();
            }
            try {
                const response = await fetch('/stop', { method: 'POST' });
                if (response.ok) {
                    toggleStopButton(false);
                }
            } catch (error) {
                console.error('Error stopping chat:', error);
            }
        });
    }

    function showToast(message) {
        if (!liveToast) return;
        toastBody.textContent = message;
        const toast = new bootstrap.Toast(liveToast);
        toast.show();
    }

    async function fetchUniqueTags() {
        try {
            const response = await fetch('/sessions/tags');
            const data = await response.json();
            allUniqueTags = data.tags || [];
            renderTagFilters();
        } catch (error) {
            console.error('Error fetching tags:', error);
        }
    }

    async function fetchForks(uuid) {
        try {
            const response = await fetch(`/sessions/${uuid}/forks`);
            const data = await response.json();
            currentForkMap = data.forks || {};
        } catch (error) {
            console.error('Error fetching forks:', error);
            currentForkMap = {};
        }
    }

    function renderTagFilters() {
        if (!tagFilterContainer) return;
        if (!allUniqueTags || allUniqueTags.length === 0) {
            tagFilterContainer.innerHTML = '';
            return;
        }

        tagFilterContainer.innerHTML = allUniqueTags.map(tag => `
            <span class="tag-badge ${activeTags.has(tag) ? 'selected' : ''}" data-tag="${tag}">${tag}</span>
        `).join('');

        tagFilterContainer.querySelectorAll('.tag-badge').forEach(badge => {
            badge.onclick = () => toggleTagFilter(badge.dataset.tag);
        });
    }

    function toggleTagFilter(tag) {
        if (activeTags.has(tag)) {
            activeTags.delete(tag);
        } else {
            activeTags.add(tag);
        }
        renderTagFilters();
        sidebarOffset = 0;
        loadSessions(false);
    }

    async function updateSessionTags(uuid, tags) {
        try {
            const response = await fetch(`/sessions/${uuid}/tags`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tags })
            });
            const data = await response.json();
            if (data.success) {
                fetchUniqueTags();
                loadSessions(false);
                return true;
            }
        } catch (error) {
            console.error('Error updating tags:', error);
        }
        return false;
    }

    function renderChatTags(session) {
        const headerContainer = document.getElementById('chat-tags-header');
        const sidebarContainer = document.getElementById('chat-tags-sidebar');
        if (!headerContainer || !sidebarContainer) return;

        if (!session || !session.uuid) {
            headerContainer.innerHTML = '';
            sidebarContainer.innerHTML = '';
            return;
        }

        const tags = session.tags || [];
        const isMobile = window.innerWidth < 768;

        let html = tags.map(tag => `<span class="tag-badge selected">${tag}</span>`).join('');
        html += `<span class="tag-badge add-tag-btn" title="Edit Tags"><i class="bi bi-plus"></i> Tags</span>`;

        if (isMobile) {
            headerContainer.innerHTML = '';
            sidebarContainer.innerHTML = html;
        } else {
            sidebarContainer.innerHTML = '';
            headerContainer.innerHTML = html;
        }

        // Clicking on tags or the add button opens the modal
        const targetContainer = isMobile ? sidebarContainer : headerContainer;
        const allBadges = targetContainer.querySelectorAll('.tag-badge');
        allBadges.forEach(badge => {
            badge.onclick = () => {
                let modalInstance = bootstrap.Modal.getInstance(taggingModal);
                if (!modalInstance) {
                    modalInstance = new bootstrap.Modal(taggingModal);
                }

                let workingTags = [...tags];

                function renderModalTags() {
                    modalCurrentTags.innerHTML = workingTags.map(t => `
                        <span class="tag-badge selected" data-tag="${t}">${t} <i class="bi bi-x ms-1 remove-tag"></i></span>
                    `).join('');

                    modalCurrentTags.querySelectorAll('.remove-tag').forEach(btn => {
                        btn.onclick = (e) => {
                            e.stopPropagation();
                            const tagToRemove = btn.parentElement.dataset.tag;
                            workingTags = workingTags.filter(t => t !== tagToRemove);
                            renderModalTags();
                        };
                    });

                    // Render existing tags suggestions
                    modalExistingTags.innerHTML = allUniqueTags
                        .filter(t => !workingTags.includes(t))
                        .map(t => `<span class="tag-badge" data-tag="${t}">${t}</span>`)
                        .join('');

                    modalExistingTags.querySelectorAll('.tag-badge').forEach(badge => {
                        badge.onclick = () => {
                            workingTags.push(badge.dataset.tag);
                            renderModalTags();
                        };
                    });
                }

                renderModalTags();
                tagInput.value = '';

                function addTagFromInput() {
                    const rawVal = tagInput.value.trim();
                    if (!rawVal) return;

                    // Support comma-separated tags
                    const newTags = rawVal.split(',').map(t => t.trim()).filter(t => t !== '');
                    let added = false;

                    newTags.forEach(val => {
                        if (!workingTags.includes(val)) {
                            workingTags.push(val);
                            added = true;
                        }
                    });

                    if (added) {
                        tagInput.value = '';
                        renderModalTags();
                    }
                }

                tagInput.onkeydown = (e) => {
                    if (e.key === 'Enter' || e.key === ',') {
                        e.preventDefault();
                        addTagFromInput();
                    }
                };

                if (btnAddTag) {
                    btnAddTag.onclick = (e) => {
                        e.preventDefault();
                        addTagFromInput();
                    };
                }

                btnSaveTags.onclick = async () => {
                    if (await updateSessionTags(session.uuid, workingTags)) {
                        session.tags = workingTags;
                        renderChatTags(session);
                        modalInstance.hide();
                    }
                };

                modalInstance.show();
            };
        });
    }

    function debounce(func, timeout = 300) {
        let timer;
        return (...args) => {
            clearTimeout(timer);
            timer = setTimeout(() => { func.apply(this, args); }, timeout);
        };
    }

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
                    const modalInstance = bootstrap.Modal.getInstance(toolsModal);
                    if (modalInstance) modalInstance.hide();
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

    if (loadMoreBtn) {
        loadMoreBtn.addEventListener('click', () => {
            const activeSessionItem = document.querySelector('.session-item.active-session');
            if (activeSessionItem) {
                loadMessages(activeSessionItem.dataset.uuid, PAGE_LIMIT, currentOffset);
            }
        });
    }

    if (sessionSearch) {
        sessionSearch.addEventListener('input', debounce(() => {
            if (sessionSearch.value.trim() !== "") {
                activeTags.clear();
                renderTagFilters();
            }
            loadSessions();
        }, 300));
    }

    if (sidebarLoadMoreBtn) {
        sidebarLoadMoreBtn.addEventListener('click', () => {
            sidebarOffset += SIDEBAR_PAGE_LIMIT;
            loadSessions(true);
        });
    }

    // Load sessions when sidebar is shown
    historySidebar.addEventListener('show.bs.offcanvas', () => loadSessions());

    // Load sessions on page load
    fetchUniqueTags();
    loadSessions();

    // Initial load from server-side messages
    if (window.INITIAL_MESSAGES && window.INITIAL_MESSAGES.length > 0) {
        if (chatWelcome) chatWelcome.classList.add('d-none');
        window.INITIAL_MESSAGES.forEach((msg, idx) => {
            const msgDiv = createMessageDiv(msg.role, msg.content, null, null, idx);
            if (msgDiv) chatContainer.appendChild(msgDiv);
        });
        chatContainer.scrollTop = chatContainer.scrollHeight;
        currentOffset = window.INITIAL_MESSAGES.length;
        window.HAS_INITIAL_MESSAGES = true;
    }

    
    async function loadMessages(uuid, limit = PAGE_LIMIT, offset = 0, isAutoRestore = false) {
        if (isLoadingHistory) return;
        if (offset > 0) isLoadingHistory = true;

        if (offset === 0) {
            currentActiveUUID = uuid;
            await fetchForks(uuid);
        }

        try {
            const response = await fetch(`/sessions/${uuid}/messages?limit=${limit}&offset=${offset}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            const messages = data.messages || [];
            const total = data.total || 0;
            
            if (offset === 0) {
                // Clear existing messages only if it's the first page
                chatContainer.innerHTML = '<div id="scroll-sentinel" style="height: 10px; width: 100%;"></div>';
                currentOffset = 0;
                window.TOTAL_MESSAGES = total; // Update global
                if (chatWelcome) chatWelcome.classList.add('d-none');
            }

            if (messages.length > 0) {
                if (offset === 0) {
                    messages.forEach((msg, idx) => {
                        const index = (msg.raw_index !== undefined) ? msg.raw_index : idx;
                        const msgDiv = createMessageDiv(msg.role, msg.content, null, null, index);
                        if (msgDiv) chatContainer.appendChild(msgDiv);
                    });
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                } else {
                    // Prepend for "Load More"
                    const scrollHeightBefore = chatContainer.scrollHeight;
                    
                    const sentinel = document.getElementById('scroll-sentinel');
                    const loadMore = document.getElementById('load-more-container');
                    const originalFirstMessage = loadMore ? loadMore.nextSibling : (sentinel ? sentinel.nextSibling : chatContainer.firstChild);

                    // If total is 100, offset is 20, limit is 20.
                    // We loaded messages 60 to 79 (total - offset - limit to total - offset)
                    // The index of the first message in this chunk is total - offset - messages.length
                    const baseIndex = total - offset - messages.length;

                    messages.forEach((msg, idx) => {
                        const index = (msg.raw_index !== undefined) ? msg.raw_index : (baseIndex + idx);
                        const msgDiv = createMessageDiv(msg.role, msg.content, null, null, index); 
                        if (msgDiv) {
                            chatContainer.insertBefore(msgDiv, originalFirstMessage);
                        }
                    });
                    
                    chatContainer.scrollTop = chatContainer.scrollHeight - scrollHeightBefore;
                }
                
                currentOffset += messages.length;
                
                // Show/Hide Load More
                if (currentOffset < total) {
                    if (loadMoreContainer) loadMoreContainer.classList.remove('d-none');
                } else {
                    if (loadMoreContainer) loadMoreContainer.classList.add('d-none');
                }

                if (isAutoRestore) {
                    showToast('Resumed last session');
                }
            } else {
                if (offset === 0) {
                    if (chatWelcome) chatWelcome.classList.remove('d-none');
                }
                if (loadMoreContainer) loadMoreContainer.classList.add('d-none');
            }
        } catch (error) {
            console.error('Error loading messages:', error);
        } finally {
            isLoadingHistory = false;
        }
    }

    async function loadSessions(append = false) {
        if (isLoadingSidebar) return;
        if (!append) sidebarOffset = 0;
        
        let query = "";
        if (sessionSearch) {
            query = sessionSearch.value.trim();
        }
        
        let url = `/sessions?limit=${SIDEBAR_PAGE_LIMIT}&offset=${sidebarOffset}`;
        
        if (activeTags.size > 0) {
            url += `&tags=${encodeURIComponent(Array.from(activeTags).join(','))}`;
        }
        
        if (query) {
            url = `/sessions/search?q=${encodeURIComponent(query)}`;
            // Clear tags if searching by text for now to avoid complexity, 
            // or we could combine them if backend search supported it.
        }

        try {
            isLoadingSidebar = true;
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const sessions = await response.json();
            
            // Auto-create if none and not searching
            if (!query && !append && sessions.length === 0) {
                const newRes = await fetch('/sessions/new', { method: 'POST' });
                if (newRes.ok) {
                    loadSessions();
                    return;
                }
            }

            try {
                renderSessions(sessions, append);
            } catch (renderError) {
                console.error('Error rendering sessions:', renderError);
            }
            
            // Handle Load More visibility
            if (query) {
                if (sidebarLoadMoreContainer) sidebarLoadMoreContainer.classList.add('d-none');
            } else {
                const unpinnedCount = sessions.filter(s => !s.pinned).length;
                if (unpinnedCount === SIDEBAR_PAGE_LIMIT) {
                    if (sidebarLoadMoreContainer) sidebarLoadMoreContainer.classList.remove('d-none');
                } else {
                    if (sidebarLoadMoreContainer) sidebarLoadMoreContainer.classList.add('d-none');
                }
            }

            const activeSession = sessions.find(s => s.active);
            try {
                renderChatTags(activeSession);
            } catch (tagError) {
                console.error('Error rendering chat tags:', tagError);
            }
            
            // Check if we need to auto-load (only on initial load)
            if (!append && !query) {
                const hasMessages = chatContainer.querySelectorAll('.message').length > 0;
                if (activeSession && !hasMessages && !window.HAS_INITIAL_MESSAGES) {
                     loadMessages(activeSession.uuid, PAGE_LIMIT, 0, true);
                }
            }
        } catch (error) {
            console.error('Error loading sessions:', error);
            if (sessionsList && !append) sessionsList.innerHTML = `<div class="alert alert-danger mx-3 mt-3">Failed to load history: ${error.message}</div>`;
        } finally {
            isLoadingSidebar = false;
        }
    }

    function renderSessions(sessions, append = false) {
        if (!append && sessions.length === 0) {
            sessionsList.innerHTML = '<div class="text-center p-3 text-muted">No history found.</div>';
            return;
        }

        const html = sessions.map(s => `
            <div class="list-group-item list-group-item-action bg-dark text-light session-item ${(s.active || s.has_active_fork) ? 'active-session' : ''}" data-uuid="${s.uuid}">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1 overflow-hidden">
                        <span class="session-title text-truncate">${s.title || 'Untitled Chat'}</span>
                        <div class="session-tags-list">
                            ${(s.tags || []).map(t => `<span class="session-tag-item">${t}</span>`).join('')}
                        </div>
                        <span class="session-time">${s.time || ''}</span>
                    </div>
                    <div class="d-flex align-items-center gap-1">
                        ${(s.active || s.has_active_fork) ? '<span class="badge bg-primary rounded-pill small me-1">Active</span>' : ''}
                        <button class="btn btn-sm pin-btn border-0 ${s.pinned ? 'pinned' : ''}" data-uuid="${s.uuid}" title="${s.pinned ? 'Unpin Chat' : 'Pin Chat'}">
                            <i class="bi ${s.pinned ? 'bi-pin-fill' : 'bi-pin'}"></i>
                        </button>
                        <button class="btn btn-sm rename-session-btn border-0" data-uuid="${s.uuid}" title="Rename Chat">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger border-0 delete-session-btn" data-uuid="${s.uuid}" title="Delete Chat">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `).join('');

        if (append) {
            sessionsList.insertAdjacentHTML('beforeend', html);
        } else {
            sessionsList.innerHTML = html;
        }

        attachSessionListeners();
    }

    async function renameSession(uuid, newTitle, titleSpan) {
        try {
            const response = await fetch(`/sessions/${uuid}/title`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: newTitle })
            });
            const data = await response.json();
            if (data.success) {
                titleSpan.textContent = newTitle;
                showToast('Chat renamed');
            } else {
                alert('Failed to rename chat: ' + (data.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error renaming session:', error);
            alert('Failed to rename chat.');
        }
    }

    async function switchSession(uuid) {
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
                const historyEl = document.getElementById('historySidebar');
                const offcanvas = bootstrap.Offcanvas.getInstance(historyEl);
                if (offcanvas) offcanvas.hide();
                loadSessions();
            }
        } catch (error) {
            console.error('Error switching session:', error);
            alert('Failed to switch session.');
        }
    }

    function attachSessionListeners() {
        document.querySelectorAll('.session-item').forEach(item => {
            item.onclick = async (e) => {
                if (e.target.closest('button')) return;

                const uuid = item.dataset.uuid;
                if (item.classList.contains('active-session')) {
                    bootstrap.Offcanvas.getInstance(historySidebar).hide();
                    return;
                }
                
                await switchSession(uuid);
            };
        });

        document.querySelectorAll('.pin-btn').forEach(btn => {
            btn.onclick = async (e) => {
                e.stopPropagation();
                const uuid = btn.dataset.uuid;
                try {
                    const response = await fetch(`/sessions/${uuid}/pin`, { method: 'POST' });
                    const data = await response.json();
                    loadSessions();
                } catch (error) {
                    console.error('Error pinning session:', error);
                }
            };
        });

        document.querySelectorAll('.rename-session-btn').forEach(btn => {
            btn.onclick = (e) => {
                e.stopPropagation();
                const uuid = btn.dataset.uuid;
                const item = btn.closest('.session-item');
                const titleSpan = item.querySelector('.session-title');
                const oldTitle = titleSpan.textContent.trim();
                
                currentRenameUUID = uuid;
                currentRenameTitleEl = titleSpan;
                if (renameInput) renameInput.value = oldTitle;
                if (renameModal) renameModal.show();
            };
        });

        document.querySelectorAll('.delete-session-btn').forEach(btn => {
            btn.onclick = async (e) => {
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
            };
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

        // Sort: User prompts first, then system patterns
        patterns.sort((a, b) => {
            if (a.type === 'user' && b.type !== 'user') return -1;
            if (a.type !== 'user' && b.type === 'user') return 1;
            return a.name.localeCompare(b.name);
        });

        patternsList.innerHTML = patterns.map(p => {
            if (p.type === 'user') {
                return `
                <div class="list-group-item bg-dark text-light border-secondary d-flex justify-content-between align-items-center">
                    <div class="flex-grow-1 cursor-pointer user-prompt-item" data-name="${p.name}">
                        <div class="d-flex align-items-center">
                            <h6 class="mb-1 text-info"><i class="bi bi-file-text me-2"></i>${p.name}</h6>
                        </div>
                        <small class="text-muted">${p.description}</small>
                    </div>
                    <div class="d-flex gap-2">
                        <button class="btn btn-sm btn-outline-warning edit-prompt-btn" data-name="${p.name}" title="Edit"><i class="bi bi-pencil"></i></button>
                        <button class="btn btn-sm btn-outline-danger delete-prompt-btn" data-name="${p.name}" title="Delete"><i class="bi bi-trash"></i></button>
                    </div>
                </div>`;
            } else {
                return `
                <button type="button" class="list-group-item list-group-item-action bg-dark text-light border-secondary pattern-item" data-pattern="${p.name}">
                    <div class="d-flex w-100 justify-content-between">
                        <h6 class="mb-1"><i class="bi bi-magic me-2"></i>${p.name}</h6>
                    </div>
                    <small class="text-muted">${p.description || ''}</small>
                </button>`;
            }
        }).join('');

        // System Pattern Click
        document.querySelectorAll('.pattern-item').forEach(item => {
            item.addEventListener('click', () => {
                const pattern = item.dataset.pattern;
                messageInput.value = `/p ${pattern} ${messageInput.value}`;
                bootstrap.Modal.getInstance(patternsModal).hide();
                messageInput.focus();
                messageInput.dispatchEvent(new Event('input'));
            });
        });

        // User Prompt Click (Load)
        document.querySelectorAll('.user-prompt-item').forEach(item => {
            item.addEventListener('click', async () => {
                const name = item.dataset.name;
                // Fetch content? Or just assume it was loaded?
                // The list endpoint didn't return content. We need to fetch or just execute.
                // Actually, prompts are files. We can't just "/p name" them unless the backend supports it.
                // The backend "apply_pattern" reads from PATTERNS dict. It doesn't read files yet.
                // BUT, the request was "list prompts... option to edit or delete".
                // If I click it, maybe I want to RUN it?
                // For now, let's load it into the input as text so the user can send it.
                try {
                    // We need an endpoint to get the content. 
                    // We can reuse the `get_pats` if we included content, or add a simple get endpoint.
                    // Or, we can use `read_file` via tool? No, frontend.
                    // Let's assume for now clicking puts `/p name` and we update backend to handle file prompts.
                    // WAIT, I updated `get_pats` but didn't update `apply_pattern`.
                    // Let's implement client-side fetch for content to populate input.
                    // I'll add a quick fetch logic here.
                    const res = await fetch(`/api/prompt-helper/prompts/${name}`); // Need this endpoint? No, we have PUT/DELETE.
                    // We don't have GET content endpoint in prompt_helper.
                    // I will add GET /api/prompt-helper/prompts/{filename} to the router next.
                } catch (e) {}
            });
        });
        
        // Delete Prompt
        document.querySelectorAll('.delete-prompt-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                if (confirm(`Delete prompt "${btn.dataset.name}"?`)) {
                    try {
                        const res = await fetch(`/api/prompt-helper/prompts/${btn.dataset.name}`, { method: 'DELETE' });
                        if (res.ok) {
                            allPatterns = allPatterns.filter(p => p.name !== btn.dataset.name);
                            renderPatterns(allPatterns);
                        } else {
                            alert('Failed to delete prompt.');
                        }
                    } catch (err) {
                        console.error(err);
                    }
                }
            });
        });

        // Edit Prompt (Open Modal)
        document.querySelectorAll('.edit-prompt-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const name = btn.dataset.name;
                const modalEl = document.getElementById('editPromptModal');
                const editModal = new bootstrap.Modal(modalEl);
                
                try {
                    const res = await fetch(`/api/prompt-helper/prompts/${name}`);
                    const data = await res.json();
                    if (data.content) {
                        document.getElementById('edit-prompt-filename').value = name;
                        document.getElementById('edit-prompt-content').value = data.content;
                        editModal.show();
                    }
                } catch (err) {
                    console.error(err);
                    alert('Failed to load prompt content.');
                }
            });
        });

        // Handle Prompt Save
        const savePromptBtn = document.getElementById('btn-save-prompt-edit');
        if (savePromptBtn) {
            savePromptBtn.onclick = async () => {
                const filename = document.getElementById('edit-prompt-filename').value;
                const content = document.getElementById('edit-prompt-content').value;
                const formData = new FormData();
                formData.append('content', content);

                try {
                    const res = await fetch(`/api/prompt-helper/prompts/${filename}`, {
                        method: 'PUT',
                        body: formData
                    });
                    const data = await res.json();
                    if (data.success) {
                        showToast('Prompt updated successfully!');
                        bootstrap.Modal.getInstance(document.getElementById('editPromptModal')).hide();
                    } else {
                        alert('Failed to update prompt.');
                    }
                } catch (err) {
                    console.error(err);
                    alert('Error saving prompt.');
                }
            };
        }
        
        // User Prompt Item Click (Load content into chat input)
        document.querySelectorAll('.user-prompt-item').forEach(item => {
            item.addEventListener('click', async () => {
                const name = item.dataset.name;
                try {
                    const res = await fetch(`/api/prompt-helper/prompts/${name}`);
                    const data = await res.json();
                    if (data.content) {
                        messageInput.value = data.content;
                        bootstrap.Modal.getInstance(patternsModal).hide();
                        messageInput.focus();
                        messageInput.dispatchEvent(new Event('input'));
                    }
                } catch (err) {
                    console.error(err);
                }
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
    fileUpload.addEventListener('change', async (e) => {
        if (e.target.files.length > 0) {
            await attachments.addFiles(e.target.files);
            switchToFlashModel();
            fileUpload.value = ''; // Reset input to allow re-selecting same file
        }
    });

    /*
    clearFileBtn.addEventListener('click', () => {
        fileUpload.value = '';
        currentFile = null;
        filePreviewArea.classList.add('d-none');
    });
    */

        chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const message = messageInput.value.trim();
        const queuedFiles = attachments.getFiles();
        
        if (!message && queuedFiles.length === 0) return;

        // Add user message to chat
        const userMsgIndex = window.TOTAL_MESSAGES || 0;
        const attachmentText = queuedFiles.length > 0 ? 
            ` [${queuedFiles.length} attachment(s)]` : '';
            
        // For local display, we show the first file as a thumbnail if it's an image
        const firstFile = queuedFiles.length > 0 ? queuedFiles[0] : null;
        
        appendMessage('user', message + attachmentText, null, firstFile, userMsgIndex);
        window.TOTAL_MESSAGES = userMsgIndex + 1;

        // --- Tree Helper Integration ---
        if (window.promptTreeView && window.promptTreeView.sessionId) {
            // Check if there's an active node waiting for answer
            const activeNode = window.promptTreeView.nodes.find(n => n.id === window.promptTreeView.currentNodeId && !n.answer);
            if (activeNode) {
                window.promptTreeView.submitAnswer(activeNode.id, message);
                messageInput.value = '';
                messageInput.style.height = '';
                attachments.clear();
                return; // Stop standard chat flow
            }
        }
        // ------------------------------
        
        // Clear inputs immediately
        messageInput.value = '';
        messageInput.style.height = '';
        const filesToSend = [...queuedFiles]; 
        attachments.clear();

        // Show loading state
        const loadingId = appendLoading();
        toggleStopButton(true);

        try {
            const formData = new FormData();
            formData.append('message', message);
            
            for (const file of filesToSend) {
                // Files are already compressed by AttachmentManager if they are images
                formData.append('file', file);
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

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('text/event-stream')) {
                await processStream(response, loadingId);
            } else {
                const data = await response.json();
                removeLoading(loadingId);
                appendMessage('bot', data.response);
            }

        } catch (error) {
            removeLoading(loadingId);
            console.error('Detailed Chat Error:', error);
            let displayError = error.message || 'Unknown Error';
            if (error instanceof TypeError && error.message === 'Failed to fetch') {
                displayError = 'Network Error: Could not connect to the server. Check if the service is running and accessible.';
            }
            appendMessage('bot', `Error: ${displayError}`);
        } finally {
            toggleStopButton(false);
        }
    });

    async function processStream(response, loadingId) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let messageDiv = null;
        
        let fullText = "";
        let toolLogs = [];
        let buffer = "";
        let errorYielded = false;
        
        const renderInterval = 100; // ms
        let lastRenderTime = 0;

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();

                for (const line of lines) {
                    const trimmedLine = line.trim();
                    if (!trimmedLine || trimmedLine.startsWith(':')) continue; // Skip empty or heartbeats

                    if (trimmedLine.startsWith('data: ')) {
                        const dataStr = trimmedLine.substring(6).trim();
                        if (dataStr === '[DONE]') continue;
                        
                        try {
                            const data = JSON.parse(dataStr);
                            if (data.type === 'message' && data.role === 'assistant') {
                                fullText += data.content;
                            } else if (data.type === 'question') {
                                // Render question card
                                renderQuestionCard(data);
                            } else if (data.type === 'model_switch') {
                                // Update hidden input for subsequent requests
                                if (modelInput) modelInput.value = data.new_model;
                                
                                // Update active state in the dropdown menu
                                modelLinks.forEach(link => {
                                    if (link.dataset.model === data.new_model) {
                                        link.classList.add('active');
                                    } else {
                                        link.classList.remove('active');
                                    }
                                });

                                // Update footer label
                                const label = document.getElementById('model-label');
                                if (label) {
                                    // Make it look nice, e.g. "Gemini 3 Flash (Auto-switched)"
                                    let cleanName = data.new_model.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                                    // Remove 'Preview' etc if redundant, but keep it clear
                                    label.textContent = cleanName + " (Auto-switched)";
                                    label.classList.add('text-warning'); // Highlight the change
                                }
                            } else if (data.type === 'tool_use') {
                                toolLogs.push({ type: 'call', name: data.tool_name, input: data.parameters });
                            } else if (data.type === 'tool_result') {
                                if (data.output && data.output.trim() !== "") {
                                    toolLogs.push({ type: 'output', output: data.output, full_path: data.full_output_path });
                                }
                            } else if (data.type === 'error') {
                                fullText += `\n\n[Error: ${data.content}]\n\n`;
                                errorYielded = true;
                            }
                            
                            if (!messageDiv && (fullText.trim().length > 0 || toolLogs.length > 0)) {
                                const botMsgIndex = window.TOTAL_MESSAGES || 0;
                                messageDiv = createStreamingMessage('bot', botMsgIndex);
                                window.TOTAL_MESSAGES = botMsgIndex + 1;
                                removeLoading(loadingId);
                                if (chatWelcome) chatWelcome.classList.add('d-none');
                            }

                            if (messageDiv) {
                                const now = Date.now();
                                if (now - lastRenderTime > renderInterval) {
                                    updateStreamingMessage(messageDiv, fullText, toolLogs);
                                    lastRenderTime = now;
                                }
                            }
                        } catch (e) {
                            console.error('Error parsing stream chunk:', e, dataStr);
                        }
                    }
                }
            }
            if (messageDiv) {
                updateStreamingMessage(messageDiv, fullText, toolLogs, true);
            } else {
                removeLoading(loadingId);
            }
            toggleStopButton(false);
        } catch (error) {
            console.error('Stream processing error:', error);
            if (!errorYielded) {
                if (!messageDiv) {
                    messageDiv = createStreamingMessage('bot');
                    removeLoading(loadingId);
                }
                const errorDiv = document.createElement('div');
                errorDiv.className = 'text-danger small mt-2';
                errorDiv.textContent = 'Connection lost. Message may be incomplete.';
                messageDiv.appendChild(errorDiv);
            }
        }
    }

    function createStreamingMessage(sender, index = null) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender);
        if (index !== null) messageDiv.dataset.index = index;
        
        const contentArea = document.createElement('div');
        contentArea.className = 'message-content';
        messageDiv.appendChild(contentArea);
        
        const logsArea = document.createElement('div');
        logsArea.className = 'tool-logs mt-2 d-none';
        messageDiv.appendChild(logsArea);
        
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        return messageDiv;
    }

    function renderQuestionCard(data) {
        const { question, options, allow_multiple } = data;
        
        const card = document.createElement('div');
        card.className = 'question-card';
        
        const qText = document.createElement('div');
        qText.className = 'question-text';
        qText.innerText = question;
        card.appendChild(qText);
        
        const optContainer = document.createElement('div');
        optContainer.className = 'options-container';
        
        const dismissCard = () => {
            card.classList.add('removing');
            setTimeout(() => card.remove(), 200);
        };

        if (!options || options.length === 0) {
            // Open-ended question
            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'form-control bg-dark text-light border-secondary mb-2';
            input.placeholder = 'Type your answer...';
            card.appendChild(input);
            
            const submit = document.createElement('button');
            submit.className = 'btn btn-primary btn-sm w-100';
            submit.innerText = 'Submit';
            submit.onclick = () => {
                const val = input.value.trim();
                if (val) {
                    submitAnswer(val);
                    dismissCard();
                }
            };
            card.appendChild(submit);
            
            // Allow Enter key
            input.onkeydown = (e) => {
                if (e.key === 'Enter') submit.click();
            };
        } else {
            // Multiple choice
            const selected = new Set();
            
            options.forEach(opt => {
                const btn = document.createElement('button');
                btn.className = 'option-btn';
                btn.innerText = opt;
                btn.onclick = () => {
                    if (allow_multiple) {
                        if (selected.has(opt)) {
                            selected.delete(opt);
                            btn.classList.remove('active');
                        } else {
                            selected.add(opt);
                            btn.classList.add('active');
                        }
                    } else {
                        submitAnswer(opt);
                        dismissCard();
                    }
                };
                optContainer.appendChild(btn);
            });
            
            card.appendChild(optContainer);
            
            if (allow_multiple) {
                const submit = document.createElement('button');
                submit.className = 'btn btn-primary btn-sm submit-btn';
                submit.innerText = 'Submit Selection';
                submit.onclick = () => {
                    if (selected.size > 0) {
                        submitAnswer(Array.from(selected).join(', '));
                        dismissCard();
                    }
                };
                card.appendChild(submit);
            }
        }
        
        chatContainer.appendChild(card);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    async function submitAnswer(text) {
        // Send answer as a normal user message
        messageInput.value = text;
        chatForm.dispatchEvent(new Event('submit'));
    }

    function updateStreamingMessage(messageDiv, text, toolLogs, isFinal = false) {
        const contentArea = messageDiv.querySelector('.message-content');
        const logsArea = messageDiv.querySelector('.tool-logs');
        
        // Render Text
        if (text.trim().length > 0) {
            if (typeof marked !== 'undefined') {
                contentArea.innerHTML = marked.parse(text);
            } else {
                contentArea.textContent = text;
            }
        }
        
        // Render Logs
        if (toolLogs.length > 0) {
            logsArea.classList.remove('d-none');
            logsArea.innerHTML = toolLogs.map(log => {
                if (log.type === 'call') {
                    return `<div class="small text-info border-start border-info ps-2 mb-1" style="font-family: monospace;">
                        <strong>Tool Call:</strong> ${log.name}<br>
                        <span class="text-muted" style="word-break: break-all; font-size: 0.7rem;">${JSON.stringify(log.input)}</span>
                    </div>`;
                } else {
                    if (!log.output || log.output.trim() === "") return "";
                    let outputHtml = `<div class="small text-success border-start border-success ps-2 mb-2" style="font-family: monospace;">
                        <strong>Tool Output:</strong><br>
                        <pre class="m-0" style="font-size: 0.7rem; max-height: 150px; overflow: auto; background: #1a1a1a; padding: 5px; border-radius: 4px;">${log.output}</pre>`;
                    
                    if (log.full_path) {
                        outputHtml += `<div class="mt-1"><a href="${log.full_path}" target="_blank" class="btn btn-sm btn-outline-success py-0" style="font-size: 0.6rem;"><i class="bi bi-download"></i> Download Full Output</a></div>`;
                    }
                    
                    outputHtml += `</div>`;
                    return outputHtml;
                }
            }).join('');
        }
        
        if (isFinal) {
            // Update Actions
            let actionsDiv = messageDiv.querySelector('.message-actions');
            if (!actionsDiv) {
                actionsDiv = document.createElement('div');
                actionsDiv.className = 'message-actions';
                messageDiv.prepend(actionsDiv);
            }
            actionsDiv.innerHTML = ''; // Clear

            const copyBtn = document.createElement('button');
            copyBtn.className = 'copy-btn';
            copyBtn.title = 'Copy to clipboard';
            copyBtn.innerHTML = '<i class="bi bi-clipboard"></i>';
            copyBtn.onclick = (e) => {
                e.stopPropagation();
                navigator.clipboard.writeText(text).then(() => {
                    const icon = copyBtn.querySelector('i');
                    icon.className = 'bi bi-check2';
                    setTimeout(() => { icon.className = 'bi bi-clipboard'; }, 2000);
                });
            };
            actionsDiv.appendChild(copyBtn);

            const forkBtn = document.createElement('button');
            forkBtn.className = 'clone-btn';
            forkBtn.title = 'Fork conversation from this message';
            forkBtn.innerHTML = `<svg width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z"></path></svg>`;
            forkBtn.onclick = (e) => {
                e.stopPropagation();
                const activeSessionItem = document.querySelector('.session-item.active-session');
                if (activeSessionItem) {
                    handleClone(activeSessionItem.dataset.uuid, parseInt(messageDiv.dataset.index));
                }
            };
            actionsDiv.appendChild(forkBtn);

            // Highlight code
            if (typeof hljs !== 'undefined') {
                messageDiv.querySelectorAll('pre code').forEach((block) => {
                    hljs.highlightElement(block);
                });
            }

            // Render Math
            try {
                if (typeof renderMathInElement === 'function') {
                    renderMathInElement(messageDiv, {
                        delimiters: [
                            {left: '$$', right: '$$', display: true},
                            {left: '$', right: '$', display: false},
                            {left: '\\(', right: '\\)', display: false},
                            {left: '\\[', right: '\\]', display: true}
                        ],
                        throwOnError: false
                    });
                }
            } catch (e) {
                console.error('Error rendering math:', e);
            }
        }
        
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function createMessageDiv(sender, text, attachmentInfo = null, file = null, index = null) {
        if (!text && !attachmentInfo) return null;
        if (text && text.trim() === "" && !attachmentInfo) return null;

        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender);
        if (index !== null) messageDiv.dataset.index = index;
        
        let contentHtml = '';

        // Image Preview Logic
        let imageUrl = null;
        if (file && file.type.startsWith('image/')) {
            imageUrl = URL.createObjectURL(file);
        } else if (text && sender === 'user') {
            // Regex to find attachment path: matches both / and \ 
            const match = text.match(/@tmp[\\\/]user_attachments[\\\/]([^\s]+)/);
            if (match) {
                const filename = match[1];
                imageUrl = `/uploads/${filename}`;
            }
        }

        if (imageUrl) {
            contentHtml += `<img src="${imageUrl}" class="message-thumbnail mb-2" style="max-width: 150px; border-radius: 8px; cursor: pointer; display: block;" onclick="window.open('${imageUrl}', '_blank')">`;
        }

        if (attachmentInfo) {
            contentHtml += `<div class="text-muted small mb-1"><i class="bi bi-paperclip"></i> ${attachmentInfo}</div>`;
        }
        
        // Use marked to parse markdown safely
        let parsedText = text;
        try {
            if (typeof marked !== 'undefined') {
                if (typeof marked.parse === 'function') {
                    parsedText = marked.parse(text);
                } else if (typeof marked === 'function') {
                    parsedText = marked(text);
                }
            }
        } catch (e) {
            console.error('Error parsing markdown:', e);
        }
        
        contentHtml += `<div class="message-content">${parsedText}</div>`;

        messageDiv.innerHTML = contentHtml;
        
        // Add Action Buttons
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'message-actions';

        const copyBtn = document.createElement('button');
        copyBtn.className = 'copy-btn';
        copyBtn.title = 'Copy to clipboard';
        copyBtn.innerHTML = '<i class="bi bi-clipboard"></i>';
        copyBtn.onclick = (e) => {
            e.stopPropagation();
            navigator.clipboard.writeText(text).then(() => {
                const icon = copyBtn.querySelector('i');
                icon.className = 'bi bi-check2';
                setTimeout(() => { icon.className = 'bi bi-clipboard'; }, 2000);
            });
        };
        actionsDiv.appendChild(copyBtn);

        if (sender === 'bot' && index !== null) {
            const forkBtn = document.createElement('button');
            forkBtn.className = 'clone-btn';
            forkBtn.title = 'Fork conversation from this message';
            forkBtn.innerHTML = `<svg width="14" height="14" fill="currentColor" viewBox="0 0 16 16"><path d="M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25 2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25 2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z"></path></svg>`;
            forkBtn.onclick = (e) => {
                e.stopPropagation();
                const activeSessionItem = document.querySelector('.session-item.active-session');
                if (activeSessionItem) {
                    handleClone(activeSessionItem.dataset.uuid, parseInt(index));
                }
            };
            actionsDiv.appendChild(forkBtn);
        }

        // User Message Actions: Edit and Fork Navigation
        if (sender === 'user' && index !== null) {
            // Edit Button
            const editBtn = document.createElement('button');
            editBtn.className = 'clone-btn'; // Reuse same style
            editBtn.title = 'Edit and branch conversation';
            editBtn.innerHTML = '<i class="bi bi-pencil"></i>';
            editBtn.onclick = (e) => {
                e.stopPropagation();
                if (confirm('Edit this question and branch the conversation?')) {
                    // 1. Populate input
                    messageInput.value = text;
                    messageInput.focus();
                    messageInput.dispatchEvent(new Event('input'));
                    
                    // 2. Clone at the point before this message
                    const activeSessionItem = document.querySelector('.session-item.active-session');
                    if (activeSessionItem) {
                        const msgIndex = parseInt(index);
                        handleClone(activeSessionItem.dataset.uuid, msgIndex - 1, false); 
                    }
                }
            };
            actionsDiv.appendChild(editBtn);

            // Fork Navigation Arrows (now on the user message that branched)
            const forkPoint = index - 1;
            if (currentForkMap[forkPoint]) {
                const forks = currentForkMap[forkPoint];
                const totalBranches = forks.length + 1;
                
                const navSpan = document.createElement('span');
                navSpan.className = 'fork-nav-controls d-flex align-items-center bg-dark rounded px-1 me-1';
                navSpan.style.fontSize = '0.7rem';
                navSpan.style.border = '1px solid rgba(255,255,255,0.1)';

                const prevBtn = document.createElement('button');
                prevBtn.className = 'btn btn-link btn-sm p-0 text-secondary border-0';
                prevBtn.innerHTML = '<i class="bi bi-chevron-left"></i>';
                
                const nextBtn = document.createElement('button');
                nextBtn.className = 'btn btn-link btn-sm p-0 text-secondary border-0';
                nextBtn.innerHTML = '<i class="bi bi-chevron-right"></i>';

                const branchInfo = document.createElement('span');
                branchInfo.className = 'mx-1 text-muted';
                branchInfo.textContent = `${totalBranches} forks`;

                nextBtn.onclick = (e) => { e.stopPropagation(); switchSession(forks[0]); };
                prevBtn.onclick = (e) => { e.stopPropagation(); switchSession(forks[forks.length - 1]); };

                navSpan.appendChild(prevBtn);
                navSpan.appendChild(branchInfo);
                navSpan.appendChild(nextBtn);
                actionsDiv.appendChild(navSpan);
            }
        }

        messageDiv.prepend(actionsDiv);

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

        // Render Math
        try {
            if (typeof renderMathInElement === 'function') {
                renderMathInElement(messageDiv, {
                    delimiters: [
                        {left: '$$', right: '$$', display: true},
                        {left: '$', right: '$', display: false},
                        {left: '\\(', right: '\\)', display: false},
                        {left: '\\[', right: '\\]', display: true}
                    ],
                    throwOnError: false
                });
            }
        } catch (e) {
            console.error('Error rendering math:', e);
        }
        
        return messageDiv;
    }

    function appendMessage(sender, text, attachmentInfo = null, file = null, index = null) {
        try {
            const messageDiv = createMessageDiv(sender, text, attachmentInfo, file, index);
            if (messageDiv) {
                chatContainer.appendChild(messageDiv);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }
            return messageDiv;
        } catch (e) {
            console.error('Error in appendMessage:', e);
            return null;
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
        return { id, element: messageDiv };
    }

    function removeLoading(id) {
        const element = document.getElementById(id);
        if (element) {
            element.remove();
        }
    }

    // Infinite Scroll Observer
    const scrollSentinel = document.getElementById('scroll-sentinel');
    if (scrollSentinel) {
        const observer = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting && !isLoadingHistory) {
                const activeSessionItem = document.querySelector('.session-item.active-session');
                const hasMore = !loadMoreContainer.classList.contains('d-none');
                
                if (activeSessionItem && hasMore && currentOffset > 0) {
                    loadMessages(activeSessionItem.dataset.uuid, PAGE_LIMIT, currentOffset);
                }
            }
        }, {
            root: chatContainer,
            threshold: 0.1
        });
        observer.observe(scrollSentinel);
    }

    // Swipe Gestures for Mobile
    let touchStartX = 0;
    let touchStartY = 0;
    const swipeThreshold = 50;
    const edgeThreshold = 40;

    document.addEventListener('touchstart', (e) => {
        // Only track if swipe starts near edges
        const x = e.touches[0].clientX;
        if (x < edgeThreshold || x > window.innerWidth - edgeThreshold) {
            touchStartX = x;
            touchStartY = e.touches[0].clientY;
        } else {
            touchStartX = 0; // Reset
        }
    }, { passive: true });

    document.addEventListener('touchend', (e) => {
        if (touchStartX === 0) return;

        const touchEndX = e.changedTouches[0].clientX;
        const touchEndY = e.changedTouches[0].clientY;
        const diffX = touchEndX - touchStartX;
        const diffY = touchEndY - touchStartY;

        // Must be horizontal and meet threshold
        if (Math.abs(diffX) > Math.abs(diffY) * 1.5 && Math.abs(diffX) > swipeThreshold) {
            if (diffX > 0 && touchStartX < edgeThreshold) {
                // Swipe Left-to-Right from left edge: Open History
                const historyEl = document.getElementById('historySidebar');
                const historyOffcanvas = bootstrap.Offcanvas.getInstance(historyEl) || new bootstrap.Offcanvas(historyEl);
                historyOffcanvas.show();
            } else if (diffX < 0 && touchStartX > window.innerWidth - edgeThreshold) {
                // Swipe Right-to-Left from right edge: Open Actions
                const actionsEl = document.getElementById('actionsSidebar');
                const actionsOffcanvas = bootstrap.Offcanvas.getInstance(actionsEl) || new bootstrap.Offcanvas(actionsEl);
                actionsOffcanvas.show();
            }
        }
        touchStartX = 0; // Reset
    }, { passive: true });
});
