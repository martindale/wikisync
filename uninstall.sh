#!/bin/bash

# WikiSync Uninstall Script
# Removes Wikipedia synchronization tool from the system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/wikipedia"
SERVICE_NAME="wikisync"

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Stop and disable service
stop_service() {
    print_status "Stopping and disabling service..."
    
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        systemctl stop "$SERVICE_NAME"
    fi
    
    if systemctl is-enabled --quiet "$SERVICE_NAME"; then
        systemctl disable "$SERVICE_NAME"
    fi
}

# Remove systemd service
remove_service() {
    print_status "Removing systemd service..."
    
    if [ -f "/etc/systemd/system/$SERVICE_NAME.service" ]; then
        rm -f "/etc/systemd/system/$SERVICE_NAME.service"
        systemctl daemon-reload
    fi
}

# Remove log rotation
remove_log_rotation() {
    print_status "Removing log rotation configuration..."
    
    if [ -f "/etc/logrotate.d/$SERVICE_NAME" ]; then
        rm -f "/etc/logrotate.d/$SERVICE_NAME"
    fi
}

# Remove installation directory
remove_installation() {
    print_status "Removing installation directory..."
    
    if [ -d "$INSTALL_DIR" ]; then
        read -p "Remove all downloaded Wikipedia data? This will free up disk space. (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$INSTALL_DIR"
            print_status "Installation directory removed"
        else
            print_warning "Installation directory preserved at $INSTALL_DIR"
        fi
    fi
}

# Remove system user
remove_user() {
    print_status "Removing system user..."
    
    if id "wikisync" &>/dev/null; then
        userdel wikisync 2>/dev/null || true
    fi
}

# Main uninstall function
main() {
    echo "WikiSync Uninstall Script"
    echo "========================"
    echo
    
    check_root
    
    stop_service
    remove_service
    remove_log_rotation
    remove_installation
    remove_user
    
    echo
    print_status "Uninstallation completed!"
    echo
    echo "Note: If you chose to preserve the installation directory,"
    echo "you can manually remove it later with: sudo rm -rf $INSTALL_DIR"
}

# Run main function
main "$@" 