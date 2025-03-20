#!/bin/bash

# Set up environment variables 
export GITHUB_TOKEN=$passwd
export REPO_OWNER="asonmotivation"
export REPO_NAME="R"
export WORKFLOW_NAME="Windows 2022"
export BRANCH="main"

# Enable detailed logging to file
mkdir -p /tmp/logs
export PYTHONUNBUFFERED=1

# Start the web server in the background
python3 web_server.py > /tmp/logs/web_server.log 2>&1 &

# Start the monitoring script with full logging
python3 monitor.py > /tmp/logs/monitor.log 2>&1
