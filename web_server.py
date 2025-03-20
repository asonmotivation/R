import http.server
import socketserver
import json
import threading
import time
import importlib
import sys
import os
import argparse

# Set up argument parser for port configuration
parser = argparse.ArgumentParser(description='RDP Monitor Web Dashboard')
parser.add_argument('--port', type=int, default=8000, help='Port to run the server on (default: 8000)')
args = parser.parse_args()

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
    <title>RDP Monitor Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
    <style>
        :root {
            --primary: #28a745;
            --primary-dark: #218838;
            --secondary: #17a2b8;
            --secondary-dark: #138496;
            --warning: #ffc107;
            --warning-dark: #e0a800;
            --danger: #dc3545;
            --danger-dark: #c82333;
            --dark: #343a40;
            --darker: #212529;
            --darkest: #111418;
            --light: #adb5bd;
            --lighter: #ced4da;
            --lightest: #e9ecef;
            --border: #495057;
            --text: #f8f9fa;
            --text-muted: #6c757d;
        }
        
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: var(--dark);
            color: var(--text);
        }
        
        .dashboard {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background: linear-gradient(135deg, var(--primary-dark), var(--secondary-dark));
            color: white;
            padding: 20px;
            border-radius: 10px 10px 0 0;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            margin: 0;
            font-size: 24px;
        }
        
        .header .status-pill {
            display: flex;
            align-items: center;
            background: rgba(255, 255, 255, 0.2);
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 14px;
        }
        
        .header .status-pill .dot {
            height: 10px;
            width: 10px;
            background-color: white;
            border-radius: 50%;
            margin-right: 8px;
            position: relative;
        }
        
        .header .status-pill .dot.active {
            background-color: #5fff8f;
            box-shadow: 0 0 0 3px rgba(95, 255, 143, 0.3);
            animation: pulse 1.5s infinite;
        }
        
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(95, 255, 143, 0.7); }
            70% { box-shadow: 0 0 0 5px rgba(95, 255, 143, 0); }
            100% { box-shadow: 0 0 0 0 rgba(95, 255, 143, 0); }
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .card {
            background: var(--darker);
            border-radius: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .card-header {
            padding: 15px 20px;
            border-bottom: 1px solid var(--border);
            font-weight: bold;
            display: flex;
            justify-content: space-between;
            align-items: center;
            background-color: var(--darkest);
        }
        
        .card-content {
            padding: 20px;
        }
        
        .info-grid {
            display: grid;
            grid-template-columns: auto 1fr;
            gap: 10px 15px;
        }
        
        .info-label {
            font-weight: 500;
            color: var(--text-muted);
        }
        
        .info-value {
            font-family: 'Consolas', monospace;
            color: var(--text);
        }
        
        .badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 12px;
            color: white;
            font-weight: 500;
        }
        
        .badge-success { background-color: var(--primary); }
        .badge-warning { background-color: var(--warning); color: #333; }
        .badge-danger { background-color: var(--danger); }
        .badge-info { background-color: var(--secondary); }
        .badge-dark { background-color: var(--dark); }
        
        .rdp-card {
            margin-top: 0;
            background: var(--darker);
            border-radius: 10px;
            overflow: hidden;
        }
        
        .rdp-header {
            background: linear-gradient(135deg, #2c3e50, #4ca1af);
            color: white;
            padding: 15px 20px;
            font-weight: bold;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .rdp-details {
            padding: 20px;
        }
        
        .copy-btn {
            background: rgba(255, 255, 255, 0.2);
            border: none;
            padding: 3px 10px;
            border-radius: 3px;
            cursor: pointer;
            font-size: 12px;
            color: white;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .copy-btn:hover {
            background: rgba(255, 255, 255, 0.3);
        }
        
        .detail-row {
            display: flex;
            margin-bottom: 12px;
            align-items: center;
        }
        
        .detail-label {
            width: 100px;
            font-weight: 500;
            color: var(--text-muted);
        }
        
        .detail-value {
            flex: 1;
            font-family: 'Consolas', monospace;
            background: var(--dark);
            padding: 8px 12px;
            border-radius: 5px;
            border: 1px solid var(--border);
            color: var(--text);
        }
        
        .progress-bar-container {
            height: 8px;
            background-color: var(--border);
            border-radius: 4px;
            margin: 8px 0;
            overflow: hidden;
        }
        
        .progress-bar {
            height: 100%;
            background-color: var(--primary);
            border-radius: 4px;
            transition: width 0.3s ease;
        }
        
        .progress-bar.warning {
            background-color: var(--warning);
        }
        
        .progress-bar.danger {
            background-color: var(--danger);
        }
        
        .timer-row {
            display: flex;
            justify-content: space-between;
            margin-top: 5px;
            font-size: 12px;
            color: var(--text-muted);
        }
        
        .logs {
            margin-top: 0;
            max-height: 200px;
            overflow-y: auto;
            background: var(--darkest);
            padding: 15px;
            border-radius: 5px;
            font-family: 'Consolas', monospace;
            font-size: 12px;
            color: var(--text);
        }
        
        .log-entry {
            margin-bottom: 5px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 5px;
            white-space: pre-wrap;
            word-break: break-all;
        }
        
        .system-card {
            grid-column: span 2;
        }
        
        .stat-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 15px;
        }
        
        .stat-box {
            background: var(--darker);
            border-radius: 5px;
            padding: 15px;
            text-align: center;
            border: 1px solid var(--border);
        }
        
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            margin: 10px 0;
            color: var(--primary);
        }
        
        .stat-label {
            font-size: 12px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .time-remaining {
            text-align: center;
            padding: 15px;
            background: var(--darker);
            border-radius: 5px;
            margin-top: 15px;
        }
        
        .time-value {
            font-size: 36px;
            font-weight: bold;
            margin: 10px 0;
            font-family: 'Consolas', monospace;
            color: var(--primary);
        }
        
        .time-label {
            font-size: 12px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .copy-button {
            background: var(--darkest);
            color: var(--text);
            border: 1px solid var(--border);
            margin-left: 8px;
            cursor: pointer;
        }
        
        .copy-button:hover {
            background: var(--primary-dark);
            color: white;
        }
        
        .log-count {
            font-size: 12px;
            padding: 4px 8px;
            background: var(--darkest);
            border-radius: 12px;
            color: var(--text-muted);
        }
        
        @keyframes pulse {
            0% { opacity: 0.6; }
            50% { opacity: 1; }
            100% { opacity: 0.6; }
        }
        
        .monitor-status {
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }
        
        .status-indicator {
            height: 8px;
            width: 8px;
            border-radius: 50%;
            background-color: var(--primary);
            animation: pulse 1.5s infinite;
        }
        
        .tooltip {
            position: relative;
            display: inline-block;
        }
        
        .tooltip .tooltiptext {
            visibility: hidden;
            width: 140px;
            background-color: var(--darkest);
            color: var(--text);
            text-align: center;
            border-radius: 6px;
            padding: 5px;
            position: absolute;
            z-index: 1;
            bottom: 125%;
            left: 50%;
            margin-left: -70px;
            opacity: 0;
            transition: opacity 0.3s;
            font-size: 12px;
            border: 1px solid var(--border);
        }
        
        .tooltip:hover .tooltiptext {
            visibility: visible;
            opacity: 1;
        }
        
        @media (max-width: 768px) {
            .grid {
                grid-template-columns: 1fr;
            }
            
            .system-card {
                grid-column: span 1;
            }
        }

        #server-time {
            font-size: 14px;
            opacity: 0.8;
            color: var(--text-muted);
        }
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <div>
                <h1>RDP Monitor Dashboard</h1>
                <div id="server-time">Server time: Loading...</div>
            </div>
            <div class="status-pill">
                <div id="monitor-status-dot" class="dot"></div>
                <span id="monitor-status-text">Checking status...</span>
            </div>
        </div>
        
        <div class="grid">
            <!-- Workflow Status Card -->
            <div class="card">
                <div class="card-header">
                    <span><i class="fas fa-cogs"></i> Workflow Status</span>
                    <span id="workflow-status-badge" class="badge badge-info">Checking...</span>
                </div>
                <div class="card-content">
                    <div class="info-grid">
                        <div class="info-label">ID:</div>
                        <div id="workflow-id" class="info-value">Loading...</div>
                        
                        <div class="info-label">Started:</div>
                        <div id="workflow-start" class="info-value">-</div>
                        
                        <div class="info-label">Runtime:</div>
                        <div id="workflow-runtime" class="info-value">-</div>
                        
                        <div class="info-label">Next check:</div>
                        <div id="next-check" class="info-value">-</div>
                        
                        <div class="info-label">Next restart:</div>
                        <div id="next-restart" class="info-value">-</div>
                    </div>
                    
                    <div class="time-remaining">
                        <div class="time-label">Time until restart</div>
                        <div id="runtime-value" class="time-value">-</div>
                        <div class="progress-bar-container">
                            <div id="runtime-progress" class="progress-bar" style="width: 0%"></div>
                        </div>
                        <div class="timer-row">
                            <span>0h</span>
                            <span>6h (Max)</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Server Stats Card -->
            <div class="card">
                <div class="card-header">
                    <span><i class="fas fa-server"></i> System Information</span>
                    <span id="last-check-time">Last check: Never</span>
                </div>
                <div class="card-content">
                    <div class="stat-grid">
                        <div class="stat-box">
                            <div class="stat-label">Status</div>
                            <div id="status-active" class="stat-value"><i class="fas fa-check-circle"></i></div>
                        </div>
                        
                        <div class="stat-box">
                            <div class="stat-label">Uptime</div>
                            <div id="server-uptime" class="stat-value">-</div>
                        </div>
                        
                        <div class="stat-box">
                            <div class="stat-label">API Calls</div>
                            <div id="api-calls" class="stat-value">0</div>
                        </div>
                        
                        <div class="stat-box">
                            <div class="stat-label">Check Interval</div>
                            <div id="check-interval" class="stat-value">5m</div>
                        </div>
                    </div>
                    
                    <div class="info-grid" style="margin-top: 15px;">
                        <div class="info-label">Repository:</div>
                        <div id="repo-info" class="info-value">Loading...</div>
                        
                        <div class="info-label">Workflow:</div>
                        <div id="workflow-name" class="info-value">Loading...</div>
                        
                        <div class="info-label">Branch:</div>
                        <div id="branch-name" class="info-value">Loading...</div>
                    </div>
                </div>
            </div>
            
            <!-- RDP Connection Card -->
            <div class="rdp-card" style="grid-column: span 2;">
                <div class="rdp-header">
                    <span><i class="fas fa-desktop"></i> Remote Desktop Connection</span>
                    <span id="rdp-status" class="badge badge-info">Checking...</span>
                </div>
                <div class="rdp-details">
                    <div class="detail-row">
                        <div class="detail-label">Address:</div>
                        <div class="detail-value" id="rdp-ip">Loading...</div>
                        <button class="copy-btn" onclick="copyToClipboard('rdp-ip')"><i class="fas fa-copy"></i> Copy</button>
                    </div>
                    <div class="detail-row">
                        <div class="detail-label">Username:</div>
                        <div class="detail-value" id="rdp-username">Loading...</div>
                        <button class="copy-btn" onclick="copyToClipboard('rdp-username')"><i class="fas fa-copy"></i> Copy</button>
                    </div>
                    <div class="detail-row">
                        <div class="detail-label">Password:</div>
                        <div class="detail-value" id="rdp-password">Loading...</div>
                        <button class="copy-btn" onclick="copyToClipboard('rdp-password')"><i class="fas fa-copy"></i> Copy</button>
                    </div>
                    
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-top: 15px;">
                        <div class="info-grid">
                            <div class="info-label">Created:</div>
                            <div class="info-value" id="rdp-created">-</div>
                            
                            <div class="info-label">Expires:</div>
                            <div class="info-value" id="rdp-expiry">-</div>
                        </div>
                        
                        <div class="time-remaining">
                            <div class="time-label">RDP Remaining Time</div>
                            <div id="rdp-remaining" class="time-value">-</div>
                            <div class="progress-bar-container">
                                <div id="rdp-progress" class="progress-bar" style="width: 0%"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Logs Card -->
            <div class="card system-card">
                <div class="card-header">
                    <span><i class="fas fa-list"></i> System Logs</span>
                    <span id="log-count" class="badge badge-dark">0 entries</span>
                </div>
                <div class="card-content" style="padding: 0;">
                    <div id="logs" class="logs">
                        <div class="log-entry">System initializing...</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Track stats for display
        let stats = {
            apiCalls: 0,
            startTime: new Date(),
            serverStarted: new Date()
        };
        
        function updateServerTime() {
            const now = new Date();
            document.getElementById('server-time').textContent = 'Server time: ' + now.toLocaleString();
            
            // Update uptime
            const uptimeMinutes = Math.floor((now - stats.serverStarted) / 60000);
            const hours = Math.floor(uptimeMinutes / 60);
            const minutes = uptimeMinutes % 60;
            document.getElementById('server-uptime').textContent = hours + 'h ' + minutes + 'm';
        }
        
        function calculateTimeLeft(expiry) {
            if (!expiry || expiry === '-') return null;
            
            try {
                // Handle different date formats
                let expiryDate;
                if (expiry.includes('UTC')) {
                    expiryDate = new Date(expiry);
                } else {
                    // Try to parse format like "2023-01-01 12:34:56 UTC"
                    const parts = expiry.split(' ');
                    if (parts.length >= 2) {
                        expiryDate = new Date(parts[0] + 'T' + parts[1] + 'Z');
                    } else {
                        return null;
                    }
                }
                
                const now = new Date();
                const timeLeftMs = expiryDate - now;
                
                if (timeLeftMs <= 0) return { hours: 0, minutes: 0, seconds: 0, percent: 100 };
                
                const seconds = Math.floor(timeLeftMs / 1000);
                const minutes = Math.floor(seconds / 60);
                const hours = Math.floor(minutes / 60);
                
                // Calculate percentage for a 6 hour period (21600 seconds)
                const maxSeconds = 21600;
                const remainingPercent = Math.min(100, Math.max(0, (maxSeconds - seconds) / maxSeconds * 100));
                
                return {
                    hours: hours,
                    minutes: minutes % 60,
                    seconds: seconds % 60,
                    percent: remainingPercent
                };
            } catch (e) {
                console.error('Error calculating time left:', e);
                return null;
            }
        }
        
        function formatTimeLeft(timeObj) {
            if (!timeObj) return '-';
            return `${timeObj.hours}h ${timeObj.minutes}m ${timeObj.seconds}s`;
        }
        
        function updateProgressBar(elementId, percent, warningThreshold = 75, dangerThreshold = 90) {
            const progressBar = document.getElementById(elementId);
            progressBar.style.width = `${percent}%`;
            
            // Reset classes
            progressBar.classList.remove('warning', 'danger');
            
            // Apply appropriate class based on thresholds
            if (percent >= dangerThreshold) {
                progressBar.classList.add('danger');
            } else if (percent >= warningThreshold) {
                progressBar.classList.add('warning');
            }
        }
        
        function updateStatus() {
            stats.apiCalls++;
            document.getElementById('api-calls').textContent = stats.apiCalls;
            
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    // Update monitoring status
                    const monitorDot = document.getElementById('monitor-status-dot');
                    const monitorText = document.getElementById('monitor-status-text');
                    
                    if (data.monitoring) {
                        monitorDot.classList.add('active');
                        monitorText.textContent = 'Monitoring Active';
                        document.getElementById('status-active').innerHTML = '<i class="fas fa-check-circle" style="color: var(--primary);"></i>';
                    } else {
                        monitorDot.classList.remove('active');
                        monitorText.textContent = 'Monitoring Inactive';
                        document.getElementById('status-active').innerHTML = '<i class="fas fa-times-circle" style="color: var(--danger);"></i>';
                    }
                    
                    // Update workflow information
                    document.getElementById('workflow-id').textContent = data.current_workflow_id || 'None';
                    document.getElementById('workflow-start').textContent = data.workflow_start_time || 'Not started';
                    document.getElementById('workflow-runtime').textContent = data.workflow_runtime || '-';
                    document.getElementById('next-check').textContent = data.last_check || 'Never';
                    document.getElementById('next-restart').textContent = data.next_restart || 'Not scheduled';
                    document.getElementById('last-check-time').textContent = 'Last check: ' + (data.last_check || 'Never');
                    
                    // Update workflow status badge
                    const workflowBadge = document.getElementById('workflow-status-badge');
                    workflowBadge.textContent = data.workflow_status || 'Unknown';
                    
                    if (data.workflow_status === 'in_progress') {
                        workflowBadge.className = 'badge badge-success';
                    } else if (data.workflow_status === 'queued') {
                        workflowBadge.className = 'badge badge-info';
                    } else if (data.workflow_status === 'completed') {
                        workflowBadge.className = 'badge badge-dark';
                    } else {
                        workflowBadge.className = 'badge badge-warning';
                    }
                    
                    // Update RDP details
                    document.getElementById('rdp-ip').textContent = data.rdp_ip || 'Not available';
                    document.getElementById('rdp-username').textContent = data.rdp_username || 'Not available';
                    document.getElementById('rdp-password').textContent = data.rdp_password || 'Not available';
                    document.getElementById('rdp-created').textContent = data.rdp_created_time || '-';
                    document.getElementById('rdp-expiry').textContent = data.rdp_expiry_time || '-';
                    
                    // Update RDP status
                    const rdpStatus = document.getElementById('rdp-status');
                    if (data.rdp_status === 'active' || (data.rdp_ip && data.rdp_ip !== 'Not available yet' && data.rdp_ip !== '-')) {
                        rdpStatus.textContent = 'Active';
                        rdpStatus.className = 'badge badge-success';
                    } else if (data.rdp_status === 'pending' || data.workflow_status === 'in_progress') {
                        rdpStatus.textContent = 'Pending';
                        rdpStatus.className = 'badge badge-warning';
                    } else {
                        rdpStatus.textContent = 'Inactive';
                        rdpStatus.className = 'badge badge-danger';
                    }
                    
                    // Update time remaining and progress bars
                    if (data.workflow_runtime && data.workflow_status === 'in_progress') {
                        // Extract hours and minutes from format like "5h 30m"
                        const runtimeMatch = data.workflow_runtime.match(/(\d+)h\s+(\d+)m/);
                        if (runtimeMatch) {
                            const hours = parseInt(runtimeMatch[1], 10);
                            const minutes = parseInt(runtimeMatch[2], 10);
                            const totalMinutes = hours * 60 + minutes;
                            const totalSeconds = totalMinutes * 60;
                            
                            // Calculate percentage (assuming 6 hour max = 360 minutes)
                            const maxSeconds = 21600; // 6 hours in seconds
                            const percent = Math.min(100, (totalSeconds / maxSeconds) * 100);
                            
                            // Format for display
                            document.getElementById('runtime-value').textContent = 
                                (6 - hours) + 'h ' + (60 - minutes) % 60 + 'm';
                            
                            // Update progress bar
                            updateProgressBar('runtime-progress', percent);
                        }
                    } else {
                        document.getElementById('runtime-value').textContent = '-';
                        document.getElementById('runtime-progress').style.width = '0%';
                    }
                    
                    // Update RDP time remaining
                    const timeLeft = calculateTimeLeft(data.rdp_expiry_time);
                    if (timeLeft) {
                        document.getElementById('rdp-remaining').textContent = formatTimeLeft(timeLeft);
                        updateProgressBar('rdp-progress', timeLeft.percent);
                    } else {
                        document.getElementById('rdp-remaining').textContent = '-';
                        document.getElementById('rdp-progress').style.width = '0%';
                    }
                    
                    // Update repository info
                    document.getElementById('repo-info').textContent = 
                        (window.REPO_OWNER || '[configured]') + '/' + 
                        (window.REPO_NAME || '[configured]');
                    document.getElementById('workflow-name').textContent = 
                        window.WORKFLOW_NAME || '[configured]';
                    document.getElementById('branch-name').textContent = 
                        window.BRANCH || 'main';
                    document.getElementById('check-interval').textContent = 
                        (window.CHECK_INTERVAL ? Math.floor(window.CHECK_INTERVAL / 60) : 5) + 'm';
                    
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
                        
                        // Auto-scroll to bottom
                        logsContainer.scrollTop = logsContainer.scrollHeight;
                        
                        // Update log count
                        document.getElementById('log-count').textContent = data.logs.length + ' entries';
                    } else {
                        const logEntry = document.createElement('div');
                        logEntry.className = 'log-entry';
                        logEntry.textContent = 'No logs available';
                        logsContainer.appendChild(logEntry);
                        document.getElementById('log-count').textContent = '0 entries';
                    }
                })
                .catch(error => {
                    console.error('Error fetching status:', error);
                    // Update UI to show error state
                    document.getElementById('monitor-status-dot').classList.remove('active');
                    document.getElementById('monitor-status-text').textContent = 'Connection Error';
                });
        }
        
        function copyToClipboard(elementId) {
            const element = document.getElementById(elementId);
            const text = element.textContent;
            
            if (!text || text === 'Loading...' || text === 'Not available') {
                return;
            }
            
            navigator.clipboard.writeText(text).then(() => {
                // Visual feedback
                element.style.backgroundColor = '#e8f5e9';
                setTimeout(() => {
                    element.style.backgroundColor = '#f5f5f5';
                }, 500);
            }).catch(err => {
                console.error('Copy failed:', err);
            });
        }
        
        // Expose configuration for the UI
        window.REPO_OWNER = "${os.environ.get('REPO_OWNER', 'asonmotivation')}";
        window.REPO_NAME = "${os.environ.get('REPO_NAME', 'R')}";
        window.WORKFLOW_NAME = "${os.environ.get('WORKFLOW_NAME', 'Windows 2022')}";
        window.BRANCH = "${os.environ.get('BRANCH', 'main')}";
        window.CHECK_INTERVAL = ${os.environ.get('CHECK_INTERVAL', '300')};
        
        // Initialize
        updateStatus();
        setInterval(updateStatus, 5000);  // Poll every 5 seconds
        
        // Update server time every second
        updateServerTime();
        setInterval(updateServerTime, 1000);
    </script>
</body>
</html>
"""

# Run the server
if __name__ == "__main__":
    PORT = args.port
    Handler = StatusHandler
    
    try:
        print(f"Starting RDP Monitor dashboard on port {PORT}...")
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            print(f"Server running at http://localhost:{PORT}/")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("Server stopped by user")
    except Exception as e:
        print(f"Server error: {e}")
