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
        
        # Dynamic tech-related job titles for comprehensive discovery
        self.dynamic_job_searches = [
            # Frontend Technologies
            "Frontend Developer", "React Developer", "Vue.js Developer", "Angular Developer",
            "JavaScript Developer", "TypeScript Developer", "HTML/CSS Developer", "UI Developer",
            "React Native Developer", "Flutter Developer", "Next.js Developer", "Svelte Developer",
            
            # Backend Technologies
            "Backend Developer", "Python Developer", "Node.js Developer", "Java Developer",
            "C# Developer", "PHP Developer", "Ruby Developer", "Go Developer", "Rust Developer",
            "Django Developer", "Flask Developer", "Express.js Developer", "Spring Developer",
            
            # Full Stack
            "Full Stack Developer", "MEAN Stack Developer", "MERN Stack Developer", 
            "LAMP Stack Developer", "JAMstack Developer", "T3 Stack Developer",
            
            # Software Engineering
            "Software Engineer", "Senior Software Engineer", "Junior Software Engineer",
            "Software Developer", "Application Developer", "Systems Developer",
            "Platform Engineer", "Solutions Engineer",
            
            # Mobile Development
            "Mobile Developer", "iOS Developer", "Android Developer", "React Native Developer",
            "Flutter Developer", "Xamarin Developer", "Ionic Developer", "Swift Developer",
            "Kotlin Developer",
            
            # DevOps & Infrastructure
            "DevOps Engineer", "Site Reliability Engineer", "Platform Engineer", "Cloud Engineer",
            "Infrastructure Engineer", "Build Engineer", "Release Engineer", "Deployment Engineer",
            "Docker Engineer", "Kubernetes Engineer", "AWS Engineer", "Azure Engineer", "GCP Engineer",
            
            # Data & Analytics
            "Data Engineer", "Data Scientist", "Machine Learning Engineer", "AI Engineer",
            "Big Data Engineer", "ETL Developer", "Business Intelligence Developer", "Analytics Engineer",
            "MLOps Engineer", "Data Architect", "Database Developer",
            
            # Security
            "Security Engineer", "Cybersecurity Engineer", "Application Security Engineer",
            "Network Security Engineer", "Information Security Engineer", "Penetration Tester",
            
            # Quality Assurance
            "QA Engineer", "Test Engineer", "Automation Engineer", "QA Analyst",
            "Test Automation Engineer", "Performance Test Engineer", "Manual Tester",
            
            # Web Development
            "Web Developer", "WordPress Developer", "Shopify Developer", "Drupal Developer",
            "Magento Developer", "Webflow Developer", "CMS Developer",
            
            # Game Development
            "Game Developer", "Unity Developer", "Unreal Engine Developer", "Game Programmer",
            "Mobile Game Developer", "3D Developer",
            
            # Emerging Technologies
            "Blockchain Developer", "Smart Contract Developer", "Web3 Developer", "DeFi Developer",
            "NFT Developer", "Cryptocurrency Developer", "Solidity Developer",
            
            # Database & Systems
            "Database Administrator", "Database Developer", "System Administrator", "Network Engineer",
            "Database Engineer", "SQL Developer", "NoSQL Developer",
            
            # Technical Leadership
            "Technical Lead", "Engineering Manager", "CTO", "VP Engineering", "Principal Engineer",
            "Staff Engineer", "Senior Staff Engineer", "Architect", "Solutions Architect", "Technical Architect",
            
            # Internships and Entry Level
            "Software Engineering Intern", "Developer Intern", "Tech Intern", "Engineering Intern",
            "Junior Developer", "Associate Developer", "Entry Level Developer", "Graduate Developer",
            
            # Specialized Roles
            "API Developer", "Microservices Developer", "Integration Developer", "Automation Developer",
            "Performance Engineer", "Scalability Engineer", "Search Engineer", "Recommendation Engineer",
            "Computer Vision Engineer", "NLP Engineer", "Robotics Engineer", "Embedded Developer",
            "Firmware Developer", "Hardware Engineer", "FPGA Developer"
        ]
        
        # Major tech locations for comprehensive coverage
        self.tech_locations = [
            "remote", "San Francisco, CA", "New York, NY", "Seattle, WA", "Austin, TX",
            "Boston, MA", "Los Angeles, CA", "Chicago, IL", "Denver, CO", "Atlanta, GA",
            "Miami, FL", "Phoenix, AZ", "San Diego, CA", "Portland, OR", "Nashville, TN",
            "Raleigh, NC", "Dallas, TX", "Houston, TX", "Minneapolis, MN", "Salt Lake City, UT",
            "Orlando, FL", "San Jose, CA", "Palo Alto, CA", "Mountain View, CA", "Redmond, WA",
            "Bellevue, WA", "Cambridge, MA", "Menlo Park, CA"
        ]
        
        # Job types for filtering
        self.job_types = ["full-time", "part-time", "contract", "intern", "remote"]
        
    async def start_auto_discovery(self, interval_hours: int = 1):
        """Start the automated job discovery process with continuous operation."""
        if self.is_running:
            logger.info("Auto job discovery is already running")
            return
        
        # Add job discovery task (runs every hour by default)
        self.scheduler.add_job(
            self._dynamic_discover_jobs,
            IntervalTrigger(hours=interval_hours),
            id="auto_job_discovery",
            replace_existing=True
        )
        
        # Add cleanup task (runs every 6 hours)
        self.scheduler.add_job(
            self._cleanup_old_jobs,
            IntervalTrigger(hours=6),
            id="job_cleanup",
            replace_existing=True
        )
        
        # Add always-on discovery task (runs every 30 minutes for high-priority searches)
        self.scheduler.add_job(
            self._priority_discovery,
            IntervalTrigger(minutes=30),
            id="priority_discovery",
            replace_existing=True
        )
        
        self.scheduler.start()
        self.is_running = True
        
        logger.info(f"Started continuous auto job discovery:")
        logger.info(f"  - Full discovery: every {interval_hours} hours")
        logger.info(f"  - Priority discovery: every 30 minutes")
        logger.info(f"  - Cleanup: every 6 hours (removes jobs > 72 hours)")
    
    async def stop_auto_discovery(self):
        """Stop the automated job discovery process."""
        if self.scheduler.running:
            self.scheduler.shutdown()
        self.is_running = False
        logger.info("Stopped auto job discovery")
    
    async def _discover_jobs(self):
        """Discover fresh jobs from all configured searches with multiple locations and job types."""
        logger.info("🔍 Starting automated job discovery...")
        
        all_discovered_jobs = []
        
        for search_config in self.job_searches:
            try:
                title = search_config['title']
                locations = search_config.get('locations', ['remote'])
                job_types = search_config.get('job_types', ['full-time'])
                
                logger.info(f"Searching for {title} jobs in {len(locations)} locations with {len(job_types)} job types...")
                
                # Search across all locations for this job title
                for location in locations:
                    try:
                        # Get jobs from all sources for this location
                        jobs = await self.job_scraper.get_jobs(
                            job_title=title,
                            location=location
                        )
                        
                        # Process and enrich job data
                        enriched_jobs = await self._enrich_job_data(jobs, {
                            'title': title,
                            'location': location,
                            'job_types': job_types
                        })
                        all_discovered_jobs.extend(enriched_jobs)
                        
                        logger.info(f"Found {len(enriched_jobs)} jobs for {title} in {location}")
                        
                        # Add delay between location searches
                        await asyncio.sleep(3)
                        
                    except Exception as e:
                        logger.error(f"Error searching {title} in {location}: {str(e)}")
                        continue
                
                # Add delay between different job titles
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
    
    async def _dynamic_discover_jobs(self):
        """Discover jobs from dynamic tech job titles across all locations."""
        logger.info("🔍 Starting dynamic job discovery...")
        
        all_discovered_jobs = []
        
        # Use a rotating subset of job titles to avoid overwhelming the system
        import random
        selected_titles = random.sample(self.dynamic_job_searches, min(10, len(self.dynamic_job_searches)))
        
        for job_title in selected_titles:
            try:
                logger.info(f"Searching for {job_title} across multiple locations...")
                
                # Search in top 5 locations (including remote)
                top_locations = random.sample(self.tech_locations, min(5, len(self.tech_locations)))
                if "remote" not in top_locations:
                    top_locations[0] = "remote"  # Always include remote
                
                for location in top_locations:
                    try:
                        # Get jobs from all sources
                        jobs = await self.job_scraper.get_jobs(
                            job_title=job_title,
                            location=location
                        )
                        
                        # Enrich and filter jobs
                        enriched_jobs = await self._enrich_job_data(jobs, {
                            'title': job_title,
                            'location': location,
                            'job_types': self.job_types
                        })
                        
                        all_discovered_jobs.extend(enriched_jobs)
                        logger.info(f"Found {len(enriched_jobs)} jobs for {job_title} in {location}")
                        
                        # Small delay between locations
                        await asyncio.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"Error searching {job_title} in {location}: {str(e)}")
                        continue
                
                # Delay between job titles
                await asyncio.sleep(3)
                
            except Exception as e:
                logger.error(f"Error discovering jobs for {job_title}: {str(e)}")
                continue
        
        # Store discovered jobs
        if all_discovered_jobs:
            await self._store_discovered_jobs(all_discovered_jobs)
            logger.info(f"✅ Dynamic discovery completed - found {len(all_discovered_jobs)} total jobs")
        else:
            logger.warning("No new jobs found in dynamic discovery cycle")
    
    async def _priority_discovery(self):
        """High-frequency discovery for high-demand roles."""
        logger.info("⚡ Starting priority job discovery...")
        
        # High-priority job titles that are searched more frequently
        priority_titles = [
            "Software Engineer", "Frontend Developer", "Backend Developer", 
            "Full Stack Developer", "React Developer", "Python Developer",
            "DevOps Engineer", "Data Engineer", "Machine Learning Engineer"
        ]
        
        all_discovered_jobs = []
        
        for job_title in priority_titles[:3]:  # Rotate through 3 priority titles
            try:
                # Focus on remote and top tech hubs
                priority_locations = ["remote", "San Francisco, CA", "New York, NY", "Seattle, WA"]
                
                for location in priority_locations:
                    try:
                        jobs = await self.job_scraper.get_jobs(
                            job_title=job_title,
                            location=location
                        )
                        
                        enriched_jobs = await self._enrich_job_data(jobs, {
                            'title': job_title,
                            'location': location,
                            'job_types': self.job_types,
                            'priority': True
                        })
                        
                        all_discovered_jobs.extend(enriched_jobs)
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        logger.error(f"Priority search error for {job_title} in {location}: {str(e)}")
                        continue
                
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Priority discovery error for {job_title}: {str(e)}")
                continue
        
        if all_discovered_jobs:
            await self._store_discovered_jobs(all_discovered_jobs)
            logger.info(f"⚡ Priority discovery completed - found {len(all_discovered_jobs)} jobs")
    
    async def _cleanup_old_jobs(self):
        """Remove jobs older than 72 hours from the database."""
        logger.info("🧹 Starting automatic job cleanup...")
        
        try:
            # Calculate cutoff date (72 hours ago)
            cutoff_date = datetime.now() - timedelta(hours=72)
            
            # Get all jobs
            result = await self.firebase_service.get_discovered_jobs()
            if not result.get('success'):
                logger.error(f"Failed to get jobs for cleanup: {result.get('error')}")
                return
            
            all_jobs = result.get('data', [])
            jobs_to_keep = []
            jobs_to_remove = []
            
            for job in all_jobs:
                try:
                    job_date_str = job.get('discovered_at', '')
                    if job_date_str:
                        # Parse the job discovery date
                        job_date = datetime.fromisoformat(job_date_str.replace('Z', '+00:00')).replace(tzinfo=None)
                        
                        if job_date >= cutoff_date:
                            jobs_to_keep.append(job)
                        else:
                            jobs_to_remove.append(job)
                    else:
                        # If no date, keep the job (safety measure)
                        jobs_to_keep.append(job)
                        
                except Exception as e:
                    logger.error(f"Error processing job date for cleanup: {str(e)}")
                    # Keep job if there's an error processing it
                    jobs_to_keep.append(job)
            
            # Update database with only recent jobs
            if jobs_to_remove:
                cleanup_result = await self.firebase_service.cleanup_old_jobs(jobs_to_keep)
                if cleanup_result.get('success'):
                    logger.info(f"🧹 Cleanup completed: removed {len(jobs_to_remove)} old jobs, kept {len(jobs_to_keep)} recent jobs")
                else:
                    logger.error(f"Failed to cleanup old jobs: {cleanup_result.get('error')}")
            else:
                logger.info("🧹 Cleanup completed: no old jobs to remove")
                
        except Exception as e:
            logger.error(f"Error during job cleanup: {str(e)}")
    
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
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-ZaZ0-9.-]+\.[A-Z|a-z]{2,}\b'
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
    
    async def search_custom_job_title(self, job_title: str, locations: List[str] = None, job_types: List[str] = None) -> Dict:
        """Search for a custom job title specified by the user."""
        try:
            logger.info(f"🔍 Custom search for: {job_title}")
            
            if not locations:
                locations = ["remote", "San Francisco, CA", "New York, NY", "Seattle, WA", "Austin, TX"]
            
            if not job_types:
                job_types = ["full-time", "contract", "remote"]
            
            all_jobs = []
            
            for location in locations:
                try:
                    jobs = await self.job_scraper.get_jobs(
                        job_title=job_title,
                        location=location
                    )
                    
                    enriched_jobs = await self._enrich_job_data(jobs, {
                        'title': job_title,
                        'location': location,
                        'job_types': job_types,
                        'custom_search': True
                    })
                    
                    all_jobs.extend(enriched_jobs)
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error in custom search for {job_title} in {location}: {str(e)}")
                    continue
            
            # Store the custom search results
            if all_jobs:
                await self._store_discovered_jobs(all_jobs)
                logger.info(f"Custom search completed: found {len(all_jobs)} jobs for '{job_title}'")
            
            return {
                "success": True,
                "data": all_jobs,
                "total": len(all_jobs),
                "search_title": job_title,
                "locations_searched": locations
            }
            
        except Exception as e:
            logger.error(f"Error in custom job search: {str(e)}")
            return {"success": False, "error": str(e)}

# Global instance
auto_job_discovery = AutoJobDiscoveryService()