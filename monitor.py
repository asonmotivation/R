import os
import time
import requests
import json
import logging
import sys
from datetime import datetime, timezone, timedelta

# Set up logging to stdout only since we may not have write permissions
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# GitHub configuration
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
REPO_OWNER = os.environ.get("REPO_OWNER", "asonmotivation")
REPO_NAME = os.environ.get("REPO_NAME", "R")
WORKFLOW_NAME = os.environ.get("WORKFLOW_NAME", "Windows 2022")
BRANCH = os.environ.get("BRANCH", "master")  # Default branch

# Time constants
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "300"))  # 5 minutes
MAX_RUNTIME = int(os.environ.get("MAX_RUNTIME", "21000"))  # 5h50m in seconds
MAX_RETRY_ATTEMPTS = 3  # Maximum retry attempts for API calls

# Status variables (in-memory only, no file writes)
status = {
    "monitoring": True,
    "last_check": "Never",
    "current_workflow_id": "None",
    "workflow_status": "Unknown",
    "workflow_start_time": "Unknown",
    "workflow_runtime": "0 hours",
    "next_restart": "Unknown",
    "logs": []
}

# Keep a circular buffer of the last 100 log messages
log_buffer = []
MAX_LOG_ENTRIES = 100

# Custom logger that also stores messages for web display
class BufferedHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        log_buffer.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {msg}")
        if len(log_buffer) > MAX_LOG_ENTRIES:
            log_buffer.pop(0)
        
        # Update the status logs
        status["logs"] = log_buffer.copy()

# Add our custom handler
logger = logging.getLogger()
formatter = logging.Formatter('%(levelname)s - %(message)s')
buffered_handler = BufferedHandler()
buffered_handler.setFormatter(formatter)
logger.addHandler(buffered_handler)

def get_headers():
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

def get_workflow_id():
    """Get the workflow ID for the Windows workflow"""
    logging.info(f"Finding workflow ID for '{WORKFLOW_NAME}'")
    
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows"
    retry_count = 0
    
    while retry_count < MAX_RETRY_ATTEMPTS:
        try:
            response = requests.get(url, headers=get_headers())
            response.raise_for_status()
            workflows = response.json().get("workflows", [])
            
            for workflow in workflows:
                if workflow.get("name") == WORKFLOW_NAME:
                    workflow_id = workflow.get("id")
                    logging.info(f"Found workflow ID: {workflow_id}")
                    return workflow_id
                    
            # If we didn't find by name, try finding by filename
            for workflow in workflows:
                if workflow.get("path", "").endswith("win2022.yml"):
                    workflow_id = workflow.get("id")
                    logging.info(f"Found workflow ID by filename: {workflow_id}")
                    return workflow_id
            
            logging.error(f"Could not find workflow with name '{WORKFLOW_NAME}'")
            
            # Print all available workflows for debugging
            logging.info("Available workflows:")
            for workflow in workflows:
                logging.info(f"  - {workflow.get('name')} (path: {workflow.get('path')})")
                
            return None
            
        except requests.exceptions.RequestException as e:
            retry_count += 1
            logging.error(f"Error fetching workflows (attempt {retry_count}): {e}")
            if retry_count < MAX_RETRY_ATTEMPTS:
                time.sleep(60)  # Wait 1 minute before retrying
            else:
                logging.error("Max retry attempts reached")
                return None

def get_latest_run(workflow_id):
    """Get the latest workflow run"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/{workflow_id}/runs"
    retry_count = 0
    
    while retry_count < MAX_RETRY_ATTEMPTS:
        try:
            response = requests.get(url, headers=get_headers())
            response.raise_for_status()
            runs = response.json().get("workflow_runs", [])
            
            if runs:
                return runs[0]
            return None
            
        except requests.exceptions.RequestException as e:
            retry_count += 1
            logging.error(f"Error fetching workflow runs (attempt {retry_count}): {e}")
            if retry_count < MAX_RETRY_ATTEMPTS:
                time.sleep(60)  # Wait 1 minute before retrying
            else:
                logging.error("Max retry attempts reached")
                return None

def trigger_workflow(workflow_id):
    """Trigger the workflow using the workflow_dispatch event"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/{workflow_id}/dispatches"
    
    # Make sure we're using the correct branch name and payload format
    # The correct format is important for the API
    data = {
        "ref": BRANCH,  # Use the BRANCH environment variable instead of hardcoded value
        "inputs": {}      # Add this even if empty for proper API format
    }
    
    retry_count = 0
    while retry_count < MAX_RETRY_ATTEMPTS:
        try:
            logging.info(f"Triggering workflow with branch: {BRANCH}")
            response = requests.post(url, headers=get_headers(), data=json.dumps(data))
            
            if response.status_code == 204:  # Success for this API returns 204 No Content
                logging.info("🚀 Successfully triggered workflow!")
                return True
                
            # If not 204, log the error details
            logging.error(f"Error response: {response.status_code} - {response.text}")
            response.raise_for_status()
            
        except requests.exceptions.RequestException as e:
            retry_count += 1
            logging.error(f"Error triggering workflow (attempt {retry_count}): {e}")
            if retry_count < MAX_RETRY_ATTEMPTS:
                time.sleep(60)  # Wait 1 minute before retrying
            else:
                logging.error("Failed to trigger workflow after maximum retry attempts")
                
                # Try an alternative approach - list runs instead of trigger
                try:
                    logging.info("Attempting to list workflow runs as fallback...")
                    list_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/{workflow_id}/runs"
                    list_response = requests.get(list_url, headers=get_headers())
                    list_response.raise_for_status()
                    logging.info(f"Workflow runs exist, you may need to trigger manually: {REPO_OWNER}/{REPO_NAME}/actions")
                except Exception as list_err:
                    logging.error(f"Error listing runs: {list_err}")
                
                return False

