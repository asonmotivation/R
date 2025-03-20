import os
import time
import requests
import json
import logging
import sys
import re
from datetime import datetime, timezone, timedelta

# Set up detailed logging to stdout
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
BRANCH = os.environ.get("BRANCH", "main")  # Default branch

# Time constants
CHECK_INTERVAL = int(os.environ.get("CHECK_INTERVAL", "300"))  # 5 minutes
MAX_RUNTIME = int(os.environ.get("MAX_RUNTIME", "21000"))  # 5h50m in seconds
MAX_RETRY_ATTEMPTS = 3  # Maximum retry attempts for API calls

# Keep a circular buffer of the last 100 log messages
log_buffer = []
MAX_LOG_ENTRIES = 100

# Status variables (in-memory only, no file writes)
status = {
    "monitoring": True,
    "last_check": "Never",
    "current_workflow_id": "None",
    "workflow_status": "Unknown",
    "workflow_start_time": "Unknown",
    "workflow_runtime": "0 hours",
    "next_restart": "Unknown",
    "logs": [],
    # RDP specific information
    "rdp_ip": "Not available yet",
    "rdp_username": "Not available yet",
    "rdp_password": "Not available yet",
    "rdp_created_time": "Not available yet",
    "rdp_expiry_time": "Not available yet",
    "rdp_remaining_time": "Calculating...",
    "rdp_status": "Not created yet"
}

# Custom logger that also stores messages for web display
class BufferedHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        formatted_msg = f"{timestamp} - {msg}"
        
        # Add to our private log buffer
        log_buffer.append(formatted_msg)
        if len(log_buffer) > MAX_LOG_ENTRIES:
            log_buffer.pop(0)
        
        # Update status with latest logs for display
        status["logs"] = log_buffer.copy()

# Add our custom handler to the root logger
logger = logging.getLogger()
formatter = logging.Formatter('%(levelname)s - %(message)s')
buffered_handler = BufferedHandler()
buffered_handler.setFormatter(formatter)
logger.addHandler(buffered_handler)

def get_headers():
    """Get proper headers for GitHub API calls"""
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

def get_workflow_id():
    """Get the workflow ID for the Windows workflow"""
    logging.info(f"[PRIVATE] Finding workflow ID for '{WORKFLOW_NAME}'")
    
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows"
    retry_count = 0
    
    while retry_count < MAX_RETRY_ATTEMPTS:
        try:
            logging.info(f"[PRIVATE] Making API request to: {url}")
            response = requests.get(url, headers=get_headers())
            response.raise_for_status()
            workflows = response.json().get("workflows", [])
            
            logging.info(f"[PRIVATE] Found {len(workflows)} workflows in total")
            
            for workflow in workflows:
                if workflow.get("name") == WORKFLOW_NAME:
                    workflow_id = workflow.get("id")
                    logging.info(f"[PRIVATE] Found workflow ID: {workflow_id} for name: {WORKFLOW_NAME}")
                    return workflow_id
                    
            # If we didn't find by name, try finding by filename
            logging.warning(f"[PRIVATE] Could not find workflow by name '{WORKFLOW_NAME}', trying by filename")
            for workflow in workflows:
                if workflow.get("path", "").endswith("win2022.yml"):
                    workflow_id = workflow.get("id")
                    logging.info(f"[PRIVATE] Found workflow ID by filename: {workflow_id}")
                    return workflow_id
            
            logging.error(f"[PRIVATE] Could not find workflow with name '{WORKFLOW_NAME}' or appropriate filename")
            
            # Print all available workflows for debugging
            logging.info("[PRIVATE] Available workflows:")
            for workflow in workflows:
                logging.info(f"[PRIVATE]   - {workflow.get('name')} (path: {workflow.get('path')})")
                
            return None
            
        except requests.exceptions.RequestException as e:
            retry_count += 1
            logging.error(f"[PRIVATE] Error fetching workflows (attempt {retry_count}): {e}")
            if retry_count < MAX_RETRY_ATTEMPTS:
                wait_time = 60 * retry_count  # Exponential backoff
                logging.info(f"[PRIVATE] Waiting {wait_time} seconds before retry")
                time.sleep(wait_time)
            else:
                logging.error("[PRIVATE] Max retry attempts reached")
                return None

