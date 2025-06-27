# Firebase Setup Guide

## Getting Your Firebase Service Account Key

To fix the "Firebase service account key not found" warning, you need to download the actual service account key from Firebase Console:

### Steps:

1. **Go to Firebase Console**
   - Visit: https://console.firebase.google.com/
   - Select your project: `automated-669ff`

2. **Navigate to Service Accounts**
   - Click on the gear icon (⚙️) in the left sidebar
   - Select "Project settings"
   - Click on the "Service accounts" tab

3. **Generate Private Key**
   - Scroll down to "Firebase Admin SDK"
   - Click "Generate new private key"
   - Click "Generate key" in the popup

4. **Save the Key File**
   - A JSON file will be downloaded
   - Rename it to `firebase-service-account.json`
   - Move it to the `backend/` folder
   - Replace the placeholder file that's currently there

### Security Note:
- Never commit the real service account key to version control
- Add `firebase-service-account.json` to your `.gitignore` file
- The current placeholder file is safe to commit

### Alternative Setup (using environment variable):
Instead of placing the file in the project, you can set an environment variable:
```bash
export FIREBASE_SERVICE_ACCOUNT_PATH="/path/to/your/firebase-service-account.json"
```

## What's Fixed:

✅ **FastAPI Deprecation Warnings**: Updated to use modern `lifespan` events instead of deprecated `on_event`
✅ **Reload Warning**: Fixed by using `"main:app"` string instead of direct app object
✅ **Firebase Configuration**: Added proper client-side config and service account template
✅ **Environment Variables**: Created proper `.env` files for both frontend and backend
✅ **Error Handling**: Added clear setup instructions and better error messages

## Testing the Setup:

After replacing the service account key, restart the backend:
```bash
cd backend
python main.py
```

You should see:
- ✅ Firebase initialized from service account file
- ✅ Application started successfully
- 🚀 Starting server on http://localhost:8000

No more warnings! 🎉