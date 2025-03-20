import os
import time
import requests
import json
import logging
from datetime import datetime, timezone, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/app/logs/monitor.log")
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

# Status file for web interface
STATUS_FILE = "/app/logs/status.json"

# Initialize status
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

def update_status_file():
    """Update the status file for the web interface"""
    try:
        with open(STATUS_FILE, 'w') as f:
            json.dump(status, f)
    except Exception as e:
        logging.error(f"Error updating status file: {e}")

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
    data = {"ref": BRANCH}
    
    retry_count = 0
    while retry_count < MAX_RETRY_ATTEMPTS:
        try:
            response = requests.post(url, headers=get_headers(), data=json.dumps(data))
            response.raise_for_status()
            logging.info("🚀 Successfully triggered workflow!")
            return True
            
        except requests.exceptions.RequestException as e:
            retry_count += 1
            logging.error(f"Error triggering workflow (attempt {retry_count}): {e}")
            if retry_count < MAX_RETRY_ATTEMPTS:
                time.sleep(60)  # Wait 1 minute before retrying
            else:
                logging.error("Failed to trigger workflow after maximum retry attempts")
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
        update_status_file()
        exit(1)
    
    workflow_id = get_workflow_id()
    if not workflow_id:
        logging.error("Could not find the workflow. Please check the workflow name.")
        status["monitoring"] = False
        update_status_file()
        exit(1)
    
    # Initial trigger if no workflow is running
    latest_run = get_latest_run(workflow_id)
    if not latest_run or latest_run["status"] != "in_progress":
        logging.info("No active workflow run found. Triggering initial workflow run...")
        trigger_workflow(workflow_id)
    
    while True:
        try:
            # Update last check time
            now = datetime.now(timezone.utc)
            status["last_check"] = format_time(now)
            
            latest_run = get_latest_run(workflow_id)
            
            if not latest_run:
                logging.warning("No workflow runs found. Triggering new workflow run...")
                status["workflow_status"] = "None Found"
                status["current_workflow_id"] = "None"
                update_status_file()
                
                trigger_workflow(workflow_id)
                time.sleep(120)
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
                logging.info(f"Workflow run #{run_id} is finished (conclusion: {conclusion}). Starting new run...")
                status["next_restart"] = "Immediately (previous workflow completed)"
                update_status_file()
                
                trigger_workflow(workflow_id)
                time.sleep(120)  # Wait before checking again
                
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
                if runtime > MAX_RUNTIME:
                    logging.warning(f"Workflow #{run_id} approaching timeout. Starting new run...")
                    trigger_workflow(workflow_id)
                    time.sleep(120)
            
            # Update status file for web interface
            update_status_file()
            
        except Exception as e:
            logging.error(f"Error in monitoring loop: {e}", exc_info=True)
            time.sleep(60)  # Wait a bit on error
        
        # Wait before next check
        logging.info(f"Waiting {CHECK_INTERVAL/60} minutes before next check...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    # Make sure logs directory exists
    os.makedirs("/app/logs", exist_ok=True)
    
    # Initialize status file
    update_status_file()
    
    # Start monitoring
    monitor_and_restart()
