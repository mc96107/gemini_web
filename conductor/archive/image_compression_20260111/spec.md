# Specification: Client-Side Image Compression

## Overview
Implement client-side image compression in the web UI to reduce token usage and ensure uploaded photos fit within the model's context window limits. By compressing images in the browser, we also save bandwidth and improve upload speed.

## Functional Requirements
- **Automatic Compression:** Automatically compress any image file selected via the file upload input before it is sent to the `/chat` endpoint.
- **Resizing:** Resize images to a maximum dimension of 1536px (width or height), maintaining the original aspect ratio.
- **Quality Reduction:** Apply JPEG/WebP compression quality (target 0.8) to reduce file size.
- **Format Conversion:** Convert all uploaded images to the WebP format for optimal compression efficiency.
- **File Size Target:** Aim for a compressed file size under 1MB where possible.
- **Seamless Integration:** The compression should happen silently in the background during the form submission process.

## Non-Functional Requirements
- **Performance:** Compression should be fast enough to not noticeably delay the "Thinking..." state transition.
- **Compatibility:** Use standard Browser APIs (Canvas API) for compression to ensure compatibility across modern browsers.

## Acceptance Criteria
- [ ] Large images (> 5MB) are successfully compressed to < 1MB before reaching the server.
- [ ] Images are resized to a maximum of 1536px on their longest side.
- [ ] The server receives a WebP image regardless of the original upload format (JPEG, PNG, etc.).
- [ ] The user can still see the original filename in the UI preview, but the sent data is compressed.
- [ ] The chat functionality continues to work normally with the compressed images.

## Out of Scope
- Manual compression settings or sliders for the user.
- Server-side image processing or resizing.
- Compression of non-image file types.
