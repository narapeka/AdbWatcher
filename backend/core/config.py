import os
import yaml
import logging
from typing import Dict, List, Optional, Any
import time

# Singleton instance of config
_config_instance = None

class Config:
    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = config_file
        self.data = {}
        self.load_config()
        
        # General settings
        self.log_level = self.data.get('general', {}).get('log_level', 'INFO')
        self.event_cooldown = self.data.get('general', {}).get('cooldown_seconds', 3)
        self.enable_watcher = self.data.get('general', {}).get('enable_watcher', True)  # Default to enabled
        
        # ADB settings
        self.adb_device_ip = self.data.get('adb', {}).get('device_ip')
        # Construct device_id from IP and fixed port 5555
        self.adb_device_id = f"{self.adb_device_ip}:5555" if self.adb_device_ip else None
        self.adb_logcat_pattern = self.data.get('adb', {}).get('logcat', {}).get('pattern', '')
        self.adb_logcat_buffer = self.data.get('adb', {}).get('logcat', {}).get('buffer', 'system')
        self.adb_logcat_tags = self.data.get('adb', {}).get('logcat', {}).get('tags', 'ActivityTaskManager:I')
        
        # Path mappings
        self.path_mappings = []
        for mapping in self.data.get('mapping_paths', []):
            if isinstance(mapping, dict) and 'source' in mapping and 'target' in mapping:
                self.path_mappings.append(mapping)
        
        # Notification settings
        notification_data = self.data.get('notification', {})
        self.notification_endpoint = notification_data.get('endpoint')
        self.notification_timeout = notification_data.get('timeout_seconds', 10)
    
    def load_config(self) -> None:
        """Load configuration from YAML file"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', self.config_file)
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.data = yaml.safe_load(f)
            logging.debug(f"Configuration loaded from {config_path}")
        except FileNotFoundError:
            logging.error(f"Configuration file not found: {config_path}")
            self.data = {}
        except yaml.YAMLError as e:
            logging.error(f"Error parsing configuration file: {e}")
            self.data = {}
    
    def save_config(self) -> bool:
        """Save configuration to YAML file"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', self.config_file)
        
        try:
            # Create a backup of the file first
            backup_path = f"{config_path}.bak"
            try:
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as src:
                        with open(backup_path, 'w', encoding='utf-8') as dst:
                            dst.write(src.read())
            except Exception as e:
                logging.warning(f"Failed to create backup of config file: {e}")
                
            # Write the configuration with explicit flush and fsync
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.data, f, default_flow_style=False)
                f.flush()
                os.fsync(f.fileno())
                
            # Verify the file was written
            time.sleep(0.1)  # Brief pause to ensure file system operations complete
            with open(config_path, 'r', encoding='utf-8') as f:
                written_data = yaml.safe_load(f)
                if written_data != self.data:
                    logging.error("Configuration verification failed - written data doesn't match")
                    return False
                    
            logging.debug(f"Configuration saved to {config_path}")
            return True
        except Exception as e:
            logging.error(f"Error saving configuration: {e}")
            return False
    
    def update_config(self, new_config: Dict[str, Any]) -> bool:
        """Update configuration with new values"""
        try:
            # Update the data dictionary with new values
            self.data.update(new_config)
            
            # Handle device_ip to device_id conversion for backward compatibility
            if 'adb' in new_config and 'device_ip' in new_config['adb']:
                # If device_ip is provided, ensure it's saved correctly
                device_ip = new_config['adb']['device_ip']
                if device_ip:
                    # Validate IP format
                    import ipaddress
                    try:
                        ipaddress.ip_address(device_ip)
                        # Keep device_ip in the config
                        self.data['adb']['device_ip'] = device_ip
                    except ValueError:
                        logging.error(f"Invalid IP address format: {device_ip}")
                        return False
            
            # Save to file immediately
            if not self.save_config():
                logging.error("Failed to save configuration after update")
                return False
                
            # Reload the configuration to ensure instance properties are updated with actual saved values
            self.load_config()
            
            # Refresh instance properties
            self.__init__(self.config_file)
            
            return True
        except Exception as e:
            logging.error(f"Error updating configuration: {e}")
            return False
    
    def get_all(self) -> Dict[str, Any]:
        """Get entire configuration as dictionary"""
        # Ensure device_ip is included in the response for frontend compatibility
        config_data = self.data.copy()
        if 'adb' in config_data and 'device_ip' not in config_data['adb']:
            # If device_ip is not in the config but device_id is, extract IP from device_id
            if 'device_id' in config_data['adb'] and config_data['adb']['device_id']:
                device_id = config_data['adb']['device_id']
                if ':' in device_id:
                    device_ip = device_id.split(':')[0]
                    config_data['adb']['device_ip'] = device_ip
                else:
                    config_data['adb']['device_ip'] = device_id
        
        # Ensure notification.ip is included for frontend compatibility
        if 'notification' in config_data and 'endpoint' in config_data['notification']:
            endpoint = config_data['notification']['endpoint']
            if endpoint:
                import re
                match = re.match(r'http://([^:]+):\d+/play', endpoint)
                if match:
                    config_data['notification']['ip'] = match.group(1)
        
        return config_data
        
def get_config(config_file: str = None) -> Config:
    """Get singleton instance of Config"""
    global _config_instance
    
    if _config_instance is None or config_file is not None:
        _config_instance = Config(config_file or "config.yaml")
    
    return _config_instance 