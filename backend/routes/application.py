from fastapi import APIRouter, Request, Form, UploadFile, File, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import os
import aiofiles
import uuid
from typing import Optional, Annotated, List, Dict
import pathlib

from services.file_handler import FileHandler
from services.pdf_parser import PDFParser
from services.gemini_generator import GeminiGenerator
from services.pdf_writer import PDFWriter
from services.job_scraper import JobScraper
from services.auto_applicator import AutoApplicator
from services.firebase_service import firebase_service
from services.auto_job_discovery import auto_job_discovery
from utils.limiter import RateLimiter
from utils.scheduler import JobApplicationScheduler

router = APIRouter()

# Get the absolute path to the templates directory
base_dir = pathlib.Path(__file__).parent.parent
templates_dir = base_dir / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Initialize services
file_handler = FileHandler()
pdf_parser = PDFParser()
gemini_generator = GeminiGenerator()
pdf_writer = PDFWriter()
rate_limiter = RateLimiter()
job_scraper = JobScraper()
auto_applicator = AutoApplicator()
job_scheduler = JobApplicationScheduler()

# Get the global scheduler instance
def get_scheduler():
    """Get the global scheduler instance from main.py"""
    from main import scheduler
    return scheduler

@router.get("/", response_class=HTMLResponse)
async def get_form(request: Request):
    """
    Serve the job application form page.
    """
    return templates.TemplateResponse("form.html", {"request": request})

@router.post("/submit")
async def submit_application(
    request: Request,
    full_name: Annotated[str, Form()],
    email: Annotated[str, Form()],
    job_title: Annotated[str, Form()],
    cv: Annotated[UploadFile, File()],
    certificate: Annotated[Optional[UploadFile], File()] = None,
):
    """
    Handle job application form submission.
    Process uploaded files and generate a cover letter.
    """
    # Check rate limit
    rate_check = rate_limiter.check_rate_limit(email)
    if not rate_check["allowed"]:
        return templates.TemplateResponse(
            "form.html", 
            {
                "request": request, 
                "message": rate_check["message"], 
                "error": True
            }
        )
    
    try:
        # Save uploaded CV
        cv_success, cv_path = await file_handler.save_uploaded_file(
            cv, full_name, file_type="cv"
        )
        
        if not cv_success:
            return templates.TemplateResponse(
                "form.html", 
                {"request": request, "message": f"Error saving CV: {cv_path}", "error": True}
            )
        
        # Save certificate if provided
        cert_path = None
        if certificate:
            cert_success, cert_path = await file_handler.save_uploaded_file(
                certificate, full_name, file_type="certificate"
            )
            
            if not cert_success:
                return templates.TemplateResponse(
                    "form.html", 
                    {"request": request, "message": f"Error saving certificate: {cert_path}", "error": True}
                )
        
        # Parse the CV
        cv_data = pdf_parser.parse_cv(cv_path)
        cv_text = cv_data["full_text"]
        
        if not cv_text:
            return templates.TemplateResponse(
                "form.html", 
                {"request": request, "message": "Could not extract text from CV", "error": True}
            )
        
        # Generate cover letter using Gemini instead of GPT
        cover_letter_result = await gemini_generator.generate_cover_letter(
            cv_text=cv_text,
            job_title=job_title,
            name=full_name
        )
        
        if not cover_letter_result["success"]:
            return templates.TemplateResponse(
                "form.html", 
                {"request": request, "message": f"Error generating cover letter: {cover_letter_result.get('error', 'Unknown error')}", "error": True}
            )
        
        # Save cover letter as PDF
        cover_letter_text = cover_letter_result["cover_letter"]
        pdf_success, pdf_path = pdf_writer.generate_cover_letter_pdf(
            content=cover_letter_text,
            user_name=full_name,
            job_title=job_title
        )
        
        if not pdf_success or pdf_path is None:
            return templates.TemplateResponse(
                "form.html", 
                {"request": request, "message": "Failed to save cover letter as PDF", "error": True}
            )
        
        # Save application data to Firebase
        application_data = {
            "full_name": full_name,
            "email": email,
            "job_title": job_title,
            "status": "completed",
            "cvPath": cv_path,
            "coverLetterPath": pdf_path,
            "certificatePath": cert_path
        }
        
        firebase_result = await firebase_service.create_application(application_data)
        if not firebase_result["success"]:
            print(f"Warning: Failed to save to Firebase: {firebase_result.get('error')}")
        
        # Increment rate limit counters
        rate_limiter.increment_counters(email)
        
        # Get the relative PDF path for the URL
        pdf_relative_path = os.path.relpath(pdf_path, "backend")
        pdf_url = f"/{pdf_relative_path.replace(os.sep, '/')}"
        
        # Return success with cover letter and PDF link
        return templates.TemplateResponse(
            "form.html", 
            {
                "request": request, 
                "message": "Cover letter generated successfully with Gemini!", 
                "cover_letter": cover_letter_text,
                "pdf_url": pdf_url,
                "job_title": job_title,
                "full_name": full_name
            }
        )
        
    except Exception as e:
        return templates.TemplateResponse(
            "form.html", 
            {"request": request, "message": f"An error occurred: {str(e)}", "error": True}
        )

