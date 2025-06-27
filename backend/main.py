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

# Load environment variables
load_dotenv()

# Global scheduler instance
scheduler = JobApplicationScheduler()

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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS + ["*"],  # Add your frontend domain here
    allow_credentials=True,
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

if __name__ == "__main__":
    # Run the application with uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")  # Bind to all interfaces for production
    print(f"🚀 Starting server on {host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=False)