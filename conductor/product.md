# Initial Concept

A "Gemini Termux Agent" providing a web-based chat interface with advanced authentication (Passkeys and Ethereum signing) specifically designed for the Termux environment on Android.

# Product Guide - Gemini Termux Agent

## Target Audience
The Gemini Termux Agent is designed for:
* **Developers and Power Users:** Individuals who utilize the Termux environment on Android for development, scripting, and mobile computing.
* **Privacy-Conscious Users:** Those seeking a self-hosted, private AI chat interface that runs locally on their device.
* **Web3 Enthusiasts:** Users who value decentralized identity and secure authentication methods like Ethereum signing and Passkeys.

## Goals & Benefits
* **Seamless Mobile AI:** Provide a robust and user-friendly web interface for interacting with Large Language Models (LLMs) directly from an Android device via Termux.
* **Secure Local Access:** Implement modern authentication standards (Passkeys, WebAuthn, and Ethereum-based login) to ensure that the local AI agent and its data remain private and accessible only to authorized users.
* **Termux-Native Experience:** Optimize the application for the unique constraints and capabilities of the Termux environment, including simple deployment and wake-lock management.

## Key Features
* **Interactive Web Chat:** A responsive chat interface featuring conversation history and dynamic UI updates.
* **Math Rendering:** Built-in support for LaTeX mathematical expressions via KaTeX, enabling high-quality rendering of formulas.
* **Chat Export:** Export full conversation history as Markdown files for offline storage or sharing.
* **Infinite Scroll History:** Seamlessly load and browse previous messages by scrolling to the top of the chat window.
* **Fast Initial Load:** Implements Initial State Inlining to pre-render the active session on the server, ensuring conversations appear instantly upon startup.
* **Automatic Model Fallback:** Intelligent error detection that automatically switches to a secondary model (e.g., from Pro to Flash) if the primary model is over-capacity (429 error), ensuring uninterrupted service.
* **User Message Image Preview:** Inline thumbnails for uploaded images in the chat history and immediate previews for new uploads.
* **Client-Side Image Compression:** Automatically compresses and resizes uploaded photos in the browser to ensure they fit within the model's context window while saving bandwidth.
* **Session Auto-Restoration:** Automatically reloads the last active chat session upon login, providing a seamless continuation of previous conversations.
* **Smart History Pagination:** Efficiently handles long chat histories by lazy-loading messages, ensuring fast initial load times regardless of conversation length.
* **Real-Time Streaming:** Responses are streamed chunk-by-chunk using Server-Sent Events (SSE), providing immediate feedback and preventing timeouts on complex tasks.
* **Live Tool Logs:** Transparent execution of background tools (filesystem, search, etc.) with real-time logs displayed directly in the chat.
* **Advanced Authentication:** Support for passwordless login via Passkeys (WebAuthn) and cryptographically secure login via Ethereum wallet signatures.
* **Per-Session Tool Security:** Granular control over Gemini CLI tools (e.g., file access, shell execution) on a per-session basis. All tools are disabled by default for maximum security, allowing users to selectively enable only the tools required for the current task.
* **Pattern-Based Prompting:** A template system (Patterns) that allows users to leverage expert-crafted prompts for specific tasks like Agile story creation or insightful AI analysis.
* **Admin Dashboard:** A dedicated interface for managing users, monitoring system status, and configuring agent behavior.

## User Experience & Visual Aesthetic
* **Terminal-Inspired Dark Mode:** A sleek, high-contrast dark theme that pays homage to the terminal environments preferred by its core audience.
* **Mobile-First Design:** A minimalist and functional layout optimized for mobile browsers, ensuring ease of use on the go.
* **Clarity and Accessibility:** Focused on high readability for both chat text and code snippets, utilizing clear typography and distinct visual separation for messages.