import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv
import pathlib

# Use relative import for the router
from routes.application import router as application_router
from utils.scheduler import JobApplicationScheduler
from services.auto_job_discovery import auto_job_discovery
from services.auto_applicator import AutoApplicator

# Load environment variables
load_dotenv()

# Global scheduler instance
scheduler = JobApplicationScheduler()

# Initialize services globally
auto_applicator = AutoApplicator()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    # Startup
    await scheduler.start()
    
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

# Get allowed origins from environment
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")

# Add CORS middleware - Fixed for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for production
    allow_credentials=False,  # Must be False when using "*"
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(application_router, prefix="", tags=["applications"])

# Health check endpoint for Render
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "message": "Service is running"}

# Define the root endpoint
@app.get("/")
async def root(request: Request):
    """
    Root endpoint, redirects to the auto-apply page.
    """
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/auto-apply")

# Event handler for startup
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        # Restore any active auto-apply schedules
        await auto_applicator.restore_schedules_on_startup()
        print("✅ Auto-applicator schedules restored successfully")
    except Exception as e:
        print(f"⚠️ Warning: Failed to restore schedules: {e}")
    
    # Start auto job discovery if not already running
    try:
        await auto_job_discovery.start_auto_discovery(interval_hours=1)
        print("✅ Auto job discovery started successfully")
    except Exception as e:
        print(f"⚠️ Warning: Auto job discovery startup failed: {e}")

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