#!/bin/bash

# OpenCode Agent Systemd Setup Script
# Port: 8020

set -e

SERVICE_NAME="opencode-agent"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME.service"
CUR_DIR=$(pwd)
USER_NAME=$(whoami)
APP_FILE="opencode_agent_release.py"
PORT=8020

# Sanity checks
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo ./setup_systemd.sh)"
  exit 1
fi

if [ ! -f "$CUR_DIR/$APP_FILE" ]; then
    echo "Error: $APP_FILE not found in $CUR_DIR"
    echo "Please run 'python scripts/recombine.py' first."
    exit 1
fi

if [ ! -d "$CUR_DIR/.venv" ]; then
    echo "Error: Virtual environment (.venv) not found."
    echo "Please run 'uv venv' and 'uv pip install -r requirements.txt' first."
    exit 1
fi

echo "Creating systemd service at $SERVICE_PATH..."

cat <<EOF > "$SERVICE_PATH"
[Unit]
Description=OpenCode Agent Service
After=network.target

[Service]
User=$USER_NAME
Group=$USER_NAME
WorkingDirectory=$CUR_DIR
ExecStart=$CUR_DIR/.venv/bin/python $APP_FILE --port $PORT --host 0.0.0.0
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

echo "Reloading systemd daemon..."
systemctl daemon-reload

echo "Enabling and starting $SERVICE_NAME..."
systemctl enable "$SERVICE_NAME"
systemctl start "$SERVICE_NAME"

echo "------------------------------------------------"
echo "Service '$SERVICE_NAME' is now active."
echo "Port: $PORT"
echo "To check status: systemctl status $SERVICE_NAME"
echo "To view logs: journalctl -u $SERVICE_NAME -f"
echo "------------------------------------------------"
