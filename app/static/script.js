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

    async function handleExport() {
        const activeSessionItem = document.querySelector('.session-item.active-session');
        if (!activeSessionItem) {
            alert('No active session to export.');
            return;
        }
        const uuid = activeSessionItem.dataset.uuid;
        let title = activeSessionItem.querySelector('.session-title').textContent.trim();
        if (!title) title = "chat_export";

        try {
            const response = await fetch(`/sessions/${uuid}/messages`);
            if (!response.ok) throw new Error('Network response was not ok');
            const messages = await response.json();

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
        if (!chatTagsHeader) return;
        if (!session || !session.uuid) {
            chatTagsHeader.innerHTML = '';
            return;
        }

        const tags = session.tags || [];
        const isMobile = window.innerWidth < 768;
        let visibleTags = tags;
        let hiddenCount = 0;

        if (isMobile && tags.length > 2) {
            visibleTags = tags.slice(0, 2);
            hiddenCount = tags.length - 2;
        }

        let html = visibleTags.map(tag => `<span class="tag-badge selected">${tag}</span>`).join('');
        if (hiddenCount > 0) {
            html += `<span class="tag-badge selected">+${hiddenCount} more</span>`;
        }
        html += `<span class="tag-badge add-tag-btn" title="Edit Tags"><i class="bi bi-plus"></i> Tags</span>`;

        chatTagsHeader.innerHTML = html;

        // Grouping logic: clicking on "+N more" or individual tags on mobile can open the modal
        const allBadges = chatTagsHeader.querySelectorAll('.tag-badge');
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
        window.INITIAL_MESSAGES.forEach(msg => {
            const msgDiv = createMessageDiv(msg.role, msg.content);
            if (msgDiv) chatContainer.appendChild(msgDiv);
        });
        chatContainer.scrollTop = chatContainer.scrollHeight;
        currentOffset = window.INITIAL_MESSAGES.length;
        window.HAS_INITIAL_MESSAGES = true;
    }

    
    async function loadMessages(uuid, limit = PAGE_LIMIT, offset = 0, isAutoRestore = false) {
        if (isLoadingHistory) return;
        if (offset > 0) isLoadingHistory = true;

        try {
            const response = await fetch(`/sessions/${uuid}/messages?limit=${limit}&offset=${offset}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const messages = await response.json();
            
            if (offset === 0) {
                // Clear existing messages only if it's the first page
                chatContainer.innerHTML = '<div id="scroll-sentinel" style="height: 10px; width: 100%;"></div>';
                currentOffset = 0;
                if (chatWelcome) chatWelcome.classList.add('d-none');
            }

            if (messages.length > 0) {
                if (offset === 0) {
                    messages.forEach(msg => {
                        const msgDiv = createMessageDiv(msg.role, msg.content);
                        if (msgDiv) chatContainer.appendChild(msgDiv);
                    });
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                } else {
                    // Prepend for "Load More"
                    // We need to maintain scroll position
                    const scrollHeightBefore = chatContainer.scrollHeight;
                    
                    // Messages are in chronological order for the range.
                    // To maintain chronological order when prepending, we insert each message 
                    // before the original first message of the container.
                    const sentinel = document.getElementById('scroll-sentinel');
                    const loadMore = document.getElementById('load-more-container');
                    const originalFirstMessage = loadMore ? loadMore.nextSibling : (sentinel ? sentinel.nextSibling : chatContainer.firstChild);

                    messages.forEach(msg => {
                        const msgDiv = createMessageDiv(msg.role, msg.content);
                        if (msgDiv) {
                            chatContainer.insertBefore(msgDiv, originalFirstMessage);
                        }
                    });
                    
                    chatContainer.scrollTop = chatContainer.scrollHeight - scrollHeightBefore;
                }
                
                currentOffset += messages.length;
                
                // Show/Hide Load More (Still useful for fallback/logic)
                if (messages.length === limit) {
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
            <div class="list-group-item list-group-item-action bg-dark text-light session-item ${s.active ? 'active-session' : ''}" data-uuid="${s.uuid}">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1 overflow-hidden">
                        <span class="session-title text-truncate">${s.title || 'Untitled Chat'}</span>
                        <div class="session-tags-list">
                            ${(s.tags || []).map(t => `<span class="session-tag-item">${t}</span>`).join('')}
                        </div>
                        <span class="session-time">${s.time || ''}</span>
                    </div>
                    <div class="d-flex align-items-center gap-1">
                        ${s.active ? '<span class="badge bg-primary rounded-pill small me-1">Active</span>' : ''}
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

    function attachSessionListeners() {
        document.querySelectorAll('.session-item').forEach(item => {
            item.onclick = async (e) => {
                if (e.target.closest('button')) return;

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
                
                const newTitle = prompt('Enter new chat title:', oldTitle);
                if (newTitle && newTitle !== oldTitle) {
                    renameSession(uuid, newTitle, titleSpan);
                }
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
            
            // Auto-switch to Gemini 3 Flash Preview for better vision support
            const flashModel = "gemini-3-flash-preview";
            modelInput.value = flashModel;
            
            // Update UI label and active state
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
    });

    clearFileBtn.addEventListener('click', () => {
        fileUpload.value = '';
        currentFile = null;
        filePreviewArea.classList.add('d-none');
    });

        // Send Message

        chatForm.addEventListener('submit', async (e) => {

    
        e.preventDefault();
        const message = messageInput.value.trim();
        if (!message && !currentFile) return;

        // Add user message to chat
        appendMessage('user', message, currentFile ? `[Attachment: ${currentFile.name}]` : null, currentFile);
        
        // Clear inputs immediately
        messageInput.value = '';
        messageInput.style.height = '';
        fileUpload.value = '';
        filePreviewArea.classList.add('d-none');
        const fileToSend = currentFile; // Keep ref for sending
        currentFile = null;

        // Show loading state
        const loadingId = appendLoading();
        toggleStopButton(true);

        try {
            const formData = new FormData();
            formData.append('message', message);
            if (fileToSend) {
                let finalFile = fileToSend;
                // Compress if it's an image
                if (fileToSend.type.startsWith('image/') && typeof compressImage === 'function') {
                    try {
                        finalFile = await compressImage(fileToSend);
                    } catch (compressError) {
                        console.error('Compression failed, sending original:', compressError);
                    }
                }
                formData.append('file', finalFile);
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
                                messageDiv = createStreamingMessage('bot');
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

    function createStreamingMessage(sender) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender);
        
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
            messageDiv.prepend(copyBtn);
            
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

    function createMessageDiv(sender, text, attachmentInfo = null, file = null) {
        if (!text && !attachmentInfo) return null;
        if (text && text.trim() === "" && !attachmentInfo) return null;

        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', sender);
        
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
        messageDiv.prepend(copyBtn);

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

    function appendMessage(sender, text, attachmentInfo = null, file = null) {
        try {
            const messageDiv = createMessageDiv(sender, text, attachmentInfo, file);
            chatContainer.appendChild(messageDiv);
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
    // Swipe Gestures for Mobile
    let touchStartX = 0;
    let touchStartY = 0;
    const swipeThreshold = 50;
    const edgeThreshold = 30;

    document.addEventListener('touchstart', (e) => {
        touchStartX = e.touches[0].clientX;
        touchStartY = e.touches[0].clientY;
    }, { passive: true });

    document.addEventListener('touchend', (e) => {
        const touchEndX = e.changedTouches[0].clientX;
        const touchEndY = e.changedTouches[0].clientY;
        const diffX = touchEndX - touchStartX;
        const diffY = touchEndY - touchStartY;

        // Ensure horizontal swipe
        if (Math.abs(diffX) > Math.abs(diffY) && Math.abs(diffX) > swipeThreshold) {
            if (diffX > 0 && touchStartX < edgeThreshold) {
                // Swipe Left-to-Right from left edge: Open History
                const historyOffcanvas = bootstrap.Offcanvas.getInstance(document.getElementById('historySidebar')) || new bootstrap.Offcanvas(document.getElementById('historySidebar'));
                historyOffcanvas.show();
            } else if (diffX < 0 && touchStartX > window.innerWidth - edgeThreshold) {
                // Swipe Right-to-Left from right edge: Open Actions
                const actionsOffcanvas = bootstrap.Offcanvas.getInstance(document.getElementById('actionsSidebar')) || new bootstrap.Offcanvas(document.getElementById('actionsSidebar'));
                actionsOffcanvas.show();
            }
        }
    }, { passive: true });
});
