#!/usr/bin/env python3
"""
Configuration for SpyX Educational Tool
FOR EDUCATIONAL PURPOSES ONLY - Use only in authorized lab environments
"""

import os
import sys

# Network Configuration
INTERFACE = None  # Will be auto-detected
MONITOR_INTERFACE = None  # Will be created from INTERFACE
AP_INTERFACE = None  # Will use the same interface

# Web Server Configuration
WEB_PORT = 80
HTTPS_PORT = 443
WEB_HOST = '0.0.0.0'

# DHCP Configuration
DHCP_START = '192.168.1.10'
DHCP_END = '192.168.1.50'
DHCP_GATEWAY = '192.168.1.1'
DHCP_NETMASK = '255.255.255.0'

# WiFi Configuration
SSID = None  # Will be set by user
CHANNEL = 6

# Paths
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'templates')
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
CAPTURE_SCRIPT = os.path.join(os.path.dirname(__file__), 'capture.php')

# Colors for terminal output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

# ASCII Banner
BANNER = f"""
{Colors.RED}╔═══════════════════════════════════════════════════════════╗
║                    {Colors.WHITE}SPYX Educational Tool{Colors.RED}                      ║
║              {Colors.YELLOW}Wireless Security Testing Framework{Colors.RED}               ║
║          {Colors.CYAN}FOR AUTHORIZED LAB USE ONLY{Colors.RED}                          ║
╚═══════════════════════════════════════════════════════════╝{Colors.END}
"""

# Warning message
WARNING = f"""
{Colors.YELLOW}{Colors.BOLD}[!] LEGAL NOTICE [!]{Colors.END}
{Colors.WHITE}This tool is for EDUCATIONAL PURPOSES only.
Use ONLY on devices and networks you OWN or have EXPLICIT PERMISSION to test.
Unauthorized use is illegal and unethical.
I understand and will use this only in my authorized lab environment.{Colors.END}
"""
