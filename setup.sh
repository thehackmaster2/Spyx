#!/bin/bash
# SpyX Installation Script - Educational Purpose Only

echo "========================================="
echo "SpyX Educational Tool - Installation"
echo "FOR LAB USE ONLY"
echo "========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (sudo ./setup.sh)"
    exit 1
fi

# Install dependencies
echo "[*] Installing system dependencies..."
apt-get update
apt-get install -y hostapd dnsmasq php python3 python3-pip iptables wireless-tools

# Install Python packages
echo "[*] Installing Python packages..."
pip3 install -r requirements.txt

# Create directory structure
echo "[*] Creating directory structure..."
mkdir -p spyx/templates
mkdir -p spyx/logs

# Copy files
echo "[*] Copying files..."
# (Files will be created separately)

# Set permissions
chmod +x spyx.py
chmod +x setup.sh

echo "[✓] Installation complete!"
echo "Run: sudo python3 spyx.py"
