# Gemini Termux Agent

A mobile-first, secure web interface for interacting with Google's Gemini AI, specifically optimized for the Termux environment on Android.

## Features

*   **Modular Architecture:** Cleanly separated backend (FastAPI), frontend (Jinja2/Bootstrap), and service layers.
*   **Structured Interactive Questioning:** The AI can ask multiple-choice or open-ended questions using "Question Cards" directly in the main chat, providing a more structured way to gather your requirements.
*   **Multi-Modal Chat:** Support for text and file attachments.
*   **Tree Prompt Helper:** A context-aware, guided system to help you build professional and effective system prompts through interactive Q&A.
*   **Global Interaction Customization:** Admins can globally customize the system instructions for both the Prompt Helper and the main chat's Interactive Mode via the Admin Dashboard.
*   **Conversation Branching:** Edit previous questions to fork conversations and explore different paths seamlessly.
*   **Tree View Visualization:** Visualize and navigate your conversation branches as a structured tree.
*   **Custom Prompt Management:** Save, edit, and delete your own synthesized prompts directly within the UI. Custom prompts are integrated into the Patterns modal for easy reuse.
*   **Advanced Chat Management:** Organize your history with tags, pinning, and custom chat titles.
*   **User Role Management:** Admins can manage users and toggle roles (user/admin) directly from the dashboard.
*   **Per-User Preferences:** Customize your experience, such as toggling Interactive Mode or showing/hiding the Drive Mode (Mic) icon.
*   **Mobile-First UX:** Optimized for Termux with 100dvh support and intuitive swipe gestures (swipe left for history, right for actions).
*   **Advanced Authentication:** Login via Passkeys (WebAuthn), Ethereum Wallet signatures, or traditional passwords.
*   **Progressive Web App (PWA):** Install the agent directly to your home screen for an app-like experience.
*   **Pattern-Based Prompting:** Leverage specialized prompts for consistent, high-quality AI responses.
*   **Self-Hosted & Private:** Runs entirely on your local device via Termux.

## Screenshots

| Login | Security Settings | Available Patterns |
| :---: | :---: | :---: |
| ![Login](./screenshots/login.png) | ![Security](./screenshots/password.png) | ![Patterns](./screenshots/patterns.png) |

| Chat Interface | Chat History |
| :---: | :---: |
| ![Chat](./screenshots/chat.png) | ![History](./screenshots/chat_history.png) |

## Installation & Setup

### For Android (Termux)
The application is optimized for Termux on Android.

1.  **Install Termux** (F-Droid version recommended).
2.  **Clone the repository** (or transfer the files):
    ```bash
    pkg update && pkg upgrade
    pkg install git python -y
    git clone https://github.com/your-username/gemini_web.git
    cd gemini_web
    ```
3.  **Install and Patch Gemini CLI**:
    The Gemini CLI needs a small patch to work correctly in the Termux environment:
    ```bash
    yarn global add @google/gemini-cli
    mkdir -p ~/.config/yarn/global/node_modules/clipboardy
    cat > ~/.config/yarn/global/node_modules/clipboardy/index.js << 'EOF'
    export function write() { return Promise.resolve(); }
    export function read() { return Promise.resolve(""); }
    export default { write, read };
    EOF
    cat > ~/.config/yarn/global/node_modules/clipboardy/package.json << 'EOF'
    {
      "name": "clipboardy",
      "version": "0.0.0",
      "type": "module"
    }
    EOF
    ```
4.  **Run the automated Termux setup**:
    ```bash
    pkg install ghostscript -y
    chmod +x setup_py.sh
    ./setup_py.sh
    ```
    *This will install necessary packages, global dependencies, and register a Termux service named `gemini-agent`.*
4.  **Start the service**:
    ```bash
    sv-enable gemini-agent
    sv up gemini-agent
    ```
5.  **Access the UI**: Open your browser and go to `http://localhost:8000`.

