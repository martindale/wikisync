# WikiSync - Wikipedia Local Synchronization
A tool to download and maintain a local copy of Wikipedia using official database dumps.  Designed to run as a Linux service with automatic synchronization.

## Features
- Downloads Wikipedia database dumps from official sources
- Automatic unpacking of compressed files
- Canonical directory with latest versions always available
- Incremental synchronization to keep local copy up-to-date
- Configurable retention policies
- Systemd service integration
- Progress tracking and logging
- Resource usage optimization

## Installation
### Prerequisites
- Python 3.8+
- 500GB+ free disk space (for full Wikipedia dump)
- Internet connection for initial download and updates

### Quick Install
```bash
# Clone the repository
git clone git@github.com:martindale/wikisync.git
cd wikisync

# Run the installer
sudo ./install.sh
```
### Manual Installation
1. Copy files to `/opt/wikipedia`:
```bash
sudo mkdir -p /opt/wikipedia
sudo cp -r * /opt/wikipedia/
sudo chown -R root:root /opt/wikipedia
sudo chmod +x /opt/wikipedia/wikisync.py
```

2. Install Python dependencies:
```bash
sudo pip3 install -r requirements.txt
```

3. Install systemd service:
```bash
sudo cp systemd/wikisync.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable wikisync
```

## Configuration
Edit `/opt/wikipedia/config.yaml` to customize:
- Wikipedia language version
- Download directory
- Sync frequency
- Retention policies
- Resource limits

## Usage
### Start the service
```bash
sudo systemctl start wikisync
```

### Check status
```bash
sudo systemctl status wikisync
```

### View logs
```bash
sudo journalctl -u wikisync -f
```

### Manual sync
```bash
sudo /opt/wikipedia/wikisync.py --sync
```

### Check status and available files
```bash
sudo /opt/wikipedia/wikisync.py --status
```

This will show:
- Last synchronization time
- Number of compressed, unpacked, and canonical files
- Total disk usage
- List of available canonical files in `/opt/wikipedia/latest/`

## Directory Structure
```
/opt/wikipedia/
├── wikisync.py          # Main synchronization script
├── config.yaml          # Configuration file
├── requirements.txt     # Python dependencies
├── install.sh          # Installation script
├── systemd/            # Systemd service files
├── logs/               # Log files
├── data/               # Downloaded compressed Wikipedia dumps
├── unpacked/           # Unpacked files (historical versions)
└── latest/             # Canonical latest versions (always up-to-date)
```

## File Organization

- **`/opt/wikipedia/data/`**: Contains compressed Wikipedia dumps (`.bz2`, `.gz` files)
- **`/opt/wikipedia/unpacked/`**: Contains unpacked files from previous syncs
- **`/opt/wikipedia/latest/`**: Contains the most recent unpacked versions of all files

Applications should reference files from the `latest/` directory to always get the most current data.

## License
MIT License - see LICENSE file for details.
