/**
 * TreePromptHelper Component
 * Manages the guided prompt building UI and interaction.
 */
class PromptTreeView {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.sessionId = null;
        this.nodes = [];
        this.currentNodeId = null;
        this.onAnswerCallback = null;
        this.onRewindCallback = null;
        this.onSaveCallback = null;
    }

    async init() {
        // Check for existing session
        try {
            const response = await fetch('/api/prompt-helper/session');
            const data = await response.json();
            if (data.session) {
                this.sessionId = data.session.id;
                this.nodes = data.session.nodes;
                this.currentNodeId = data.session.current_node_id;
                this.render();
            }
        } catch (error) {
            console.error('Error initializing PromptTreeView:', error);
        }
    }

    async startNewSession() {
        try {
            const response = await fetch('/api/prompt-helper/start', { method: 'POST' });
            const data = await response.json();
            if (data.success) {
                this.sessionId = data.session_id;
                this.currentNodeId = data.node_id;
                await this.refreshSession();
                this.dispatchQuestion(data.next_question, data.node_id);
            }
        } catch (error) {
            console.error('Error starting new session:', error);
        }
    }

    async refreshSession() {
        const response = await fetch('/api/prompt-helper/session');
        const data = await response.json();
        if (data.session) {
            this.nodes = data.session.nodes;
            this.currentNodeId = data.session.current_node_id;
            this.render();
        }
    }

    async submitAnswer(nodeId, answer) {
        const formData = new FormData();
        formData.append('node_id', nodeId);
        formData.append('answer', answer);

        try {
            const response = await fetch('/api/prompt-helper/answer', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            if (data.success) {
                await this.refreshSession();
                if (data.next_question) {
                    this.dispatchQuestion(data.next_question, data.node_id);
                }
                if (this.onAnswerCallback) this.onAnswerCallback(data);
            }
        } catch (error) {
            console.error('Error submitting answer:', error);
        }
    }

    dispatchQuestion(questionData, nodeId) {
        const event = new CustomEvent('tree-helper-question', {
            detail: {
                question: questionData.question,
                options: questionData.options,
                nodeId: nodeId,
                isComplete: questionData.is_complete
            }
        });
        window.dispatchEvent(event);
    }

    async rewindTo(nodeId) {
        const formData = new FormData();
        formData.append('node_id', nodeId);

        try {
            const response = await fetch('/api/prompt-helper/rewind', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            if (data.success) {
                await this.refreshSession();
                
                // Trigger event for UI to clear subsequent messages
                window.dispatchEvent(new CustomEvent('tree-helper-rewind', { detail: { nodeId } }));
                
                // Get the now-unanswered question to re-ask
                const node = this.nodes.find(n => n.id === nodeId);
                if (node) {
                    this.dispatchQuestion(node, nodeId);
                }

                if (this.onRewindCallback) this.onRewindCallback(data);
            }
        } catch (error) {
            console.error('Error rewinding session:', error);
        }
    }

    async savePrompt(title) {
        const formData = new FormData();
        formData.append('title', title);

        try {
            const response = await fetch('/api/prompt-helper/save', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            if (data.success) {
                if (window.showToast) showToast('Prompt saved to prompts/ folder!');
                window.dispatchEvent(new CustomEvent('tree-helper-save', { detail: data }));
                if (this.onSaveCallback) this.onSaveCallback(data);
            }
            return data;
        } catch (error) {
            console.error('Error saving prompt:', error);
            if (window.showToast) showToast('Failed to save prompt.');
        }
    }

    render() {
        if (!this.container) return;

        this.container.innerHTML = '';
        const treeCard = document.createElement('div');
        treeCard.className = 'card shadow-sm mb-3 border-secondary';
        
        const cardHeader = document.createElement('div');
        cardHeader.className = 'card-header bg-dark text-info d-flex justify-content-between align-items-center border-bottom border-secondary';
        cardHeader.innerHTML = '<span class="fw-bold"><i class="bi bi-diagram-3 me-2"></i>Prompt Helper</span>';
        
        const closeBtn = document.createElement('button');
        closeBtn.className = 'btn-close btn-close-white';
        closeBtn.onclick = () => this.container.style.display = 'none';
        cardHeader.appendChild(closeBtn);
        
        const cardBody = document.createElement('div');
        cardBody.className = 'card-body p-0 bg-black';
        cardBody.style.maxHeight = '400px';
        cardBody.style.overflowY = 'auto';

        const listGroup = document.createElement('div');
        listGroup.className = 'list-group list-group-flush';

        this.nodes.forEach((node, index) => {
            const item = document.createElement('div');
            item.className = 'list-group-item bg-dark text-light border-secondary p-2';
            if (node.id === this.currentNodeId) item.classList.add('tree-node-active', 'bg-black');

            const content = document.createElement('div');
            content.className = 'd-flex w-100 justify-content-between align-items-start';
            
            const questionText = document.createElement('div');
            questionText.className = 'small fw-bold text-info';
            questionText.innerText = node.question;
            
            const rewindIcon = document.createElement('i');
            rewindIcon.className = 'bi bi-arrow-counterclockwise text-muted cursor-pointer hover-info ms-2';
            rewindIcon.title = "Rewind to here";
            rewindIcon.onclick = (e) => {
                e.stopPropagation();
                if (confirm('Rewind the session to this question? All subsequent answers will be lost.')) {
                    this.rewindTo(node.id);
                }
            };

            content.appendChild(questionText);
            content.appendChild(rewindIcon);
            
            const answerText = document.createElement('div');
            answerText.className = 'mt-1 small text-secondary italic';
            answerText.innerText = node.answer || (node.id === this.currentNodeId ? '...' : '---');
            
            item.appendChild(content);
            item.appendChild(answerText);
            
            listGroup.appendChild(item);
        });

        if (this.nodes.length === 0) {
            const emptyState = document.createElement('div');
            emptyState.className = 'p-4 text-center text-muted';
            emptyState.innerHTML = '<p class="small">No active session.</p><button class="btn btn-sm btn-primary w-100" id="start-tree-btn">Start Guided Session</button>';
            cardBody.appendChild(emptyState);
            
            setTimeout(() => {
                const btn = document.getElementById('start-tree-btn');
                if (btn) btn.onclick = () => this.startNewSession();
            }, 0);
        } else {
            cardBody.appendChild(listGroup);
            
            // Add Save Button if last node is answered
            const lastNode = this.nodes[this.nodes.length - 1];
            if (lastNode.answer) {
                 const footer = document.createElement('div');
                 footer.className = 'p-2 border-top border-secondary text-center bg-dark';
                 const saveBtn = document.createElement('button');
                 saveBtn.className = 'btn btn-sm btn-success w-100';
                 saveBtn.innerHTML = '<i class="bi bi-save me-1"></i> Save Final Prompt';
                 saveBtn.onclick = () => {
                     const title = prompt('Enter a title for this prompt:', 'Guided Prompt');
                     if (title) this.savePrompt(title);
                 };
                 footer.appendChild(saveBtn);
                 cardBody.appendChild(footer);
            }
        }

        treeCard.appendChild(cardHeader);
        treeCard.appendChild(cardBody);
        this.container.appendChild(treeCard);
    }

        treeCard.appendChild(cardHeader);
        treeCard.appendChild(cardBody);
        this.container.appendChild(treeCard);
    }
}
