const AttachmentManager = require('../app/static/attachment_manager.js');

// Mock compressImage if it's not defined
global.compressImage = jest.fn(file => Promise.resolve(file));
global.URL = {
    createObjectURL: jest.fn(() => 'blob:mock-url'),
    revokeObjectURL: jest.fn()
};

describe('AttachmentManager', () => {
    let manager;
    let mockOnQueueChange;
    let mockOnSizeLimitExceeded;

    beforeEach(() => {
        mockOnQueueChange = jest.fn();
        mockOnSizeLimitExceeded = jest.fn();
        manager = new AttachmentManager({
            maxTotalSize: 1000, // 1000 bytes for easy testing
            onQueueChange: mockOnQueueChange,
            onSizeLimitExceeded: mockOnSizeLimitExceeded
        });
        jest.clearAllMocks();
    });

    test('should add files to the queue', async () => {
        const file = new File(['hello'], 'test.txt', { type: 'text/plain' });
        // File size is 5 bytes
        await manager.addFiles([file]);

        expect(manager.attachments.length).toBe(1);
        expect(manager.attachments[0].name).toBe('test.txt');
        expect(mockOnQueueChange).toHaveBeenCalledWith(manager.attachments);
    });

    test('should remove files from the queue', async () => {
        const file = new File(['hello'], 'test.txt', { type: 'text/plain' });
        await manager.addFiles([file]);
        const id = manager.attachments[0].id;
        
        manager.removeAttachment(id);

        expect(manager.attachments.length).toBe(0);
        expect(mockOnQueueChange).toHaveBeenCalledTimes(2);
    });

    test('should enforce cumulative size limit', async () => {
        const largeFile = { size: 600, name: 'large.txt', type: 'text/plain' };
        const anotherLargeFile = { size: 500, name: 'too_large.txt', type: 'text/plain' };

        await manager.addFiles([largeFile]);
        expect(manager.attachments.length).toBe(1);

        await manager.addFiles([anotherLargeFile]);
        expect(manager.attachments.length).toBe(1); // Not added
        expect(mockOnSizeLimitExceeded).toHaveBeenCalledWith('too_large.txt');
    });

    test('should calculate total size correctly', async () => {
        const file1 = { size: 100, name: 'f1.txt', type: 'text/plain' };
        const file2 = { size: 200, name: 'f2.txt', type: 'text/plain' };

        await manager.addFiles([file1, file2]);
        expect(manager.getTotalSize()).toBe(300);
    });
});

// Minimal File shim for Node environment if needed
function File(parts, name, properties) {
    this.parts = parts;
    this.name = name;
    this.type = properties.type;
    this.size = parts.reduce((acc, part) => acc + part.length, 0);
}
global.File = File;
