/**
 * Compresses an image file client-side.
 * @param {File} file - The original image file.
 * @returns {Promise<File>} - A promise that resolves to the compressed WebP File.
 */
async function compressImage(file) {
    // Only compress images
    if (!file.type.startsWith('image/')) {
        return file;
    }

    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            const img = new Image();
            img.onload = () => {
                const canvas = document.createElement('canvas');
                let width = img.width;
                let height = img.height;
                const maxDim = 1536;

                // Calculate new dimensions
                if (width > maxDim || height > maxDim) {
                    if (width > height) {
                        height = Math.round((height * maxDim) / width);
                        width = maxDim;
                    } else {
                        width = Math.round((width * maxDim) / height);
                        height = maxDim;
                    }
                }

                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext('2d');
                
                // Use better image scaling if supported
                ctx.imageSmoothingEnabled = true;
                ctx.imageSmoothingQuality = 'high';
                
                ctx.drawImage(img, 0, 0, width, height);

                // Convert to WebP with 0.8 quality
                canvas.toBlob((blob) => {
                    if (blob) {
                        // Create a new File object with .webp extension
                        const newFileName = file.name.replace(/\.[^/.]+$/, "") + ".webp";
                        const compressedFile = new File([blob], newFileName, {
                            type: 'image/webp',
                            lastModified: Date.now()
                        });
                        resolve(compressedFile);
                    } else {
                        // Fallback to original if compression fails
                        resolve(file);
                    }
                }, 'image/webp', 0.8);
            };
            img.onerror = () => reject(new Error('Failed to load image for compression.'));
            img.src = e.target.result;
        };
        reader.onerror = () => reject(new Error('Failed to read file for compression.'));
        reader.readAsDataURL(file);
    });
}