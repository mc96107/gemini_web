# OpenCode Agent

A secure web interface for interacting with Google's Gemini AI, specifically optimized for Raspberry Pi 4 and other Linux environments.

## Features

*   **Modular Architecture:** Cleanly separated backend (FastAPI), frontend (Jinja2/Bootstrap), and service layers.
*   **Structured Interactive Questioning:** The AI can ask multiple-choice or open-ended questions using "Question Cards" directly in the main chat, providing a more structured way to gather your requirements.
*   **Multi-Modal Chat:** Support for text and file attachments.
*   **Global Interaction Customization:** Admins can globally customize the system instructions for the main chat's Interactive Mode via the Admin Dashboard.
*   **Conversation Branching:** Edit previous questions to fork conversations and explore different paths seamlessly.
*   **Tree View Visualization:** Visualize and navigate your conversation branches as a structured tree.
*   **Custom Prompt Management:** Save, edit, and delete your own synthesized prompts directly within the UI. Custom prompts are integrated into the Patterns modal for easy reuse.
*   **Advanced Chat Management:** Organize your history with tags, pinning, and custom chat titles.
*   **User Role Management:** Admins can manage users and toggle roles (user/admin) directly from the dashboard.
*   **Per-User Preferences:** Customize your experience, such as toggling Interactive Mode or showing/hiding the Drive Mode (Mic) icon.
*   **Modern Web UX:** Optimized for high-performance responsive browsing with intuitive gestures.
*   **Advanced Authentication:** Login via Passkeys (WebAuthn), Ethereum Wallet signatures, or traditional passwords.
*   **Progressive Web App (PWA):** Install the agent directly for an app-like experience.
*   **Pattern-Based Prompting:** Leverage specialized prompts for consistent, high-quality AI responses.
*   **Self-Hosted & Private:** Runs entirely on your local device.

## Installation & Setup

### For Raspberry Pi 4 (Raspberry Pi OS 64-bit)

1.  **Update system**:
    ```bash
    sudo apt update && sudo apt upgrade -y
    sudo apt install git python3-venv ghostscript -y
    ```
2.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-username/opencode_web.git
    cd opencode_web
    ```
3.  **Install OpenCode CLI**:
    ```bash
    npm install -g @anomaly/opencode
    ```
4.  **Setup Environment**:
    ```bash
    uv venv
    uv pip install -r requirements.txt
    ```
5.  **Run the automated systemd setup**:
    ```bash
    chmod +x setup_systemd.sh
    sudo ./setup_systemd.sh
    ```
    *This will create and register a systemd service named `opencode-agent` running on port 8020.*

### For Desktop / Development
1.  Clone the repository.
2.  Install dependencies:
    *   **Ghostscript:** Required for PDF compression.
        *   **Windows:** [Download and install Ghostscript](https://ghostscript.com/releases/gsdnld.html). Ensure the `bin` folder is in your PATH.
        *   **Linux/macOS:** `sudo apt install ghostscript` or `brew install ghostscript`.
    *   **Python packages:**
        ```bash
        uv venv
        uv pip install -r requirements.txt
        ```
3.  Run the application:
    ```bash
    uv run python -m app.main
    ```

## Usage Guide

1.  **Initial Setup**: On your first run, visit `http://localhost:8020/setup` to create the admin user and configure your `GOOGLE_API_KEY`.
2.  **Login**: Use the credentials created during setup. You can later add Passkeys or Link an Ethereum Wallet for faster login.
3.  **Chatting**: Simply type your message in the chat box. Use the "Patterns" button to select specialized AI personas.
4.  **History & Organization**: Access previous conversations via the sidebar. Use the "Tags" button to categorize chats and the "Tree" button to visualize conversation branches.
5.  **User Management & Admin**: Admins can visit `/admin` to add/remove users and change user roles.
6.  **PWA**: For the best experience, use the "Add to Home Screen" option in your browser to install it as a Progressive Web App.


## Building for Release

The OpenCode Termux Agent can be bundled into a single-file portable application for easier distribution and deployment.

### 1. Generate the Release Bundle
To recombine the modular project structure into a single-file script, run the recombination script:
```bash
python scripts/recombine.py
```
This will create `opencode_agent_release.py` in the root directory.

### 2. Setup & Test Release Environment
You can automate the creation of a dedicated virtual environment and test the release bundle using:
```bash
python setup_release.py
```
This script will:
*   Regenerate the `opencode_agent_release.py` bundle.
*   Create a `venv_release` virtual environment.
*   Install all necessary dependencies into that environment.
*   Offer to start the bundled application for verification.

## Serving with Nginx (Reverse Proxy)

To access your OpenCode Agent securely over the internet or a local network via a standard domain, you can use Nginx as a reverse proxy.

### Sample Nginx Configuration
Create a new configuration file (e.g., `/etc/nginx/sites-available/opencode-agent`):

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
sudo ln -s /etc/nginx/sites-available/opencode-agent /etc/nginx/sites-enabled/
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
