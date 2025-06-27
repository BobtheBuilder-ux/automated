import os
import logging
import json
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import aiofiles

from services.auto_applicator import AutoApplicator
from services.email_service import EmailService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='job_scheduler.log'
)
logger = logging.getLogger(__name__)

class JobApplicationScheduler:
    """Scheduler for automated job applications."""
    
    def __init__(self):
        self.auto_applicator = AutoApplicator()
        self.email_service = EmailService()
        
        # Ensure scheduler directory exists
        self.scheduler_dir = os.path.join("backend", "static", "scheduler")
        os.makedirs(self.scheduler_dir, exist_ok=True)
        
        self.jobs_file = os.path.join(self.scheduler_dir, "scheduled_jobs.json")
        
        # Initialize background tasks
        self.running_tasks = {}
        self._scheduler_task = None
        self.is_running = False
        
    async def start(self):
        """Start the scheduler background task"""
        if not self.is_running and (self._scheduler_task is None or self._scheduler_task.done()):
            self.is_running = True
            self._scheduler_task = asyncio.create_task(self._scheduler_loop())
            logger.info("Job scheduler started")

    async def stop(self):
        """Stop the scheduler"""
        self.is_running = False
        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("Job scheduler stopped")
    
    def start_scheduler(self):
        """Start the background scheduler task if not already running (sync wrapper)."""
        if not self.is_running:
            try:
                # Try to get the current event loop
                loop = asyncio.get_running_loop()
                # Schedule the start coroutine
                asyncio.create_task(self.start())
            except RuntimeError:
                # No event loop running, this will be called later when the app starts
                logger.info("No event loop running, scheduler will start when app starts")
    
    async def _scheduler_loop(self):
        """Background loop to check and run scheduled jobs."""
        while self.is_running:
            try:
                await self._check_and_run_scheduled_jobs()
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
            
            # Check every minute
            await asyncio.sleep(60)
    
    async def _check_and_run_scheduled_jobs(self):
        """Check and run any scheduled jobs that are due."""
        # Get all scheduled jobs
        jobs = await self._get_scheduled_jobs()
        
        # Check each job
        for job_id, job in jobs.items():
            # Skip if job is not active
            if job.get("status") not in ["scheduled", "running"]:
                continue
                
            # Check if next run is due
            next_run = job.get("next_run")
            if not next_run:
                continue
                
            # Parse next run time
            next_run_time = datetime.strptime(next_run, "%Y-%m-%d %H:%M:%S")
            
            # If it's time to run
            if datetime.now() >= next_run_time:
                # Start a task to run the job
                asyncio.create_task(self._run_job(job_id, job))
    
    async def _run_job(self, job_id: str, job: Dict):
        """Run a scheduled job."""
        try:
            # Update job status to running
            job["status"] = "running"
            job["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await self._update_job(job_id, job)
            
            # Run the job
            success, applications, error_message = await self.auto_applicator.apply_to_jobs(
                user_name=job["user_name"],
                user_email=job["user_email"],
                job_title=job["job_title"],
                location=job["location"],
                cv_path=job["cv_path"],
                max_applications=job["max_applications_per_run"]
            )
            
            # Update job after running
            job["runs_completed"] = job.get("runs_completed", 0) + 1
            
            # Check if this is the last run for recurring jobs
            if job["schedule_type"] == "recurring" and job["total_runs"] is not None:
                if job["runs_completed"] >= job["total_runs"]:
                    job["status"] = "completed"
                    job["next_run"] = None
                else:
                    # Schedule next run
                    next_run_time = datetime.now() + timedelta(days=job["frequency_days"])
                    job["next_run"] = next_run_time.strftime("%Y-%m-%d %H:%M:%S")
                    job["status"] = "scheduled"
            else:
                # For one-time jobs
                job["status"] = "completed"
                job["next_run"] = None
            
            # Record results
            job["last_result"] = {
                "success": success,
                "applications_count": len(applications),
                "error_message": error_message if not success else None,
                "run_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            if not success:
                job["last_error"] = error_message
                
            # Send email notification about job completion
            if applications:
                await self.email_service.send_application_summary(
                    recipient_email=job["user_email"],
                    name=job["user_name"],
                    applications=applications,
                    job_title=job["job_title"]
                )
            
            # Update job in storage
            await self._update_job(job_id, job)
            
        except Exception as e:
            logger.error(f"Error running job {job_id}: {str(e)}")
            
            # Update job with error
            job["status"] = "error"
            job["last_error"] = str(e)
            await self._update_job(job_id, job)
    
    async def schedule_auto_application(
        self,
        user_id: str,
        user_name: str,
        user_email: str,
        job_title: str,
        location: str,
        cv_path: str,
        schedule_type: str = "once",
        max_applications_per_run: int = 5,
        frequency_days: int = 7,
        total_runs: Optional[int] = None
    ) -> str:
        """
        Schedule an automated job application.
        
        Args:
            user_id: Unique identifier for the user
            user_name: Name of the user
            user_email: Email of the user
            job_title: Job title to search for
            location: Location to search in
            cv_path: Path to the CV file
            schedule_type: Type of schedule ('once' or 'recurring')
            max_applications_per_run: Maximum applications per run
            frequency_days: Frequency of recurring jobs in days
            total_runs: Total number of runs for recurring jobs
            
        Returns:
            Job ID
        """
        # Create job ID
        job_id = str(uuid.uuid4())
        
        # Set next run time (now for immediate execution)
        next_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Create job object
        job = {
            "job_id": job_id,
            "user_id": user_id,
            "user_name": user_name,
            "user_email": user_email,
            "job_title": job_title,
            "location": location,
            "cv_path": cv_path,
            "schedule_type": schedule_type,
            "max_applications_per_run": max_applications_per_run,
            "frequency_days": frequency_days if schedule_type == "recurring" else None,
            "total_runs": total_runs if schedule_type == "recurring" else 1,
            "runs_completed": 0,
            "status": "scheduled",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "next_run": next_run,
            "last_run": None,
            "last_error": None,
            "last_result": None
        }
        
        # Save job
        await self._add_job(job_id, job)
        
        # Send email notification about scheduled job
        await self.email_service.send_scheduled_job_notification(
            recipient_email=user_email,
            name=user_name,
            job_title=job_title,
            job_id=job_id,
            schedule_type=schedule_type,
            next_run=next_run
        )
        
        return job_id
    
    async def get_user_jobs(self, user_id: str) -> List[Dict]:
        """Get all jobs for a specific user."""
        jobs = await self._get_scheduled_jobs()
        user_jobs = []
        
        for job_id, job in jobs.items():
            if job.get("user_id") == user_id:
                user_jobs.append(job)
        
        return user_jobs
    
    async def get_all_jobs(self) -> Dict[str, Dict]:
        """Get all scheduled jobs."""
        return await self._get_scheduled_jobs()
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a scheduled job."""
        jobs = await self._get_scheduled_jobs()
        
        if job_id in jobs:
            jobs[job_id]["status"] = "cancelled"
            await self._save_all_jobs(jobs)
            logger.info(f"Cancelled job {job_id}")
            return True
        
        return False
    
    async def delete_job(self, job_id: str) -> bool:
        """Delete a scheduled job."""
        jobs = await self._get_scheduled_jobs()
        
        if job_id in jobs:
            del jobs[job_id]
            await self._save_all_jobs(jobs)
            logger.info(f"Deleted job {job_id}")
            return True
        
        return False
    
    async def _get_scheduled_jobs(self) -> Dict[str, Dict]:
        """Load scheduled jobs from file."""
        try:
            if os.path.exists(self.jobs_file):
                async with aiofiles.open(self.jobs_file, 'r') as f:
                    content = await f.read()
                    return json.loads(content) if content.strip() else {}
            return {}
        except Exception as e:
            logger.error(f"Error loading scheduled jobs: {str(e)}")
            return {}
    
    async def _save_job(self, job_id: str, job_data: Dict):
        """Save a single job."""
        jobs = await self._get_scheduled_jobs()
        jobs[job_id] = job_data
        await self._save_all_jobs(jobs)
    
    async def _update_job(self, job_id: str, job_data: Dict):
        """Update an existing job."""
        await self._save_job(job_id, job_data)
    
    async def _save_all_jobs(self, jobs: Dict[str, Dict]):
        """Save all jobs to file."""
        try:
            async with aiofiles.open(self.jobs_file, 'w') as f:
                await f.write(json.dumps(jobs, indent=2))
        except Exception as e:
            logger.error(f"Error saving scheduled jobs: {str(e)}")