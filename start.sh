#!/bin/bash

# Create logs directory with proper permissions
mkdir -p /tmp/logs
chmod -R 777 /tmp/logs

# Set up environment variables 
export GITHUB_TOKEN=${GITHUB_TOKEN:-$passwd}
export REPO_OWNER=${REPO_OWNER:-"asonmotivation"}
export REPO_NAME=${REPO_NAME:-"R"}
export WORKFLOW_NAME=${WORKFLOW_NAME:-"Windows 2022"}
export BRANCH=${BRANCH:-"main"}
export PYTHONUNBUFFERED=1

echo "Starting RDP Monitor Service on Hugging Face Spaces..."

# Start the web server on port 7860 for Hugging Face Spaces
python3 web_server.py --port 7860 > /tmp/logs/web_server.log 2>&1 &

# Start the monitoring script with full logging
python3 monitor.py > /tmp/logs/monitor.log 2>&1
