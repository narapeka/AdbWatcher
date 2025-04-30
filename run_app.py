#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import multiprocessing
import signal
import socket
import requests

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import backend directly - this is the simplest and most reliable approach
from backend.main import start_server
from backend.core.logger import get_logger

# Set up logging
logger = get_logger("run_app")

def run_backend():
    """Run the backend server"""
    logger.info("Starting backend server...")
    try:
        # Use a direct subprocess call to run uvicorn
        uvicorn_cmd = ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7700"]
        subprocess.run(uvicorn_cmd, check=True)
    except KeyboardInterrupt:
        logger.info("Backend server stopped")
    except Exception as e:
        logger.error(f"Error starting backend: {str(e)}")

def run_frontend():
    """Run the frontend development server"""
    logger.info("Starting frontend server...")
    try:
        # Change to frontend directory
        frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")
        if not os.path.exists(frontend_dir):
            logger.error(f"Error: Frontend directory not found at {frontend_dir}")
            return
            
        os.chdir(frontend_dir)
        
        # Check if package.json exists
        if not os.path.exists("package.json"):
            logger.error("Error: package.json not found in frontend directory")
            logger.error("Make sure you've run 'npm install' in the frontend directory")
            return
            
        # Find npm executable
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
        
        # Run npm run dev
        subprocess.run([npm_cmd, "run", "dev"], check=True)
    except KeyboardInterrupt:
        logger.info("Frontend server stopped")
    except FileNotFoundError as e:
        logger.error(f"Error: {npm_cmd} not found. Make sure Node.js is installed and in your PATH")
        logger.error(f"Download Node.js from: https://nodejs.org/")
    except Exception as e:
        logger.error(f"Error starting frontend: {str(e)}")
    finally:
        # Change back to root directory
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

def is_port_open(host, port, timeout=0.1):
    """Check if a port is open on the given host"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def wait_for_backend_ready(host="localhost", port=7700, max_wait=60, check_interval=0.5):
    """Wait for backend server to become available, with a maximum wait time"""
    logger.info(f"Waiting for backend to be ready (max {max_wait}s)...")
    start_time = time.time()
    
    # First wait for port to be open
    while time.time() - start_time < max_wait:
        if is_port_open(host, port):
            # Port is open, now check if API is responding
            try:
                response = requests.get(f"http://{host}:{port}/api/health", timeout=2)
                if response.status_code == 200:
                    logger.info(f"Backend ready after {time.time() - start_time:.1f} seconds")
                    return True
            except:
                # API not ready yet, continue waiting
                pass
                
        time.sleep(check_interval)
        
    logger.warning(f"Backend did not become ready within {max_wait} seconds")
    # Continue anyway - frontend will retry connections
    return False

def main():
    # Initialize process list
    processes = []
    
    # Start backend first
    logger.info("Starting ADB Watcher application")
    backend_process = multiprocessing.Process(target=run_backend)
    backend_process.start()
    processes.append(backend_process)
    
    # Wait for backend to initialize (but no more than 15 seconds)
    wait_for_backend_ready(max_wait=15)
    
    # Then start frontend
    frontend_process = multiprocessing.Process(target=run_frontend)
    frontend_process.start()
    processes.append(frontend_process)
    
    # Set up clean shutdown handler
    def shutdown_handler(sig, frame):
        logger.info("Shutting down servers...")
        for process in processes:
            if process.is_alive():
                process.terminate()
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    # Wait for processes to complete
    try:
        for process in processes:
            process.join()
    except KeyboardInterrupt:
        shutdown_handler(None, None)

if __name__ == "__main__":
    # On Windows, we need to use the spawn method for multiprocessing
    if sys.platform == "win32":
        multiprocessing.set_start_method('spawn', force=True)
    main() 