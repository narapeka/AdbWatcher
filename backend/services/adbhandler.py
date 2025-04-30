#!/usr/bin/env python3
import subprocess
import logging
import time
import ipaddress
import os
import threading
from pathlib import Path

from backend.core.config import get_config
from backend.core.logger import get_logger

# Import adb-shell components
from adb_shell.adb_device import AdbDeviceTcp
from adb_shell.auth.sign_pythonrsa import PythonRSASigner
from adb_shell.auth.keygen import keygen
from adb_shell.exceptions import AdbConnectionError, AdbTimeoutError

logger = get_logger(__name__)

class ADBHandler:
    # Registry to keep track of instances by device_id
    _instances = {}
    _lock = threading.RLock()  # Reentrant lock for thread-safe operations
    
    @classmethod
    def get_instance(cls, device_id=None):
        """
        Get or create an ADBHandler instance for the specified device_id
        If no device_id is provided, it will use the default from config
        """
        with cls._lock:
            config = get_config()
            device_id = device_id or config.adb_device_id
            
            # If instance doesn't exist for this device_id, create it
            if device_id not in cls._instances:
                cls._instances[device_id] = cls(device_id, _use_registry=True)
                logger.debug(f"Created new ADBHandler instance for device: {device_id}")
            else:
                logger.debug(f"Reusing existing ADBHandler instance for device: {device_id}")
                
            return cls._instances[device_id]
    
    def __init__(self, device_id=None, _use_registry=False):
        """
        Initialize the ADBHandler
        The _use_registry parameter is used internally to prevent direct instantiation
        """
        # Enforce using the get_instance pattern
        if not _use_registry:
            logger.warning("Direct instantiation of ADBHandler is deprecated. Use ADBHandler.get_instance() instead.")
        
        config = get_config()
        self.device_id = device_id or config.adb_device_id
        self.config = config
        
        # Store device IP for reconnection attempts
        self.device_ip = None
        self.device_port = "5555"  # Default ADB port
        
        if self.device_id and ':' in self.device_id:
            # If device_id is in the format IP:PORT
            parts = self.device_id.split(':')
            try:
                # Validate it's a proper IP address
                ipaddress.ip_address(parts[0])
                self.device_ip = parts[0]
                self.device_port = parts[1] if len(parts) > 1 else "5555"
            except ValueError:
                # Not a valid IP
                logger.error(f"Invalid IP address format: {parts[0]}")
                self.device_ip = None
        
        # Connection state
        self.connected = False
        self.connection_lock = threading.RLock()  # Lock for connection operations
        self.last_connection_attempt = 0  # Timestamp of last connection attempt
        self.connection_backoff = 1  # Initial backoff time in seconds
        
        # Persistent connection process
        self.persistent_process = None
        
        # Process handle for logcat
        self.logcat_process = None
        self.is_monitoring = False
        
        # No automatic connection in constructor - defer until needed

    def ensure_connection(self, force=False, timeout=5):
        """
        Unified method to ensure device is connected
        
        Args:
            force: If True, restart ADB server even if connection exists
            timeout: Connection timeout in seconds
            
        Returns:
            bool: Whether connection is established
        """
        with self.connection_lock:
            current_time = time.time()
            
            # Skip if we already tried recently (unless forced)
            if not force and current_time - self.last_connection_attempt < self.connection_backoff:
                logger.debug(f"Skipping connection attempt (backoff: {self.connection_backoff}s)")
                return self.connected
                
            # Update attempt time
            self.last_connection_attempt = current_time
            
            # If we're already connected and not forced, do a quick check
            if self.connected and not force and self.persistent_process and self.persistent_process.poll() is None:
                try:
                    # Quick check to verify connection is responsive
                    result = subprocess.run(
                        ['adb', '-s', f"{self.device_ip}:{self.device_port}", 'shell', 'echo check'],
                        timeout=timeout, capture_output=True, text=True, check=False
                    )
                    if result.returncode == 0 and "check" in result.stdout:
                        # Connection is good, reset backoff
                        self.connection_backoff = 1
                        return True
                except Exception:
                    # Connection check failed, proceed with reconnection
                    pass
            
            # Stop any existing processes before reconnection
            if self.persistent_process:
                try:
                    self.persistent_process.terminate()
                    self.persistent_process.wait(timeout=2)
                except:
                    pass
                self.persistent_process = None
            
            # Restart ADB server if forced
            if force:
                self.restart_adb()
            
            # Validate IP
            if not self.device_ip:
                logger.error("No valid IP address provided for connection")
                self.connected = False
                return False
            
            # Establish connection
            logger.info(f"Connecting to device {self.device_ip}:{self.device_port} (timeout: {timeout}s)")
            try:
                # Connect the device
                result = subprocess.run(
                    ['adb', 'connect', f"{self.device_ip}:{self.device_port}"], 
                    timeout=timeout, capture_output=True, text=True
                )
                
                if "connected" not in result.stdout.lower() and "already connected" not in result.stdout.lower():
                    logger.error(f"Failed to connect: {result.stdout}")
                    self.connected = False
                    # Increase backoff for next attempt (cap at 30 seconds)
                    self.connection_backoff = min(self.connection_backoff * 2, 30)
                    return False
                
                # Start persistent shell process to keep connection alive
                self.persistent_process = subprocess.Popen(
                    ['adb', '-s', f"{self.device_ip}:{self.device_port}", 'shell', 
                     'while true; do echo ping; sleep 5; done'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                self.connected = True
                # Reset backoff on success
                self.connection_backoff = 1
                logger.info(f"Successfully connected to {self.device_ip}:{self.device_port}")
                return True
                
            except subprocess.TimeoutExpired:
                logger.error(f"Connection timed out after {timeout}s")
                self.connected = False
                # Increase backoff for next attempt (cap at 30 seconds)
                self.connection_backoff = min(self.connection_backoff * 2, 30)
                return False
            except Exception as e:
                logger.error(f"Connection error: {e}")
                self.connected = False
                # Increase backoff for next attempt (cap at 30 seconds)
                self.connection_backoff = min(self.connection_backoff * 2, 30)
                return False

    def start_persistent_connection(self):
        """Start a persistent ADB shell connection"""
        # This is now just a wrapper around ensure_connection for backward compatibility
        return self.ensure_connection(force=False, timeout=5)

    def connect(self):
        """Establish connection to the device"""
        # This is now just a wrapper around ensure_connection for backward compatibility
        return self.ensure_connection(force=False, timeout=5)

    def is_device_connected(self):
        """Check if ADB device is connected"""
        with self.connection_lock:
            # First check if our process is still running
            if self.persistent_process and self.persistent_process.poll() is None:
                # It's running, but do a quick check only if it's been a while since our last check
                current_time = time.time()
                if current_time - self.last_connection_attempt > 30:  # Check every 30 seconds
                    try:
                        result = subprocess.run(
                            ['adb', '-s', f"{self.device_ip}:{self.device_port}", 'shell', 'echo check'],
                            timeout=2, capture_output=True, text=True, check=False
                        )
                        if result.returncode == 0 and "check" in result.stdout:
                            self.connected = True
                            return True
                        else:
                            # Process is running but not responsive
                            self.connected = False
                            return self.ensure_connection()
                    except:
                        # Quick check failed, try reconnection with minimal timeout
                        return self.ensure_connection(timeout=2)
                # If we checked recently, use cached state
                return self.connected
            else:
                # Process isn't running, try to connect with minimal timeout
                return self.ensure_connection(timeout=2)

    def force_connect(self):
        """Try to reconnect to a lost device by restarting ADB server first"""
        # Use our unified connection method with force=True
        return self.ensure_connection(force=True, timeout=10)

    def execute_command(self, cmd):
        """Execute an ADB shell command"""
        # Ensure we have a connection before executing command
        if not self.ensure_connection(timeout=2):
            logger.error("Device not connected, cannot execute command")
            return None
                
        try:
            result = subprocess.run(
                ['adb', '-s', f"{self.device_ip}:{self.device_port}", 'shell', cmd],
                timeout=15, capture_output=True, text=True, check=False
            )
            if result.returncode == 0:
                return result.stdout
            else:
                logger.error(f"Command failed: {result.stderr}")
                return None
        except Exception as e:
            logger.error(f"Error executing command: {str(e)}")
            self.connected = False
            return None

    def restart_adb(self):
        """Restart ADB server"""
        logger.info("Restarting ADB server...")
        try:
            subprocess.run(["adb", "kill-server"], timeout=5)
            time.sleep(1)
            subprocess.run(["adb", "start-server"], timeout=5)
            return True
        except Exception as e:
            logger.error(f"Failed to restart ADB: {str(e)}")
            return False

    def start_logcat_process(self):
        """Start logcat process"""
        # Ensure connection before starting logcat
        if not self.ensure_connection(timeout=3):
            logger.error("Device not connected, cannot start logcat")
            return None
            
        # Get configuration values or use defaults
        buffer_name = self.config.adb_logcat_buffer
        tags = self.config.adb_logcat_tags
        filter_pattern = self.config.adb_logcat_pattern
        
        try:
            # Clear logcat buffer first 
            clear_result = subprocess.run(
                ['adb', '-s', f"{self.device_ip}:{self.device_port}", 'logcat', '-c'],
                timeout=5
            )
            
            # Build the logcat command
            base_cmd = ["adb", "-s", f"{self.device_ip}:{self.device_port}",
                "logcat", 
                f"--buffer={buffer_name}", 
                tags, "*:S", 
                "-e", filter_pattern
            ]
            
            # Start the process
            self.logcat_process = subprocess.Popen(
                base_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                bufsize=1  # Line buffered
            )
            
            self.is_monitoring = True
            logger.info(f"Started logcat process (PID: {self.logcat_process.pid})")
            return self.logcat_process
            
        except Exception as e:
            logger.error(f"Failed to start logcat process: {str(e)}")
            self.is_monitoring = False
            return None
    
    def stop_logcat_process(self):
        """Stop the running logcat process"""
        if self.logcat_process:
            try:
                self.logcat_process.terminate()
                self.logcat_process.wait(timeout=5)
                logger.info("Logcat process terminated")
            except Exception as e:
                logger.error(f"Error stopping logcat process: {str(e)}")
                try:
                    self.logcat_process.kill()
                except Exception as e2:
                    logger.error(f"Failed to kill logcat process: {str(e2)}")
            finally:
                self.logcat_process = None
                self.is_monitoring = False
    
    def test_adb_connection(self):
        """Test ADB connection and return result"""
        # Check if already connected
        if self.is_device_connected():
            return {
                "status": "success",
                "message": f"Device {self.device_id} already connected",
                "device_id": self.device_id
            }
        
        # Try simple connection first
        logger.info(f"Testing connection to device {self.device_id}")
        if self.connect():
            return {
                "status": "success", 
                "message": f"Successfully connected to device {self.device_id}",
                "device_id": self.device_id
            }
        
        # If simple connection failed, try force connect
        logger.info(f"Simple connection failed, trying to restart ADB server")
        if self.force_connect():
            return {
                "status": "success",
                "message": f"Successfully connected to device {self.device_id} after restarting ADB server",
                "device_id": self.device_id
            }
        
        # Both connection attempts failed
        return {
            "status": "error",
            "message": f"Failed to connect to device {self.device_id}",
            "device_id": self.device_id
        } 