@router.get("/download/{file_path:path}")
async def download_file(file_path: str):
    """
    Serve file for download.
    """
    # Clean up the file path - remove any leading path separators
    file_path = file_path.lstrip('/')
    
    # If the path already includes static/uploads, use it as is
    # Otherwise, assume it's just the filename and prepend the uploads directory
    if file_path.startswith("static/uploads/"):
        # Path already includes static/uploads
        full_path = os.path.join("backend", file_path)
    else:
        # Just filename, add the uploads directory
        full_path = os.path.join("backend", "static", "uploads", file_path)
    
    # Security check to prevent directory traversal
    backend_static_path = os.path.normpath("backend/static")
    if not os.path.normpath(full_path).startswith(backend_static_path):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail=f"File not found: {full_path}")
    
    return FileResponse(path=full_path, filename=os.path.basename(full_path))

@router.get("/auto-apply", response_class=HTMLResponse)
async def get_auto_apply_form(request: Request):
    """
    Serve the automated job application form page.
    """
    return templates.TemplateResponse("auto_apply.html", {"request": request})

# Add alias for underscore version to handle both variations
@router.get("/auto_apply", response_class=HTMLResponse)
async def get_auto_apply_form_alias(request: Request):
    """
    Alias for auto-apply form page (underscore version).
    """
    return templates.TemplateResponse("auto_apply.html", {"request": request})

@router.post("/search-jobs")
async def search_jobs(
    request: Request,
    job_title: Annotated[str, Form()],
    location: Annotated[str, Form()] = "remote"
):
    """
    Search for job listings based on title and location.
    """
    try:
        # Get job listings
        jobs = await job_scraper.get_jobs(job_title, location)
        
        if not jobs:
            return templates.TemplateResponse(
                "auto_apply.html", 
                {
                    "request": request, 
                    "message": f"No jobs found for '{job_title}' in '{location}'", 
                    "error": True
                }
            )
        
        return templates.TemplateResponse(
            "auto_apply.html", 
            {
                "request": request, 
                "message": f"Found {len(jobs)} jobs for '{job_title}'", 
                "jobs": jobs,
                "job_title": job_title,
                "location": location
            }
        )
        
    except Exception as e:
        return templates.TemplateResponse(
            "auto_apply.html", 
            {"request": request, "message": f"Error searching jobs: {str(e)}", "error": True}
        )

