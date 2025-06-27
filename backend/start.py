#!/usr/bin/env python3
"""
Production startup script for Render deployment
This ensures the server runs continuously without shutting down
"""

import os
import uvicorn
from main import app

def start_server():
    """Start the FastAPI server for production"""
    # Get configuration from environment variables
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"🚀 Starting production server on {host}:{port}")
    print("📊 Server will run continuously...")
    
    # Run with production settings
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True,
        loop="asyncio",
        # Keep the server running
        reload=False,
        # Production optimizations
        workers=1,  # Single worker for free tier
        timeout_keep_alive=5,
        limit_concurrency=100,
        limit_max_requests=1000
    )

if __name__ == "__main__":
    start_server()