def get_latest_run(workflow_id):
    """Get the latest workflow run"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/{workflow_id}/runs"
    retry_count = 0
    
    while retry_count < MAX_RETRY_ATTEMPTS:
        try:
            logging.info(f"[PRIVATE] Checking latest run for workflow ID: {workflow_id}")
            response = requests.get(url, headers=get_headers())
            response.raise_for_status()
            runs = response.json().get("workflow_runs", [])
            
            if runs:
                latest_run = runs[0]
                run_id = latest_run.get("id")
                status = latest_run.get("status")
                conclusion = latest_run.get("conclusion")
                created_at = latest_run.get("created_at")
                
                logging.info(f"[PRIVATE] Latest run: #{run_id}, Status: {status}, Conclusion: {conclusion}, Created: {created_at}")
                return latest_run
            
            logging.warning(f"[PRIVATE] No workflow runs found for workflow ID: {workflow_id}")
            return None
            
        except requests.exceptions.RequestException as e:
            retry_count += 1
            logging.error(f"[PRIVATE] Error fetching workflow runs (attempt {retry_count}): {e}")
            if retry_count < MAX_RETRY_ATTEMPTS:
                wait_time = 60 * retry_count  # Exponential backoff
                logging.info(f"[PRIVATE] Waiting {wait_time} seconds before retry")
                time.sleep(wait_time)
            else:
                logging.error("[PRIVATE] Max retry attempts reached")
                return None

def trigger_workflow(workflow_id):
    """Trigger the workflow using the workflow_dispatch event"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/{workflow_id}/dispatches"
    
    # Make sure we're using the correct branch name and payload format
    data = {
        "ref": BRANCH,
        "inputs": {}
    }
    
    retry_count = 0
    while retry_count < MAX_RETRY_ATTEMPTS:
        try:
            logging.info(f"[PRIVATE] Triggering workflow {workflow_id} with branch: {BRANCH}")
            logging.debug(f"[PRIVATE] Payload: {json.dumps(data)}")
            
            response = requests.post(url, headers=get_headers(), data=json.dumps(data))
            
            if response.status_code == 204:  # Success for this API returns 204 No Content
                logging.info(f"[PRIVATE] Successfully triggered workflow! Status code: {response.status_code}")
                return True
                
            # If not 204, log the error details
            logging.error(f"[PRIVATE] Error response: {response.status_code} - {response.text}")
            logging.error(f"[PRIVATE] Request headers (sanitized): {get_headers()}")
            logging.error(f"[PRIVATE] Request data: {json.dumps(data)}")
            
            # Check specific errors
            if response.status_code == 401:
                logging.error("[PRIVATE] Authentication error - check GITHUB_TOKEN")
            elif response.status_code == 403:
                logging.error("[PRIVATE] Authorization error - token may not have enough permissions")
            elif response.status_code == 404:
                logging.error("[PRIVATE] Resource not found - check REPO_OWNER, REPO_NAME and workflow_id")
            elif response.status_code == 422:
                logging.error("[PRIVATE] Validation error - check 'ref' parameter, it might be incorrect")
                
            response.raise_for_status()
            
        except requests.exceptions.RequestException as e:
            retry_count += 1
            logging.error(f"[PRIVATE] Error triggering workflow (attempt {retry_count}): {e}")
            if retry_count < MAX_RETRY_ATTEMPTS:
                wait_time = 60 * retry_count  # Exponential backoff
                logging.info(f"[PRIVATE] Waiting {wait_time} seconds before retry")
                time.sleep(wait_time)
            else:
                logging.error("[PRIVATE] Failed to trigger workflow after maximum retry attempts")
                return False

