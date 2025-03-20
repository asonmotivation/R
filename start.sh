#!/bin/bash

# Display basic info
echo "=== RDP Monitor Service ==="
echo "Starting up..."

# Don't try to install packages - they should be pre-installed in the Dockerfile
# Don't try to change permissions

# Set up environment variables for the monitor script
export GITHUB_TOKEN=$passwd
export REPO_OWNER="asonmotivation"
export REPO_NAME="R"
export WORKFLOW_NAME="Windows 2022"

# Start the web server in the background
echo "Starting web interface on port 7860..."
python3 web_server.py &

# Start the monitoring script
echo "Starting monitor service..."
python3 monitor.py
