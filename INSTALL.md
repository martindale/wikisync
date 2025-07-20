# WikiSync Installation Guide

This guide provides detailed instructions for installing WikiSync on Linux systems.

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 18.04+, CentOS 7+, Debian 9+, etc.)
- **Python**: 3.8 or higher
- **Disk Space**: Minimum 50GB free space (500GB+ recommended for full Wikipedia)
- **Memory**: 2GB RAM minimum (4GB+ recommended)
- **Network**: Stable internet connection for initial download

### Required Packages

Install the following system packages:

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv curl wget
```

**CentOS/RHEL/Fedora:**
```bash
sudo yum install python3 python3-pip curl wget
# or for newer versions:
sudo dnf install python3 python3-pip curl wget
```

## Installation Methods

### Method 1: Quick Install (Recommended)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-repo/wikisync.git
   cd wikisync
   ```

2. **Run the installer:**
   ```bash
   sudo ./install.sh
   ```

The installer will:
- Check system requirements
- Create necessary directories
- Install Python dependencies
- Set up the systemd service
- Configure log rotation

### Method 2: Manual Installation

1. **Create installation directory:**
   ```bash
   sudo mkdir -p /opt/wikipedia
   sudo chown root:root /opt/wikipedia
   sudo chmod 755 /opt/wikipedia
   ```

2. **Copy files:**
   ```bash
   sudo cp wikisync.py /opt/wikipedia/
   sudo cp config.yaml /opt/wikipedia/
   sudo cp requirements.txt /opt/wikipedia/
   sudo chmod +x /opt/wikipedia/wikisync.py
   ```

3. **Create subdirectories:**
   ```bash
   sudo mkdir -p /opt/wikipedia/{data,temp,logs}
   sudo chmod 755 /opt/wikipedia/{data,temp,logs}
   ```

4. **Install Python dependencies:**
   ```bash
   sudo pip3 install -r /opt/wikipedia/requirements.txt
   ```

5. **Install systemd service:**
   ```bash
   sudo cp systemd/wikisync.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable wikisync
   ```

## Configuration

### Basic Configuration

Edit the configuration file:
```bash
sudo nano /opt/wikipedia/config.yaml
```

Key configuration options:

- **Language**: Set `wikipedia.language` to your preferred language code (e.g., "en", "de", "fr")
- **Sync Frequency**: Modify `sync.frequency` (daily, weekly, monthly)
- **Sync Time**: Set `sync.time` to specify when syncs should run (24-hour format)
- **Download Directory**: Change `download.directory` if needed

### Advanced Configuration

#### Resource Limits
```yaml
resources:
  max_memory_mb: 2048      # Maximum memory usage
  max_cpu_percent: 80      # Maximum CPU usage
  disk_space_threshold_gb: 10  # Minimum free disk space
```

#### Retention Policy
```yaml
retention:
  keep_versions: 3         # Number of versions to keep
  max_age_days: 30         # Maximum age of files
  cleanup_after_sync: true # Auto-cleanup after sync
```

#### Logging
```yaml
logging:
  level: INFO              # Log level (DEBUG, INFO, WARNING, ERROR)
  file: /opt/wikipedia/logs/wikisync.log
  max_size_mb: 100         # Maximum log file size
  backup_count: 5          # Number of backup files
```

## Post-Installation Setup

### 1. Start the Service

```bash
sudo systemctl start wikisync
```

### 2. Check Service Status

```bash
sudo systemctl status wikisync
```

### 3. View Logs

```bash
# View real-time logs
sudo journalctl -u wikisync -f

# View recent logs
sudo journalctl -u wikisync --since "1 hour ago"
```

### 4. Manual Synchronization

```bash
# Perform immediate sync
sudo /opt/wikipedia/wikisync.py --sync

# Check current status
sudo /opt/wikipedia/wikisync.py --status
```

## Verification

### Check Installation

1. **Verify service is running:**
   ```bash
   sudo systemctl is-active wikisync
   ```

2. **Check downloaded files:**
   ```bash
   ls -la /opt/wikipedia/data/
   ```

3. **Verify log files:**
   ```bash
   ls -la /opt/wikipedia/logs/
   ```

### Test Configuration

```bash
# Test configuration loading
sudo /opt/wikipedia/wikisync.py --status
```

## Troubleshooting

### Common Issues

#### 1. Permission Denied
```bash
# Fix permissions
sudo chown -R root:root /opt/wikipedia
sudo chmod 755 /opt/wikipedia
sudo chmod +x /opt/wikipedia/wikisync.py
```

#### 2. Python Dependencies Missing
```bash
# Reinstall dependencies
sudo pip3 install -r /opt/wikipedia/requirements.txt
```

#### 3. Service Won't Start
```bash
# Check service logs
sudo journalctl -u wikisync -n 50

# Check configuration
sudo /opt/wikipedia/wikisync.py --status
```

#### 4. Insufficient Disk Space
```bash
# Check available space
df -h /opt

# Clean up old files
sudo /opt/wikipedia/wikisync.py --cleanup
```

### Log Analysis

Common log messages and their meanings:

- `Starting Wikipedia synchronization` - Sync process started
- `File already up to date` - No download needed
- `Successfully downloaded` - File downloaded successfully
- `Insufficient system resources` - Resource limits exceeded
- `Error downloading` - Network or server issues

## Uninstallation

To completely remove WikiSync:

```bash
sudo ./uninstall.sh
```

This will:
- Stop and disable the service
- Remove systemd configuration
- Remove log rotation settings
- Optionally remove downloaded data
- Remove the system user

## Support

For issues and questions:

1. Check the logs: `sudo journalctl -u wikisync`
2. Review configuration: `sudo cat /opt/wikipedia/config.yaml`
3. Test manually: `sudo /opt/wikipedia/wikisync.py --sync`
4. Check system resources: `df -h && free -h` 