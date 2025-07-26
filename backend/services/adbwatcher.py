#!/usr/bin/env python3
import time
import threading
import queue
from datetime import datetime
import logging

from backend.core.config import get_config
from backend.core.logger import get_logger
from backend.services.adbhandler import ADBHandler
from backend.core.utils import parse_video_path, send_http_notification

logger = get_logger(__name__)

class ADBWatcher:
    #-------------------------------------------------
    # Initialization
    #-------------------------------------------------
    def __init__(self):
        # Load configuration
        self.config = get_config()
        
        # Initialize ADB handler
        self.adb_handler = ADBHandler.get_instance(self.config.adb_device_id)
        
        # Connection state
        self.connection_check_interval = 30  # Default: check connection every 30 seconds
        self.device_connected = False  # Track connection state in a class variable
        
        # Thread control
        self.device_watchdog_thread = None
        self.device_watchdog_running = False
        
        # Process handle for logcat
        self.process = None
        
        # Monitoring state
        self.is_running = False
        self.monitoring_failed = False  # Track if monitoring was attempted but failed
        
        # Event tracking to prevent duplicate/historical events
        self.last_processed_event = None
        self.last_event_time = 0
        
        # Log buffer
        self.log_buffer = queue.Queue(maxsize=1000)
        # Filtered log buffer for important events only
        self.filtered_logs = []
        self.log_thread = None

        # Start device watchdog if enabled
        if self.config.enable_watcher:
            self.start_device_watchdog()

    #-------------------------------------------------
    # Public API: Monitoring Lifecycle
    #-------------------------------------------------
    def start_service(self):
        """Start monitoring ADB logcat"""
        # Always reload the latest config settings
        self.config = get_config()
        
        # Update log level if changed
        new_level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        logging.getLogger().setLevel(new_level)
        
        # Reset monitoring failed flag
        self.monitoring_failed = False
        
        # Check if monitoring is enabled in config
        if not self.config.enable_watcher:
            logger.info("Monitoring is disabled in configuration.")
            return False
        
        # Ensure device watchdog is running first (it manages connections)
        if not self.device_watchdog_thread or not self.device_watchdog_thread.is_alive():
            self.start_device_watchdog()
            # Give watchdog a moment to check connection
            time.sleep(1)  # Reduced from 2 seconds to 1 second
                
        # Try to connect with a faster timeout first - most devices respond quickly if available
        if not self.device_connected:
            # Use a quick connection attempt first (3 second timeout)
            self.device_connected = self.adb_handler.ensure_connection(force=False, timeout=3)
            
            # If quick connection failed, try with force flag but only if not already attempted recently
            if not self.device_connected:
                self.device_connected = self.adb_handler.ensure_connection(force=True, timeout=5)
                
            if not self.device_connected:
                logger.error("Could not connect to device after multiple attempts")
                self.monitoring_failed = True
                return False
            
        if self.is_running:
            return True
            
        # Start the logcat process
        self.process = self.adb_handler.start_logcat_process()
        if not self.process:
            self.monitoring_failed = True  # Set flag indicating monitoring was attempted but failed
            return False
            
        self.is_running = True
        
        # Start log reader thread
        self.log_thread = threading.Thread(target=self._run_logcat_processor)
        self.log_thread.daemon = True
        self.log_thread.start()
        
        logger.info("Monitoring started successfully")
        return True

    def stop_service(self):
        """Stop monitoring ADB logcat"""
        was_running = self.is_running
        self.is_running = False
        
        # Only reset monitoring_failed flag if explicitly stopped by user
        # This way, if monitoring failed due to device issues, the status remains accurate
        if was_running:
            # If monitoring was actually running, reset the failed flag
            self.monitoring_failed = False
        
        # Stop the ADB handler
        self.adb_handler.stop_logcat_process()
        
        # Wait for log reader thread to exit
        if self.log_thread and self.log_thread.is_alive():
            self.log_thread.join(timeout=2)
        
        self.process = None
        
        # Check if watcher is disabled, and stop device watchdog if it is
        if not self.config.enable_watcher:
            logger.info("Watcher disabled, stopping device watchdog")
            self.stop_device_watchdog()
        
        logger.info("Monitoring stopped")
        return True

    def restart_service(self):
        """Restart the monitoring process"""
        logger.info("Restarting monitoring...")
        
        # Stop existing process if running
        self.stop_service()
        
        # Check device connection
        if not self.adb_handler.is_device_connected():
            logger.warning("Device not connected, attempting reconnection...")
            if not self.adb_handler.force_connect():
                logger.error("Failed to reconnect to device during restart")
                self.monitoring_failed = True
                return False
        
        # Start monitoring
        success = self.start_service()
        if not success:
            logger.error("Failed to restart monitoring")
            self.monitoring_failed = True
            return False
        
        return True

    #-------------------------------------------------
    # Public API: Device Watchdog
    #-------------------------------------------------
    def start_device_watchdog(self):
        """Start dedicated thread to monitor device connection"""
        if self.device_watchdog_thread and self.device_watchdog_thread.is_alive():
            logger.debug("Device watchdog already running")
            return
        
        self.device_watchdog_running = True
        self.device_watchdog_thread = threading.Thread(target=self._run_device_watchdog)
        self.device_watchdog_thread.daemon = True
        self.device_watchdog_thread.start()
        logger.info("Device watchdog thread started")
    
    def stop_device_watchdog(self):
        """Stop the device watchdog thread"""
        self.device_watchdog_running = False
        if self.device_watchdog_thread and self.device_watchdog_thread.is_alive():
            # Let the thread exit naturally on next cycle
            logger.info("Device watchdog thread stopped")
        self.device_watchdog_thread = None

    #-------------------------------------------------
    # Public API: Status and Configuration
    #-------------------------------------------------
    def get_watcher_status(self):
        # Handle any configuration changes
        self.apply_config_changes()
        
        return {
            "is_running": self.is_running,
            "device_connected": self.device_connected,
            "device_id": self.config.adb_device_id,
            "notification_endpoint": self.config.notification_endpoint,
            "enable_watcher": self.config.enable_watcher,
            "monitoring_failed": self.monitoring_failed
        }
    
    def apply_config_changes(self):
        """Handle configuration changes that affect the watcher state"""
        # Reload configuration
        old_device_id = self.config.adb_device_id
        self.config = get_config()
        
        # Check if device_id changed
        if old_device_id != self.config.adb_device_id:
            logger.info(f"Device ID changed from {old_device_id} to {self.config.adb_device_id}")
            # Recreate ADB handler with new device ID
            self.adb_handler = ADBHandler.get_instance(self.config.adb_device_id)
            # If monitoring is running, we should restart it
            if self.is_running:
                logger.info("Restarting service due to device ID change")
                self.restart_service()
        
        # Check if enable_watcher state changed
        if not self.config.enable_watcher:
            # If watcher is disabled, stop everything
            logger.info("Watcher disabled in configuration, stopping all monitoring")
            self.stop_service()  # This will also stop the device watchdog
        elif not self.device_watchdog_thread or not self.device_watchdog_thread.is_alive():
            # If watcher is enabled but watchdog isn't running, start it
            logger.info("Watcher enabled in configuration, starting device watchdog")
            self.start_device_watchdog()

    #-------------------------------------------------
    # Public API: Log Access
    #-------------------------------------------------
    def get_raw_logs(self, count=100):
        """Get recent raw logs from buffer"""
        logs = []
        # Create a copy of the queue to avoid modifying the original
        temp_queue = self.log_buffer.queue.copy()
        
        # Get the last 'count' logs
        num_logs = min(count, len(temp_queue))
        logs = list(temp_queue)[-num_logs:]
        
        return logs
    
    def get_event_logs(self, count=50):
        """Get only important logs with original events and mapped paths"""
        # Return the most recent filtered logs up to the requested count
        return self.filtered_logs[-count:] if self.filtered_logs else []

    #-------------------------------------------------
    # Private: Device Watchdog Implementation
    #-------------------------------------------------
    def _run_device_watchdog(self):
        """Dedicated thread to monitor device connection independently of monitoring state"""
        last_connected_state = False
        
        try:
            while self.device_watchdog_running:
                # Check if watcher is still enabled
                self.config = get_config()  # Reload config to check latest enable_watcher status
                
                if not self.config.enable_watcher:
                    logger.info("Watcher disabled in config, stopping device watchdog")
                    self.device_watchdog_running = False
                    break
                
                # Use the persistent connection to check device status
                # Use a fast timeout for regular polling to avoid hanging
                device_connected = self.adb_handler.is_device_connected()
                
                # Update the class-level connection state
                self.device_connected = device_connected
                
                # If device state changed
                if device_connected != last_connected_state:
                    self._handle_connection_state_change(device_connected, last_connected_state)
                
                # Update last state
                last_connected_state = device_connected
                
                # Wait before next check
                time.sleep(self.connection_check_interval)
                
        except Exception as e:
            logger.error(f"Error in device watchdog thread: {str(e)}")
        finally:
            logger.info("Device watchdog thread exiting")

    def _handle_connection_state_change(self, device_connected, last_connected_state):
        """Handle changes in device connection state"""
        if device_connected and not last_connected_state:
            # Auto-recover if monitoring was enabled but failed
            if self.config.enable_watcher and (self.monitoring_failed or not self.is_running):
                logger.info("Auto-recovering monitoring after device reconnection")
                # Reset counters and flags
                self.monitoring_failed = False
                # Restart monitoring
                self.restart_service()

    #-------------------------------------------------
    # Private: Log Processing Implementation
    #-------------------------------------------------
    def _run_logcat_processor(self):
        """Background thread to read log lines"""
        logger.info("Logcat processor thread started")
        
        try:
            while self.is_running and self.process:
                # Read from process stdout
                try:
                    line = self.process.stdout.readline()
                    if not line:
                        # Empty line might indicate process has ended
                        if self.process.poll() is not None:
                            logger.warning("Logcat processor thread has ended")
                            break
                        continue
                    
                    # Process the log line
                    self._process_logcat_entry(line)
                        
                except UnicodeDecodeError as e:
                    logger.error(f"Unicode decode error reading logcat line: {str(e)}")
                    # Continue processing other lines
                    continue
                except Exception as e:
                    logger.error(f"Error reading logcat line: {str(e)}")
        except Exception as e:
            logger.error(f"Error in logcat processor thread: {str(e)}")
        finally:
            logger.info("Logcat processor thread exiting")

    def _process_logcat_entry(self, line):
        """Process a log line from the device"""
        # Ensure line is properly decoded
        try:
            if isinstance(line, bytes):
                line = line.decode('utf-8', errors='replace')
            elif not isinstance(line, str):
                line = str(line)
        except Exception as e:
            logger.error(f"Error decoding log line: {str(e)}")
            return
        
        # Add to buffer
        try:
            self.log_buffer.put_nowait(line)
        except queue.Full:
            # If buffer is full, remove oldest item
            try:
                self.log_buffer.get_nowait()
                self.log_buffer.put_nowait(line)
            except:
                pass
        
        # Since we're already filtering in ADB command, process all lines for START events
        if "START" in line and "cmp=" in line:
            logger.debug(f"Processing logcat line: {line}")
            
            # Extract the video path
            video_path = parse_video_path(line, self.config.path_mappings)
            
            if video_path:
                # Check for duplicate events within cooldown period
                is_duplicate = self._is_duplicate_event(video_path)
                notification_status = "Not sent (duplicate event)" if is_duplicate else "Not configured (no endpoint)" if not self.config.notification_endpoint else None
                
                # Add to filtered logs buffer (only important events)
                self._store_detected_event(line, video_path, notification_status)
                
                # If not a duplicate, process the event
                if not is_duplicate:
                    logger.info(f"Detected video playback: {video_path}")
                    
                    # Send HTTP notification if endpoint is configured
                    if self.config.notification_endpoint:
                        notification_success = send_http_notification(
                            self.config.notification_endpoint, 
                            video_path, 
                            timeout=self.config.notification_timeout,
                            device_ip=self.config.adb_device_ip
                        )
                        # Update the notification status in the filtered log
                        if self.filtered_logs:
                            self.filtered_logs[-1]["notification_status"] = "Sent successfully" if notification_success else "Failed to send"

    def _is_duplicate_event(self, video_path):
        """Check if this is a duplicate of a recently processed event"""
        if not video_path:
            return False
            
        current_time = time.time()
        
        if (video_path == self.last_processed_event and 
            current_time - self.last_event_time < self.config.event_cooldown):
            logger.debug(f"Skipping duplicate event within cooldown period: {video_path}")
            return True
            
        self.last_processed_event = video_path
        self.last_event_time = current_time
        return False

    def _store_detected_event(self, original_line, mapped_path, notification_status=None):
        """Add important logs to the filtered log buffer"""
        # Create a filtered log entry with the original event, mapped path, and notification status
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "original_event": original_line.strip(),
            "mapped_path": mapped_path,
            "notification_status": notification_status
        }
        
        # Keep a maximum of 100 filtered logs
        if len(self.filtered_logs) >= 100:
            self.filtered_logs.pop(0)
        
        self.filtered_logs.append(entry)


#-------------------------------------------------
# Singleton instance
#-------------------------------------------------
_watcher_instance = None

def get_watcher():
    """Get singleton instance of ADBWatcher"""
    global _watcher_instance
    
    if _watcher_instance is None:
        _watcher_instance = ADBWatcher()
    
    return _watcher_instance 