# Automated Job Application System

A comprehensive automated job application system that helps streamline the job search process with AI-powered cover letter generation, automated job discovery, and application tracking.

## 🚀 Features

### Core Features
- **AI-Powered Cover Letter Generation** - Uses Google Gemini AI to create personalized cover letters
- **Automated Job Discovery** - Scrapes job boards and discovers fresh opportunities
- **Smart Job Matching** - Filters and matches jobs based on your preferences
- **Application Tracking** - Firebase-powered dashboard to track all applications
- **Auto-Apply Scheduling** - Schedule automated job applications
- **Real-time Analytics** - Track success rates and application statistics

### Technical Features
- **Modern Next.js Frontend** - Responsive React-based UI with Tailwind CSS
- **Python FastAPI Backend** - High-performance API with async support
- **Firebase Integration** - Real-time database and authentication
- **Render.com Deployment** - Cloud-hosted backend with auto-scaling
- **Cron Job Keep-Alive** - Prevents backend from sleeping on free tier

## 🏗️ Architecture

```
automated/
├── frontend/          # Next.js React application
│   ├── app/          # App router pages
│   ├── components/   # Reusable UI components
│   └── lib/          # Utilities and services
├── backend/          # Python FastAPI server
│   ├── routes/       # API endpoints
│   ├── services/     # Business logic
│   ├── utils/        # Helper functions
│   └── templates/    # HTML templates
└── docs/             # Documentation
```

## 🛠️ Technology Stack

### Frontend
- **Next.js 15** - React framework with App Router
- **Tailwind CSS** - Utility-first CSS framework
- **Radix UI** - Accessible component primitives
- **Lucide Icons** - Beautiful SVG icons

### Backend
- **Python 3.13** - Modern Python with async support
- **FastAPI** - High-performance web framework
- **Google Gemini AI** - Advanced language model for content generation
- **Firebase Firestore** - NoSQL database for real-time data
- **APScheduler** - Background task scheduling
- **BeautifulSoup** - Web scraping for job discovery

### Infrastructure
- **Render.com** - Backend hosting and deployment
- **Vercel** - Frontend hosting (recommended)
- **GitHub Actions** - CI/CD pipeline (optional)

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- pnpm (recommended) or npm
- Firebase project
- Google Gemini API key

### Backend Setup

1. **Clone and navigate to backend**
   ```bash
   cd backend
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Setup**
   Create `.env` file:
   ```env
   PORT=8000
   ENVIRONMENT=development
   FIREBASE_SERVICE_ACCOUNT_PATH=firebase-service-account.json
   GEMINI_API_KEY=your_gemini_api_key_here
   MAX_REQUESTS_PER_HOUR=10
   MAX_REQUESTS_PER_DAY=50
   ```

4. **Firebase Setup**
   - Download service account key from Firebase Console
   - Save as `firebase-service-account.json` in backend folder

5. **Run Backend**
   ```bash
   python main.py
   ```

### Frontend Setup

1. **Navigate to frontend**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   pnpm install
   ```

3. **Environment Setup**
   Create `.env.local`:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

4. **Run Frontend**
   ```bash
   pnpm dev
   ```

### Keep-Alive Setup (Production)

For Render.com deployment, set up the cron job to prevent backend sleeping:

```bash
cd backend
./setup_keepalive.sh
```

## 📖 Usage

### 1. Generate Cover Letters
- Upload your CV (PDF format)
- Enter job title and details
- AI generates personalized cover letter
- Download as PDF

### 2. Automated Job Discovery
- Configure job search preferences
- System automatically discovers new jobs
- Jobs are filtered and stored in Firebase
- View discovered jobs in the Find Jobs page

### 3. Auto-Apply Scheduling
- Schedule automated applications
- Set frequency and limits
- Monitor application status
- Track responses and interviews

### 4. Dashboard Analytics
- View application statistics
- Track success rates
- Monitor job discovery performance
- Export data for analysis

## 🔧 Configuration

### Job Discovery Settings
Edit `backend/services/auto_job_discovery.py`:
```python
self.job_searches = [
    {"title": "Frontend Developer", "location": "remote"},
    {"title": "Full Stack Developer", "location": "remote"},
    # Add more search configurations
]
```

### Rate Limiting
Configure in `backend/utils/limiter.py`:
```python
MAX_REQUESTS_PER_HOUR = 10
MAX_REQUESTS_PER_DAY = 50
```

## 🚀 Deployment

### Backend (Render.com)

1. **Connect GitHub Repository**
2. **Configure Environment Variables**
3. **Set Build Command**: `pip install -r requirements.txt`
4. **Set Start Command**: `python main.py`
5. **Deploy**

### Frontend (Vercel)

1. **Connect GitHub Repository**
2. **Set Environment Variables**:
   ```env
   NEXT_PUBLIC_API_URL=https://your-backend-url.onrender.com
   ```
3. **Deploy**

## 📊 Monitoring

### Logs
- Backend logs: Check Render.com dashboard
- Keep-alive logs: `/tmp/backend_keepalive.log`
- Frontend logs: Browser console and Vercel dashboard

### Health Checks
- Backend health: `GET /health`
- Connection test: Use frontend connection test button
- Cron job status: `crontab -l`

## 🛡️ Security

- Environment variables for sensitive data
- Firebase security rules
- Rate limiting on API endpoints
- Input validation and sanitization
- CORS configuration for cross-origin requests

## 📝 API Endpoints

### Core Endpoints
- `POST /api/submit` - Submit job application
- `POST /api/search-jobs` - Search for jobs
- `GET /applications` - Get all applications
- `GET /applications/stats` - Get application statistics

### Job Discovery
- `GET /discovered-jobs` - Get discovered jobs
- `GET /discovery-stats` - Get discovery statistics
- `POST /start-job-discovery` - Start automated discovery
- `POST /stop-job-discovery` - Stop automated discovery

### Health & Monitoring
- `GET /health` - Health check endpoint
- `GET /` - Root endpoint (redirects to auto-apply)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Google Gemini AI for advanced language generation
- Firebase for real-time database capabilities
- Render.com for reliable backend hosting
- The open-source community for amazing tools and libraries

## 📞 Support

For support, email: [your-email@example.com] or create an issue on GitHub.

## 🔄 Changelog

### v1.0.0 (2025-06-27)
- Initial release
- AI-powered cover letter generation
- Automated job discovery
- Real-time dashboard
- Firebase integration
- Render.com deployment
- Cron job keep-alive system