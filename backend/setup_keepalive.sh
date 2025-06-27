#!/bin/bash

# Setup script for Backend Keep-Alive Cron Job
# This script installs and configures the cron job to keep your backend alive

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KEEP_ALIVE_SCRIPT="$SCRIPT_DIR/keep_alive.sh"
CRON_CONFIG="$SCRIPT_DIR/crontab_config"

echo "🚀 Setting up Backend Keep-Alive Cron Job..."

# Check if keep_alive.sh exists and is executable
if [[ ! -f "$KEEP_ALIVE_SCRIPT" ]]; then
    echo "❌ Error: keep_alive.sh not found at $KEEP_ALIVE_SCRIPT"
    exit 1
fi

if [[ ! -x "$KEEP_ALIVE_SCRIPT" ]]; then
    echo "🔧 Making keep_alive.sh executable..."
    chmod +x "$KEEP_ALIVE_SCRIPT"
fi

# Test the script first
echo "🧪 Testing keep-alive script..."
if "$KEEP_ALIVE_SCRIPT"; then
    echo "✅ Keep-alive script test successful"
else
    echo "⚠️  Keep-alive script test completed (check logs for details)"
fi

# Backup existing crontab
echo "💾 Backing up existing crontab..."
crontab -l > "$SCRIPT_DIR/crontab_backup_$(date +%Y%m%d_%H%M%S)" 2>/dev/null || echo "No existing crontab found"

# Check if the cron job already exists
if crontab -l 2>/dev/null | grep -q "keep_alive.sh"; then
    echo "⚠️  Keep-alive cron job already exists. Removing old version..."
    crontab -l 2>/dev/null | grep -v "keep_alive.sh" | crontab -
fi

# Add the new cron job
echo "➕ Adding keep-alive cron job..."
(crontab -l 2>/dev/null; echo "*/13 * * * * $KEEP_ALIVE_SCRIPT") | crontab -

# Verify installation
echo "🔍 Verifying cron job installation..."
if crontab -l | grep -q "keep_alive.sh"; then
    echo "✅ Cron job successfully installed!"
    echo ""
    echo "📋 Current crontab:"
    crontab -l | grep "keep_alive.sh"
    echo ""
    echo "📁 Log file location: /tmp/backend_keepalive.log"
    echo "🕐 The script will run every 13 minutes"
    echo ""
    echo "🔧 To manage the cron job:"
    echo "   View logs: tail -f /tmp/backend_keepalive.log"
    echo "   Remove job: crontab -e (then delete the keep_alive.sh line)"
    echo "   Test manually: $KEEP_ALIVE_SCRIPT"
else
    echo "❌ Failed to install cron job"
    exit 1
fi

echo ""
echo "🎉 Setup complete! Your backend will now be kept alive automatically."