@router.post("/auto-apply")
async def schedule_auto_apply(
    request: Request,
    background_tasks: BackgroundTasks,
    full_name: Annotated[str, Form()],
    email: Annotated[str, Form()],
    job_title: Annotated[str, Form()],
    location: Annotated[str, Form()],
    cv: Annotated[UploadFile, File()],
    max_applications: Annotated[int, Form()] = 5,
    schedule_type: Annotated[str, Form()] = "once",
    frequency_days: Annotated[int, Form()] = 7,
    total_runs: Annotated[Optional[int], Form()] = None
):
    """
    Schedule automated job applications based on user criteria.
    """
    # Check rate limit
    rate_check = rate_limiter.check_rate_limit(email)
    if not rate_check["allowed"]:
        return templates.TemplateResponse(
            "auto_apply.html", 
            {
                "request": request, 
                "message": rate_check["message"], 
                "error": True
            }
        )
    
    try:
        # Save uploaded CV
        cv_success, cv_path = await file_handler.save_uploaded_file(
            cv, full_name, file_type="cv"
        )
        
        if not cv_success:
            return templates.TemplateResponse(
                "auto_apply.html", 
                {"request": request, "message": f"Error saving CV: {cv_path}", "error": True}
            )
        
        # Generate a unique user ID
        user_id = str(uuid.uuid4())
        
        # Schedule the auto-application task
        scheduler = get_scheduler()
        job_id = await scheduler.schedule_auto_application(
            user_id=user_id,
            user_name=full_name,
            user_email=email,
            job_title=job_title,
            location=location,
            cv_path=cv_path,
            schedule_type=schedule_type,
            max_applications_per_run=max_applications,
            frequency_days=frequency_days,
            total_runs=total_runs
        )
        
        # Save auto-apply submission to Firebase database
        auto_apply_data = {
            "full_name": full_name,
            "email": email,
            "job_title": job_title,
            "location": location,
            "status": "auto_apply_scheduled",
            "type": "auto_apply",
            "schedule_type": schedule_type,
            "max_applications": max_applications,
            "frequency_days": frequency_days,
            "total_runs": total_runs,
            "job_id": job_id,
            "user_id": user_id,
            "cvPath": cv_path,
            "application_notes": f"Auto-apply job scheduled for {job_title} in {location}. Max {max_applications} applications per run."
        }
        
        firebase_result = await firebase_service.create_application(auto_apply_data)
        if not firebase_result["success"]:
            print(f"Warning: Failed to save auto-apply submission to Firebase: {firebase_result.get('error')}")
        else:
            print(f"✅ Auto-apply submission saved to Firebase with ID: {firebase_result.get('id')}")
        
        # Increment rate limit counters
        rate_limiter.increment_counters(email)
        
        return templates.TemplateResponse(
            "auto_apply.html", 
            {
                "request": request, 
                "message": f"Auto-application job scheduled successfully! Job ID: {job_id}", 
                "job_id": job_id,
                "schedule_info": await job_scheduler.get_job_details(job_id)
            }
        )
        
    except Exception as e:
        return templates.TemplateResponse(
            "auto_apply.html", 
            {"request": request, "message": f"An error occurred: {str(e)}", "error": True}
        )

# Add alias for underscore version to handle both variations
@router.post("/auto_apply")
async def schedule_auto_apply_alias(
    request: Request,
    background_tasks: BackgroundTasks,
    full_name: Annotated[str, Form()],
    email: Annotated[str, Form()],
    job_title: Annotated[str, Form()],
    location: Annotated[str, Form()],
    cv: Annotated[UploadFile, File()],
    max_applications: Annotated[int, Form()] = 5,
    schedule_type: Annotated[str, Form()] = "once",
    frequency_days: Annotated[int, Form()] = 7,
    total_runs: Annotated[Optional[int], Form()] = None
):
    """
    Alias for auto-apply scheduling (underscore version).
    """
    return await schedule_auto_apply(
        request, background_tasks, full_name, email, job_title, location, cv,
        max_applications, schedule_type, frequency_days, total_runs
    )

@router.get("/application-status/{user_email}")
async def get_application_status(request: Request, user_email: str):
    """
    Get status of all job applications for a user.
    """
    try:
        # Get application summary
        summary = await auto_applicator.get_application_summary(user_email)
        
        return templates.TemplateResponse(
            "application_status.html", 
            {
                "request": request, 
                "summary": summary,
                "user_email": user_email
            }
        )
        
    except Exception as e:
        return templates.TemplateResponse(
            "auto_apply.html", 
            {"request": request, "message": f"Error getting application status: {str(e)}", "error": True}
        )

@router.get("/scheduled-jobs/{user_id}")
async def get_scheduled_jobs(request: Request, user_id: str):
    """
    Get all scheduled jobs for a user.
    """
    try:
        jobs = job_scheduler.get_scheduled_jobs(user_id)
        
        return templates.TemplateResponse(
            "scheduled_jobs.html", 
            {
                "request": request, 
                "jobs": jobs,
                "user_id": user_id
            }
        )
        
    except Exception as e:
        return templates.TemplateResponse(
            "auto_apply.html", 
            {"request": request, "message": f"Error getting scheduled jobs: {str(e)}", "error": True}
        )

