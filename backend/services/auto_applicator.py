import os
import logging
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import aiofiles
import time
from concurrent.futures import ThreadPoolExecutor
import aiohttp  # Ensure this import is available

from .job_scraper import JobScraper
from .pdf_parser import PDFParser
from .gemini_generator import GeminiGenerator
from .pdf_writer import PDFWriter
from .email_service import EmailService
from .application_strategies import StrategyFactory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='auto_application.log'
)
logger = logging.getLogger(__name__)

# Set up console output for real-time feedback
import sys

class AutoApplicator:
    """Service to automatically apply to jobs based on scraped listings."""
    
    def __init__(self):
        self.job_scraper = JobScraper()
        self.pdf_parser = PDFParser()
        self.generator = GeminiGenerator()
        self.pdf_writer = PDFWriter()
        self.email_service = EmailService()
        
        # Performance tuning parameters
        self.max_concurrent_applications = 5  # Process this many applications in parallel
        self.application_timeout = 180  # 3 minutes timeout per application
        self.email_fallback = True  # Send email applications when direct applications fail
        
        # Keep-alive configuration
        self.keep_alive_interval = 60  # Send health ping every 60 seconds
        self.keep_alive_task = None
        self.keep_alive_url = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:8000")
        
        # Ensure application history directory exists
        self.history_dir = os.path.join("backend", "static", "application_history")
        os.makedirs(self.history_dir, exist_ok=True)
        
    async def _keep_alive_ping(self):
        """Background task to periodically ping the health endpoint to prevent shutdown."""
        try:
            health_url = f"{self.keep_alive_url}/health"
            logger.info(f"Starting keep-alive pings to {health_url} every {self.keep_alive_interval} seconds")
            print(f"🔄 Starting keep-alive pings to keep server active")
            
            async with aiohttp.ClientSession() as session:
                while True:
                    try:
                        async with session.get(health_url) as response:
                            if response.status == 200:
                                logger.debug(f"Keep-alive ping successful: {response.status}")
                            else:
                                logger.warning(f"Keep-alive ping returned unexpected status: {response.status}")
                    except Exception as e:
                        logger.error(f"Keep-alive ping failed: {str(e)}")
                    
                    await asyncio.sleep(self.keep_alive_interval)
        except asyncio.CancelledError:
            logger.info("Keep-alive task cancelled")
        except Exception as e:
            logger.error(f"Error in keep-alive task: {str(e)}")
    
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
            # Start the keep-alive task to prevent the server from spinning down
            self.keep_alive_task = asyncio.create_task(self._keep_alive_ping())
            
            start_time = time.time()
            print(f"\n🚀 Starting auto-apply process for {user_name} ({user_email})")
            print(f"📋 Looking for {job_title} jobs in {location}...")
            logger.info(f"Starting auto-apply process for {user_name} ({user_email}) - {job_title} in {location}")
            
            # Get job listings
            print(f"🔍 Scraping job listings from multiple sources...")
            sys.stdout.flush()
            jobs = await self.job_scraper.get_jobs(job_title, location)
            
            if not jobs:
                print(f"❌ No jobs found for '{job_title}' in '{location}'")
                return False, [], f"No jobs found for '{job_title}' in '{location}'"
                
            print(f"✅ Found {len(jobs)} matching jobs!")
            
            # Parse CV
            print(f"📄 Parsing your CV...")
            sys.stdout.flush()
            cv_text = await self.pdf_parser.parse_pdf(cv_path)
            if not cv_text:
                print(f"❌ Failed to parse CV")
                return False, [], "Failed to parse CV"
            
            print(f"✅ CV parsed successfully!")
            logger.info(f"Found {len(jobs)} jobs and parsed CV successfully")
            
            # Filter jobs to avoid duplicates
            print(f"🔄 Filtering out jobs you've already applied to...")
            sys.stdout.flush()
            filtered_jobs = await self._filter_jobs(jobs, user_email)
            
            if not filtered_jobs:
                print(f"ℹ️ No new jobs found that haven't been applied to already")
                return False, [], "No new jobs found that haven't been applied to already"
                
            print(f"✅ {len(filtered_jobs)} new jobs available to apply!")
            logger.info(f"After filtering, {len(filtered_jobs)} jobs are available to apply")
            
            # Limit applications
            jobs_to_apply = filtered_jobs[:max_applications]
            
            # Apply to each job concurrently
            applications = []
            
            print(f"📝 Applying to {len(jobs_to_apply)} jobs in parallel...")
            sys.stdout.flush()
            
            # Process applications in parallel batches
            tasks = []
            # Process jobs in batches to avoid overwhelming resources
            batch_size = min(self.max_concurrent_applications, len(jobs_to_apply))
            print(f"📝 Applying to {len(jobs_to_apply)} jobs in batches of {batch_size}...")
            sys.stdout.flush()
            
            # Create tasks for each job application
            for job in jobs_to_apply:
                task = asyncio.create_task(self._apply_to_job_with_timeout(
                    job=job,
                    cv_text=cv_text,
                    user_name=user_name,
                    user_email=user_email,
                    cv_path=cv_path
                ))
                tasks.append(task)
            
            # Wait for all applications to complete with proper concurrency control
            results = []
            for i in range(0, len(tasks), batch_size):
                batch = tasks[i:i+batch_size]
                batch_results = await asyncio.gather(*batch)
                results.extend(batch_results)
            
            for job, (success, cover_letter_path) in zip(jobs_to_apply, results):
                if success:
                    job["status"] = "applied"
                    job["applied_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    job["cover_letter_path"] = cover_letter_path
                    applications.append(job)
            
            # Save application history
            await self._save_applications(applications, user_email)
            
            # If applications were made, send a summary email
            if applications:
                print(f"📧 Sending application summary email to {user_email}...")
                sys.stdout.flush()
                await self.email_service.send_application_summary(
                    recipient_email=user_email,
                    name=user_name,
                    applications=applications,
                    job_title=job_title
                )
                print(f"✅ Summary email sent!")
                
            elapsed_time = time.time() - start_time
            print(f"\n🎉 Auto-apply process completed in {elapsed_time:.2f} seconds")
            print(f"📊 Successfully applied to {len(applications)} jobs")
            logger.info(f"Auto-apply process completed in {elapsed_time:.2f} seconds with {len(applications)} successful applications")
            
            # Cancel the keep-alive task as we're done with the application process
            if self.keep_alive_task and not self.keep_alive_task.done():
                self.keep_alive_task.cancel()
                try:
                    await self.keep_alive_task
                except asyncio.CancelledError:
                    pass
            
            return True, applications, f"Successfully applied to {len(applications)} jobs"
            
        except Exception as e:
            # Cancel the keep-alive task in case of error
            if self.keep_alive_task and not self.keep_alive_task.done():
                self.keep_alive_task.cancel()
                try:
                    await self.keep_alive_task
                except asyncio.CancelledError:
                    pass
            
            logger.error(f"Error in apply_to_jobs: {str(e)}")
            print(f"❌ Error in job application process: {str(e)}")
            return False, [], f"Error in apply_to_jobs: {str(e)}"
    
    async def _apply_to_job_with_timeout(self, job, cv_text, user_name, user_email, cv_path):
        """Apply to a job with a timeout to prevent hanging on problematic applications"""
        job_title = job.get('title', 'Unknown position')
        company = job.get('company', 'Unknown company')
        
        print(f"  🔹 Applying to: {job_title} at {company}...")
        sys.stdout.flush()
        
        try:
            return await asyncio.wait_for(
                self._apply_to_job(job, cv_text, user_name, user_email, cv_path),
                timeout=self.application_timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"Application timed out for {job_title} at {company}")
            print(f"  ⏱️ Application timed out for {job_title} at {company}")
            
            # If timeout occurs and email fallback is enabled, send application via email
            if self.email_fallback:
                print(f"  📧 Attempting email fallback for {job_title}...")
                sys.stdout.flush()
                return await self._apply_via_email(job, cv_text, user_name, user_email, cv_path)
            return False, ""
        except Exception as e:
            logger.error(f"Error applying to job {job_title}: {str(e)}")
            print(f"  ❌ Error applying to {job_title}: {str(e)}")
            
            # If any error occurs and email fallback is enabled, send application via email
            if self.email_fallback:
                print(f"  📧 Attempting email fallback for {job_title}...")
                sys.stdout.flush()
                return await self._apply_via_email(job, cv_text, user_name, user_email, cv_path)
            return False, ""
    
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
            job_source = job.get("source", "")
            
            # Generate cover letter
            print(f"  📝 Generating cover letter for {job_title} at {company}...")
            sys.stdout.flush()
            cover_letter_result = await self.generator.generate_cover_letter(
                job_title=job_title,
                company_name=company,
                job_description=job_description,
                cv_text=cv_text,
                applicant_name=user_name
            )
            
            if not cover_letter_result or not cover_letter_result.get("success"):
                logger.error(f"Failed to generate cover letter for {job_title} at {company}")
                print(f"  ❌ Failed to generate cover letter for {job_title}")
                return False, ""
                
            cover_letter = cover_letter_result.get("cover_letter", "")
                
            # Create cover letter PDF
            print(f"  📄 Creating cover letter PDF...")
            sys.stdout.flush()
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
                print(f"  ❌ Failed to create cover letter PDF for {job_title}")
                return False, ""
            
            # Try to apply using appropriate strategy for the job source
            print(f"  🌐 Submitting application via {job_source}...")
            sys.stdout.flush()
            
            # Get appropriate strategy based on job source
            strategy = StrategyFactory.create_strategy(job_source)
            
            # Set up user data
            user_data = {
                "name": user_name,
                "email": user_email
            }
            
            # Apply using the strategy
            success, message = await strategy.apply_with_timeout(
                job_data=job,
                user_data=user_data,
                cv_path=cv_path,
                cover_letter_path=cover_letter_path
            )
            
            if success:
                print(f"  ✅ Application submitted successfully for {job_title}!")
                logger.info(f"Applied to {job_title} at {company} for {user_name} ({user_email})")
                
                # Send confirmation email for this application
                print(f"  📧 Sending confirmation email...")
                sys.stdout.flush()
                await self.email_service.send_application_confirmation(
                    recipient_email=user_email,
                    name=user_name,
                    job_title=job_title,
                    company=company,
                    cover_letter_path=cover_letter_path
                )
                print(f"  ✅ Confirmation email sent!")
                
                return True, cover_letter_path
            else:
                logger.warning(f"Failed to apply to {job_title} at {company}: {message}")
                print(f"  ❌ Direct application failed: {message}")
                
                # Try email fallback if direct application failed
                if self.email_fallback:
                    print(f"  📧 Attempting email fallback...")
                    sys.stdout.flush()
                    return await self._apply_via_email(job, cv_text, user_name, user_email, cv_path, cover_letter_path)
                
                return False, ""
            
        except Exception as e:
            logger.error(f"Error in _apply_to_job: {str(e)}")
            print(f"  ❌ Error in application process: {str(e)}")
            if self.email_fallback:
                print(f"  📧 Attempting email fallback due to error...")
                sys.stdout.flush()
                return await self._apply_via_email(job, cv_text, user_name, user_email, cv_path)
            return False, ""
    
    async def _apply_via_email(
        self,
        job: Dict,
        cv_text: str,
        user_name: str,
        user_email: str,
        cv_path: str,
        cover_letter_path: str = None
    ) -> Tuple[bool, str]:
        """
        Apply to a job via email when direct application fails.
        
        Args:
            job: Job details
            cv_text: CV text content
            user_name: Name of the applicant
            user_email: Email of the applicant
            cv_path: Path to the CV file
            cover_letter_path: Path to existing cover letter if available
            
        Returns:
            Tuple of (success, cover_letter_path)
        """
        try:
            # Get job details
            job_title = job.get("title", "")
            company = job.get("company", "")
            company_email = job.get("contact_email")
            job_description = job.get("description", "")
            
            # Extract email from job if not provided
            if not company_email:
                # Use the application strategy's email extraction
                email_strategy = StrategyFactory.create_email_strategy()
                company_email = email_strategy.extract_email_from_job(job)
                print(f"  📧 Using extracted email: {company_email}")
            
            # If no company email found, try to find it from URL
            if not company_email and job.get("url"):
                # Extract domain from URL
                url = job.get("url", "")
                import re
                domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
                if domain_match:
                    domain = domain_match.group(1)
                    company_email = f"careers@{domain}"
                    print(f"  📧 Using domain-based email: {company_email}")
            
            # If still no email, use a default format based on company name
            if not company_email:
                company_name_for_email = company.lower().replace(" ", "").replace(".", "").replace(",", "")
                company_email = f"careers@{company_name_for_email}.com"
                print(f"  📧 Using generated email: {company_email}")
            
            # Generate cover letter if not provided
            if not cover_letter_path:
                print(f"  📝 Generating cover letter for email application...")
                sys.stdout.flush()
                cover_letter_result = await self.generator.generate_cover_letter(
                    job_title=job_title,
                    company_name=company,
                    job_description=job_description,
                    cv_text=cv_text,
                    applicant_name=user_name
                )
                
                if not cover_letter_result or not cover_letter_result.get("success"):
                    logger.error(f"Failed to generate cover letter for {job_title} at {company}")
                    print(f"  ❌ Failed to generate cover letter for email application")
                    return False, ""
                    
                cover_letter = cover_letter_result.get("cover_letter", "")
                    
                # Create cover letter PDF
                print(f"  📄 Creating cover letter PDF for email...")
                sys.stdout.flush()
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
                    print(f"  ❌ Failed to create cover letter PDF for email application")
                    return False, ""
            
            # Send application via email
            print(f"  📧 Sending email application to {company_email}...")
            sys.stdout.flush()
            email_subject = f"Application for {job_title} position at {company}"
            email_body = f"""
Dear Hiring Manager,

Please find attached my CV and cover letter for the {job_title} position at {company}.

I believe my skills and experience align well with the requirements for this role, and I'm excited about the opportunity to contribute to your team.

Thank you for considering my application. I look forward to the possibility of discussing this opportunity with you further.

Best regards,
{user_name}
{user_email}
            """
            
            # Send email with attachments
            email_success = await self.email_service.send_job_application(
                recipient_email=company_email,
                subject=email_subject,
                body=email_body,
                sender_name=user_name,
                sender_email=user_email,
                attachments=[cv_path, cover_letter_path]
            )
            
            if email_success:
                logger.info(f"Sent application via email for {job_title} at {company} to {company_email}")
                print(f"  ✅ Email application sent successfully to {company_email}!")
                
                # Send confirmation to the applicant
                print(f"  📧 Sending confirmation email to applicant...")
                sys.stdout.flush()
                await self.email_service.send_application_confirmation(
                    recipient_email=user_email,
                    name=user_name,
                    job_title=job_title,
                    company=company,
                    cover_letter_path=cover_letter_path,
                    application_method="email"
                )
                print(f"  ✅ Confirmation email sent to applicant!")
                
                return True, cover_letter_path
            else:
                logger.error(f"Failed to send application email for {job_title} at {company}")
                print(f"  ❌ Failed to send email application to {company_email}")
                return False, ""
            
        except Exception as e:
            logger.error(f"Error in _apply_via_email: {str(e)}")
            print(f"  ❌ Email application error: {str(e)}")
            return False, ""
    
    async def _filter_jobs(self, jobs: List[Dict], user_email: str) -> List[Dict]:
        """Filter jobs to avoid applying to the same job multiple times."""
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
        """Get list of jobs that the user has already applied to."""
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
        """Save new job applications to the user's history."""
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
        """Convert email to a filesystem-safe string."""
        return email.replace("@", "_at_").replace(".", "_dot_")
    
    async def get_application_summary(self, user_email: str) -> Dict[str, any]:
        """Get a summary of the user's job applications."""
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