def extract_rdp_details(workflow_id, run_id):
    """Extract RDP connection details from the workflow logs"""
    global status
    
    logging.info(f"[PRIVATE] Attempting to extract RDP details from workflow #{run_id}")
    
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/runs/{run_id}/logs"
    retry_count = 0
    
    while retry_count < MAX_RETRY_ATTEMPTS:
        try:
            # First try to get the download URL for logs
            logging.info(f"[PRIVATE] Requesting logs URL for run #{run_id}")
            response = requests.get(url, headers=get_headers(), stream=True)
            
            if response.status_code == 302:  # GitHub redirects to the actual log file
                log_url = response.headers.get('Location')
                logging.info(f"[PRIVATE] Got redirect to logs at: {log_url}")
                
                if log_url:
                    logging.info(f"[PRIVATE] Downloading logs from: {log_url}")
                    log_response = requests.get(log_url)
                    logs = log_response.text
                    
                    # Save a snippet of logs for debugging (first 100 chars)
                    log_snippet = logs[:100].replace('\n', ' ') if logs else "No logs found"
                    logging.info(f"[PRIVATE] Log snippet: {log_snippet}...")
                    
                    # Extract connection info using regex patterns
                    # IP pattern (look for IP addresses)
                    ip_match = re.search(r'(RDP Address|IP): (\d+\.\d+\.\d+\.\d+:\d+|\d+\.\d+\.\d+\.\d+)', logs)
                    if ip_match:
                        status["rdp_ip"] = ip_match.group(2)
                        logging.info(f"[PRIVATE] Found RDP IP: {status['rdp_ip']}")
                    else:
                        logging.warning(f"[PRIVATE] Could not find RDP IP in logs")
                    
                    # Username pattern
                    user_match = re.search(r'(Username|User): ([a-zA-Z0-9]+)', logs)
                    if user_match:
                        status["rdp_username"] = user_match.group(2)
                        logging.info(f"[PRIVATE] Found RDP Username: {status['rdp_username']}")
                    else:
                        logging.warning(f"[PRIVATE] Could not find RDP Username in logs")
                    
                    # Password pattern
                    pass_match = re.search(r'(Password|Pass): ([a-zA-Z0-9]+)', logs)
                    if pass_match:
                        status["rdp_password"] = pass_match.group(2)
                        logging.info(f"[PRIVATE] Found RDP Password: {status['rdp_password']}")
                    else:
                        logging.warning(f"[PRIVATE] Could not find RDP Password in logs")
                    
                    # Set RDP status based on what we found
                    if status["rdp_ip"] != "Not available yet":
                        status["rdp_status"] = "Running"
                        logging.info(f"[PRIVATE] RDP is now running with IP: {status['rdp_ip']}")
                        
                        # Calculate RDP created time and expiry time
                        if status["workflow_start_time"] != "Unknown":
                            created_time = datetime.strptime(status["workflow_start_time"], "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=timezone.utc)
                            status["rdp_created_time"] = format_time(created_time)
                            
                            # RDP expires after 6 hours from workflow start
                            expiry_time = created_time + timedelta(hours=6)
                            status["rdp_expiry_time"] = format_time(expiry_time)
                            
                            # Calculate remaining time
                            now = datetime.now(timezone.utc)
                            if now < expiry_time:
                                remaining_seconds = (expiry_time - now).total_seconds()
                                hours = int(remaining_seconds // 3600)
                                minutes = int((remaining_seconds % 3600) // 60)
                                status["rdp_remaining_time"] = f"{hours}h {minutes}m"
                                logging.info(f"[PRIVATE] RDP remaining time: {status['rdp_remaining_time']}")
                            else:
                                status["rdp_remaining_time"] = "Expired"
                                status["rdp_status"] = "Expired"
                                logging.warning(f"[PRIVATE] RDP session has expired")
                    
                    return True
                    
            else:
                logging.error(f"[PRIVATE] Failed to get logs URL: {response.status_code} - {response.text}")
                
            return False
            
        except Exception as e:
            retry_count += 1
            logging.error(f"[PRIVATE] Error extracting RDP details (attempt {retry_count}): {e}")
            if retry_count < MAX_RETRY_ATTEMPTS:
                wait_time = 60 * retry_count  # Exponential backoff
                logging.info(f"[PRIVATE] Waiting {wait_time} seconds before retry")
                time.sleep(wait_time)
            else:
                logging.error("[PRIVATE] Max retry attempts reached for extracting RDP details")
                return False

def calculate_runtime(run):
    """Calculate how long a workflow has been running in seconds"""
    if not run.get("updated_at"):
        logging.debug("[PRIVATE] Cannot calculate runtime - no updated_at timestamp")
        return 0
        
    updated_time = datetime.strptime(run["updated_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    runtime = (now - updated_time).total_seconds()
    logging.debug(f"[PRIVATE] Calculated runtime: {runtime} seconds")
    return runtime

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
    
    logging.info("[PRIVATE] 🔍 Starting workflow monitor")
    
    if not GITHUB_TOKEN:
        logging.error("[PRIVATE] GITHUB_TOKEN environment variable not set! Exiting.")
        status["monitoring"] = False
        logging.error("GitHub token not set. Check your configuration.")
        exit(1)
    
    workflow_id = get_workflow_id()
    if not workflow_id:
        logging.error("[PRIVATE] Could not find the workflow. Please check the workflow name and repository.")
        status["monitoring"] = False
        logging.error("Workflow not found. Check configuration and permissions.")
        exit(1)
    
    # Track the last time we triggered a workflow to avoid spamming
    last_trigger_time = None
    min_trigger_interval = 300  # 5 minutes minimum between trigger attempts
    
    # Initial trigger if no workflow is running
    latest_run = get_latest_run(workflow_id)
    if not latest_run or latest_run["status"] != "in_progress":
        logging.info("[PRIVATE] No active workflow run found. Triggering initial workflow run...")
        if trigger_workflow(workflow_id):
            last_trigger_time = datetime.now(timezone.utc)
            logging.info("[PRIVATE] Initial workflow triggered successfully!")
        else:
            logging.error("[PRIVATE] Failed to trigger initial workflow")
    
    while True:
        try:
            # Update last check time
            now = datetime.now(timezone.utc)
            status["last_check"] = format_time(now)
            logging.debug(f"[PRIVATE] Current check time: {status['last_check']}")
            
            # Check if we can trigger a new workflow (anti-spam)
            can_trigger = True
            if last_trigger_time:
                seconds_since_last_trigger = (now - last_trigger_time).total_seconds()
                if seconds_since_last_trigger < min_trigger_interval:
                    can_trigger = False
                    logging.info(f"[PRIVATE] Cooling down. {min_trigger_interval - seconds_since_last_trigger:.0f} seconds until next possible trigger.")
            
            latest_run = get_latest_run(workflow_id)
            
            if not latest_run:
                logging.warning("[PRIVATE] No workflow runs found. This might indicate an issue with the repository or permissions.")
                status["workflow_status"] = "None Found"
                status["current_workflow_id"] = "None"
                
                if can_trigger:
                    logging.info("[PRIVATE] Attempting to trigger new workflow run...")
                    if trigger_workflow(workflow_id):
                        last_trigger_time = now
                        logging.info("[PRIVATE] New workflow triggered successfully!")
                    else:
                        logging.error("[PRIVATE] Failed to trigger new workflow")
                else:
                    logging.info("[PRIVATE] Skipping trigger due to cool-down period.")
                time.sleep(60)
                continue
                
            run_id = latest_run["id"]
            status["current_workflow_id"] = str(run_id)
            workflow_status = latest_run["status"]
            status["workflow_status"] = workflow_status
            conclusion = latest_run.get("conclusion")
            
            logging.info(f"[PRIVATE] Latest run #{run_id}: Status: {workflow_status}, Conclusion: {conclusion}")
            
            # Update workflow start time
            if latest_run.get("created_at"):
                created_time = datetime.strptime(latest_run["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                status["workflow_start_time"] = format_time(created_time)
                logging.info(f"[PRIVATE] Workflow start time: {status['workflow_start_time']}")
            
            # Check if workflow is completed or failed
            if workflow_status == "completed" or conclusion in ["success", "failure", "cancelled", "timed_out"]:
                logging.info(f"[PRIVATE] Workflow run #{run_id} is finished with conclusion: {conclusion}.")
                
                if can_trigger:
                    logging.info("[PRIVATE] Starting new run since previous workflow is complete...")
                    status["next_restart"] = "Immediately (previous workflow completed)"
                    if trigger_workflow(workflow_id):
                        last_trigger_time = now
                        logging.info("[PRIVATE] New workflow triggered successfully!")
                    else:
                        logging.error("[PRIVATE] Failed to trigger new workflow")
                else:
                    logging.info("[PRIVATE] Waiting for cool-down period before starting new run.")
                    status["next_restart"] = f"After cool-down ({min_trigger_interval - (now - last_trigger_time).total_seconds():.0f}s)"
                    
                time.sleep(60)  # Check more frequently during transitions
                
            # If workflow is running, check if it's nearing the timeout
            elif workflow_status == "in_progress":
                runtime = calculate_runtime(latest_run)
                status["workflow_runtime"] = format_duration(runtime)
                hours = runtime / 3600
                
                logging.info(f"[PRIVATE] Workflow #{run_id} running for {hours:.2f} hours ({runtime:.0f} seconds)")
                
                # Calculate next restart time
                time_left = MAX_RUNTIME - runtime
                next_restart = now + timedelta(seconds=time_left)
                status["next_restart"] = format_time(next_restart)
                
                logging.info(f"[PRIVATE] Time left until restart: {time_left:.0f} seconds, scheduled for {status['next_restart']}")
                
                # If approaching timeout (5h50m), start a new workflow
                if runtime > MAX_RUNTIME and can_trigger:
                    logging.warning(f"[PRIVATE] Workflow #{run_id} approaching timeout after {hours:.2f} hours. Starting new run...")
                    if trigger_workflow(workflow_id):
                        last_trigger_time = now
                        logging.info("[PRIVATE] New workflow triggered successfully!")
                    else:
                        logging.error("[PRIVATE] Failed to trigger new workflow")
                    time.sleep(60)
                else:
                    # If not close to timeout, check less frequently
                    check_interval = min(CHECK_INTERVAL, 300)  # Check at most every 5 minutes
                    logging.info(f"[PRIVATE] Waiting {check_interval/60} minutes before next check...")
                    
                    # Try to extract RDP details if they're not yet available
                    if status["rdp_ip"] == "Not available yet" or status["rdp_username"] == "Not available yet":
                        logging.info("[PRIVATE] RDP details not yet available, attempting to extract them...")
                        extract_rdp_details(workflow_id, run_id)
                    else:
                        # Periodically refresh RDP details to ensure they're current
                        if runtime > 300 and runtime % 900 < 60:  # Check every 15 minutes (900 seconds)
                            logging.info("[PRIVATE] Refreshing RDP connection details...")
                            extract_rdp_details(workflow_id, run_id)
                    
                    time.sleep(check_interval)
            
        except Exception as e:
            logging.error(f"[PRIVATE] Error in monitoring loop: {e}")
            import traceback
            logging.error(f"[PRIVATE] Full exception: {traceback.format_exc()}")
            
            # Use exponential backoff for error cases
            time.sleep(60)

if __name__ == "__main__":
    logging.info("[PRIVATE] Starting RDP Monitor Service")
    try:
        # Start monitoring
        monitor_and_restart()
    except KeyboardInterrupt:
        logging.info("[PRIVATE] Monitor service stopped by user.")
    except Exception as e:
        logging.error(f"[PRIVATE] Fatal error in monitor service: {e}")
        import traceback
        logging.error(f"[PRIVATE] Full exception: {traceback.format_exc()}")
        status["monitoring"] = False