@router.post("/cancel-job/{job_id}")
async def cancel_job(request: Request, job_id: str):
    """
    Cancel a scheduled job.
    """
    try:
        scheduler = get_scheduler()
        success = await scheduler.cancel_job(job_id)
        if success:
            return JSONResponse(content={"success": True, "message": "Job cancelled successfully"})
        else:
            raise HTTPException(status_code=404, detail="Job not found")
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": f"Error: {str(e)}"},
            status_code=500
        )

# --- Dashboard Endpoints ---

@router.get("/applications")
async def get_applications():
    """
    Return a list of all job applications from Firebase.
    """
    try:
        result = await firebase_service.get_all_applications()
        if result["success"]:
            return result
        else:
            # Fallback to mock data if Firebase is not available
            mock_applications = [
                {
                    "id": "1",
                    "full_name": "Miracle Ezechukwu",
                    "email": "miracle@example.com",
                    "job_title": "Frontend Developer",
                    "status": "completed",
                    "createdAt": "2025-06-27T15:29:00Z",
                    "coverLetterPath": "static/uploads/cover_letter_Miracle_Ezechukwu_Frontend_developer_20250627152927.pdf",
                    "cvPath": "static/uploads/cv_Miracle_Ezechukwu_20250627152923_41e780ac.pdf",
                    "company_name": "TechCorp Solutions",
                    "company_email": "hr@techcorp.com",
                    "job_description": "We are seeking a talented Frontend Developer to join our dynamic team. The ideal candidate will have experience with React, JavaScript, and modern web technologies. You'll be responsible for creating responsive user interfaces and collaborating with our design and backend teams.",
                    "job_board": "LinkedIn",
                    "application_url": "https://linkedin.com/jobs/frontend-developer-123456",
                    "email_sent": True,
                    "email_sent_to": "hr@techcorp.com",
                    "email_subject": "Application for Frontend Developer Position - Miracle Ezechukwu",
                    "email_body": "Dear Hiring Manager at TechCorp Solutions,\n\nI hope this email finds you well. I am writing to express my strong interest in the Frontend Developer position at TechCorp Solutions...",
                    "email_sent_at": "2025-06-27T15:30:00Z",
                    "response_received": False,
                    "application_notes": "Applied through LinkedIn. Strong match for React skills."
                },
                {
                    "id": "2",
                    "full_name": "Miracle Ezechukwu",
                    "email": "miracle@example.com",
                    "job_title": "Full Stack Developer",
                    "status": "completed",
                    "createdAt": "2025-06-26T14:20:00Z",
                    "coverLetterPath": "static/uploads/cover_letter_Miracle_Ezechukwu_Full_Stack_developer_20250626142000.pdf",
                    "cvPath": "static/uploads/cv_Miracle_Ezechukwu_20250626142000_41e780ac.pdf",
                    "company_name": "InnovateLabs Inc",
                    "company_email": "careers@innovatelabs.com",
                    "job_description": "Looking for a Full Stack Developer with expertise in Node.js, React, and database management. The role involves building scalable web applications and working closely with product managers to deliver high-quality software solutions.",
                    "job_board": "Indeed",
                    "application_url": "https://indeed.com/jobs/full-stack-developer-789012",
                    "email_sent": True,
                    "email_sent_to": "careers@innovatelabs.com",
                    "email_subject": "Application for Full Stack Developer Position - Miracle Ezechukwu",
                    "email_body": "Dear Hiring Manager at InnovateLabs Inc,\n\nI am excited to apply for the Full Stack Developer position...",
                    "email_sent_at": "2025-06-26T14:25:00Z",
                    "response_received": True,
                    "response_date": "2025-06-27T09:15:00Z",
                    "interview_scheduled": True,
                    "interview_date": "2025-06-30T10:00:00Z",
                    "application_notes": "Received positive response! Interview scheduled for Monday."
                },
                {
                    "id": "3",
                    "full_name": "Miracle Ezechukwu",
                    "email": "miracle@example.com",
                    "job_title": "React Developer",
                    "status": "completed",
                    "createdAt": "2025-06-25T11:45:00Z",
                    "coverLetterPath": "static/uploads/cover_letter_Miracle_Ezechukwu_React_developer_20250625114500.pdf",
                    "cvPath": "static/uploads/cv_Miracle_Ezechukwu_20250625114500_41e780ac.pdf",
                    "company_name": "StartupXYZ",
                    "company_email": "hello@startupxyz.com",
                    "job_description": "Early-stage startup seeking a React Developer to build our customer-facing platform. Must have experience with React, TypeScript, and state management. Equity compensation available.",
                    "job_board": "AngelList",
                    "application_url": "https://angel.co/company/startupxyz/jobs/react-developer",
                    "email_sent": True,
                    "email_sent_to": "hello@startupxyz.com",
                    "email_subject": "Application for React Developer Position - Miracle Ezechukwu",
                    "email_body": "Dear Startup Team,\n\nI'm thrilled to apply for the React Developer position at StartupXYZ...",
                    "email_sent_at": "2025-06-25T11:50:00Z",
                    "response_received": False,
                    "application_notes": "Startup environment, potential for equity. No response yet."
                }
            ]
            return {"success": True, "data": mock_applications}
    except Exception as e:
        print(f"Error in get_applications: {e}")
        # Return mock data as fallback
        mock_applications = [
            {
                "id": "1",
                "full_name": "Miracle Ezechukwu",
                "email": "miracle@example.com",
                "job_title": "Frontend Developer",
                "status": "completed",
                "createdAt": "2025-06-27T15:29:00Z",
                "coverLetterPath": "static/uploads/cover_letter_Miracle_Ezechukwu_Frontend_developer_20250627152927.pdf",
                "cvPath": "static/uploads/cv_Miracle_Ezechukwu_20250627152923_41e780ac.pdf",
                "company_name": "TechCorp Solutions",
                "company_email": "hr@techcorp.com",
                "job_description": "We are seeking a talented Frontend Developer to join our dynamic team. The ideal candidate will have experience with React, JavaScript, and modern web technologies.",
                "job_board": "LinkedIn",
                "application_url": "https://linkedin.com/jobs/frontend-developer-123456",
                "email_sent": True,
                "email_sent_to": "hr@techcorp.com",
                "email_subject": "Application for Frontend Developer Position - Miracle Ezechukwu",
                "email_body": "Dear Hiring Manager at TechCorp Solutions...",
                "email_sent_at": "2025-06-27T15:30:00Z",
                "response_received": False,
                "application_notes": "Applied through LinkedIn. Strong match for React skills."
            }
        ]
        return {"success": True, "data": mock_applications}

