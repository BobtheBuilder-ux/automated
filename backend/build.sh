#!/bin/bash
# Render.com build script - Updated for production deployment

echo "🔨 Starting build process..."

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p static/uploads
mkdir -p static/application_history
mkdir -p static/scheduler

# Set permissions
echo "🔒 Setting permissions..."
chmod -R 755 static/

# Make start script executable
chmod +x start.py

echo "✅ Build completed successfully!"