#!/usr/bin/env python3
"""
WikiSync - Wikipedia Local Synchronization Tool

Downloads and maintains a local copy of Wikipedia using official database dumps.
Designed to run as a Linux service with automatic synchronization.
"""

import os
import sys
import time
import hashlib
import logging
import argparse
import schedule
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml
import requests
from tqdm import tqdm
import psutil
from dateutil import parser as date_parser


class WikiSync:
    """Main Wikipedia synchronization class."""
    
    def __init__(self, config_path: str = "/opt/wikipedia/config.yaml"):
        """Initialize WikiSync with configuration."""
        self.config_path = config_path
        self.config = self._load_config()
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'WikiSync/1.0 (https://github.com/your-repo/wikisync)'
        })
        
    def _load_config(self) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except FileNotFoundError:
            self._create_default_config()
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            print(f"Error loading config: {e}")
            sys.exit(1)
    
    def _create_default_config(self):
        """Create default configuration if none exists."""
        default_config = {
            'wikipedia': {
                'language': 'en',
                'base_url': 'https://dumps.wikimedia.org',
                'dump_url': 'https://dumps.wikimedia.org/{language}wiki/latest/'
            },
            'download': {
                'directory': '/opt/wikipedia/data',
                'temp_directory': '/opt/wikipedia/temp',
                'max_concurrent_downloads': 3,
                'chunk_size': 8192,
                'timeout': 300,
                'retry_attempts': 3,
                'retry_delay': 60
            },
            'sync': {
                'frequency': 'daily',
                'time': '02:00',
                'check_interval': 3600,
                'incremental': True,
                'verify_checksums': True
            },
            'files': [
                'pages-articles.xml.bz2',
                'pages-articles-multistream.xml.bz2',
                'pages-meta-current.xml.bz2',
                'page.sql.gz',
                'categorylinks.sql.gz',
                'langlinks.sql.gz'
            ],
            'retention': {
                'keep_versions': 3,
                'max_age_days': 30,
                'cleanup_after_sync': True
            },
            'resources': {
                'max_memory_mb': 2048,
                'max_cpu_percent': 80,
                'disk_space_threshold_gb': 10
            },
            'logging': {
                'level': 'INFO',
                'file': '/opt/wikipedia/logs/wikisync.log',
                'max_size_mb': 100,
                'backup_count': 5,
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            }
        }
        
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
    
    def _setup_logging(self):
        """Setup logging configuration."""
        log_config = self.config['logging']
        log_file = log_config['file']
        
        # Create log directory
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, log_config['level']),
            format=log_config['format'],
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
    
    def _check_resources(self) -> bool:
        """Check if system resources are sufficient."""
        resources = self.config['resources']
        
        # Check memory
        memory = psutil.virtual_memory()
        if memory.available < resources['max_memory_mb'] * 1024 * 1024:
            self.logger.warning(f"Insufficient memory: {memory.available / 1024 / 1024:.1f}MB available")
            return False
        
        # Check disk space
        download_dir = self.config['download']['directory']
        disk_usage = psutil.disk_usage(download_dir)
        free_gb = disk_usage.free / 1024 / 1024 / 1024
        if free_gb < resources['disk_space_threshold_gb']:
            self.logger.warning(f"Insufficient disk space: {free_gb:.1f}GB free")
            return False
        
        return True
    
    def _get_dump_info(self) -> Dict:
        """Get information about available dumps."""
        language = self.config['wikipedia']['language']
        dump_url = self.config['wikipedia']['dump_url'].format(language=language)
        
        try:
            response = self.session.get(dump_url, timeout=self.config['download']['timeout'])
            response.raise_for_status()
            
            # Parse the HTML to find dump files
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            dump_info = {}
            for link in soup.find_all('a'):
                href = link.get('href')
                if href and any(file in href for file in self.config['files']):
                    file_url = dump_url + href
                    dump_info[href] = {
                        'url': file_url,
                        'size': self._get_file_size(file_url),
                        'timestamp': self._extract_timestamp(href)
                    }
            
            return dump_info
        except Exception as e:
            self.logger.error(f"Error getting dump info: {e}")
            return {}
    
    def _get_file_size(self, url: str) -> int:
        """Get file size from URL."""
        try:
            response = self.session.head(url, timeout=self.config['download']['timeout'])
            return int(response.headers.get('content-length', 0))
        except:
            return 0
    
    def _extract_timestamp(self, filename: str) -> Optional[datetime]:
        """Extract timestamp from filename."""
        # Look for date patterns in filename
        import re
        date_patterns = [
            r'(\d{8})',  # YYYYMMDD
            r'(\d{4}-\d{2}-\d{2})',  # YYYY-MM-DD
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, filename)
            if match:
                try:
                    return date_parser.parse(match.group(1))
                except:
                    continue
        
        return None
    
    def _download_file(self, url: str, local_path: str, file_size: int = 0) -> bool:
        """Download a single file with progress tracking."""
        try:
            response = self.session.get(url, stream=True, timeout=self.config['download']['timeout'])
            response.raise_for_status()
            
            with open(local_path, 'wb') as f:
                with tqdm(total=file_size, unit='B', unit_scale=True, desc=os.path.basename(local_path)) as pbar:
                    for chunk in response.iter_content(chunk_size=self.config['download']['chunk_size']):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
            
            return True
        except Exception as e:
            self.logger.error(f"Error downloading {url}: {e}")
            return False
    
    def _verify_checksum(self, file_path: str, expected_checksum: str) -> bool:
        """Verify file checksum if available."""
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5()
                for chunk in iter(lambda: f.read(4096), b""):
                    file_hash.update(chunk)
                actual_checksum = file_hash.hexdigest()
                return actual_checksum == expected_checksum
        except Exception as e:
            self.logger.error(f"Error verifying checksum: {e}")
            return False
    
    def _cleanup_old_files(self):
        """Clean up old files based on retention policy."""
        retention = self.config['retention']
        download_dir = Path(self.config['download']['directory'])
        
        if not download_dir.exists():
            return
        
        # Get all files in download directory
        files = []
        for file_path in download_dir.rglob('*'):
            if file_path.is_file():
                files.append((file_path, file_path.stat().st_mtime))
        
        # Sort by modification time (newest first)
        files.sort(key=lambda x: x[1], reverse=True)
        
        # Keep only the specified number of versions
        for file_path, mtime in files[retention['keep_versions']:]:
            try:
                file_path.unlink()
                self.logger.info(f"Deleted old file: {file_path}")
            except Exception as e:
                self.logger.error(f"Error deleting {file_path}: {e}")
        
        # Remove files older than max_age_days
        cutoff_time = time.time() - (retention['max_age_days'] * 24 * 3600)
        for file_path, mtime in files:
            if mtime < cutoff_time:
                try:
                    file_path.unlink()
                    self.logger.info(f"Deleted old file: {file_path}")
                except Exception as e:
                    self.logger.error(f"Error deleting {file_path}: {e}")
    
    def sync(self) -> bool:
        """Perform full synchronization."""
        self.logger.info("Starting Wikipedia synchronization")
        
        if not self._check_resources():
            self.logger.error("Insufficient system resources")
            return False
        
        # Create directories
        download_dir = Path(self.config['download']['directory'])
        temp_dir = Path(self.config['download']['temp_directory'])
        download_dir.mkdir(parents=True, exist_ok=True)
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Get dump information
        dump_info = self._get_dump_info()
        if not dump_info:
            self.logger.error("No dump information available")
            return False
        
        # Download files
        success_count = 0
        for filename, info in dump_info.items():
            local_path = download_dir / filename
            temp_path = temp_dir / filename
            
            # Check if file already exists and is up to date
            if local_path.exists():
                local_size = local_path.stat().st_size
                if local_size == info['size']:
                    self.logger.info(f"File already up to date: {filename}")
                    success_count += 1
                    continue
            
            self.logger.info(f"Downloading {filename} ({info['size'] / 1024 / 1024 / 1024:.1f}GB)")
            
            # Download to temp file first
            if self._download_file(info['url'], temp_path, info['size']):
                # Move to final location
                temp_path.rename(local_path)
                success_count += 1
                self.logger.info(f"Successfully downloaded: {filename}")
            else:
                self.logger.error(f"Failed to download: {filename}")
        
        # Cleanup old files
        if self.config['retention']['cleanup_after_sync']:
            self._cleanup_old_files()
        
        self.logger.info(f"Synchronization completed: {success_count}/{len(dump_info)} files")
        return success_count == len(dump_info)
    
    def run_service(self):
        """Run as a service with scheduled synchronization."""
        self.logger.info("Starting WikiSync service")
        
        # Schedule sync based on configuration
        sync_config = self.config['sync']
        if sync_config['frequency'] == 'daily':
            schedule.every().day.at(sync_config['time']).do(self.sync)
        elif sync_config['frequency'] == 'weekly':
            schedule.every().week.at(sync_config['time']).do(self.sync)
        elif sync_config['frequency'] == 'monthly':
            schedule.every().month.at(sync_config['time']).do(self.sync)
        
        # Run initial sync
        self.sync()
        
        # Main service loop
        while True:
            schedule.run_pending()
            time.sleep(sync_config['check_interval'])
    
    def status(self) -> Dict:
        """Get current status information."""
        download_dir = Path(self.config['download']['directory'])
        
        status = {
            'last_sync': None,
            'files_count': 0,
            'total_size_gb': 0,
            'disk_usage_gb': 0,
            'next_sync': None
        }
        
        if download_dir.exists():
            files = list(download_dir.rglob('*'))
            status['files_count'] = len([f for f in files if f.is_file()])
            status['total_size_gb'] = sum(f.stat().st_size for f in files if f.is_file()) / 1024 / 1024 / 1024
            
            # Get last modification time
            if files:
                status['last_sync'] = datetime.fromtimestamp(max(f.stat().st_mtime for f in files))
        
        # Get disk usage
        if download_dir.exists():
            disk_usage = psutil.disk_usage(download_dir)
            status['disk_usage_gb'] = disk_usage.used / 1024 / 1024 / 1024
        
        return status


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Wikipedia Local Synchronization Tool')
    parser.add_argument('--config', default='/opt/wikipedia/config.yaml', help='Configuration file path')
    parser.add_argument('--sync', action='store_true', help='Perform synchronization')
    parser.add_argument('--service', action='store_true', help='Run as service')
    parser.add_argument('--status', action='store_true', help='Show status')
    
    args = parser.parse_args()
    
    wikisync = WikiSync(args.config)
    
    if args.sync:
        success = wikisync.sync()
        sys.exit(0 if success else 1)
    elif args.service:
        wikisync.run_service()
    elif args.status:
        status = wikisync.status()
        print(f"Last sync: {status['last_sync']}")
        print(f"Files: {status['files_count']}")
        print(f"Total size: {status['total_size_gb']:.1f}GB")
        print(f"Disk usage: {status['disk_usage_gb']:.1f}GB")
    else:
        parser.print_help()


if __name__ == '__main__':
    main() 