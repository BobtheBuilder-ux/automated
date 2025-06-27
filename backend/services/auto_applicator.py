import os
import logging
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import aiofiles

from .job_scraper import JobScraper
from .pdf_parser import PDFParser
from .gemini_generator import GeminiGenerator
from .pdf_writer import PDFWriter
from .email_service import EmailService

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
        
        # Ensure application history directory exists
        self.history_dir = os.path.join("backend", "static", "application_history")
        os.makedirs(self.history_dir, exist_ok=True)
        
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