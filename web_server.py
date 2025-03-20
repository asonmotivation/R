import http.server
import socketserver
import json
import os
import time
import threading
from datetime import datetime

# Global status dictionary to be updated by the monitor script
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

# Function to format time
def format_time(timestamp):
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

# Status file path for communication between monitor and web server
STATUS_FILE = "/app/logs/status.json"

# Log file to read
LOG_FILE = "/app/logs/monitor.log"

# Function to read and update status
def update_status():
    global status
    while True:
        try:
            if os.path.exists(STATUS_FILE):
                with open(STATUS_FILE, 'r') as f:
                    status = json.load(f)
            
            # Read the last few lines from the log
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, 'r') as f:
                    logs = f.readlines()
                    status["logs"] = logs[-20:]  # Get last 20 lines
                    
        except Exception as e:
            print(f"Error updating status: {e}")
        
        time.sleep(5)  # Update every 5 seconds

# Start the status update thread
status_thread = threading.Thread(target=update_status, daemon=True)
status_thread.start()

# HTML template for the web interface
HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RDP Monitor Status</title>
    <style>
        :root {
            --bg-color: #f5f5f5;
            --text-color: #333;
            --header-bg: #4a4a4a;
            --header-text: white;
            --card-bg: white;
            --border-color: #ddd;
            --primary-color: #5D5CDE;
            --success-color: #28a745;
            --warning-color: #ffc107;
            --danger-color: #dc3545;
            --info-color: #17a2b8;
        }
        
        @media (prefers-color-scheme: dark) {
            :root {
                --bg-color: #121212;
                --text-color: #eee;
                --header-bg: #1f1f1f;
                --header-text: #ffffff;
                --card-bg: #1f1f1f;
                --border-color: #333;
                --primary-color: #7676FF;
            }
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 0;
            line-height: 1.6;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            background-color: var(--header-bg);
            color: var(--header-text);
            padding: 20px 0;
            margin-bottom: 30px;
            text-align: center;
        }
        
        h1 {
            margin: 0;
            font-size: 24px;
        }
        
        .status-card {
            background-color: var(--card-bg);
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid var(--border-color);
        }
        
        .status-item {
            margin-bottom: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 8px;
        }
        
        .status-item:last-child {
            border-bottom: none;
            margin-bottom: 0;
        }
        
        .status-label {
            font-weight: 600;
        }
        
        .badge {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
            color: white;
        }
        
        .badge-success {
            background-color: var(--success-color);
        }
        
        .badge-danger {
            background-color: var(--danger-color);
        }
        
        .badge-warning {
            background-color: var(--warning-color);
            color: #333;
        }
        
        .badge-info {
            background-color: var(--info-color);
        }
        
        .badge-primary {
            background-color: var(--primary-color);
        }
        
        .log-container {
            background-color: var(--card-bg);
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            padding: 20px;
            margin-top: 20px;
            border: 1px solid var(--border-color);
            height: 300px;
            overflow-y: auto;
        }
        
        .log-title {
            font-weight: 600;
            margin-bottom: 12px;
        }
        
        #log-entries {
            font-family: monospace;
            font-size: 12px;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        
        footer {
            text-align: center;
            margin-top: 30px;
            padding: 20px 0;
            font-size: 14px;
            color: #666;
        }
    </style>
</head>
<body>
    <header>
        <div class="container">
            <h1>RDP Monitor Status</h1>
        </div>
    </header>
    
    <div class="container">
        <div class="status-card">
            <div class="status-item">
                <span class="status-label">Monitor Service:</span>
                <span id="monitor-status"></span>
            </div>
            <div class="status-item">
                <span class="status-label">Last Check:</span>
                <span id="last-check"></span>
            </div>
            <div class="status-item">
                <span class="status-label">Current Workflow:</span>
                <span id="workflow-id"></span>
            </div>
            <div class="status-item">
                <span class="status-label">Workflow Status:</span>
                <span id="workflow-status"></span>
            </div>
            <div class="status-item">
                <span class="status-label">Start Time:</span>
                <span id="start-time"></span>
            </div>
            <div class="status-item">
                <span class="status-label">Current Runtime:</span>
                <span id="runtime"></span>
            </div>
            <div class="status-item">
                <span class="status-label">Next Restart:</span>
                <span id="next-restart"></span>
            </div>
        </div>
        
        <div class="log-container">
            <div class="log-title">Recent Logs:</div>
            <div id="log-entries"></div>
        </div>
    </div>
    
    <footer>
        <div class="container">
            RDP Monitor Dashboard | Auto-refreshes every 10 seconds
        </div>
    </footer>
    
    <script>
        // Function to update the UI with status data
        function updateStatus() {
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    // Update status badges
                    document.getElementById('monitor-status').innerHTML = 
                        data.monitoring ? 
                        '<span class="badge badge-success">Running</span>' : 
                        '<span class="badge badge-danger">Stopped</span>';
                    
                    document.getElementById('last-check').textContent = data.last_check;
                    document.getElementById('workflow-id').textContent = data.current_workflow_id;
                    
                    // Set workflow status with appropriate badge
                    let statusBadge = '';
                    if (data.workflow_status === 'in_progress') {
                        statusBadge = '<span class="badge badge-primary">In Progress</span>';
                    } else if (data.workflow_status === 'completed') {
                        statusBadge = '<span class="badge badge-success">Completed</span>';
                    } else if (data.workflow_status === 'Unknown') {
                        statusBadge = '<span class="badge badge-warning">Unknown</span>';
                    } else {
                        statusBadge = '<span class="badge badge-info">' + data.workflow_status + '</span>';
                    }
                    document.getElementById('workflow-status').innerHTML = statusBadge;
                    
                    document.getElementById('start-time').textContent = data.workflow_start_time;
                    document.getElementById('runtime').textContent = data.workflow_runtime;
                    document.getElementById('next-restart').textContent = data.next_restart;
                    
                    // Update logs
                    document.getElementById('log-entries').textContent = data.logs.join('');
                    
                    // Auto-scroll logs to bottom
                    const logContainer = document.querySelector('.log-container');
                    logContainer.scrollTop = logContainer.scrollHeight;
                })
                .catch(error => console.error('Error fetching status:', error));
        }
        
        // Update status immediately and then every 10 seconds
        updateStatus();
        setInterval(updateStatus, 10000);
    </script>
</body>
</html>
"""

# Handler class
class StatusHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(status).encode())
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML.encode())

# Start the web server
PORT = 7860
Handler = StatusHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Web server running at port {PORT}")
    httpd.serve_forever()
