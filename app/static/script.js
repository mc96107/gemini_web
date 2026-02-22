document.addEventListener('DOMContentLoaded', () => {
    // --- Global State ---
    let currentActiveUUID = window.ACTIVE_SESSION_UUID || null;
    let currentOffset = 0;
    let sidebarOffset = 0;
    const PAGE_LIMIT = 20;
    const SIDEBAR_PAGE_LIMIT = 15;
    let isLoadingHistory = false;
    let isLoadingSidebar = false;
    let planModeActive = false;
    let activeTags = new Set();
    let allUniqueTags = [];
    let currentForkMap = {}; // index -> [uuids]
    let allPatterns = [];
    let sessionGeneration = 0; // Bug 9: generation counter to prevent init race

    // --- DOM Elements ---
    const chatForm = document.getElementById('chat-form');
    const messageInput = document.getElementById('message-input');
    const chatContainer = document.getElementById('chat-container');
    const sendBtn = document.getElementById('send-btn');
    const stopBtn = document.getElementById('stop-btn');
    const chatWelcome = document.getElementById('chat-welcome');
    
    const modelInput = document.getElementById('model-input');
    const modelLabel = document.getElementById('model-label');
    const modelLinks = document.querySelectorAll('[data-model]');
    
    const workspaceInput = document.getElementById('session-workspace-input');
    const updateWorkspaceBtn = document.getElementById('btn-update-workspace');
    const workspaceStatus = document.getElementById('workspace-status');
    const workspaceSuggestions = document.getElementById('workspace-suggestions');
    const defaultWorkspaceSetting = document.getElementById('setting-default-workspace');
    const defaultModelSetting = document.getElementById('setting-default-model');

    const historySidebar = document.getElementById('historySidebar');
    const sessionSearch = document.getElementById('session-search');
    const newChatBtn = document.getElementById('new-chat-btn');
    
    const patternsModalEl = document.getElementById('patternsModal');
    const patternsList = document.getElementById('patterns-list');
    
    const planModeBtn = document.getElementById('plan-mode-btn');
    const driveModeBtn = document.getElementById('drive-mode-btn');

    const treeViewModalEl = document.getElementById('treeViewModal');
    const treeContainer = document.getElementById('tree-container');

    const exportBtn = document.getElementById('export-btn');
    const exportBtnMobile = document.getElementById('export-btn-mobile');
    const resetBtn = document.getElementById('reset-btn');
    const resetBtnMobile = document.getElementById('reset-btn-mobile');

    const renameModalEl = document.getElementById('renameSessionModal');
    const renameInput = document.getElementById('rename-input');
    const btnSaveRename = document.getElementById('btn-save-rename');
    let currentRenameUUID = null;

    const taggingModalEl = document.getElementById('taggingModal');
    const modalCurrentTags = document.getElementById('modal-current-tags');
    const modalExistingTags = document.getElementById('modal-existing-tags');
    const tagInput = document.getElementById('tag-input');
    const btnAddTag = document.getElementById('btn-add-tag');
    const btnSaveTags = document.getElementById('btn-save-tags');

    const editPromptModalEl = document.getElementById('editPromptModal');
    const btnSavePrompt = document.getElementById('btn-save-prompt');

    const sidebarLoadMoreBtn = document.getElementById('sidebar-load-more-btn');
    // Bug 7: Wire sidebar "Load More" button
    if (sidebarLoadMoreBtn) {
        sidebarLoadMoreBtn.onclick = () => {
            sidebarOffset += SIDEBAR_PAGE_LIMIT;
            loadSessions(true);
        };
    }

    // Bug 8: Wire session search input with debounce
    if (sessionSearch) {
        let searchTimer;
        sessionSearch.oninput = () => {
            clearTimeout(searchTimer);
            searchTimer = setTimeout(() => loadSessions(), 300);
        };
    }

    // --- Managers ---
    const driveMode = (typeof DriveModeManager !== 'undefined') ? new DriveModeManager() : { isSupported: () => false };
    const attachments = (typeof AttachmentManager !== 'undefined') ? new AttachmentManager({
        maxTotalSize: 20 * 1024 * 1024,
        onQueueChange: (items) => renderAttachmentQueue(items),
        onSizeLimitExceeded: (name) => showToast(`Size limit exceeded: ${name}`)
    }) : { getFiles: () => [], clear: () => {} };

    // --- UI Helpers ---
    function showToast(message) {
        const toastEl = document.getElementById('liveToast');
        const toastBody = document.getElementById('toast-body');
        if (toastEl && toastBody) {
            toastBody.textContent = message;
            const toast = new bootstrap.Toast(toastEl);
            toast.show();
        }
    }

    function toggleStopButton(show) {
        if (!sendBtn || !stopBtn) return;
        if (show) {
            sendBtn.classList.add('d-none');
            stopBtn.classList.remove('d-none');
        } else {
            sendBtn.classList.remove('d-none');
            stopBtn.classList.add('d-none');
        }
    }

    function updateActiveModelUI(model) {
        if (!modelInput) return;
        modelInput.value = model;
        let found = false;
        modelLinks.forEach(link => {
            if (link.dataset.model === model) {
                link.classList.add('active');
                let modelName = link.innerText;
                modelName = modelName.replace('Stable (v0.28+)', '').replace('Preview', '').trim();
                if (modelLabel) modelLabel.textContent = modelName;
                found = true;
            } else link.classList.remove('active');
        });
        if (!found && modelLabel) {
            modelLabel.textContent = model.split('/').pop().replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        }
    }

    // --- Workspace Management ---
    async function loadWorkspaces() {
        try {
            const res = await fetch('/workspaces');
            const data = await res.json();
            if (data.workspaces && workspaceSuggestions) {
                workspaceSuggestions.innerHTML = data.workspaces.map(w => `<option value="${w}">`).join('');
                window.WORKSPACE_ROOT = data.root;
            }
        } catch (err) { console.error('loadWorkspaces error:', err); }
    }

    async function loadSessionWorkspace(uuid) {
        if (!workspaceInput || !uuid) return;
        try {
            const res = await fetch(`/session/workspace/${uuid}`);
            const data = await res.json();
            if (data.path) workspaceInput.value = data.path;
        } catch (err) { console.error('loadSessionWorkspace error:', err); }
    }

    if (updateWorkspaceBtn && workspaceInput) {
        updateWorkspaceBtn.onclick = async () => {
            const uuid = currentActiveUUID || 'pending';
            const path = workspaceInput.value.trim();
            if (!path) { showToast('Enter a workspace path'); return; }
            workspaceStatus.textContent = 'Updating...';
            try {
                const res = await fetch('/session/workspace', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ uuid, path })
                });
                const data = await res.json();
                if (data.success) {
                    workspaceStatus.textContent = 'Workspace updated!';
                    workspaceStatus.className = 'mt-2 small text-center text-success';
                    setTimeout(() => { workspaceStatus.textContent = ''; }, 2000);
                    loadPatterns();
                } else {
                    workspaceStatus.textContent = 'Error: Path must be within root';
                    workspaceStatus.className = 'mt-2 small text-center text-danger';
                }
            } catch (err) { workspaceStatus.textContent = 'Network error'; }
        };
    }

    // --- Settings ---
    if (defaultModelSetting && window.USER_SETTINGS) {
        defaultModelSetting.value = window.USER_SETTINGS.default_model || '';
        defaultModelSetting.onchange = async () => {
            const model = defaultModelSetting.value;
            const res = await fetch('/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ default_model: model }) });
            if (res.ok) { window.USER_SETTINGS.default_model = model; if (!currentActiveUUID) updateActiveModelUI(model); showToast('Default model updated'); }
        };
    }

    if (defaultWorkspaceSetting && window.USER_SETTINGS) {
        defaultWorkspaceSetting.value = window.USER_SETTINGS.default_workspace || '';
        defaultWorkspaceSetting.onchange = async () => {
            const workspace = defaultWorkspaceSetting.value.trim();
            if (!workspace) return;
            const res = await fetch('/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ default_workspace: workspace }) });
            if (res.ok) { window.USER_SETTINGS.default_workspace = workspace; showToast('Default workspace updated'); loadWorkspaces(); }
        };
    }

    const showMicSetting = document.getElementById('setting-show-mic');
    if (showMicSetting && window.USER_SETTINGS) {
        showMicSetting.checked = window.USER_SETTINGS.show_mic !== false;
        showMicSetting.onchange = async () => {
            const enabled = showMicSetting.checked;
            const res = await fetch('/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ show_mic: enabled }) });
            if (res.ok) { window.USER_SETTINGS.show_mic = enabled; updateDriveModeVisibility(); }
        };
    }

    const showPlanSetting = document.getElementById('setting-show-plan');
    if (showPlanSetting && window.USER_SETTINGS) {
        showPlanSetting.checked = window.USER_SETTINGS.show_plan === true;
        showPlanSetting.onchange = async () => {
            const enabled = showPlanSetting.checked;
            const res = await fetch('/settings', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ show_plan: enabled }) });
            if (res.ok) { window.USER_SETTINGS.show_plan = enabled; updatePlanModeVisibility(); }
        };
    }

    function updateDriveModeVisibility() {
        if (!driveModeBtn) return;
        const isEnabled = window.USER_SETTINGS && window.USER_SETTINGS.show_mic !== false;
        if (driveMode.isSupported && driveMode.isSupported() && isEnabled) driveModeBtn.classList.remove('d-none');
        else driveModeBtn.classList.add('d-none');
    }

    function updatePlanModeVisibility() {
        if (!planModeBtn) return;
        planModeBtn.classList.remove('d-none');
    }

    // --- Session History ---
    async function loadSessions(append = false) {
        if (isLoadingSidebar) return;
        if (!append) sidebarOffset = 0;
        isLoadingSidebar = true;
        let query = sessionSearch ? sessionSearch.value.trim() : "";
        let url = `/sessions?limit=${SIDEBAR_PAGE_LIMIT}&offset=${sidebarOffset}`;
        if (activeTags.size > 0) url += `&tags=${encodeURIComponent(Array.from(activeTags).join(','))}`;
        if (query) url = `/sessions/search?q=${encodeURIComponent(query)}`;
        try {
            const res = await fetch(url);
            const data = await res.json();
            renderSessions(data, append);
            const sessions = Array.isArray(data) ? data : (data.history || []);
            const activeSession = sessions.find(s => s.active || s.uuid === currentActiveUUID);
            if (activeSession && activeSession.model) updateActiveModelUI(activeSession.model);
            if (sidebarLoadMoreBtn) {
                 const total = data.total_unpinned || 0;
                 sidebarLoadMoreBtn.parentElement.classList.toggle('d-none', Array.isArray(data) || (sidebarOffset + sessions.length >= total));
            }
        } catch (e) { console.error('loadSessions error:', e); } 
        finally { isLoadingSidebar = false; }
    }

    function renderSessions(data, append = false) {
        const pinnedList = document.getElementById('pinned-sessions-list');
        const historyList = document.getElementById('history-sessions-list');
        const pinnedHeader = document.getElementById('pinned-sessions-header');
        let pinned = data.pinned || [];
        let history = Array.isArray(data) ? data : (data.history || []);
        const createHTML = (s) => `
            <div class="list-group-item list-group-item-action bg-dark text-light session-item ${(s.active || s.uuid === currentActiveUUID) ? 'active-session' : ''}" data-uuid="${s.uuid}">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1 overflow-hidden">
                        <span class="session-title text-truncate d-block">${s.title || 'Untitled Chat'}</span>
                        <div class="session-tags-list">${(s.tags || []).map(t => `<span class="session-tag-item">${t}</span>`).join('')}</div>
                        <span class="session-time text-muted small">${s.time || ''}</span>
                    </div>
                    <div class="d-flex align-items-center gap-1">
                        <button class="btn btn-sm pin-btn border-0 ${s.pinned ? 'text-warning' : 'text-muted'}" data-uuid="${s.uuid}"><i class="bi ${s.pinned ? 'bi-pin-fill' : 'bi-pin'}"></i></button>
                        <button class="btn btn-sm tag-btn border-0 text-warning" data-uuid="${s.uuid}"><i class="bi bi-tags"></i></button>
                        <button class="btn btn-sm rename-session-btn border-0 text-info" data-uuid="${s.uuid}"><i class="bi bi-pencil"></i></button>
                        <button class="btn btn-sm btn-outline-danger border-0 delete-session-btn" data-uuid="${s.uuid}"><i class="bi bi-trash"></i></button>
                    </div>
                </div>
            </div>`;
        if (!append) {
            if (pinnedList) pinnedList.innerHTML = pinned.map(createHTML).join('');
            if (historyList) historyList.innerHTML = history.map(createHTML).join('');
            if (pinnedHeader) pinnedHeader.classList.toggle('d-none', pinned.length === 0);
        } else if (historyList) historyList.insertAdjacentHTML('beforeend', history.map(createHTML).join(''));
        attachSessionListeners();
    }

    function attachSessionListeners() {
        document.querySelectorAll('.session-item').forEach(item => { item.onclick = (e) => { if (!e.target.closest('button')) switchSession(item.dataset.uuid); }; });
        document.querySelectorAll('.pin-btn').forEach(btn => { btn.onclick = async (e) => { e.stopPropagation(); await fetch(`/sessions/${btn.dataset.uuid}/pin`, { method: 'POST' }); loadSessions(); }; });
        document.querySelectorAll('.tag-btn').forEach(btn => { btn.onclick = (e) => { e.stopPropagation(); openTaggingModal(btn.dataset.uuid); }; });
        document.querySelectorAll('.rename-session-btn').forEach(btn => {
            btn.onclick = (e) => {
                e.stopPropagation();
                currentRenameUUID = btn.dataset.uuid;
                renameInput.value = btn.closest('.session-item').querySelector('.session-title').textContent;
                new bootstrap.Modal(renameModalEl).show();
            };
        });
        document.querySelectorAll('.delete-session-btn').forEach(btn => {
            btn.onclick = async (e) => {
                e.stopPropagation();
                if (confirm('Delete this chat?')) { await fetch('/sessions/delete', { method: 'POST', body: new URLSearchParams({ session_uuid: btn.dataset.uuid }) }); if (btn.dataset.uuid === currentActiveUUID) window.location.reload(); else loadSessions(); }
            };
        });
    }

    if (btnSaveRename) {
        btnSaveRename.onclick = async () => {
            const title = renameInput.value.trim();
            if (!title || !currentRenameUUID) return;
            const res = await fetch(`/sessions/${currentRenameUUID}/title`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title }) });
            if (res.ok) { bootstrap.Modal.getInstance(renameModalEl).hide(); loadSessions(); }
        };
    }

    async function handleNewChat() {
        try {
            sessionGeneration++;
            const res = await fetch('/sessions/new', { method: 'POST' });
            if (res.ok) {
                currentActiveUUID = null;
                window.ACTIVE_SESSION_UUID = null;
                window.INITIAL_MESSAGES = [];
                chatContainer.innerHTML = '';
                if (chatWelcome) chatWelcome.classList.remove('d-none');
                currentOffset = 0;
                window.TOTAL_MESSAGES = 0;
                if (window.USER_SETTINGS && window.USER_SETTINGS.default_model) updateActiveModelUI(window.USER_SETTINGS.default_model);
                if (window.USER_SETTINGS && window.USER_SETTINGS.default_workspace) if (workspaceInput) workspaceInput.value = window.USER_SETTINGS.default_workspace;
                const sidebar = document.getElementById('historySidebar');
                if (sidebar) bootstrap.Offcanvas.getInstance(sidebar)?.hide();
                showToast('New session started');
                loadSessions();
                loadPatterns();
            }
        } catch (e) { console.error('Error starting new chat:', e); }
    }
    if (newChatBtn) newChatBtn.onclick = handleNewChat;

    async function switchSession(uuid) {
        if (uuid === currentActiveUUID) { 
            const sidebar = document.getElementById('historySidebar');
            if (sidebar) bootstrap.Offcanvas.getInstance(sidebar)?.hide(); 
            return; 
        }
        sessionGeneration++;
        chatContainer.innerHTML = '<div class="text-center text-muted mt-5"><p>Loading conversation...</p></div>';
        try {
            const res = await fetch('/sessions/switch', { method: 'POST', body: new URLSearchParams({ session_uuid: uuid }) });
            const data = await res.json();
            if (data.success) {
                currentActiveUUID = uuid;
                await loadMessages(uuid);
                const sidebar = document.getElementById('historySidebar');
                if (sidebar) bootstrap.Offcanvas.getInstance(sidebar)?.hide();
                loadSessions();
                loadSessionWorkspace(uuid);
                loadPatterns();
            }
        } catch (e) {
            console.error('switchSession error:', e);
            chatContainer.innerHTML = '<div class="text-center text-danger mt-5"><p>Failed to load conversation. Please try again.</p></div>';
        }
    }

    async function loadMessages(uuid, limit = PAGE_LIMIT, offset = 0) {
        if (isLoadingHistory) return;
        isLoadingHistory = true;
        if (offset === 0) { 
            currentActiveUUID = uuid; 
            chatContainer.innerHTML = '<div id="scroll-sentinel" style="height: 10px; width: 100%;"></div>'; 
            currentOffset = 0; 
            if (chatWelcome) chatWelcome.classList.add('d-none'); 
            // Re-observe the new sentinel element
            const newSentinel = document.getElementById('scroll-sentinel');
            if (newSentinel) observer.observe(newSentinel);
            await fetchForks(uuid); 
        }

        try {
            const res = await fetch(`/sessions/${uuid}/messages?limit=${limit}&offset=${offset}`);
            // Stale session guard: abort if user switched away during fetch
            if (uuid !== currentActiveUUID) return;
            const data = await res.json();
            const messages = data.messages || [];
            window.TOTAL_MESSAGES = data.total || 0;
            if (messages.length === 0 && offset === 0) {
                chatContainer.innerHTML = '<div class="text-center text-muted mt-5"><p>No messages found or failed to load chat.</p></div>';
            } else {
                if (chatContainer.querySelector('.text-muted') && chatContainer.querySelector('.text-muted').innerText.includes('No messages found')) {
                    chatContainer.innerHTML = '<div id="scroll-sentinel" style="height: 10px; width: 100%;"></div>';
                    if (observer && document.getElementById('scroll-sentinel')) observer.observe(document.getElementById('scroll-sentinel'));
                }
            }
            messages.forEach((msg, idx) => {
                const index = (msg.raw_index !== undefined) ? msg.raw_index : (window.TOTAL_MESSAGES - offset - messages.length + idx);
                const div = createMessageDiv(msg.role, msg.content, null, null, index);
                if (div) { 
                    if (offset === 0) chatContainer.appendChild(div); 
                    else chatContainer.insertBefore(div, document.getElementById('scroll-sentinel').nextSibling); 
                }
            });
            if (offset === 0) chatContainer.scrollTop = chatContainer.scrollHeight;
            currentOffset = offset + messages.length;
        } catch (e) { console.error('loadMessages error:', e); } 
        finally { isLoadingHistory = false; }
    }

    async function openTaggingModal(uuid) {
        const modal = new bootstrap.Modal(taggingModalEl);
        try {
            const res = await fetch(`/sessions/${uuid}/tags`);
            const data = await res.json();
            let workingTags = data.tags || [];
            const render = () => {
                modalCurrentTags.innerHTML = workingTags.map(t => `<span class="badge bg-primary me-1">${t} <i class="bi bi-x-circle cursor-pointer" onclick="window.removeTagFromWorking('${t}')"></i></span>`).join('');
                modalExistingTags.innerHTML = allUniqueTags.filter(t => !workingTags.includes(t)).map(t => `<span class="badge bg-secondary me-1 cursor-pointer" onclick="window.addTagToWorking('${t}')">${t}</span>`).join('');
            };
            window.removeTagFromWorking = (tag) => { workingTags = workingTags.filter(t => t !== tag); render(); };
            window.addTagToWorking = (tag) => { if (!workingTags.includes(tag)) workingTags.push(tag); render(); };
            btnAddTag.onclick = () => { const val = tagInput.value.trim(); if (val && !workingTags.includes(val)) { workingTags.push(val); tagInput.value = ''; render(); } };
            btnSaveTags.onclick = async () => { const res = await fetch(`/sessions/${uuid}/tags`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ tags: workingTags }) }); if (res.ok) { modal.hide(); loadSessions(); fetchUniqueTags(); } };
            render(); modal.show();
        } catch (e) { console.error('openTaggingModal error:', e); }
    }

    async function fetchUniqueTags() {
        try {
            const res = await fetch('/sessions/tags');
            const data = await res.json();
            allUniqueTags = data.tags || [];
            const container = document.getElementById('tag-filter-container');
            if (container) container.innerHTML = allUniqueTags.map(t => `<span class="badge ${activeTags.has(t) ? 'bg-primary' : 'bg-dark border border-secondary'} cursor-pointer me-1 mb-1" onclick="window.toggleTagFilter('${t}')">${t}</span>`).join('');
        } catch (e) {}
    }

    window.toggleTagFilter = (tag) => { if (activeTags.has(tag)) activeTags.delete(tag); else activeTags.add(tag); fetchUniqueTags(); loadSessions(); };

    // --- Chat Flow ---
    if (chatForm) {
        chatForm.onsubmit = async (e) => {
            e.preventDefault();
            const msg = messageInput.value.trim();
            const files = attachments.getFiles ? attachments.getFiles() : [];
            if (!msg && files.length === 0) return;
            
            const index = window.TOTAL_MESSAGES || 0;
            appendMessage('user', msg, null, files[0], index);
            window.TOTAL_MESSAGES = index + 1;
            
            messageInput.value = ''; messageInput.style.height = '';
            const filesToSend = [...files]; if (attachments.clear) attachments.clear();
            const loadingId = appendLoading(); toggleStopButton(true);
            
            try {
                const fd = new FormData();
                fd.append('message', msg); 
                fd.append('model', modelInput.value);
                if (planModeActive) fd.append('plan_mode', 'true');
                filesToSend.forEach(f => fd.append('file', f));
                const res = await fetch('/chat', { method: 'POST', body: fd });
                await processStream(res, loadingId);
            } catch (error) { 
                removeLoading(loadingId); 
                appendMessage('bot', `Error: ${error.message}`); 
            } finally { 
                toggleStopButton(false); 
                loadSessions(); 
            }
        };
    }

    async function processStream(response, loadingId) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let messageDiv = null, fullText = "", toolLogs = [], buffer = "";
        const streamGeneration = sessionGeneration;
        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop();
                for (const line of lines) {
                    if (!line.startsWith('data: ')) continue;
                    const dataStr = line.substring(6).trim();
                    if (dataStr === '[DONE]') continue;
                    try {
                        const data = JSON.parse(dataStr);
                        if (data.type === 'message') fullText += data.content;
                        else if (data.type === 'init') {
                            if (streamGeneration === sessionGeneration) {
                                currentActiveUUID = data.session_id;
                                window.ACTIVE_SESSION_UUID = data.session_id;
                            }
                        }
                        else if (data.type === 'plan_status') {
                            if (data.status === 'active') {
                                const loadingEl = document.getElementById(loadingId);
                                if (loadingEl) loadingEl.innerHTML = `<div class="spinner-border spinner-border-sm"></div> ${data.message || 'Thinking...'}`;
                            } else if (data.status === 'completed') {
                                if (!fullText.trim() && !toolLogs.length) removeLoading(loadingId);
                            }
                        }
                        else if (data.type === 'raw') {
                            fullText += data.content + '\n';
                        }
                        else if (data.type === 'question') { 
                            const card = createQuestionCard(data); 
                            chatContainer.appendChild(card); 
                            chatContainer.scrollTop = chatContainer.scrollHeight; 
                            if (!fullText.trim() && !toolLogs.length) removeLoading(loadingId);
                        }
                        else if (data.type === 'tool_use') toolLogs.push({ type: 'call', name: data.tool_name, input: data.parameters });
                        else if (data.type === 'tool_result') toolLogs.push({ type: 'output', output: data.output, full_path: data.full_output_path });
                        else if (data.type === 'error') fullText += `\n\n[Error: ${data.content}]`;
                        else if (data.type === 'model_switch') { updateActiveModelUI(data.new_model); showToast(`Switching to ${data.new_model}...`); }

                        if (!messageDiv && (fullText.trim() || toolLogs.length)) { 
                            messageDiv = createStreamingMessage('bot', window.TOTAL_MESSAGES++); 
                            removeLoading(loadingId); 
                        }
                        if (messageDiv) updateStreamingMessage(messageDiv, fullText, toolLogs);
                    } catch (e) {}
                }
            }
            if (messageDiv) {
                updateStreamingMessage(messageDiv, fullText, toolLogs, true);
            } else {
                removeLoading(loadingId);
                if (!fullText.trim() && toolLogs.length === 0) {
                    appendMessage('bot', '[System Error] The agent exited without responding. Check backend logs or try again.');
                }
            }
        } catch (e) { console.error('processStream error:', e); }
    }

    function createMessageDiv(sender, text, info, file, index) {
        const div = document.createElement('div'); div.className = `message ${sender}`;
        if (index !== null) div.dataset.index = index;
        let parsedText = text;
        if (sender === 'bot') parsedText = parsedText.replace(/\[Thinking\]([\s\S]*?)\[\/Thinking\]/g, (m, c) => `<div class="thinking-block">${c.trim()}</div>`);
        const content = document.createElement('div'); content.className = 'message-content';
        content.innerHTML = (typeof marked !== 'undefined') ? marked.parse(parsedText) : parsedText;
        div.appendChild(content);
        const actions = document.createElement('div'); actions.className = 'message-actions';
        const copyBtn = document.createElement('button'); copyBtn.className = 'copy-btn'; copyBtn.innerHTML = '<i class="bi bi-clipboard"></i>';
        copyBtn.onclick = () => {
            if (navigator.clipboard) {
                navigator.clipboard.writeText(text).then(() => showToast('Copied!'));
            } else {
                const ta = document.createElement('textarea');
                ta.value = text; document.body.appendChild(ta); ta.select();
                document.execCommand('copy'); document.body.removeChild(ta);
                showToast('Copied!');
            }
        };
        actions.appendChild(copyBtn);
        if (index !== null) {
            const forkBtn = document.createElement('button'); forkBtn.className = 'clone-btn'; forkBtn.innerHTML = '<i class="bi bi-pencil-square"></i>';
            forkBtn.onclick = () => { 
                if (sender === 'user') { messageInput.value = text; messageInput.focus(); handleClone(currentActiveUUID, parseInt(index) - 1, false); } 
                else handleClone(currentActiveUUID, parseInt(index)); 
            };
            actions.appendChild(forkBtn);
        }
        div.prepend(actions); return div;
    }

    function createStreamingMessage(sender, index) {
        const div = document.createElement('div'); div.className = `message ${sender} streaming`; div.dataset.index = index;
        div.innerHTML = '<div class="message-content"></div><div class="tool-logs mt-2 d-none"></div>';
        chatContainer.appendChild(div); chatContainer.scrollTop = chatContainer.scrollHeight; return div;
    }

    function updateStreamingMessage(div, text, logs, isFinal = false) {
        const content = div.querySelector('.message-content');
        let parsedText = text.replace(/\[Thinking\]([\s\S]*?)\[\/Thinking\]/g, (m, c) => `<div class="thinking-block">${c.trim()}</div>`);
        content.innerHTML = (typeof marked !== 'undefined') ? marked.parse(parsedText) : parsedText;
        const logsDiv = div.querySelector('.tool-logs');
        if (logs.length) {
            logsDiv.classList.remove('d-none');
            logsDiv.innerHTML = logs.map(l => {
                if (l.type === 'call') return `<div class="small text-info border-start border-info ps-2 mb-1"><strong>Tool Call:</strong> ${l.name}</div>`;
                return `<div class="small text-success border-start border-success ps-2 mb-2"><strong>Result:</strong><pre class="m-0" style="font-size: 0.7rem; max-height: 100px; overflow: auto;">${(l.output || '').substring(0, 500)}</pre>${l.full_path ? `<a href="${l.full_path}" target="_blank" class="small text-success">Download Full Output</a>` : ''}</div>`;
            }).join('');
        }
        if (isFinal) {
            div.classList.remove('streaming');
            div.querySelectorAll('pre code').forEach(b => typeof hljs !== 'undefined' && hljs.highlightElement(b));
            const actions = div.querySelector('.message-actions') || document.createElement('div');
            actions.className = 'message-actions'; actions.innerHTML = '';
            const copyBtn = document.createElement('button'); copyBtn.className = 'copy-btn'; copyBtn.innerHTML = '<i class="bi bi-clipboard"></i>';
            copyBtn.onclick = () => navigator.clipboard.writeText(text).then(() => showToast('Copied!'));
            actions.appendChild(copyBtn);
            const forkBtn = document.createElement('button'); forkBtn.className = 'clone-btn'; forkBtn.innerHTML = '<i class="bi bi-pencil-square"></i>';
            forkBtn.onclick = () => handleClone(currentActiveUUID, parseInt(div.dataset.index));
            actions.appendChild(forkBtn);
            if (!div.querySelector('.message-actions')) div.prepend(actions);
        }
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function createQuestionCard(data) {
        const card = document.createElement('div'); card.className = 'question-card';
        const qText = document.createElement('div'); qText.className = 'question-text'; qText.innerText = data.question; card.appendChild(qText);
        const optContainer = document.createElement('div'); optContainer.className = 'options-container';
        const dismiss = () => { card.classList.add('removing'); setTimeout(() => card.remove(), 200); };
        if (!data.options || data.options.length === 0) {
            const input = document.createElement('input'); input.type = 'text'; input.className = 'form-control bg-dark text-light mb-2'; input.placeholder = 'Type answer...'; card.appendChild(input);
            const btn = document.createElement('button'); btn.className = 'btn btn-primary btn-sm w-100'; btn.innerText = 'Submit';
            btn.onclick = () => { if (input.value.trim()) { messageInput.value = input.value.trim(); if (chatForm) chatForm.dispatchEvent(new Event('submit')); dismiss(); } };
            card.appendChild(input); card.appendChild(btn);
        } else {
            const selected = new Set();
            data.options.forEach(opt => {
                const btn = document.createElement('button'); btn.className = 'option-btn'; btn.innerText = opt;
                btn.onclick = () => {
                    if (data.allow_multiple) { if (selected.has(opt)) { selected.delete(opt); btn.classList.remove('active'); } else { selected.add(opt); btn.classList.add('active'); } }
                    else { messageInput.value = opt; if (chatForm) chatForm.dispatchEvent(new Event('submit')); dismiss(); }
                };
                optContainer.appendChild(btn);
            });
            card.appendChild(optContainer);
            if (data.allow_multiple) {
                const btn = document.createElement('button'); btn.className = 'btn btn-primary btn-sm mt-2 w-100'; btn.innerText = 'Submit';
                btn.onclick = () => { if (selected.size) { messageInput.value = Array.from(selected).join(', '); if (chatForm) chatForm.dispatchEvent(new Event('submit')); dismiss(); } };
                card.appendChild(btn);
            }
        }
        return card;
    }

    function appendMessage(sender, text, info, file, index) { const div = createMessageDiv(sender, text, info, file, index); if (div) { chatContainer.appendChild(div); chatContainer.scrollTop = chatContainer.scrollHeight; } }
    function appendLoading() { const div = document.createElement('div'); div.className = 'message bot loading'; const id = 'loading-' + Date.now(); div.id = id; div.innerHTML = '<div class="spinner-border spinner-border-sm"></div> Thinking...'; chatContainer.appendChild(div); chatContainer.scrollTop = chatContainer.scrollHeight; return id; }
    function removeLoading(id) { const el = document.getElementById(id); if (el) el.remove(); }

    async function handleClone(uuid, messageIndex, showAlert = true) {
        try {
            const res = await fetch(`/sessions/${uuid}/clone`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message_index: messageIndex }) });
            const data = await res.json();
            if (data.success) { if (showAlert) showToast('Conversation forked!'); if (data.new_uuid === "pending") { chatContainer.innerHTML = ''; loadSessions(); } else switchSession(data.new_uuid); }
        } catch (e) { console.error('handleClone error:', e); }
    }

    async function handleReset() { if (confirm('Reset chat?')) { const res = await fetch('/reset', { method: 'POST' }); const data = await res.json(); chatContainer.innerHTML = `<div class="text-center text-muted mt-5">${data.response}</div>`; currentActiveUUID = null; loadSessions(); } }
    if (resetBtn) resetBtn.onclick = handleReset;
    if (resetBtnMobile) resetBtnMobile.onclick = handleReset;

    async function handleExport() {
        if (!currentActiveUUID) return;
        try {
            const res = await fetch(`/sessions/${currentActiveUUID}/messages`);
            const data = await res.json();
            const messages = data.messages || [];
            let md = "# Export\n\n"; messages.forEach(m => md += `## ${m.role}\n${m.content}\n\n`);
            const b = new Blob([md], { type: 'text/markdown' }); const u = URL.createObjectURL(b);
            const a = document.createElement('a'); a.href = u; a.download = `chat_${currentActiveUUID}.md`; a.click();
        } catch (e) {}
    }
    if (exportBtn) exportBtn.onclick = handleExport;
    if (exportBtnMobile) exportBtnMobile.onclick = handleExport;

    async function fetchForks(uuid) { try { const res = await fetch(`/sessions/${uuid}/forks`); currentForkMap = await res.json(); } catch (e) { currentForkMap = {}; } }

    async function loadPatterns() { try { const res = await fetch('/patterns'); const data = await res.json(); allPatterns = data; renderPatterns(data); } catch (e) {} }
    function renderPatterns(patterns) {
        if (!patternsList) return;
        patternsList.innerHTML = patterns.map(p => {
            if (p.type === 'user') return `<div class="list-group-item bg-dark border-secondary d-flex justify-content-between align-items-center"><div class="pattern-item cursor-pointer" data-type="user" data-name="${p.name}"><h6 class="mb-0 text-info">${p.name}</h6></div><button class="btn btn-sm btn-outline-warning edit-prompt-btn" data-name="${p.name}"><i class="bi bi-pencil"></i></button></div>`;
            return `<button type="button" class="list-group-item list-group-item-action bg-dark text-light border-secondary pattern-item" data-type="${p.type}" data-name="${p.name}"><h6 class="mb-0">${p.name.replace('skill:', '')}</h6></button>`;
        }).join('');
        document.querySelectorAll('.pattern-item').forEach(item => { item.onclick = () => {
            const {name, type} = item.dataset;
            if (type === 'skill') messageInput.value = `Use skill '${name.replace('skill:', '')}' to ${messageInput.value}`;
            else if (type === 'system') messageInput.value = `/p ${name} ${messageInput.value}`;
            else fetch(`/prompts/${name}`).then(r => r.json()).then(d => { if (d.content) { messageInput.value = d.content; messageInput.dispatchEvent(new Event('input')); } });
            bootstrap.Modal.getInstance(patternsModalEl).hide(); messageInput.focus();
        }; });
        document.querySelectorAll('.edit-prompt-btn').forEach(btn => { btn.onclick = async (e) => { e.stopPropagation(); const res = await fetch(`/prompts/${btn.dataset.name}`); const d = await res.json(); if (d.content) { document.getElementById('edit-prompt-filename').value = btn.dataset.name; document.getElementById('edit-prompt-content').value = d.content; editPromptModalEl.dataset.mode = 'edit'; new bootstrap.Modal(editPromptModalEl).show(); } }; });
    }

    if (btnSavePrompt) {
        btnSavePrompt.onclick = async () => {
            const name = document.getElementById('edit-prompt-filename').value.trim(), content = document.getElementById('edit-prompt-content').value, mode = editPromptModalEl.dataset.mode || 'create';
            const fd = new FormData(); fd.append('content', content); if (mode === 'create') fd.append('filename', name);
            const res = await fetch(mode === 'create' ? '/prompts' : `/prompts/${name}`, { method: mode === 'create' ? 'POST' : 'PUT', body: fd });
            if (res.ok) { bootstrap.Modal.getInstance(editPromptModalEl).hide(); loadPatterns(); }
        };
    }

    // --- Observer ---
    const observer = new IntersectionObserver((entries) => { if (entries[0].isIntersecting && !isLoadingHistory && currentOffset > 0 && currentActiveUUID) loadMessages(currentActiveUUID, PAGE_LIMIT, currentOffset); }, { root: chatContainer, threshold: 0.1 });
    if (!document.getElementById('scroll-sentinel')) { const s = document.createElement('div'); s.id = 'scroll-sentinel'; s.style.height = '10px'; chatContainer.prepend(s); }
    observer.observe(document.getElementById('scroll-sentinel'));

    // --- Share ---
    if (btnConfirmShare) { btnConfirmShare.onclick = async () => {
        const u = shareUsernameInput.value.trim(); if (!u || !currentActiveUUID) return;
        const res = await fetch(`/sessions/${currentActiveUUID}/share`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: u }) });
        if (res.ok) { shareStatus.textContent = 'Shared!'; setTimeout(() => bootstrap.Modal.getInstance(shareModalEl).hide(), 1000); }
    }; }

    // --- Initialization ---
    loadWorkspaces(); loadSessions(); loadPatterns(); fetchUniqueTags();
    if (currentActiveUUID) { 
        loadSessionWorkspace(currentActiveUUID); 
        if (window.INITIAL_MESSAGES && window.INITIAL_MESSAGES.length > 0) {
            // Render server-provided initial messages into the DOM
            if (chatWelcome) chatWelcome.classList.add('d-none');
            chatContainer.innerHTML = '<div id="scroll-sentinel" style="height: 10px; width: 100%;"></div>';
            const sentinel = document.getElementById('scroll-sentinel');
            if (sentinel) observer.observe(sentinel);
            window.INITIAL_MESSAGES.forEach((msg, idx) => {
                const index = (msg.raw_index !== undefined) ? msg.raw_index : idx;
                const div = createMessageDiv(msg.role, msg.content, null, null, index);
                if (div) chatContainer.appendChild(div);
            });
            currentOffset = window.INITIAL_MESSAGES.length;
            chatContainer.scrollTop = chatContainer.scrollHeight;
            fetchForks(currentActiveUUID);
        } else {
            loadMessages(currentActiveUUID); 
        }
    }

    if (window.USER_SETTINGS) {
        updateDriveModeVisibility();
        updatePlanModeVisibility();
    }

    modelLinks.forEach(l => { l.onclick = (e) => { e.preventDefault(); updateActiveModelUI(l.dataset.model); }; });
    if (planModeBtn) planModeBtn.onclick = () => { planModeActive = !planModeActive; planModeBtn.classList.toggle('btn-warning', planModeActive); planModeBtn.classList.toggle('btn-outline-warning', !planModeActive); messageInput.placeholder = planModeActive ? "Plan Mode..." : "Message..."; };
    messageInput.oninput = () => { messageInput.style.height = 'auto'; messageInput.style.height = messageInput.scrollHeight + 'px'; };
    
    // Swipe
    let ts = 0; document.addEventListener('touchstart', e => ts = e.touches[0].clientX, { passive: true });
    document.addEventListener('touchend', e => { const dx = e.changedTouches[0].clientX - ts; if (Math.abs(dx) > 100) { if (dx > 0 && ts < 50) bootstrap.Offcanvas.getOrCreateInstance(historySidebar).show(); else if (dx < 0 && ts > window.innerWidth - 50) bootstrap.Offcanvas.getOrCreateInstance(document.getElementById('actionsSidebar')).show(); } }, { passive: true });
});
