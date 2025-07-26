from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import re

from backend.core.config import get_config
from backend.core.logger import get_logger
from backend.services.adbwatcher import get_watcher
from backend.services.adbhandler import ADBHandler

router = APIRouter()
logger = get_logger(__name__)

# Models
class StatusResponse(BaseModel):
    is_running: bool
    device_connected: bool
    device_id: Optional[str] = None
    notification_endpoint: Optional[str] = None
    enable_watcher: bool = True
    monitoring_failed: bool = False

class ConfigUpdateRequest(BaseModel):
    config: Dict[str, Any]

class ConfigResponse(BaseModel):
    config: Dict[str, Any]

class TestADBResponse(BaseModel):
    status: str
    message: str
    device_id: Optional[str] = None



class CommandResponse(BaseModel):
    success: bool
    message: str


# Routes
@router.get("/status", response_model=StatusResponse)
async def get_status():
    """Get current status of the adb watcher"""
    watcher = get_watcher()
    return watcher.get_watcher_status()

@router.post("/start", response_model=CommandResponse)
async def start_monitoring(background_tasks: BackgroundTasks):
    """Start ADB monitoring"""
    # First, update the config to enable the watcher
    config = get_config()
    
    # Set enable_watcher to True if it wasn't already
    if not config.enable_watcher:
        logger.info("Enabling ADB monitoring in configuration")
        config.update_config({"general": {"enable_watcher": True}})
    
    watcher = get_watcher()
    
    # Run in background task to avoid blocking response
    def start_task():
        success = watcher.start_service()
        if not success:
            logger.error("Failed to start monitoring")
    
    background_tasks.add_task(start_task)
    
    return {
        "success": True,
        "message": "Starting monitoring..."
    }

@router.post("/stop", response_model=CommandResponse)
async def stop_monitoring():
    """Stop ADB monitoring"""
    # First, update the config to disable the watcher
    config = get_config()
    
    # Set enable_watcher to False if it wasn't already
    if config.enable_watcher:
        logger.info("Disabling ADB monitoring in configuration")
        config.update_config({"general": {"enable_watcher": False}})
    
    watcher = get_watcher()
    success = watcher.stop_service()
    
    return {
        "success": success,
        "message": "Monitoring stopped" if success else "Failed to stop monitoring"
    }

@router.post("/restart", response_model=CommandResponse)
async def restart_monitoring(background_tasks: BackgroundTasks):
    """Restart ADB monitoring"""
    watcher = get_watcher()
    
    # Run in background task to avoid blocking response
    def restart_task():
        success = watcher.restart_service()
        if not success:
            logger.error("Failed to restart monitoring")
    
    background_tasks.add_task(restart_task)
    
    return {
        "success": True,
        "message": "Restarting monitoring..."
    }

@router.get("/logs", response_model=List[str])
async def get_logs(count: int = 100):
    """Get recent logs from the buffer"""
    watcher = get_watcher()
    return watcher.get_raw_logs(count)

@router.get("/filtered_logs")
async def get_filtered_logs(count: int = 50):
    """Get only important logs with original events and mapped paths"""
    watcher = get_watcher()
    return watcher.get_event_logs(count)

@router.get("/config", response_model=ConfigResponse)
async def get_config_data():
    """Get current configuration"""
    config = get_config()
    return {
        "config": config.get_all()
    }

@router.post("/config", response_model=CommandResponse)
async def update_config(config_data: ConfigUpdateRequest, background_tasks: BackgroundTasks):
    """Update configuration"""
    config = get_config()
    success = config.update_config(config_data.config)
    
    if success:
        # Restart watcher if it's running
        watcher = get_watcher()
        if watcher.is_running:
            background_tasks.add_task(watcher.restart_service)
    
    return {
        "success": success,
        "message": "Configuration updated successfully" if success else "Failed to update configuration"
    }

@router.post("/test/adb", response_model=TestADBResponse)
async def test_adb_connection(device_id: Optional[str] = None):
    """Test ADB connection"""
    # Validate device_id format if provided
    if device_id:
        # Check if it's in IP:PORT format
        if ':' in device_id:
            ip_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}:\d{1,5}$')
            if not ip_pattern.match(device_id):
                return {
                    "status": "error",
                    "message": "Invalid IP:PORT format. Please use format like 192.168.1.100:5555",
                    "device_id": None
                }
        else:
            # Just IP address
            ip_pattern = re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
            if not ip_pattern.match(device_id):
                return {
                    "status": "error",
                    "message": "Invalid IP format. Please use format like 192.168.1.100",
                    "device_id": None
                }
    
    handler = ADBHandler.get_instance(device_id)
    return handler.test_adb_connection()

 