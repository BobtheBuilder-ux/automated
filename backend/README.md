# Automated Job Application Backend

A Flask-based backend service for automated job application processing with Firebase integration.

## Features

- Job scraping and discovery
- Automated application generation using AI (OpenAI/Gemini)
- PDF processing and generation
- Email services
- Firebase integration for data storage
- Scheduled job processing

## Setup

1. **Environment Variables**
   ```bash
   cp .env.example .env
   ```
   Fill in your actual API keys and configuration values in `.env`

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Firebase Setup**
   - Download your Firebase service account JSON file
   - Place it as `firebase-service-account.json` in the root directory
   - Or configure Firebase credentials via environment variables in `.env`

4. **Run the Application**
   ```bash
   python main.py
   ```

## Deployment

### Render Deployment
This project is configured for deployment on Render with the included `render.yaml` file.

### Environment Variables Required
- `OPENAI_API_KEY` - OpenAI API key for AI generation
- `GOOGLE_API_KEY` - Google Gemini API key
- `FIREBASE_PROJECT_ID` - Your Firebase project ID
- `FIREBASE_PRIVATE_KEY` - Firebase service account private key
- `FIREBASE_CLIENT_EMAIL` - Firebase service account email
- Additional variables as listed in `.env.example`

## Project Structure

- `main.py` - Flask application entry point
- `routes/` - API route handlers
- `services/` - Business logic and external service integrations
- `utils/` - Utility functions and helpers
- `templates/` - HTML templates
- `static/` - Static files and uploads

## Security Notes

- Never commit `firebase-service-account.json` to version control
- Use environment variables for all sensitive configuration
- The `.gitignore` file is configured to exclude credentials