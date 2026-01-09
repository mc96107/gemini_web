#!/bin/bash

# Ensure termux-services and python are installed
pkg install termux-services python -y

# Install dependencies globally
echo "Installing dependencies..."
pip install python-dotenv fastapi uvicorn python-multipart jinja2 bcrypt itsdangerous eth-account webauthn httpx

# Set SVDIR for this session
export SVDIR="$PREFIX/var/service"

# Create directory for the service
SERVICE_NAME="gemini-agent"
SERVICE_DIR="$SVDIR/$SERVICE_NAME"
mkdir -p "$SERVICE_DIR"

# Get current directory
CUR_DIR=$(pwd)
APP_FILE="gemini_agent_release.py"

# Sanity checks
if [ ! -f "$CUR_DIR/$APP_FILE" ]; then
    echo "Error: $APP_FILE not found in $CUR_DIR"
    echo "Please run 'python scripts/recombine.py' first."
    exit 1
fi

# Create the run script for termux-services
cat <<EOF > "$SERVICE_DIR/run"
#!/data/data/com.termux/files/usr/bin/bash
exec 2>&1
# Wake lock to prevent Android from sleeping
termux-wake-lock
export HOME="/data/data/com.termux/files/home"
export PREFIX="/data/data/com.termux/files/usr"
export PATH="\$PREFIX/bin:\$PATH"

cd "$CUR_DIR"

# Load GOOGLE_API_KEY if present in .env
if [ -f .env ]; then
  export \$(grep GOOGLE_API_KEY .env | xargs)
fi

# Execute using global python
exec python "$APP_FILE" > /dev/null 2>&1
EOF

# Make run script executable
chmod +x "$SERVICE_DIR/run"

echo "Service '$SERVICE_NAME' created."
echo "To start it, run:"
echo "sv-enable $SERVICE_NAME"
echo "sv up $SERVICE_NAME"
echo ""
echo "To check logs, run:"
echo "logcat | grep $SERVICE_NAME"
echo ""
echo "Note: You might want to stop the old 'gemini-py' service if it's running:"
echo "sv down gemini-py"
