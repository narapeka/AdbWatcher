from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging
import os
import sys

# Add parent directory to path to allow absolute imports
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Use absolute imports instead of relative imports
from backend.core.logger import setup_logging
from backend.routers import api
from backend.services.adbwatcher import get_watcher

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="ADB Watcher API",
    description="API for monitoring Android device activity via ADB",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api.router, prefix="/api", tags=["api"])

# Auto-start monitoring on application startup
@app.on_event("startup")
async def startup_event():
    """Auto-start monitoring when the application starts"""
    try:
        # Get the watcher instance - it will handle device connections internally via its watchdog
        watcher = get_watcher()
        
        # Only start the service if it's not already running
        if not watcher.is_running:
            # Start the watcher service - it will check device connections internally
            watcher.start_service()
            
    except Exception as e:
        logger.exception(f"Error auto-starting monitoring: {str(e)}")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "message": str(exc)}
    )

@app.get("/", tags=["root"])
async def root():
    """Root endpoint - API is running"""
    return {"status": "API running", "message": "Welcome to ADB Watcher API"}

@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

# Add a dedicated health endpoint in the API route for startup checking
@app.get("/api/health", tags=["health"])
async def api_health_check():
    """API health check endpoint"""
    return {
        "status": "healthy",
        "api_ready": True,
        "version": "1.0.0"
    }

def start_server():
    """Start the FastAPI server"""
    # Default values
    host = "0.0.0.0"
    port = 7700
    
    logger.info(f"Starting ADB Watcher API on {host}:{port}")
    
    # Handle different ways of running based on how the script is called
    if __name__ == "__main__":
        # When running the script directly: don't use reload
        uvicorn.run(app, host=host, port=port)
    else:
        # When imported as a module: can use reload
        uvicorn.run("backend.main:app", host=host, port=port, reload=True)

if __name__ == "__main__":
    start_server() 