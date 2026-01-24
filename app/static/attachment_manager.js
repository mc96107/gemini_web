class AttachmentManager {
    constructor(options = {}) {
        this.attachments = []; // Array of objects: { file, id, compressedFile, previewUrl, size }
        this.maxTotalSize = options.maxTotalSize || 20 * 1024 * 1024; // Default 20MB
        this.onQueueChange = options.onQueueChange || (() => {});
        this.onSizeLimitExceeded = options.onSizeLimitExceeded || (() => {});
    }

    /**
     * Adds files to the queue.
     * @param {FileList|File[]} files 
     */
    async addFiles(files) {
        for (const file of Array.from(files)) {
            const id = Math.random().toString(36).substring(2, 9);
            let processedFile = file;
            let previewUrl = null;

            if (file.type.startsWith('image/')) {
                try {
                    // Assume compressImage is available globally or we'll inject it
                    if (typeof compressImage === 'function') {
                        processedFile = await compressImage(file);
                    }
                    previewUrl = URL.createObjectURL(processedFile);
                } catch (e) {
                    console.error("Compression failed for", file.name, e);
                }
            }

            const attachmentSize = processedFile.size;
            if (this.getTotalSize() + attachmentSize > this.maxTotalSize) {
                this.onSizeLimitExceeded(file.name);
                continue;
            }

            this.attachments.push({
                id,
                originalFile: file,
                file: processedFile,
                previewUrl,
                name: processedFile.name,
                size: attachmentSize,
                type: file.type
            });
        }
        this.onQueueChange(this.attachments);
    }

    removeAttachment(id) {
        const index = this.attachments.findIndex(a => a.id === id);
        if (index !== -1) {
            const attachment = this.attachments[index];
            if (attachment.previewUrl) {
                URL.revokeObjectURL(attachment.previewUrl);
            }
            this.attachments.splice(index, 1);
            this.onQueueChange(this.attachments);
        }
    }

    clear() {
        this.attachments.forEach(a => {
            if (a.previewUrl) URL.revokeObjectURL(a.previewUrl);
        });
        this.attachments = [];
        this.onQueueChange(this.attachments);
    }

    getTotalSize() {
        return this.attachments.reduce((sum, a) => sum + a.size, 0);
    }

    getFiles() {
        return this.attachments.map(a => a.file);
    }
}

if (typeof module !== 'undefined' && module.exports) {
    module.exports = AttachmentManager;
}
