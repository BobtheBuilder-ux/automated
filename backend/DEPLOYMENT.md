# Render.com Deployment Guide

## Overview
This guide will help you deploy your automated job application backend to Render.com.

## Prerequisites
1. A Render.com account
2. Your code in a Git repository (GitHub, GitLab, or Bitbucket)
3. API keys for OpenAI and Google Gemini

## Deployment Steps

### 1. Prepare Your Repository
Push your code to a Git repository that Render can access.

### 2. Create a New Web Service on Render
1. Go to your Render dashboard
2. Click "New +" and select "Web Service"
3. Connect your Git repository
4. Configure the following settings:

**Basic Settings:**
- Name: `automated-job-backend`
- Environment: `Python 3`
- Build Command: `chmod +x build.sh && ./build.sh`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

### 3. Set Environment Variables
In the Render dashboard, go to Environment and add these variables:

**Required:**
- `OPENAI_API_KEY`: Your OpenAI API key
- `GOOGLE_API_KEY`: Your Google Gemini API key
- `ENVIRONMENT`: `production`

**Optional (with defaults):**
- `ALLOWED_ORIGINS`: Your frontend URL (e.g., `https://your-frontend.com`)
- `AUTO_DISCOVERY_INTERVAL_HOURS`: `2`
- `SENDGRID_API_KEY`: If using SendGrid for emails
- `FROM_EMAIL`: Your verified sender email

### 4. Deploy
Click "Create Web Service" and Render will automatically deploy your application.

## Important Notes

### File Persistence
- Render's filesystem is ephemeral
- Uploaded files will be lost on restart
- Consider using cloud storage (AWS S3, Google Cloud Storage) for file persistence

### Firebase Integration
- The Firebase service account file is included in your deployment
- Make sure to keep your Firebase credentials secure

### Health Check
Your service includes a health check endpoint at `/health` for monitoring.

### CORS Configuration
Update the `ALLOWED_ORIGINS` environment variable with your frontend domain once deployed.

## Monitoring
- Check logs in the Render dashboard
- Use the `/health` endpoint for monitoring
- Set up alerts for service downtime

## Local Testing
Before deploying, test locally with production settings:
```bash
export PORT=8000
export HOST=0.0.0.0
export ENVIRONMENT=production
python main.py
```

## Troubleshooting
1. Check build logs for dependency installation issues
2. Verify environment variables are set correctly
3. Ensure Firebase service account file is accessible
4. Check CORS settings if frontend can't connect

## Security Considerations
- Never commit API keys to your repository
- Use Render's environment variables for sensitive data
- Keep Firebase service account secure
- Consider IP whitelisting for additional security