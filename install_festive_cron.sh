#!/bin/bash
# Festive Email Cron Job Installation Script
# This script sets up a daily cron job to send festive emails automatically

echo "🎉 Festive Email Cron Job Installer"
echo "===================================="
echo ""

# Get the absolute path to the project
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python"
SCRIPT_PATH="$PROJECT_DIR/run_festive_cron.py"
LOG_DIR="$PROJECT_DIR/logs"

# Check if virtual environment exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "❌ Error: Virtual environment not found at $VENV_PYTHON"
    echo "Please set up your virtual environment first."
    exit 1
fi

# Check if script exists
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ Error: Festive cron script not found at $SCRIPT_PATH"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Create the cron command
CRON_COMMAND="0 9 * * * cd $PROJECT_DIR && $VENV_PYTHON $SCRIPT_PATH >> $LOG_DIR/festive_cron.log 2>&1"

echo "📋 Cron job to be installed:"
echo "$CRON_COMMAND"
echo ""

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "run_festive_cron.py"; then
    echo "⚠️  A festive email cron job already exists!"
    echo ""
    read -p "Do you want to replace it? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Installation cancelled."
        exit 0
    fi
    
    # Remove old cron job
    crontab -l 2>/dev/null | grep -v "run_festive_cron.py" | crontab -
    echo "✓ Removed old cron job"
fi

# Install new cron job
(crontab -l 2>/dev/null; echo "$CRON_COMMAND") | crontab -

# Verify installation
if crontab -l 2>/dev/null | grep -q "run_festive_cron.py"; then
    echo ""
    echo "✅ Festive email cron job installed successfully!"
    echo ""
    echo "📅 Schedule: Daily at 9:00 AM"
    echo "📝 Logs: $LOG_DIR/festive_cron.log"
    echo ""
    echo "To view your cron jobs:"
    echo "  crontab -l"
    echo ""
    echo "To remove this cron job:"
    echo "  crontab -e"
    echo "  (then delete the line containing 'run_festive_cron.py')"
    echo ""
    echo "To test manually:"
    echo "  $VENV_PYTHON $SCRIPT_PATH"
    echo ""
    echo "To test with a specific date (e.g., Christmas):"
    echo "  curl -X POST 'http://localhost:8000/api/cron/send-festive-emails?test_date=12-25'"
else
    echo ""
    echo "❌ Failed to install cron job"
    exit 1
fi
