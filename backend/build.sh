#!/bin/bash
# Render.com build script

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p static/uploads
mkdir -p static/application_history
mkdir -p static/scheduler

# Set permissions
chmod -R 755 static/