@router.get("/applications/stats")
async def get_application_stats():
    """
    Return summary statistics for dashboard cards from Firebase.
    """
    try:
        result = await firebase_service.get_application_stats()
        if result["success"]:
            return result
        else:
            # Fallback to mock data if Firebase is not available
            stats = {
                "totalApplications": 1,
                "completedApplications": 1,
                "pendingApplications": 0,
                "failedApplications": 0,
                "successRate": 100
            }
            return {"success": True, "data": stats}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.delete("/applications/{application_id}")
async def delete_application(application_id: str):
    """
    Delete an application by ID from Firebase.
    """
    try:
        result = await firebase_service.delete_application(application_id)
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

# --- API Endpoints (JSON responses for frontend) ---

@router.post("/api/submit")
async def api_submit_application(
    request: Request,
    full_name: Annotated[str, Form()],
    email: Annotated[str, Form()],
    job_title: Annotated[str, Form()],
    cv: Annotated[UploadFile, File()],
    certificate: Annotated[Optional[UploadFile], File()] = None,
):
    """
    API version of submit_application that returns JSON responses.
    """
    # Check rate limit
    rate_check = rate_limiter.check_rate_limiter(email)
    if not rate_check["allowed"]:
        return JSONResponse(
            content={"success": False, "error": rate_check["message"]},
            status_code=429
        )
    
    try:
        # Save uploaded CV
        cv_success, cv_path = await file_handler.save_uploaded_file(
            cv, full_name, file_type="cv"
        )
        
        if not cv_success:
            return JSONResponse(
                content={"success": False, "error": f"Error saving CV: {cv_path}"},
                status_code=400
            )
        
        # Save certificate if provided
        cert_path = None
        if certificate:
            cert_success, cert_path = await file_handler.save_uploaded_file(
                certificate, full_name, file_type="certificate"
            )
            
            if not cert_success:
                return JSONResponse(
                    content={"success": False, "error": f"Error saving certificate: {cert_path}"},
                    status_code=400
                )
        
        # Parse the CV
        cv_data = pdf_parser.parse_cv(cv_path)
        cv_text = cv_data["full_text"]
        
        if not cv_text:
            return JSONResponse(
                content={"success": False, "error": "Could not extract text from CV"},
                status_code=400
            )
        
        # Generate cover letter using Gemini
        cover_letter_result = await gemini_generator.generate_cover_letter(
            cv_text=cv_text,
            job_title=job_title,
            name=full_name
        )
        
        if not cover_letter_result["success"]:
            return JSONResponse(
                content={"success": False, "error": f"Error generating cover letter: {cover_letter_result.get('error', 'Unknown error')}"},
                status_code=500
            )
        
        # Save cover letter as PDF
        cover_letter_text = cover_letter_result["cover_letter"]
        pdf_success, pdf_path = pdf_writer.generate_cover_letter_pdf(
            content=cover_letter_text,
            user_name=full_name,
            job_title=job_title
        )
        
        if not pdf_success or pdf_path is None:
            return JSONResponse(
                content={"success": False, "error": "Failed to save cover letter as PDF"},
                status_code=500
            )
        
        # Save application data to Firebase
        application_data = {
            "full_name": full_name,
            "email": email,
            "job_title": job_title,
            "status": "completed",
            "cvPath": cv_path,
            "coverLetterPath": pdf_path,
            "certificatePath": cert_path
        }
        
        firebase_result = await firebase_service.create_application(application_data)
        if not firebase_result["success"]:
            print(f"Warning: Failed to save to Firebase: {firebase_result.get('error')}")
        
        # Increment rate limit counters
        rate_limiter.increment_counters(email)
        
        # Get the relative PDF path for the URL
        pdf_relative_path = os.path.relpath(pdf_path, "backend")
        pdf_url = f"/{pdf_relative_path.replace(os.sep, '/')}"
        
        return JSONResponse(content={
            "success": True,
            "message": "Cover letter generated successfully!",
            "data": {
                "cover_letter": cover_letter_text,
                "pdf_url": pdf_url,
                "cv_path": cv_path,
                "cover_letter_path": pdf_path,
                "job_title": job_title,
                "full_name": full_name
            }
        })
        
    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": f"An error occurred: {str(e)}"},
            status_code=500
        )