### For Desktop / Development
1.  Clone the repository.
2.  Install dependencies:
    *   **Ghostscript:** Required for PDF compression.
        *   **Windows:** [Download and install Ghostscript](https://ghostscript.com/releases/gsdnld.html). Ensure the `bin` folder is in your PATH.
        *   **Linux/macOS:** `sudo apt install ghostscript` or `brew install ghostscript`.
    *   **Python packages:**
        ```bash
        pip install -r requirements.txt
        ```
3.  Run the application:
    ```bash
    python -m app.main
    ```

## Usage Guide

1.  **Initial Setup**: On your first run, visit `http://localhost:8000/setup` to create the admin user and configure your `GOOGLE_API_KEY`.
2.  **Login**: Use the credentials created during setup. You can later add Passkeys or Link an Ethereum Wallet for faster login.
3.  **Chatting**: Simply type your message in the chat box. Use the "Patterns" button to select specialized AI personas.
4.  **Tree Prompt Helper**: Click the "Prompt Helper" button in the actions menu to start a guided session. The helper will use your recent chat context to ask relevant questions. Once finished, you can synthesize and save a custom system prompt.
5.  **Custom Prompts**: Access your saved prompts at the top of the "Patterns" list. Click a prompt to load it, or use the icons to edit or delete the file.
6.  **Branching & Editing**: Click the edit icon next to any of your previous questions to fork the conversation from that point and explore a new path.
7.  **History & Organization**: Access previous conversations via the sidebar. Use the "Tags" button to categorize chats and the "Tree" button to visualize conversation branches.
8.  **User Management & Admin**: Admins can visit `/admin` to add/remove users and change user roles.
9.  **Global Interaction Customization**: Administrators can globally tune the AI's persona and questioning behavior for both the Prompt Helper and the main chat by updating the System Instructions in the Admin Dashboard.
10. **Preferences**: Open the "Security" modal (shield icon) to toggle general preferences, like enabling/disabling Interactive Mode or showing/hiding the microphone icon.
11. **Mobile Navigation**: Swipe from the left edge to open your chat history, or from the right edge to access chat actions.
7.  **PWA**: For the best experience, use the "Add to Home Screen" option in your mobile browser to install it as a Progressive Web App.

## Building for Release

The Gemini Termux Agent can be bundled into a single-file portable application for easier distribution and deployment.

### 1. Generate the Release Bundle
To recombine the modular project structure into a single-file script, run the recombination script:
```bash
python scripts/recombine.py
```
This will create `gemini_agent_release.py` in the root directory.

### 2. Setup & Test Release Environment
You can automate the creation of a dedicated virtual environment and test the release bundle using:
```bash
python setup_release.py
```
This script will:
*   Regenerate the `gemini_agent_release.py` bundle.
*   Create a `venv_release` virtual environment.
*   Install all necessary dependencies into that environment.
*   Offer to start the bundled application for verification.

## Serving with Nginx (Reverse Proxy)

To access your Gemini Agent securely over the internet or a local network via a standard domain, you can use Nginx as a reverse proxy.

### Sample Nginx Configuration
Create a new configuration file (e.g., `/etc/nginx/sites-available/gemini-agent`):

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (important for real-time updates)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Enable the site and restart Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/gemini-agent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Development Journey

This project was born from a unique collaborative process using AI-driven development:
1.  **Inception on Termux:** Initially scaffolded and built directly on Android using the Termux terminal emulator.
2.  **AI-Assisted Modularization:** Refactored from a monolithic script into a modular FastAPI application using the **Gemini CLI** and the **Conductor** development framework.
3.  **Cross-Platform Refinement:** Improved and hardened on Windows PowerShell, ensuring a robust and well-tested codebase.

## Credits & Inspirations

*   **[Fabric](https://github.com/danielmiessler/Fabric):** Inspiration for pattern-based prompts and expert AI personas.
*   **[Termux](https://github.com/termux/termux-app):** The powerful terminal environment that makes mobile development possible.
*   **[Gemini CLI](https://github.com/google-gemini/gemini-cli):** The core engine used for AI assistance and code generation.
*   **[Conductor](https://github.com/gemini-cli-extensions/conductor):** The spec-driven development methodology that guided the architecture and refactoring.

---

Created with ❤ using **Gemini CLI** and **Conductor**.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
