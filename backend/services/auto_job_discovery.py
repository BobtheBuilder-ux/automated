import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from .job_scraper import JobScraper
from .firebase_service import FirebaseService

logger = logging.getLogger(__name__)

class AutoJobDiscoveryService:
    """Service for automatically discovering and storing fresh job postings."""
    
    def __init__(self):
        self.job_scraper = JobScraper()
        self.firebase_service = FirebaseService()
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        
        # Job search configurations
        self.job_searches = [
            {"title": "Frontend Developer", "location": "remote"},
            {"title": "Full Stack Developer", "location": "remote"},
            {"title": "React Developer", "location": "remote"},
            {"title": "JavaScript Developer", "location": "remote"},
            {"title": "Python Developer", "location": "remote"},
            {"title": "Node.js Developer", "location": "remote"},
            {"title": "Software Engineer", "location": "remote"},
            {"title": "Web Developer", "location": "remote"},
            {"title": "Backend Developer", "location": "remote"},
            {"title": "TypeScript Developer", "location": "remote"}
        ]
        
    async def start_auto_discovery(self, interval_hours: int = 2):
        """Start the automated job discovery process."""
        if self.is_running:
            logger.info("Auto job discovery is already running")
            return
        
        self.scheduler.add_job(
            self._discover_jobs,
            IntervalTrigger(hours=interval_hours),
            id="auto_job_discovery",
            replace_existing=True
        )
        
        self.scheduler.start()
        self.is_running = True
        
        # Skip initial discovery during startup to prevent hanging
        # await self._discover_jobs()
        
        logger.info(f"Started auto job discovery - running every {interval_hours} hours")
    
    async def stop_auto_discovery(self):
        """Stop the automated job discovery process."""
        if self.scheduler.running:
            self.scheduler.shutdown()
        self.is_running = False
        logger.info("Stopped auto job discovery")
    
    async def _discover_jobs(self):
        """Discover fresh jobs from all configured searches."""
        logger.info("🔍 Starting automated job discovery...")
        
        all_discovered_jobs = []
        
        for search_config in self.job_searches:
            try:
                logger.info(f"Searching for {search_config['title']} jobs...")
                
                # Get jobs from all sources
                jobs = await self.job_scraper.get_jobs(
                    job_title=search_config['title'],
                    location=search_config['location']
                )
                
                # Process and enrich job data
                enriched_jobs = await self._enrich_job_data(jobs, search_config)
                all_discovered_jobs.extend(enriched_jobs)
                
                logger.info(f"Found {len(enriched_jobs)} recent jobs for {search_config['title']}")
                
                # Add delay between searches to avoid rate limiting
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error discovering jobs for {search_config['title']}: {str(e)}")
                continue
        
        # Store discovered jobs
        if all_discovered_jobs:
            await self._store_discovered_jobs(all_discovered_jobs)
            logger.info(f"✅ Completed job discovery - found {len(all_discovered_jobs)} total jobs")
        else:
            logger.warning("No new jobs discovered in this cycle")
    
    async def _enrich_job_data(self, jobs: List[Dict], search_config: Dict) -> List[Dict]:
        """Enrich job data with additional information and filtering."""
        enriched_jobs = []
        
        for job in jobs:
            try:
                # Add discovery metadata
                job.update({
                    'discovered_at': datetime.now().isoformat(),
                    'search_title': search_config['title'],
                    'search_location': search_config['location'],
                    'is_recent': True,
                    'auto_discovered': True
                })
                
                # Try to get full job description if not already present
                if not job.get('description') or len(job.get('description', '')) < 100:
                    try:
                        full_description = await self.job_scraper.get_job_description(job['url'])
                        if full_description and len(full_description) > 100:
                            job['description'] = full_description
                    except Exception as e:
                        logger.debug(f"Could not fetch full description for {job.get('title', 'Unknown')}: {e}")
                
                # Extract company email if possible
                description = job.get('description', '')
                company_email = self._extract_company_email(description)
                if company_email:
                    job['company_email'] = company_email
                
                # Generate unique job ID for deduplication
                job_id = self._generate_job_id(job)
                job['unique_id'] = job_id
                
                enriched_jobs.append(job)
                
            except Exception as e:
                logger.error(f"Error enriching job data: {str(e)}")
                continue
        
        return enriched_jobs
    
    def _extract_company_email(self, text: str) -> Optional[str]:
        """Extract company email from job description."""
        import re
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        
        # Filter out common non-company emails
        excluded_domains = ['example.com', 'test.com', 'noreply']
        for email in emails:
            if not any(domain in email.lower() for domain in excluded_domains):
                return email
        return None
    
    def _generate_job_id(self, job: Dict) -> str:
        """Generate a unique ID for job deduplication."""
        import hashlib
        
        # Create hash from company + title + source for uniqueness
        unique_string = f"{job.get('company', '')}-{job.get('title', '')}-{job.get('source', '')}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:12]
    
    async def _store_discovered_jobs(self, jobs: List[Dict]):
        """Store discovered jobs in Firebase with deduplication."""
        try:
            # Get existing jobs for deduplication
            existing_jobs = await self._get_existing_job_ids()
            
            new_jobs = []
            for job in jobs:
                if job['unique_id'] not in existing_jobs:
                    new_jobs.append(job)
            
            if new_jobs:
                # Store in Firebase
                result = await self.firebase_service.store_discovered_jobs(new_jobs)
                if result.get('success'):
                    logger.info(f"Stored {len(new_jobs)} new jobs (filtered {len(jobs) - len(new_jobs)} duplicates)")
                else:
                    logger.error(f"Failed to store jobs: {result.get('error')}")
            else:
                logger.info("No new unique jobs to store")
                
        except Exception as e:
            logger.error(f"Error storing discovered jobs: {str(e)}")
    
    async def _get_existing_job_ids(self) -> set:
        """Get IDs of existing jobs to avoid duplicates."""
        try:
            result = await self.firebase_service.get_discovered_jobs()
            if result.get('success'):
                existing_jobs = result.get('data', [])
                return {job.get('unique_id') for job in existing_jobs if job.get('unique_id')}
            return set()
        except Exception as e:
            logger.error(f"Error getting existing job IDs: {str(e)}")
            return set()
    
    async def get_discovered_jobs(self, 
                                 limit: int = 50, 
                                 job_title_filter: Optional[str] = None,
                                 source_filter: Optional[str] = None) -> Dict:
        """Get discovered jobs with optional filtering."""
        try:
            result = await self.firebase_service.get_discovered_jobs()
            
            if not result.get('success'):
                return {"success": False, "error": result.get('error')}
            
            jobs = result.get('data', [])
            
            # Apply filters
            if job_title_filter:
                jobs = [job for job in jobs if job_title_filter.lower() in job.get('search_title', '').lower()]
            
            if source_filter:
                jobs = [job for job in jobs if job.get('source', '').lower() == source_filter.lower()]
            
            # Sort by discovery date (newest first)
            jobs.sort(key=lambda x: x.get('discovered_at', ''), reverse=True)
            
            # Limit results
            jobs = jobs[:limit]
            
            return {
                "success": True,
                "data": jobs,
                "total": len(jobs)
            }
            
        except Exception as e:
            logger.error(f"Error getting discovered jobs: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_discovery_stats(self) -> Dict:
        """Get statistics about job discovery."""
        try:
            result = await self.firebase_service.get_discovered_jobs()
            
            if not result.get('success'):
                return {"success": False, "error": result.get('error')}
            
            jobs = result.get('data', [])
            
            # Calculate stats
            total_jobs = len(jobs)
            
            # Jobs discovered in last 24 hours
            yesterday = datetime.now() - timedelta(days=1)
            recent_jobs = [
                job for job in jobs 
                if datetime.fromisoformat(job.get('discovered_at', '').replace('Z', '+00:00')).replace(tzinfo=None) >= yesterday
            ]
            
            # Group by source
            sources = {}
            for job in jobs:
                source = job.get('source', 'Unknown')
                sources[source] = sources.get(source, 0) + 1
            
            # Group by job title
            job_titles = {}
            for job in jobs:
                title = job.get('search_title', 'Unknown')
                job_titles[title] = job_titles.get(title, 0) + 1
            
            return {
                "success": True,
                "data": {
                    "total_jobs": total_jobs,
                    "jobs_last_24h": len(recent_jobs),
                    "sources": sources,
                    "job_titles": job_titles,
                    "is_discovery_running": self.is_running
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting discovery stats: {str(e)}")
            return {"success": False, "error": str(e)}

# Global instance
auto_job_discovery = AutoJobDiscoveryService()