@router.post("/api/search-jobs")
async def api_search_jobs(
    request: Request,
    job_title: Annotated[str, Form()],
    location: Annotated[str, Form()] = "remote"
):
    """
    API version of search_jobs that returns JSON responses.
    """
    try:
        # Get job listings
        jobs = await job_scraper.get_jobs(job_title, location)
        
        if not jobs:
            return JSONResponse(content={
                "success": False,
                "error": f"No jobs found for '{job_title}' in '{location}'"
            })
        
        return JSONResponse(content={
            "success": True,
            "message": f"Found {len(jobs)} jobs for '{job_title}'",
            "data": {
                "jobs": jobs,
                "job_title": job_title,
                "location": location,
                "count": len(jobs)
            }
        })
        
    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": f"Error searching jobs: {str(e)}"},
            status_code=500
        )

@router.get("/api/health")
async def health_check():
    """
    Health check endpoint for monitoring backend status.
    """
    return JSONResponse(content={
        "success": True,
        "status": "healthy",
        "message": "Backend is running",
        "timestamp": "2025-06-27T15:30:00Z"
    })

@router.get("/api/cover-letter/{application_id}")
async def get_cover_letter_content(application_id: str):
    """
    Get cover letter content for a specific application.
    """
    try:
        # Try to get from Firebase first
        result = await firebase_service.get_all_applications()
        if result["success"]:
            application = next((app for app in result["data"] if app["id"] == application_id), None)
            if application and application.get("coverLetterPath"):
                # Try to read the PDF content (this would need a PDF text extractor)
                # For now, return a structured response
                return JSONResponse(content={
                    "success": True,
                    "content": f"""Dear Hiring Manager,

I am writing to express my strong interest in the {application.get('job_title', 'position')} role at your company.

[This cover letter was generated for {application.get('full_name', 'the applicant')} on {application.get('createdAt', 'the application date')}]

With my background and experience, I believe I would be a valuable addition to your team. I have attached my CV for your review and would welcome the opportunity to discuss how my skills can contribute to your organization.

Thank you for considering my application. I look forward to hearing from you.

Best regards,
{application.get('full_name', 'Applicant')}

---
Application Details:
- Position: {application.get('job_title', 'N/A')}
- Status: {application.get('status', 'N/A')}
- Created: {application.get('createdAt', 'N/A')}
- Cover Letter File: {application.get('coverLetterPath', 'N/A')}""",
                    "application": application
                })
        
        return JSONResponse(
            content={"success": False, "error": "Application not found"},
            status_code=404
        )
        
    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": f"Error fetching cover letter: {str(e)}"},
            status_code=500
        )

