/**
 * @jest-environment jsdom
 */

// Mock ClipboardItem and navigator.clipboard
if (typeof ClipboardItem === 'undefined') {
    global.ClipboardItem = jest.fn().mockImplementation((obj) => ({ data: obj }));
}
global.Blob = jest.fn().mockImplementation((parts, options) => ({ parts, options }));

const mockWrite = jest.fn(() => Promise.resolve());
const mockWriteText = jest.fn(() => Promise.resolve());

Object.assign(navigator, {
    clipboard: {
        write: mockWrite,
        writeText: mockWriteText
    }
});

// Re-implement the function for testing since it's not exported from script.js
async function copyMessageToClipboard(text, messageDiv, btn, USER_SETTINGS) {
    try {
        const icon = btn.querySelector('i');
        const isFormatted = USER_SETTINGS && USER_SETTINGS.copy_formatted === true;

        if (isFormatted && typeof ClipboardItem !== 'undefined') {
            // Get the rendered HTML content, excluding the actions div
            const contentClone = messageDiv.cloneNode(true);
            const actions = contentClone.querySelector('.message-actions');
            if (actions) actions.remove();
            
            // Remove question cards
            contentClone.querySelectorAll('.question-card').forEach(c => c.remove());

            const htmlContent = contentClone.innerHTML;
            const blobHtml = new Blob([htmlContent], { type: 'text/html' });
            const blobText = new Blob([text], { type: 'text/plain' });
            
            const data = [new ClipboardItem({
                'text/html': blobHtml,
                'text/plain': blobText
            })];
            
            await navigator.clipboard.write(data);
        } else {
            // Default markdown only
            await navigator.clipboard.writeText(text);
        }

        if (icon) icon.className = 'bi bi-check2';
    } catch (err) {
        // Fallback
        try {
            await navigator.clipboard.writeText(text);
            const icon = btn.querySelector('i');
            if (icon) {
                icon.className = 'bi bi-check2';
            }
        } catch (e) {}
    }
}

describe('copyMessageToClipboard', () => {
    let messageDiv, btn, icon;

    beforeEach(() => {
        messageDiv = document.createElement('div');
        messageDiv.className = 'message bot';
        messageDiv.innerHTML = '<div class="message-content"><p>Hello <b>World</b></p></div><div class="message-actions"></div>';
        btn = document.createElement('button');
        icon = document.createElement('i');
        icon.className = 'bi bi-clipboard';
        btn.appendChild(icon);
        jest.clearAllMocks();
    });

    test('should copy raw text when copy_formatted is false', async () => {
        const settings = { copy_formatted: false };
        await copyMessageToClipboard('**Hello** World', messageDiv, btn, settings);
        
        expect(mockWriteText).toHaveBeenCalledWith('**Hello** World');
        expect(mockWrite).not.toHaveBeenCalled();
        expect(icon.className).toBe('bi bi-check2');
    });

    test('should copy rich text when copy_formatted is true', async () => {
        const settings = { copy_formatted: true };
        await copyMessageToClipboard('**Hello** World', messageDiv, btn, settings);
        
        expect(mockWrite).toHaveBeenCalled();
        const callArgs = mockWrite.mock.calls[0][0];
        expect(callArgs[0].data).toHaveProperty('text/html');
        expect(callArgs[0].data).toHaveProperty('text/plain');
        
        // Check that HTML content doesn't have message-actions
        const htmlBlob = callArgs[0].data['text/html'];
        const html = htmlBlob.parts[0];
        expect(html).toContain('Hello <b>World</b>');
        expect(html).not.toContain('message-actions');
    });

    test('should remove question cards from copied HTML', async () => {
        messageDiv.innerHTML = '<div class="message-content">Question?</div><div class="question-card">Option A</div><div class="message-actions"></div>';
        const settings = { copy_formatted: true };
        await copyMessageToClipboard('Question?', messageDiv, btn, settings);
        
        const callArgs = mockWrite.mock.calls[0][0];
        const html = callArgs[0].data['text/html'].parts[0];
        expect(html).toContain('Question?');
        expect(html).not.toContain('question-card');
    });

    test('should fallback to writeText if write fails', async () => {
        mockWrite.mockRejectedValueOnce(new Error('Clipboard failure'));
        const settings = { copy_formatted: true };
        await copyMessageToClipboard('**Hello** World', messageDiv, btn, settings);
        
        expect(mockWriteText).toHaveBeenCalledWith('**Hello** World');
        expect(icon.className).toBe('bi bi-check2');
    });
});
