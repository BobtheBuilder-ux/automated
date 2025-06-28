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