@router.post("/start-job-discovery")
async def start_job_discovery(request: Request):
    """Start automated job discovery"""
    try:
        form_data = await request.form()
        interval_hours_raw = form_data.get("interval_hours", "2")
        interval_hours = int(interval_hours_raw) if isinstance(interval_hours_raw, str) else 2
        
        await auto_job_discovery.start_auto_discovery(interval_hours)
        
        return {
            "success": True,
            "message": f"Auto job discovery started - running every {interval_hours} hours"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/stop-job-discovery")
async def stop_job_discovery():
    """Stop automated job discovery"""
    try:
        await auto_job_discovery.stop_auto_discovery()
        return {"success": True, "message": "Auto job discovery stopped"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/discovered-jobs")
async def get_discovered_jobs(
    limit: int = 50,
    job_title: str = None,
    source: str = None
):
    """Get discovered jobs with optional filtering"""
    try:
        result = await auto_job_discovery.get_discovered_jobs(
            limit=limit,
            job_title_filter=job_title,
            source_filter=source
        )
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/discovery-stats")
async def get_discovery_stats():
    """Get job discovery statistics"""
    try:
        result = await auto_job_discovery.get_discovery_stats()
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/trigger-job-discovery")
async def trigger_job_discovery():
    """Manually trigger job discovery"""
    try:
        await auto_job_discovery._discover_jobs()
        return {"success": True, "message": "Job discovery triggered successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# API endpoints for frontend integration
@router.get("/api/jobs/discovered")
async def api_get_discovered_jobs(
    limit: int = 50,
    job_title: str = None,
    source: str = None
):
    """API endpoint to get discovered jobs with optional filtering"""
    try:
        result = await auto_job_discovery.get_discovered_jobs(
            limit=limit,
            job_title_filter=job_title,
            source_filter=source
        )
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/api/jobs/discovery-stats")
async def api_get_discovery_stats():
    """API endpoint to get job discovery statistics"""
    try:
        result = await auto_job_discovery.get_discovery_stats()
        return result
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/api/jobs/start-discovery")
async def api_start_job_discovery(request: Request):
    """API endpoint to start automated job discovery"""
    try:
        data = await request.json()
        interval_hours = data.get("interval_hours", 2)
        
        await auto_job_discovery.start_auto_discovery(interval_hours)
        
        return {
            "success": True,
            "message": f"Auto job discovery started - running every {interval_hours} hours"
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/search-custom-job")
async def search_custom_job(request: Request):
    """Search for a custom job title specified by the user"""
    try:
        data = await request.json()
        job_title = data.get("job_title", "").strip()
        locations = data.get("locations", ["remote"])
        job_types = data.get("job_types", ["full-time"])
        
        if not job_title:
            return {"success": False, "error": "Job title is required"}
        
        result = await auto_job_discovery.search_custom_job_title(
            job_title=job_title,
            locations=locations,
            job_types=job_types
        )
        
        return result
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/tech-job-titles")
async def get_tech_job_titles():
    """Get list of available tech job titles for autocomplete"""
    try:
        return {
            "success": True,
            "data": auto_job_discovery.dynamic_job_searches
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/discovery-status")
async def get_discovery_status():
    """Get detailed status of the auto discovery service"""
    try:
        return {
            "success": True,
            "data": {
                "is_running": auto_job_discovery.is_running,
                "total_job_titles": len(auto_job_discovery.dynamic_job_searches),
                "total_locations": len(auto_job_discovery.tech_locations),
                "job_types": auto_job_discovery.job_types,
                "discovery_frequency": "Every hour + priority every 30 minutes",
                "cleanup_frequency": "Every 6 hours (removes jobs > 72 hours old)"
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/api/auto-apply")
async def api_schedule_auto_apply(
    request: Request,
    background_tasks: BackgroundTasks,
    full_name: Annotated[str, Form()],
    email: Annotated[str, Form()],
    job_title: Annotated[str, Form()],
    location: Annotated[str, Form()],
    cv: Annotated[UploadFile, File()],
    max_applications: Annotated[int, Form()] = 5,
    schedule_type: Annotated[str, Form()] = "once",
    frequency_days: Annotated[int, Form()] = 7,
    total_runs: Annotated[Optional[int], Form()] = None
):
    """
    API version of auto-apply scheduling that returns JSON responses.
    """
    # Check rate limit
    rate_check = rate_limiter.check_rate_limiter(email)
    if not rate_check["allowed"]:
        return JSONResponse(
            content={"success": False, "error": rate_check["message"]},
            status_code=429
        )
    
    try:
        # Save uploaded CV
        cv_success, cv_path = await file_handler.save_uploaded_file(
            cv, full_name, file_type="cv"
        )
        
        if not cv_success:
            return JSONResponse(
                content={"success": False, "error": f"Error saving CV: {cv_path}"},
                status_code=400
            )
        
        # Generate a unique user ID
        user_id = str(uuid.uuid4())
        
        # Schedule the auto-application task
        scheduler = get_scheduler()
        job_id = await scheduler.schedule_auto_application(
            user_id=user_id,
            user_name=full_name,
            user_email=email,
            job_title=job_title,
            location=location,
            cv_path=cv_path,
            schedule_type=schedule_type,
            max_applications_per_run=max_applications,
            frequency_days=frequency_days,
            total_runs=total_runs
        )
        
        # Save auto-apply submission to Firebase database
        auto_apply_data = {
            "full_name": full_name,
            "email": email,
            "job_title": job_title,
            "location": location,
            "status": "auto_apply_scheduled",
            "type": "auto_apply",
            "schedule_type": schedule_type,
            "max_applications": max_applications,
            "frequency_days": frequency_days,
            "total_runs": total_runs,
            "job_id": job_id,
            "user_id": user_id,
            "cvPath": cv_path,
            "application_notes": f"Auto-apply job scheduled for {job_title} in {location}. Max {max_applications} applications per run."
        }
        
        firebase_result = await firebase_service.create_application(auto_apply_data)
        if not firebase_result["success"]:
            print(f"Warning: Failed to save auto-apply submission to Firebase: {firebase_result.get('error')}")
        else:
            print(f"✅ Auto-apply submission saved to Firebase with ID: {firebase_result.get('id')}")
        
        # Increment rate limit counters
        rate_limiter.increment_counters(email)
        
        return JSONResponse(content={
            "success": True,
            "message": f"Auto-application job scheduled successfully!",
            "data": {
                "job_id": job_id,
                "schedule_info": await scheduler.get_job_details(job_id),
                "user_id": user_id,
                "cv_path": cv_path
            }
        })
        
    except Exception as e:
        print(f"Error in API auto-apply: {str(e)}")
        return JSONResponse(
            content={"success": False, "error": f"An error occurred: {str(e)}"},
            status_code=500
        )

@router.get("/api/scheduled-jobs/{user_email}")
async def api_get_scheduled_jobs_by_email(user_email: str):
    """
    API endpoint to get scheduled jobs by user email.
    """
    try:
        # Get all jobs and filter by email
        all_jobs = await get_scheduler().get_all_jobs()
        user_jobs = []
        
        for job_id, job in all_jobs.items():
            if job.get("user_email") == user_email:
                user_jobs.append({
                    "id": job_id,
                    "job_title": job.get("job_title"),
                    "location": job.get("location"),
                    "status": job.get("status"),
                    "schedule_type": job.get("schedule_type"),
                    "created_at": job.get("created_at"),
                    "next_run": job.get("next_run"),
                    "last_run": job.get("last_run"),
                    "runs_completed": job.get("runs_completed", 0),
                    "max_applications_per_run": job.get("max_applications_per_run"),
                    "last_result": job.get("last_result")
                })
        
        return JSONResponse(content={
            "success": True,
            "data": user_jobs
        })
        
    except Exception as e:
        return JSONResponse(
            content={"success": False, "error": str(e)},
            status_code=500
        )