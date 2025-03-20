#!/bin/bash

# Display basic info
echo "=== RDP Monitor Service ==="
echo "Starting up..."

# Install Python dependencies
pip3 install -q -r requirements.txt

# Set up environment variables for the monitor script
export GITHUB_TOKEN=$passwd
export REPO_OWNER="asonmotivation"
export REPO_NAME="R"
export WORKFLOW_NAME="Windows 2022"

# Create a log directory
mkdir -p /app/logs

# Start the web server in the background
echo "Starting web interface on port 7860..."
python3 web_server.py &

# Start the monitoring script
echo "Starting monitor service..."
python3 monitor.py
