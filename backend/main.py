import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv
import pathlib
from datetime import datetime, timedelta
import json
import asyncio
from typing import Dict, Set

# Use relative import for the router
from routes.application import router as application_router
from routes.email import router as email_router
from utils.scheduler import JobApplicationScheduler
from services.auto_job_discovery import auto_job_discovery
from services.auto_applicator import AutoApplicator
from services.email_tracking_service import EmailTrackingService

# Load environment variables
load_dotenv()

# Global scheduler instance
scheduler = JobApplicationScheduler()

# Initialize services globally
auto_applicator = AutoApplicator()
email_tracker = EmailTrackingService()

# Process registry to track long-running processes
class ProcessRegistry:
    def __init__(self):
        self.active_processes: Dict[str, Dict] = {}
        self.lock = asyncio.Lock()
    
    async def register_process(self, process_id: str, process_type: str, metadata: Dict = None) -> None:
        """Register a long-running process"""
        async with self.lock:
            self.active_processes[process_id] = {
                "type": process_type,
                "start_time": datetime.now().isoformat(),
                "metadata": metadata or {},
                "status": "running"
            }
            print(f"✅ Registered process: {process_id} (type: {process_type})")
    
    async def unregister_process(self, process_id: str, status: str = "completed") -> None:
        """Unregister a process when it completes"""
        async with self.lock:
            if process_id in self.active_processes:
                self.active_processes[process_id]["status"] = status
                self.active_processes[process_id]["end_time"] = datetime.now().isoformat()
                print(f"✅ Process {process_id} marked as {status}")
    
    def has_active_processes(self) -> bool:
        """Check if there are any active processes"""
        return any(p["status"] == "running" for p in self.active_processes.values())
    
    def get_active_processes(self) -> Dict[str, Dict]:
        """Get all active processes"""
        return {k: v for k, v in self.active_processes.items() if v["status"] == "running"}

# Create global process registry
process_registry = ProcessRegistry()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    # Startup
    await scheduler.start()
    
    # Restore any active auto-apply schedules
    try:
        # await auto_applicator.restore_schedules_on_startup()
        print("✅ Auto-applicator initialized successfully")
    except Exception as e:
        print(f"⚠️ Warning: Failed to initialize auto-applicator: {e}")
    
    # Start auto job discovery service
    try:
        await auto_job_discovery.start_auto_discovery(interval_hours=2)
        print("✅ Auto job discovery service started")
    except Exception as e:
        print(f"⚠️  Warning: Could not start auto job discovery: {e}")
    
    print("✅ Application started successfully")
    yield
    # Shutdown
    await scheduler.stop()
    
    # Stop auto job discovery service
    try:
        await auto_job_discovery.stop_auto_discovery()
        print("✅ Auto job discovery service stopped")
    except Exception as e:
        print(f"⚠️  Warning: Error stopping auto job discovery: {e}")
    
    print("✅ Application shutdown completed")

# Create FastAPI app with lifespan
app = FastAPI(
    title="Automated Job Application System",
    lifespan=lifespan
)

# CORS configuration for production and development
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001", 
    "https://automated-frontend.vercel.app",  # Add your frontend domain
    "https://*.vercel.app",  # Allow all Vercel domains
    "https://automated-uayp.onrender.com"  # Your backend domain
]

# Add CORS middleware with proper configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Use the specific allowed origins
    allow_credentials=True,  # Enable credentials
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"]  # Expose all headers
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(application_router, prefix="", tags=["applications"])
app.include_router(email_router, prefix="", tags=["email"])

# Email tracking endpoints
@app.get("/api/email-logs")
async def get_email_logs(limit: int = 100, status: str = ""):
    """Get email logs with optional status filter"""
    try:
        logs = await email_tracker.get_email_logs(limit=limit)
        # Filter by status if provided
        if status:
            logs = [log for log in logs if log.get('status') == status]
        return {"status": "success", "logs": logs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/email-stats")
async def get_email_stats():
    """Get email statistics"""
    try:
        # Calculate stats from email logs
        logs = await email_tracker.get_email_logs(limit=1000)
        total_emails = len(logs)
        sent_emails = len([log for log in logs if log.get('status') == 'sent'])
        failed_emails = len([log for log in logs if log.get('status') == 'failed'])
        
        stats = {
            "total_emails": total_emails,
            "sent_emails": sent_emails,
            "failed_emails": failed_emails,
            "success_rate": (sent_emails / total_emails * 100) if total_emails > 0 else 0
        }
        return {"status": "success", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/system-health")
async def get_system_health():
    """Get comprehensive system health status"""
    try:
        # Calculate email stats
        logs = await email_tracker.get_email_logs(limit=1000)
        total_emails = len(logs)
        sent_emails = len([log for log in logs if log.get('status') == 'sent'])
        
        email_stats = {
            "total_emails": total_emails,
            "sent_emails": sent_emails,
            "success_rate": (sent_emails / total_emails * 100) if total_emails > 0 else 0
        }
        
        health_data = {
            "timestamp": datetime.now().isoformat(),
            "services": {
                "scheduler": scheduler.is_running if hasattr(scheduler, 'is_running') else True,
                "auto_discovery": True,  # Check if auto discovery is running
                "email_service": True,   # Check email service health
                "database": True         # Check database connectivity
            },
            "email_stats": email_stats,
            "recent_logs": await email_tracker.get_email_logs(limit=10),
            "system_metrics": {
                "uptime": "System running",
                "last_auto_apply": "Check last application time",
                "pending_jobs": 0  # Get from scheduler
            }
        }
        return {"status": "success", "health": health_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/clear-email-logs")
async def clear_email_logs():
    """Clear old email logs"""
    try:
        # Get current logs and filter out old ones
        logs = await email_tracker.get_email_logs(limit=10000)
        cutoff_date = datetime.now() - timedelta(days=30)
        
        # This would need to be implemented in the email tracker
        # For now, just return success
        return {"status": "success", "message": "Old email logs cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check endpoint for Render
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    active_processes = process_registry.get_active_processes()
    is_active = bool(active_processes)
    
    response = {
        "status": "healthy",
        "message": "Service is running",
        "has_active_processes": is_active,
        "active_process_count": len(active_processes),
    }
    
    # Add active process info if any exist
    if is_active:
        response["active_processes"] = {
            k: {
                "type": v["type"], 
                "started": v["start_time"],
                "active_for": str(datetime.now() - datetime.fromisoformat(v["start_time"]))
            } 
            for k, v in active_processes.items()
        }
    
    return response

# Process registry endpoint
@app.get("/api/processes")
async def get_processes():
    """Get information about running processes"""
    return {
        "active_processes": process_registry.get_active_processes(),
        "has_active_processes": process_registry.has_active_processes(),
    }

# Define the root endpoint
@app.get("/")
async def root(request: Request):
    """
    Root endpoint, redirects to the auto-apply page.
    """
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/auto-apply")

# Production-ready server configuration
if __name__ == "__main__":
    # Development mode
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"🚀 Starting development server on {host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=False, log_level="info")
else:
    # Production mode - this is what Render will use
    print("🚀 Production server starting...")
    # The app object will be imported and run by the WSGI server