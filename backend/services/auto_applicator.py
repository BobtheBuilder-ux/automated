import os
import logging
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import aiofiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .job_scraper import JobScraper
from .pdf_parser import PDFParser
from .gemini_generator import GeminiGenerator
from .pdf_writer import PDFWriter
from .email_service import EmailService
from .firebase_service import firebase_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='auto_application.log'
)
logger = logging.getLogger(__name__)

class AutoApplicator:
    """Service to automatically apply to jobs based on scraped listings."""
    
    def __init__(self):
        self.job_scraper = JobScraper()
        self.pdf_parser = PDFParser()
        self.generator = GeminiGenerator()
        self.pdf_writer = PDFWriter()
        self.email_service = EmailService()
        self.scheduler = AsyncIOScheduler()
        self.active_schedules = {}  # Track active scheduled applications
        
        # Ensure application history directory exists
        self.history_dir = os.path.join("backend", "static", "application_history")
        os.makedirs(self.history_dir, exist_ok=True)

    async def start_hourly_auto_apply(
        self,
        user_name: str,
        user_email: str,
        job_title: str,
        location: str = "remote",
        cv_path: str = None,
        max_applications_per_hour: int = 3
    ) -> Dict[str, any]:
        """
        Start hourly auto-application for a specific job title.
        
        Args:
            user_name: Name of the applicant
            user_email: Email of the applicant
            job_title: Job title to search for every hour
            location: Location to search in
            cv_path: Path to the CV file
            max_applications_per_hour: Max applications to submit each hour
            
        Returns:
            Dictionary with success status and schedule ID
        """
        try:
            # Generate unique schedule ID
            schedule_id = f"auto_apply_{user_email}_{job_title}".replace(" ", "_").replace("@", "_at_")
            
            # Stop existing schedule for this user/job title if it exists
            if schedule_id in self.active_schedules:
                self.scheduler.remove_job(schedule_id)
                logger.info(f"Stopped existing hourly auto-apply for {user_email} - {job_title}")
            
            # Store schedule configuration
            self.active_schedules[schedule_id] = {
                "user_name": user_name,
                "user_email": user_email,
                "job_title": job_title,
                "location": location,
                "cv_path": cv_path,
                "max_applications_per_hour": max_applications_per_hour,
                "created_at": datetime.now().isoformat(),
                "last_run": None,
                "total_applications": 0
            }
            
            # Schedule the job to run every hour
            self.scheduler.add_job(
                self._hourly_apply_job,
                IntervalTrigger(hours=1),
                id=schedule_id,
                args=[schedule_id],
                replace_existing=True
            )
            
            # Start scheduler if not already running
            if not self.scheduler.running:
                self.scheduler.start()
            
            # Save schedule to persistent storage
            await self._save_schedule_config(schedule_id)
            
            logger.info(f"Started hourly auto-apply for {user_email} - {job_title} (Schedule ID: {schedule_id})")
            
            return {
                "success": True,
                "schedule_id": schedule_id,
                "message": f"Hourly auto-apply started for '{job_title}'. Will check for new jobs every hour.",
                "next_run": "In 1 hour"
            }
            
        except Exception as e:
            logger.error(f"Error starting hourly auto-apply: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _hourly_apply_job(self, schedule_id: str):
        """
        Execute the hourly auto-application job.
        
        Args:
            schedule_id: Unique identifier for the scheduled job
        """
        try:
            if schedule_id not in self.active_schedules:
                logger.error(f"Schedule {schedule_id} not found in active schedules")
                return
            
            config = self.active_schedules[schedule_id]
            logger.info(f"Running hourly auto-apply for {config['user_email']} - {config['job_title']}")
            
            # Apply to jobs
            success, applications, message = await self.apply_to_jobs(
                user_name=config["user_name"],
                user_email=config["user_email"],
                job_title=config["job_title"],
                location=config["location"],
                cv_path=config["cv_path"],
                max_applications=config["max_applications_per_hour"]
            )
            
            # Update schedule stats
            config["last_run"] = datetime.now().isoformat()
            config["total_applications"] += len(applications) if applications else 0
            
            # Save updated config
            await self._save_schedule_config(schedule_id)
            
            # Send hourly summary email if applications were made
            if applications:
                await self.email_service.send_hourly_application_summary(
                    recipient_email=config["user_email"],
                    name=config["user_name"],
                    job_title=config["job_title"],
                    applications=applications,
                    total_applications_today=config["total_applications"]
                )
            
            logger.info(f"Hourly auto-apply completed: {len(applications) if applications else 0} applications submitted")
            
        except Exception as e:
            logger.error(f"Error in hourly apply job {schedule_id}: {str(e)}")

    async def stop_hourly_auto_apply(self, user_email: str, job_title: str = None) -> Dict[str, any]:
        """
        Stop hourly auto-application for a user/job title.
        
        Args:
            user_email: Email of the applicant
            job_title: Specific job title to stop (if None, stops all for user)
            
        Returns:
            Dictionary with success status
        """
        try:
            stopped_schedules = []
            
            # Find matching schedules to stop
            schedules_to_remove = []
            for schedule_id, config in self.active_schedules.items():
                if config["user_email"] == user_email:
                    if job_title is None or config["job_title"] == job_title:
                        schedules_to_remove.append(schedule_id)
                        stopped_schedules.append(config["job_title"])
            
            # Remove the schedules
            for schedule_id in schedules_to_remove:
                if self.scheduler.get_job(schedule_id):
                    self.scheduler.remove_job(schedule_id)
                del self.active_schedules[schedule_id]
                await self._delete_schedule_config(schedule_id)
            
            if not stopped_schedules:
                return {
                    "success": False,
                    "message": "No active auto-apply schedules found for the specified criteria"
                }
            
            logger.info(f"Stopped hourly auto-apply schedules for {user_email}: {stopped_schedules}")
            
            return {
                "success": True,
                "message": f"Stopped auto-apply for: {', '.join(stopped_schedules)}",
                "stopped_count": len(stopped_schedules)
            }
            
        except Exception as e:
            logger.error(f"Error stopping hourly auto-apply: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_active_schedules(self, user_email: str = None) -> Dict[str, any]:
        """
        Get list of active auto-apply schedules.
        
        Args:
            user_email: Email filter (if None, returns all schedules)
            
        Returns:
            Dictionary with active schedules
        """
        try:
            if user_email:
                user_schedules = {
                    schedule_id: config 
                    for schedule_id, config in self.active_schedules.items()
                    if config["user_email"] == user_email
                }
            else:
                user_schedules = self.active_schedules.copy()
            
            return {
                "success": True,
                "schedules": user_schedules,
                "total_active": len(user_schedules)
            }
            
        except Exception as e:
            logger.error(f"Error getting active schedules: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _save_schedule_config(self, schedule_id: str):
        """Save schedule configuration to persistent storage."""
        try:
            schedules_file = os.path.join(self.history_dir, "active_schedules.json")
            
            # Load existing schedules
            existing_schedules = {}
            if os.path.exists(schedules_file):
                async with aiofiles.open(schedules_file, "r") as f:
                    existing_schedules = json.loads(await f.read())
            
            # Update with current schedule
            existing_schedules[schedule_id] = self.active_schedules[schedule_id]
            
            # Save back to file
            async with aiofiles.open(schedules_file, "w") as f:
                await f.write(json.dumps(existing_schedules, indent=2))
                
        except Exception as e:
            logger.error(f"Error saving schedule config: {str(e)}")

    async def _delete_schedule_config(self, schedule_id: str):
        """Delete schedule configuration from persistent storage."""
        try:
            schedules_file = os.path.join(self.history_dir, "active_schedules.json")
            
            if os.path.exists(schedules_file):
                async with aiofiles.open(schedules_file, "r") as f:
                    existing_schedules = json.loads(await f.read())
                
                if schedule_id in existing_schedules:
                    del existing_schedules[schedule_id]
                    
                    async with aiofiles.open(schedules_file, "w") as f:
                        await f.write(json.dumps(existing_schedules, indent=2))
                        
        except Exception as e:
            logger.error(f"Error deleting schedule config: {str(e)}")

    async def restore_schedules_on_startup(self):
        """Restore active schedules when the service starts."""
        try:
            schedules_file = os.path.join(self.history_dir, "active_schedules.json")
            
            if not os.path.exists(schedules_file):
                return
            
            async with aiofiles.open(schedules_file, "r") as f:
                saved_schedules = json.loads(await f.read())
            
            for schedule_id, config in saved_schedules.items():
                # Restore to active schedules
                self.active_schedules[schedule_id] = config
                
                # Re-add to scheduler
                self.scheduler.add_job(
                    self._hourly_apply_job,
                    IntervalTrigger(hours=1),
                    id=schedule_id,
                    args=[schedule_id],
                    replace_existing=True
                )
            
            # Start scheduler if not already running
            if saved_schedules and not self.scheduler.running:
                self.scheduler.start()
            
            logger.info(f"Restored {len(saved_schedules)} auto-apply schedules on startup")
            
        except Exception as e:
            logger.error(f"Error restoring schedules on startup: {str(e)}")

    async def apply_to_jobs(
        self,
        user_name: str,
        user_email: str,
        job_title: str,
        location: str,
        cv_path: str,
        max_applications: int = 5
    ) -> Tuple[bool, List[Dict], str]:
        """
        Apply to jobs automatically.
        
        Args:
            user_name: Name of the applicant
            user_email: Email of the applicant
            job_title: Job title to search for
            location: Location to search in
            cv_path: Path to the CV file
            max_applications: Maximum number of applications to submit
            
        Returns:
            Tuple of (success, applications_list, error_message)
        """
        try:
            # Get job listings
            jobs = await self.job_scraper.get_jobs(job_title, location)
            
            if not jobs:
                return False, [], f"No jobs found for '{job_title}' in '{location}'"
                
            # Parse CV
            cv_text = await self.pdf_parser.parse_pdf(cv_path)
            if not cv_text:
                return False, [], "Failed to parse CV"
            
            # Filter jobs to avoid duplicates
            filtered_jobs = await self._filter_jobs(jobs, user_email)
            
            if not filtered_jobs:
                return False, [], "No new jobs found that haven't been applied to already"
                
            # Limit applications
            jobs_to_apply = filtered_jobs[:max_applications]
            
            # Apply to each job
            applications = []
            for job in jobs_to_apply:
                success, cover_letter_path = await self._apply_to_job(
                    job=job,
                    cv_text=cv_text,
                    user_name=user_name,
                    user_email=user_email,
                    cv_path=cv_path
                )
                
                if success:
                    job["status"] = "applied"
                    job["applied_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    job["cover_letter_path"] = cover_letter_path
                    applications.append(job)
                    
                    # Send confirmation email for each application
                    await self.email_service.send_application_confirmation(
                        recipient_email=user_email,
                        name=user_name,
                        job_title=job.get("title", ""),
                        company=job.get("company", ""),
                        cover_letter_path=cover_letter_path
                    )
            
            # Save application history
            await self._save_applications(applications, user_email)
            
            # If applications were made, send a summary email
            if applications:
                await self.email_service.send_application_summary(
                    recipient_email=user_email,
                    name=user_name,
                    applications=applications,
                    job_title=job_title
                )
            
            return True, applications, f"Successfully applied to {len(applications)} jobs"
            
        except Exception as e:
            logger.error(f"Error in apply_to_jobs: {str(e)}")
            return False, [], f"Error in apply_to_jobs: {str(e)}"
    
    async def _apply_to_job(
        self,
        job: Dict,
        cv_text: str,
        user_name: str,
        user_email: str,
        cv_path: str
    ) -> Tuple[bool, str]:
        """
        Apply to a specific job.
        
        Args:
            job: Job details
            cv_text: CV text content
            user_name: Name of the applicant
            user_email: Email of the applicant
            cv_path: Path to the CV file
            
        Returns:
            Tuple of (success, cover_letter_path)
        """
        try:
            # Get job details
            job_title = job.get("title", "")
            company = job.get("company", "")
            job_description = job.get("description", "")
            
            # Generate cover letter
            cover_letter = await self.generator.generate_cover_letter(
                job_title=job_title,
                company_name=company,
                job_description=job_description,
                cv_text=cv_text,
                applicant_name=user_name
            )
            
            if not cover_letter:
                logger.error(f"Failed to generate cover letter for {job_title} at {company}")
                return False, ""
                
            # Create cover letter PDF
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            cover_letter_filename = f"cover_letter_{user_name.replace(' ', '_')}_{job_title.replace(' ', '_')}_{timestamp}.pdf"
            cover_letter_path = os.path.join(os.getcwd(), "backend", "static", "uploads", cover_letter_filename)
            
            success = await self.pdf_writer.create_cover_letter_pdf(
                cover_letter_text=cover_letter,
                output_path=cover_letter_path,
                applicant_name=user_name,
                job_title=job_title,
                company_name=company
            )
            
            if not success:
                logger.error(f"Failed to create cover letter PDF for {job_title} at {company}")
                return False, ""
            
            # In a real application, you would implement the actual job application submission here
            # For now, we'll just log it and pretend it was successful
            logger.info(f"Applied to {job_title} at {company} for {user_name} ({user_email})")
            
            return True, cover_letter_path
            
        except Exception as e:
            logger.error(f"Error in _apply_to_job: {str(e)}")
            return False, ""
    
    async def _filter_jobs(self, jobs: List[Dict], user_email: str) -> List[Dict]:
        """
        Filter jobs to avoid applying to the same job multiple times.
        
        Args:
            jobs: List of job listings
            user_email: Email of the applicant
            
        Returns:
            Filtered list of jobs
        """
        try:
            # Get previously applied jobs
            applied_jobs = await self._get_applied_jobs(user_email)
            
            # Create a set of applied job IDs for faster lookup
            applied_job_ids = {job.get("id") for job in applied_jobs if job.get("id")}
            applied_job_urls = {job.get("url") for job in applied_jobs if job.get("url")}
            
            # Filter out jobs that have already been applied to
            filtered_jobs = []
            for job in jobs:
                job_id = job.get("id")
                job_url = job.get("url")
                
                # Skip jobs that have already been applied to
                if (job_id and job_id in applied_job_ids) or (job_url and job_url in applied_job_urls):
                    continue
                    
                filtered_jobs.append(job)
                
            return filtered_jobs
            
        except Exception as e:
            logger.error(f"Error in _filter_jobs: {str(e)}")
            return jobs  # If filtering fails, return all jobs
    
    async def _get_applied_jobs(self, user_email: str) -> List[Dict]:
        """
        Get list of jobs that the user has already applied to.
        
        Args:
            user_email: Email of the applicant
            
        Returns:
            List of previously applied jobs
        """
        try:
            # Create user-specific directory if it doesn't exist
            user_dir = os.path.join(self.history_dir, self._get_sanitized_email(user_email))
            os.makedirs(user_dir, exist_ok=True)
            
            # Check if applications file exists
            applications_file = os.path.join(user_dir, "applications.json")
            if not os.path.exists(applications_file):
                return []
                
            # Read applications file
            async with aiofiles.open(applications_file, "r") as f:
                contents = await f.read()
                applications = json.loads(contents)
                
            return applications
            
        except Exception as e:
            logger.error(f"Error in _get_applied_jobs: {str(e)}")
            return []
    
    async def _save_applications(self, new_applications: List[Dict], user_email: str) -> bool:
        """
        Save new job applications to the user's history.
        
        Args:
            new_applications: List of new job applications
            user_email: Email of the applicant
            
        Returns:
            Success flag
        """
        try:
            if not new_applications:
                return True
                
            # Get existing applications
            existing_applications = await self._get_applied_jobs(user_email)
            
            # Combine with new applications
            all_applications = existing_applications + new_applications
            
            # Create user-specific directory if it doesn't exist
            user_dir = os.path.join(self.history_dir, self._get_sanitized_email(user_email))
            os.makedirs(user_dir, exist_ok=True)
            
            # Save to file
            applications_file = os.path.join(user_dir, "applications.json")
            async with aiofiles.open(applications_file, "w") as f:
                await f.write(json.dumps(all_applications))
                
            return True
            
        except Exception as e:
            logger.error(f"Error in _save_applications: {str(e)}")
            return False
    
    def _get_sanitized_email(self, email: str) -> str:
        """
        Convert email to a filesystem-safe string.
        
        Args:
            email: Email address
            
        Returns:
            Sanitized email
        """
        return email.replace("@", "_at_").replace(".", "_dot_")
    
    async def get_application_summary(self, user_email: str) -> Dict[str, any]:
        """
        Get a summary of the user's job applications.
        
        Args:
            user_email: Email of the applicant
            
        Returns:
            Summary of applications
        """
        try:
            # Get all applications
            applications = await self._get_applied_jobs(user_email)
            
            # Create summary statistics
            total_applications = len(applications)
            
            # Count by status
            status_counts = {}
            for app in applications:
                status = app.get("status", "applied")
                status_counts[status] = status_counts.get(status, 0) + 1
                
            # Count by source
            source_counts = {}
            for app in applications:
                source = app.get("source", "unknown")
                source_counts[source] = source_counts.get(source, 0) + 1
                
            # Get recent applications (last 10)
            recent_applications = sorted(
                applications,
                key=lambda x: x.get("applied_at", ""),
                reverse=True
            )[:10]
            
            return {
                "total_applications": total_applications,
                "status_counts": status_counts,
                "source_counts": source_counts,
                "recent_applications": recent_applications,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            logger.error(f"Error in get_application_summary: {str(e)}")
            return {
                "total_applications": 0,
                "status_counts": {},
                "source_counts": {},
                "recent_applications": [],
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "error": str(e)
            }