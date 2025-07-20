#!/bin/bash

# WikiSync Installation Script
# Installs Wikipedia synchronization tool as a Linux service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/wikipedia"
SERVICE_NAME="wikisync"
PYTHON_VERSION="3.8"

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

# Check Python version
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.8 or higher."
        exit 1
    fi
    
    PYTHON_VERSION_CHECK=$(python3 -c "import sys; print('{}.{}'.format(sys.version_info.major, sys.version_info.minor))")
    REQUIRED_VERSION=$(echo $PYTHON_VERSION | cut -d. -f1,2)
    
    if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION_CHECK" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
        print_error "Python version $PYTHON_VERSION_CHECK is too old. Required: $PYTHON_VERSION or higher"
        exit 1
    fi
    
    print_status "Python version check passed: $PYTHON_VERSION_CHECK"
}

# Check disk space
check_disk_space() {
    local required_space=50  # GB
    local available_space=$(df -BG /opt | awk 'NR==2 {print $4}' | sed 's/G//')
    
    if [ "$available_space" -lt "$required_space" ]; then
        print_warning "Low disk space: ${available_space}GB available, ${required_space}GB recommended"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Create installation directory
create_directories() {
    print_status "Creating installation directories..."
    
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$INSTALL_DIR/data"
    mkdir -p "$INSTALL_DIR/temp"
    mkdir -p "$INSTALL_DIR/logs"
    
    # Set permissions
    chown -R root:root "$INSTALL_DIR"
    chmod 755 "$INSTALL_DIR"
    chmod 755 "$INSTALL_DIR/data"
    chmod 755 "$INSTALL_DIR/temp"
    chmod 755 "$INSTALL_DIR/logs"
}

# Copy files
copy_files() {
    print_status "Copying files to installation directory..."
    
    # Copy main script
    cp wikisync.py "$INSTALL_DIR/"
    chmod +x "$INSTALL_DIR/wikisync.py"
    
    # Copy configuration
    if [ -f "config.yaml" ]; then
        cp config.yaml "$INSTALL_DIR/"
    else
        print_warning "config.yaml not found, will be created on first run"
    fi
    
    # Copy requirements
    if [ -f "requirements.txt" ]; then
        cp requirements.txt "$INSTALL_DIR/"
    fi
    
    # Copy README
    if [ -f "README.md" ]; then
        cp README.md "$INSTALL_DIR/"
    fi
}

# Install Python dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."
    
    if [ -f "$INSTALL_DIR/requirements.txt" ]; then
        pip3 install -r "$INSTALL_DIR/requirements.txt"
    else
        # Install minimal dependencies if requirements.txt is not available
        pip3 install requests PyYAML lxml beautifulsoup4 tqdm psutil schedule python-dateutil
    fi
}

# Install systemd service
install_service() {
    print_status "Installing systemd service..."
    
    # Copy service file
    if [ -f "systemd/wikisync.service" ]; then
        cp systemd/wikisync.service "/etc/systemd/system/"
    else
        print_error "Service file not found: systemd/wikisync.service"
        exit 1
    fi
    
    # Reload systemd
    systemctl daemon-reload
    
    # Enable service
    systemctl enable "$SERVICE_NAME"
    
    print_status "Service installed and enabled"
}

# Create system user (optional)
create_user() {
    if ! id "wikisync" &>/dev/null; then
        print_status "Creating wikisync user..."
        useradd -r -s /bin/false -d "$INSTALL_DIR" wikisync
        chown -R wikisync:wikisync "$INSTALL_DIR"
    else
        print_status "wikisync user already exists"
    fi
}

# Setup log rotation
setup_log_rotation() {
    print_status "Setting up log rotation..."
    
    cat > /etc/logrotate.d/wikisync << EOF
$INSTALL_DIR/logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 root root
    postrotate
        systemctl reload $SERVICE_NAME > /dev/null 2>&1 || true
    endscript
}
EOF
}

# Display installation summary
show_summary() {
    echo
    print_status "Installation completed successfully!"
    echo
    echo "Installation directory: $INSTALL_DIR"
    echo "Service name: $SERVICE_NAME"
    echo
    echo "Next steps:"
    echo "1. Edit configuration: sudo nano $INSTALL_DIR/config.yaml"
    echo "2. Start the service: sudo systemctl start $SERVICE_NAME"
    echo "3. Check status: sudo systemctl status $SERVICE_NAME"
    echo "4. View logs: sudo journalctl -u $SERVICE_NAME -f"
    echo
    echo "Manual commands:"
    echo "  Sync now: sudo $INSTALL_DIR/wikisync.py --sync"
    echo "  Check status: sudo $INSTALL_DIR/wikisync.py --status"
    echo
}

# Main installation function
main() {
    echo "WikiSync Installation Script"
    echo "============================"
    echo
    
    check_root
    check_python
    check_disk_space
    
    create_directories
    copy_files
    install_dependencies
    install_service
    create_user
    setup_log_rotation
    
    show_summary
}

# Run main function
main "$@" 