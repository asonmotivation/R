import http.server
import socketserver
import json
import threading
import time
import importlib
import sys
import os

# Import monitor module directly
try:
    import monitor
    status = monitor.status
except ImportError:
    # Create a dummy status if monitor not available
    status = {
        "monitoring": False,
        "last_check": "Never",
        "current_workflow_id": "None",
        "workflow_status": "Not running",
        "workflow_start_time": "-",
        "workflow_runtime": "-",
        "next_restart": "-",
        "logs": ["Web server started"],
        "rdp_ip": "-",
        "rdp_username": "-",
        "rdp_password": "-",
        "rdp_created_time": "-",
        "rdp_expiry_time": "-",
        "rdp_remaining_time": "-",
        "rdp_status": "-"
    }

# Handler class
class StatusHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/status':
            try:
                importlib.reload(sys.modules['monitor'])
            except Exception as e:
                print(f"Error reloading monitor: {e}")
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(status).encode())
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML.encode())

# Simple HTML template
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Status</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }
        .status-item {
            margin-bottom: 8px;
            display: flex;
        }
        .status-label {
            font-weight: bold;
            width: 200px;
        }
        .value {
            flex: 1;
        }
        .badge {
            display: inline-block;
            padding: 3px 7px;
            border-radius: 3px;
            font-size: 12px;
            color: white;
        }
        .badge-success { background-color: #28a745; }
        .badge-warning { background-color: #ffc107; color: #333; }
        .badge-danger { background-color: #dc3545; }
        .badge-info { background-color: #17a2b8; }
        
        .rdp-card {
            margin-top: 20px;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
        }
        .rdp-title {
            font-weight: bold;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .rdp-details {
            margin-top: 15px;
        }
        .copy-btn {
            background: #eee;
            border: none;
            padding: 2px 8px;
            border-radius: 3px;
            cursor: pointer;
            font-size: 12px;
            margin-left: 5px;
        }
        .copy-btn:hover {
            background: #ddd;
        }
        .detail-row {
            display: flex;
            margin-bottom: 8px;
            align-items: center;
        }
        .detail-label {
            width: 100px;
            font-weight: bold;
        }
        .detail-value {
            flex: 1;
            font-family: monospace;
            background: #f5f5f5;
            padding: 3px 6px;
            border-radius: 3px;
        }
        
        .logs {
            margin-top: 20px;
            max-height: 200px;
            overflow-y: auto;
            background: #f5f5f5;
            padding: 10px;
            border-radius: 3px;
            font-family: monospace;
            font-size: 12px;
        }
        
        .log-entry {
            margin-bottom: 5px;
            border-bottom: 1px solid #eee;
            padding-bottom: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Monitor Status</h1>
        
        <div class="rdp-card">
            <div class="rdp-title">
                <span>Remote Desktop Connection</span>
                <span id="rdp-status" class="badge badge-info">Checking...</span>
            </div>
            <div class="rdp-details">
                <div class="detail-row">
                    <div class="detail-label">Address:</div>
                    <div class="detail-value" id="rdp-ip">Loading...</div>
                    <button class="copy-btn" onclick="copyToClipboard('rdp-ip')">Copy</button>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Username:</div>
                    <div class="detail-value" id="rdp-username">Loading...</div>
                    <button class="copy-btn" onclick="copyToClipboard('rdp-username')">Copy</button>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Password:</div>
                    <div class="detail-value" id="rdp-password">Loading...</div>
                    <button class="copy-btn" onclick="copyToClipboard('rdp-password')">Copy</button>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Created:</div>
                    <div class="detail-value" id="rdp-created">-</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Expires:</div>
                    <div class="detail-value" id="rdp-expiry">-</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Remaining:</div>
                    <div class="detail-value" id="rdp-remaining">-</div>
                </div>
            </div>
        </div>
        
        <h3>Workflow Status</h3>
        <div id="status-container">
            <div class="status-item">
                <div class="status-label">Workflow Status:</div>
                <div class="value" id="workflow-status">Loading...</div>
            </div>
            <div class="status-item">
                <div class="status-label">Current Workflow ID:</div>
                <div class="value" id="current-workflow-id">Loading...</div>
            </div>
            <div class="status-item">
                <div class="status-label">Start Time:</div>
                <div class="value" id="workflow-start-time">Loading...</div>
            </div>
            <div class="status-item">
                <div class="status-label">Running For:</div>
                <div class="value" id="workflow-runtime">Loading...</div>
            </div>
            <div class="status-item">
                <div class="status-label">Next Restart:</div>
                <div class="value" id="next-restart">Loading...</div>
            </div>
            <div class="status-item">
                <div class="status-label">Last Check:</div>
                <div class="value" id="last-check">Loading...</div>
            </div>
        </div>
        
        <h3>Logs</h3>
        <div class="logs" id="logs">
            <div class="log-entry">Loading logs...</div>
        </div>
    </div>

    <script>
        function updateStatus() {
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('last-check').textContent = data.last_check;
                    document.getElementById('current-workflow-id').textContent = data.current_workflow_id;
                    document.getElementById('workflow-status').textContent = data.workflow_status;
                    document.getElementById('workflow-start-time').textContent = data.workflow_start_time;
                    document.getElementById('workflow-runtime').textContent = data.workflow_runtime;
                    document.getElementById('next-restart').textContent = data.next_restart;
                    
                    // RDP details
                    document.getElementById('rdp-ip').textContent = data.rdp_ip;
                    document.getElementById('rdp-username').textContent = data.rdp_username;
                    document.getElementById('rdp-password').textContent = data.rdp_password;
                    document.getElementById('rdp-created').textContent = data.rdp_created_time;
                    document.getElementById('rdp-expiry').textContent = data.rdp_expiry_time;
                    document.getElementById('rdp-remaining').textContent = data.rdp_remaining_time;
                    
                    // RDP status badge
                    const rdpStatus = document.getElementById('rdp-status');
                    if (data.rdp_status === 'Running') {
                        rdpStatus.textContent = 'Active';
                        rdpStatus.className = 'badge badge-success';
                    } else if (data.rdp_status === 'Expired') {
                        rdpStatus.textContent = 'Expired';
                        rdpStatus.className = 'badge badge-danger';
                    } else if (data.rdp_status === 'Not created yet') {
                        rdpStatus.textContent = 'Starting';
                        rdpStatus.className = 'badge badge-warning';
                    } else {
                        rdpStatus.textContent = data.rdp_status;
                        rdpStatus.className = 'badge badge-info';
                    }
                    
                    // Update logs
                    const logsContainer = document.getElementById('logs');
                    logsContainer.innerHTML = '';
                    
                    if (data.logs && data.logs.length > 0) {
                        data.logs.forEach(log => {
                            const logEntry = document.createElement('div');
                            logEntry.className = 'log-entry';
                            logEntry.textContent = log;
                            logsContainer.appendChild(logEntry);
                        });
                    } else {
                        logsContainer.innerHTML = '<div class="log-entry">No logs available</div>';
                    }
                    
                    // Scroll logs to bottom
                    logsContainer.scrollTop = logsContainer.scrollHeight;
                })
                .catch(error => {
                    console.error('Error fetching status:', error);
                });
        }
        
        function copyToClipboard(elementId) {
            const element = document.getElementById(elementId);
            const text = element.textContent;
            
            navigator.clipboard.writeText(text).then(
                function() {
                    // Flash effect to show copied
                    element.style.backgroundColor = '#d4edda';
                    setTimeout(() => {
                        element.style.backgroundColor = '';
                    }, 500);
                }, 
                function() {
                    console.error('Failed to copy');
                    // Fallback copy method
                    const textArea = document.createElement('textarea');
                    textArea.value = text;
                    document.body.appendChild(textArea);
                    textArea.select();
                    document.execCommand('copy');
                    document.body.removeChild(textArea);
                    
                    element.style.backgroundColor = '#d4edda';
                    setTimeout(() => {
                        element.style.backgroundColor = '';
                    }, 500);
                }
            );
        }
        
        // Initial update
        updateStatus();
        
        // Update every 5 seconds
        setInterval(updateStatus, 5000);
    </script>
</body>
</html>
"""

# Run the server
if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 7860))
    Handler = StatusHandler
    
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"Web server running at port {PORT}")
            httpd.serve_forever()
    except Exception as e:
        print(f"Error starting web server: {e}")