def calculate_runtime(run):
    """Calculate how long a workflow has been running in seconds"""
    if not run.get("updated_at"):
        return 0
        
    updated_time = datetime.strptime(run["updated_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    return (now - updated_time).total_seconds()

def format_time(dt):
    """Format datetime object to string"""
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    return str(dt)

def format_duration(seconds):
    """Format duration in seconds to hours and minutes"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours:d}h {minutes:d}m"

def monitor_and_restart():
    """Main function to monitor workflow status and restart when needed"""
    global status
    
    logging.info("🔍 Starting workflow monitor")
    
    if not GITHUB_TOKEN:
        logging.error("GITHUB_TOKEN environment variable not set! Exiting.")
        status["monitoring"] = False
        exit(1)
    
    workflow_id = get_workflow_id()
    if not workflow_id:
        logging.error("Could not find the workflow. Please check the workflow name.")
        status["monitoring"] = False
        exit(1)
    
    # Track the last time we triggered a workflow to avoid spamming
    last_trigger_time = None
    min_trigger_interval = 300  # 5 minutes minimum between trigger attempts
    
    # Initial trigger if no workflow is running
    latest_run = get_latest_run(workflow_id)
    if not latest_run or latest_run["status"] != "in_progress":
        logging.info("No active workflow run found. Triggering initial workflow run...")
        if trigger_workflow(workflow_id):
            last_trigger_time = datetime.now(timezone.utc)
    
    while True:
        try:
            # Update last check time
            now = datetime.now(timezone.utc)
            status["last_check"] = format_time(now)
            
            # Check if we can trigger a new workflow (anti-spam)
            can_trigger = True
            if last_trigger_time:
                seconds_since_last_trigger = (now - last_trigger_time).total_seconds()
                if seconds_since_last_trigger < min_trigger_interval:
                    can_trigger = False
                    logging.info(f"Cooling down. {min_trigger_interval - seconds_since_last_trigger:.0f} seconds until next possible trigger.")
            
            latest_run = get_latest_run(workflow_id)
            
            if not latest_run:
                logging.warning("No workflow runs found.")
                status["workflow_status"] = "None Found"
                status["current_workflow_id"] = "None"
                
                if can_trigger:
                    logging.info("Triggering new workflow run...")
                    if trigger_workflow(workflow_id):
                        last_trigger_time = now
                else:
                    logging.info("Skipping trigger due to cool-down period.")
                time.sleep(60)
                continue
                
            run_id = latest_run["id"]
            status["current_workflow_id"] = str(run_id)
            workflow_status = latest_run["status"]
            status["workflow_status"] = workflow_status
            conclusion = latest_run.get("conclusion")
            
            # Update workflow start time
            if latest_run.get("created_at"):
                created_time = datetime.strptime(latest_run["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                status["workflow_start_time"] = format_time(created_time)
            
            logging.info(f"Latest run #{run_id}: Status: {workflow_status}, Conclusion: {conclusion}")
            
            # Check if workflow is completed or failed
            if workflow_status == "completed" or conclusion in ["success", "failure", "cancelled", "timed_out"]:
                logging.info(f"Workflow run #{run_id} is finished (conclusion: {conclusion}).")
                
                if can_trigger:
                    logging.info("Starting new run...")
                    status["next_restart"] = "Immediately (previous workflow completed)"
                    if trigger_workflow(workflow_id):
                        last_trigger_time = now
                else:
                    logging.info("Waiting for cool-down period before starting new run.")
                    status["next_restart"] = f"After cool-down ({min_trigger_interval - (now - last_trigger_time).total_seconds():.0f}s)"
                    
                time.sleep(60)  # Check more frequently during transitions
                
            # If workflow is running, check if it's nearing the timeout
            elif workflow_status == "in_progress":
                runtime = calculate_runtime(latest_run)
                status["workflow_runtime"] = format_duration(runtime)
                hours = runtime / 3600
                
                # Calculate next restart time
                time_left = MAX_RUNTIME - runtime
                next_restart = now + timedelta(seconds=time_left)
                status["next_restart"] = format_time(next_restart)
                
                logging.info(f"Workflow #{run_id} running for {hours:.2f} hours")
                
                # If approaching timeout (5h50m), start a new workflow
                if runtime > MAX_RUNTIME and can_trigger:
                    logging.warning(f"Workflow #{run_id} approaching timeout. Starting new run...")
                    if trigger_workflow(workflow_id):
                        last_trigger_time = now
                    time.sleep(60)
                else:
                    # If not close to timeout, check less frequently
                    check_interval = min(CHECK_INTERVAL, 300)  # Check at most every 5 minutes
                    logging.info(f"Waiting {check_interval/60} minutes before next check...")
                    time.sleep(check_interval)
            
        except Exception as e:
            logging.error(f"Error in monitoring loop: {e}")
            # Use exponential backoff for error cases
            time.sleep(60)

if __name__ == "__main__":
    # Start monitoring
    monitor_and_restart()
