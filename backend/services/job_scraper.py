import requests
from bs4 import BeautifulSoup
import time
import random
import logging
import asyncio
import json
import os
from typing import List, Dict, Optional, Tuple, Set
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='job_scraping.log'
)
logger = logging.getLogger(__name__)

class JobScraper:
    """Service for scraping job postings from various job boards."""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
        }
        
        # Initialize cache
        self.cache_dir = os.path.join("backend", "static", "job_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Set up driver pool for parallel scraping
        self.max_drivers = 3  # Maximum number of concurrent browser instances
        self.driver_semaphore = asyncio.Semaphore(self.max_drivers)
        
        # Default timeouts
        self.cache_expiry = 3600  # Cache results for 1 hour
        self.scrape_timeout = 30  # Timeout for individual scraping operations
        
    def _setup_selenium(self):
        """Set up a headless Chrome browser for Selenium."""
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-infobars')
        options.add_argument('--mute-audio')
        options.add_argument('--disable-notifications')
        options.page_load_strategy = 'eager'  # Don't wait for all resources to load
        
        # Set up Chrome driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(15)  # Reduce page load timeout to avoid hanging
        return driver
    
    def _get_cache_key(self, source: str, job_title: str, location: str) -> str:
        """Generate a cache key for a job search."""
        return f"{source}_{job_title.lower().replace(' ', '_')}_{location.lower().replace(' ', '_')}.json"
    
    async def _get_cached_jobs(self, source: str, job_title: str, location: str) -> Tuple[bool, List[Dict]]:
        """
        Get cached job results if available and not expired.
        
        Returns:
            Tuple of (cache_hit, job_list)
        """
        cache_key = self._get_cache_key(source, job_title, location)
        cache_path = os.path.join(self.cache_dir, cache_key)
        
        # Check if cache exists and is not expired
        if os.path.exists(cache_path):
            try:
                cache_time = os.path.getmtime(cache_path)
                current_time = time.time()
                
                # If cache is fresh (less than cache_expiry seconds old)
                if current_time - cache_time < self.cache_expiry:
                    async with open(cache_path, 'r') as f:
                        jobs = json.loads(await f.read())
                    logger.info(f"Using cached results for {source} {job_title} in {location}")
                    return True, jobs
            except Exception as e:
                logger.error(f"Error reading cache for {source}: {str(e)}")
        
        return False, []
    
    async def _save_to_cache(self, source: str, job_title: str, location: str, jobs: List[Dict]) -> None:
        """Save job results to cache."""
        if not jobs:
            return
            
        try:
            cache_key = self._get_cache_key(source, job_title, location)
            cache_path = os.path.join(self.cache_dir, cache_key)
            
            async with open(cache_path, 'w') as f:
                await f.write(json.dumps(jobs))
                
            logger.info(f"Cached {len(jobs)} jobs from {source} for {job_title} in {location}")
        except Exception as e:
            logger.error(f"Error saving cache for {source}: {str(e)}")

    async def search_indeed(self, job_title: str, location: str = "remote") -> List[Dict]:
        """
        Scrape job listings from Indeed, filtering for jobs posted within 48 hours.
        
        Args:
            job_title: The job title to search for
            location: Job location, defaults to "remote"
            
        Returns:
            List of recent job posting dictionaries
        """
        logger.info(f"Searching Indeed for recent {job_title} jobs in {location}")
        
        # Format job title for URL
        formatted_job = job_title.replace(' ', '+')
        formatted_location = location.replace(' ', '+')
        
        try:
            driver = self._setup_selenium()
            
            # Navigate to Indeed search results with date filter for last 3 days
            url = f"https://www.indeed.com/jobs?q={formatted_job}&l={formatted_location}&fromage=3&sort=date"
            driver.get(url)
            
            # Wait for job cards to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.job_seen_beacon"))
            )
            
            # Get all job cards
            job_cards = driver.find_elements(By.CSS_SELECTOR, "div.job_seen_beacon")
            
            results = []
            for job in job_cards[:15]:  # Get more to filter for recency
                try:
                    job_id = job.get_attribute("id")
                    title_element = job.find_element(By.CSS_SELECTOR, "h2.jobTitle a")
                    title = title_element.text.strip()
                    company = job.find_element(By.CSS_SELECTOR, "span.companyName").text.strip()
                    apply_link = title_element.get_attribute("href")
                    
                    # Extract job posting date
                    job_date = None
                    try:
                        date_element = job.find_element(By.CSS_SELECTOR, "span.date")
                        date_text = date_element.text.strip()
                        job_date = self._parse_job_date(date_text)
                    except NoSuchElementException:
                        # If no date found, try alternative selectors
                        try:
                            date_element = job.find_element(By.CSS_SELECTOR, "span[data-testid='job-age']")
                            date_text = date_element.text.strip()
                            job_date = self._parse_job_date(date_text)
                        except NoSuchElementException:
                            pass
                    
                    # Only include jobs posted within last 48 hours
                    if not self._is_recent_job(job_date, max_age_hours=48):
                        continue
                    
                    # Try to get job description
                    description = "Click to view full description"
                    try:
                        desc_snippet = job.find_element(By.CSS_SELECTOR, "div.job-snippet").text.strip()
                        description = desc_snippet
                    except NoSuchElementException:
                        pass
                    
                    results.append({
                        "source": "Indeed",
                        "job_id": job_id,
                        "title": title,
                        "company": company,
                        "description": description,
                        "url": apply_link,
                        "posted_date": job_date.isoformat() if job_date else None,
                        "posted_text": date_text if 'date_text' in locals() else None
                    })
                except Exception as e:
                    logger.error(f"Error parsing Indeed job card: {str(e)}")
            
            logger.info(f"Found {len(results)} recent jobs on Indeed for {job_title}")
            return results
            
        except Exception as e:
            logger.error(f"Error scraping Indeed: {str(e)}")
            return []
        finally:
            if 'driver' in locals():
                driver.quit()
    
    async def search_linkedin(self, job_title: str, location: str = "remote") -> List[Dict]:
        """
        Scrape job listings from LinkedIn.
        
        Args:
            job_title: The job title to search for
            location: Job location, defaults to "remote"
            
        Returns:
            List of job posting dictionaries
        """
        logger.info(f"Searching LinkedIn for {job_title} jobs in {location}")
        
        # Format job title for URL
        formatted_job = job_title.replace(' ', '%20')
        formatted_location = location.replace(' ', '%20')
        
        try:
            url = f"https://www.linkedin.com/jobs/search/?keywords={formatted_job}&location={formatted_location}"
            
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all job cards
            job_cards = soup.select('div.base-card')
            
            results = []
            for job in job_cards[:10]:  # Limit to 10 results
                try:
                    title_element = job.select_one('h3.base-search-card__title')
                    title = title_element.text.strip() if title_element else "Unknown Title"
                    
                    company_element = job.select_one('h4.base-search-card__subtitle')
                    company = company_element.text.strip() if company_element else "Unknown Company"
                    
                    link_element = job.select_one('a.base-card__full-link')
                    link = link_element.get('href') if link_element else None
                    
                    location_element = job.select_one('span.job-search-card__location')
                    job_location = location_element.text.strip() if location_element else "Unknown Location"
                    
                    job_id = link.split('?')[0].split('-')[-1] if link else "unknown"
                    
                    results.append({
                        "source": "LinkedIn",
                        "job_id": job_id,
                        "title": title,
                        "company": company,
                        "location": job_location,
                        "url": link
                    })
                except Exception as e:
                    logger.error(f"Error parsing LinkedIn job card: {str(e)}")
            
            logger.info(f"Found {len(results)} jobs on LinkedIn for {job_title}")
            return results
            
        except Exception as e:
            logger.error(f"Error scraping LinkedIn: {str(e)}")
            return []

    async def search_glassdoor(self, job_title: str, location: str = "remote") -> List[Dict]:
        """
        Scrape job listings from Glassdoor.
        
        Args:
            job_title: The job title to search for
            location: Job location, defaults to "remote"
            
        Returns:
            List of job posting dictionaries
        """
        logger.info(f"Searching Glassdoor for {job_title} jobs in {location}")
        
        # Format job title for URL
        formatted_job = job_title.replace(' ', '-')
        formatted_location = location.replace(' ', '-')
        
        try:
            driver = self._setup_selenium()
            
            # Navigate to Glassdoor search results
            url = f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={formatted_job}&locT=C&locId=1147401&locKeyword={formatted_location}"
            driver.get(url)
            
            # Wait for job cards to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "li.react-job-listing"))
            )
            
            # Get all job cards
            job_cards = driver.find_elements(By.CSS_SELECTOR, "li.react-job-listing")
            
            results = []
            for job in job_cards[:10]:  # Limit to 10 results
                try:
                    job_id = job.get_attribute("data-id")
                    title_element = job.find_element(By.CSS_SELECTOR, "a.jobLink")
                    title = title_element.text.strip()
                    company = job.find_element(By.CSS_SELECTOR, "div.job-search-results__job-tile-company").text.strip()
                    
                    # Get the job URL - handle relative URLs
                    apply_link = title_element.get_attribute("href")
                    if not apply_link.startswith("http"):
                        apply_link = f"https://www.glassdoor.com{apply_link}"
                    
                    results.append({
                        "source": "Glassdoor",
                        "job_id": job_id,
                        "title": title,
                        "company": company,
                        "description": "Click to view full description",
                        "url": apply_link
                    })
                except Exception as e:
                    logger.error(f"Error parsing Glassdoor job card: {str(e)}")
            
            logger.info(f"Found {len(results)} jobs on Glassdoor for {job_title}")
            return results
            
        except Exception as e:
            logger.error(f"Error scraping Glassdoor: {str(e)}")
            return []
        finally:
            if 'driver' in locals():
                driver.quit()

    async def search_ziprecruiter(self, job_title: str, location: str = "remote") -> List[Dict]:
        """
        Scrape job listings from ZipRecruiter.
        
        Args:
            job_title: The job title to search for
            location: Job location, defaults to "remote"
            
        Returns:
            List of job posting dictionaries
        """
        logger.info(f"Searching ZipRecruiter for {job_title} jobs in {location}")
        
        # Format job title for URL
        formatted_job = job_title.replace(' ', '+')
        formatted_location = location.replace(' ', '+')
        
        try:
            driver = self._setup_selenium()
            
            # Navigate to ZipRecruiter search results
            url = f"https://www.ziprecruiter.com/jobs/search?q={formatted_job}&l={formatted_location}"
            driver.get(url)
            
            # Wait for job cards to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "article.job_item"))
            )
            
            # Get all job cards
            job_cards = driver.find_elements(By.CSS_SELECTOR, "article.job_item")
            
            results = []
            for job in job_cards[:10]:  # Limit to 10 results
                try:
                    title_element = job.find_element(By.CSS_SELECTOR, "h2.job_title")
                    title = title_element.text.strip()
                    
                    company_element = job.find_element(By.CSS_SELECTOR, "a.company_name")
                    company = company_element.text.strip()
                    
                    link_element = job.find_element(By.CSS_SELECTOR, "a.job_link")
                    apply_link = link_element.get_attribute("href")
                    
                    job_id = f"ziprecruiter-{len(results)}"
                    
                    results.append({
                        "source": "ZipRecruiter",
                        "job_id": job_id,
                        "title": title,
                        "company": company,
                        "description": "Click to view full description",
                        "url": apply_link
                    })
                except Exception as e:
                    logger.error(f"Error parsing ZipRecruiter job card: {str(e)}")
            
            logger.info(f"Found {len(results)} jobs on ZipRecruiter for {job_title}")
            return results
            
        except Exception as e:
            logger.error(f"Error scraping ZipRecruiter: {str(e)}")
            return []
        finally:
            if 'driver' in locals():
                driver.quit()

    async def search_monster(self, job_title: str, location: str = "remote") -> List[Dict]:
        """
        Scrape job listings from Monster.
        
        Args:
            job_title: The job title to search for
            location: Job location, defaults to "remote"
            
        Returns:
            List of job posting dictionaries
        """
        logger.info(f"Searching Monster for {job_title} jobs in {location}")
        
        # Format job title for URL
        formatted_job = job_title.replace(' ', '-')
        formatted_location = location.replace(' ', '-')
        
        try:
            driver = self._setup_selenium()
            
            # Navigate to Monster search results
            url = f"https://www.monster.com/jobs/search?q={formatted_job}&where={formatted_location}"
            driver.get(url)
            
            # Wait for job cards to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "section.card-content"))
            )
            
            # Get all job cards
            job_cards = driver.find_elements(By.CSS_SELECTOR, "section.card-content")
            
            results = []
            for job in job_cards[:10]:  # Limit to 10 results
                try:
                    title_element = job.find_element(By.CSS_SELECTOR, "h3.title")
                    title = title_element.text.strip()
                    
                    company_element = job.find_element(By.CSS_SELECTOR, "div.company")
                    company = company_element.text.strip()
                    
                    link_element = job.find_element(By.CSS_SELECTOR, "a.job-cardstyle__JobCardComponent")
                    apply_link = link_element.get_attribute("href")
                    
                    job_id = f"monster-{len(results)}"
                    
                    results.append({
                        "source": "Monster",
                        "job_id": job_id,
                        "title": title,
                        "company": company,
                        "description": "Click to view full description",
                        "url": apply_link
                    })
                except Exception as e:
                    logger.error(f"Error parsing Monster job card: {str(e)}")
            
            logger.info(f"Found {len(results)} jobs on Monster for {job_title}")
            return results
            
        except Exception as e:
            logger.error(f"Error scraping Monster: {str(e)}")
            return []
        finally:
            if 'driver' in locals():
                driver.quit()

    async def search_google_jobs(self, job_title: str, location: str = "remote") -> List[Dict]:
        """
        Scrape job listings from Google Jobs, specifically targeting "hiring now" positions.
        
        Args:
            job_title: The job title to search for
            location: Job location, defaults to "remote"
            
        Returns:
            List of job posting dictionaries
        """
        logger.info(f"Searching Google Jobs for {job_title} jobs in {location} with 'hiring now' filter")
        
        # Format job title for URL - include "hiring now" in the search query
        formatted_job = job_title.replace(' ', '+')
        formatted_location = location.replace(' ', '+')
        
        try:
            driver = self._setup_selenium()
            
            # Navigate to Google Jobs search results with "hiring now" added to query
            url = f"https://www.google.com/search?q={formatted_job}+{formatted_location}+\"hiring+now\"+jobs&ibp=htl;jobs"
            driver.get(url)
            
            # Wait for job cards to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.PwjeAc"))
            )
            
            # Get all job cards
            job_cards = driver.find_elements(By.CSS_SELECTOR, "div.PwjeAc")
            
            results = []
            for i, job in enumerate(job_cards[:15]):  # Increased limit to 15 for more "hiring now" results
                try:
                    # Click on job to load details
                    job.click()
                    time.sleep(1)
                    
                    # Extract job details
                    title_element = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "h2.KLsYvd"))
                    )
                    title = title_element.text.strip()
                    
                    company_element = driver.find_element(By.CSS_SELECTOR, "div.nJlQNd")
                    company = company_element.text.strip()
                    
                    # Get the apply button URL if available
                    try:
                        apply_element = driver.find_element(By.CSS_SELECTOR, "a.pMhGee")
                        apply_link = apply_element.get_attribute("href")
                    except:
                        apply_link = url
                    
                    job_id = f"google-{i}"
                    
                    # Try to get job description
                    try:
                        description_element = driver.find_element(By.CSS_SELECTOR, "span.HBvzbc")
                        description = description_element.text.strip()
                    except:
                        description = "Click to view full description"
                    
                    # Try to extract date posted to prioritize recent listings
                    posted_date = None
                    try:
                        date_element = driver.find_element(By.CSS_SELECTOR, "div.KKh3md")
                        date_text = date_element.text.strip()
                        posted_date = self._parse_job_date(date_text)
                    except:
                        posted_date = None
                    
                    # Look for "hiring now" or "urgently hiring" indicators in the description
                    is_urgent = any(phrase in description.lower() for phrase in 
                                    ["hiring now", "urgent", "immediate", "start asap", "start immediately"])
                    
                    # Try to extract email addresses from job description
                    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                    emails = re.findall(email_pattern, description)
                    contact_email = emails[0] if emails else None
                    
                    results.append({
                        "source": "Google Jobs",
                        "job_id": job_id,
                        "title": title,
                        "company": company,
                        "description": description,
                        "url": apply_link,
                        "posted_date": posted_date.isoformat() if posted_date else None,
                        "is_urgent": is_urgent,
                        "contact_email": contact_email
                    })
                except Exception as e:
                    logger.error(f"Error parsing Google Jobs card: {str(e)}")
            
            # Sort results to prioritize urgent jobs first
            results.sort(key=lambda x: (0 if x.get("is_urgent") else 1))
            
            logger.info(f"Found {len(results)} jobs on Google Jobs for {job_title} with 'hiring now' filter")
            return results
            
        except Exception as e:
            logger.error(f"Error scraping Google Jobs: {str(e)}")
            return []
        finally:
            if 'driver' in locals():
                driver.quit()
    
    async def search_simplyhired(self, job_title: str, location: str = "remote") -> List[Dict]:
        """
        Scrape job listings from SimplyHired.
        
        Args:
            job_title: The job title to search for
            location: Job location, defaults to "remote"
            
        Returns:
            List of job posting dictionaries
        """
        logger.info(f"Searching SimplyHired for {job_title} jobs in {location}")
        
        # Format job title for URL
        formatted_job = job_title.replace(' ', '+')
        formatted_location = location.replace(' ', '+')
        
        try:
            driver = self._setup_selenium()
            
            # Navigate to SimplyHired search results
            url = f"https://www.simplyhired.com/search?q={formatted_job}&l={formatted_location}"
            driver.get(url)
            
            # Wait for job cards to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.SerpJob-jobCard"))
            )
            
            # Get all job cards
            job_cards = driver.find_elements(By.CSS_SELECTOR, "div.SerpJob-jobCard")
            
            results = []
            for job in job_cards[:10]:  # Limit to 10 results
                try:
                    title_element = job.find_element(By.CSS_SELECTOR, "h3.jobposting-title")
                    title = title_element.text.strip()
                    
                    company_element = job.find_element(By.CSS_SELECTOR, "span.jobposting-company")
                    company = company_element.text.strip()
                    
                    link_element = job.find_element(By.CSS_SELECTOR, "a.jobposting-link")
                    apply_link = link_element.get_attribute("href")
                    if not apply_link.startswith("http"):
                        apply_link = f"https://www.simplyhired.com{apply_link}"
                    
                    job_id = f"simplyhired-{len(results)}"
                    
                    # Try to get job description snippet
                    try:
                        description_element = job.find_element(By.CSS_SELECTOR, "p.jobposting-snippet")
                        description = description_element.text.strip()
                    except NoSuchElementException:
                        description = "Click to view full description"
                    
                    results.append({
                        "source": "SimplyHired",
                        "job_id": job_id,
                        "title": title,
                        "company": company,
                        "description": description,
                        "url": apply_link
                    })
                except Exception as e:
                    logger.error(f"Error parsing SimplyHired job card: {str(e)}")
            
            logger.info(f"Found {len(results)} jobs on SimplyHired for {job_title}")
            return results
            
        except Exception as e:
            logger.error(f"Error scraping SimplyHired: {str(e)}")
            return []
        finally:
            if 'driver' in locals():
                driver.quit()

    async def search_dice(self, job_title: str, location: str = "remote") -> List[Dict]:
        """
        Scrape job listings from Dice (tech jobs).
        
        Args:
            job_title: The job title to search for
            location: Job location, defaults to "remote"
            
        Returns:
            List of job posting dictionaries
        """
        logger.info(f"Searching Dice for {job_title} jobs in {location}")
        
        # Format job title for URL
        formatted_job = job_title.replace(' ', '%20')
        formatted_location = location.replace(' ', '%20')
        
        try:
            driver = self._setup_selenium()
            
            # Navigate to Dice search results
            url = f"https://www.dice.com/jobs?q={formatted_job}&location={formatted_location}"
            driver.get(url)
            
            # Wait for job cards to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.search-card"))
            )
            
            # Get all job cards
            job_cards = driver.find_elements(By.CSS_SELECTOR, "div.search-card")
            
            results = []
            for job in job_cards[:10]:  # Limit to 10 results
                try:
                    title_element = job.find_element(By.CSS_SELECTOR, "a.card-title-link")
                    title = title_element.text.strip()
                    
                    company_element = job.find_element(By.CSS_SELECTOR, "a.company-name-link")
                    company = company_element.text.strip()
                    
                    apply_link = title_element.get_attribute("href")
                    
                    # Generate a unique job ID
                    job_id = f"dice-{len(results)}"
                    
                    # Try to get job location
                    try:
                        location_element = job.find_element(By.CSS_SELECTOR, "span.search-result-location")
                        job_location = location_element.text.strip()
                    except NoSuchElementException:
                        job_location = location
                    
                    results.append({
                        "source": "Dice",
                        "job_id": job_id,
                        "title": title,
                        "company": company,
                        "location": job_location,
                        "description": "Click to view full description",
                        "url": apply_link
                    })
                except Exception as e:
                    logger.error(f"Error parsing Dice job card: {str(e)}")
            
            logger.info(f"Found {len(results)} jobs on Dice for {job_title}")
            return results
            
        except Exception as e:
            logger.error(f"Error scraping Dice: {str(e)}")
            return []
        finally:
            if 'driver' in locals():
                driver.quit()

    async def search_angellist(self, job_title: str, location: str = "remote") -> List[Dict]:
        """
        Scrape job listings from AngelList/Wellfound (startup jobs).
        
        Args:
            job_title: The job title to search for
            location: Job location, defaults to "remote"
            
        Returns:
            List of job posting dictionaries
        """
        logger.info(f"Searching AngelList/Wellfound for {job_title} jobs in {location}")
        
        # Format job title for URL
        formatted_job = job_title.replace(' ', '%20')
        formatted_location = location.replace(' ', '%20')
        
        try:
            driver = self._setup_selenium()
            
            # Navigate to Wellfound (formerly AngelList) search results
            url = f"https://wellfound.com/jobs?role={formatted_job}&location={formatted_location}"
            driver.get(url)
            
            # Wait for job cards to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.styles_component__JsszL"))
            )
            
            # Get all job cards
            job_cards = driver.find_elements(By.CSS_SELECTOR, "div.styles_component__JsszL")
            
            results = []
            for job in job_cards[:10]:  # Limit to 10 results
                try:
                    title_element = job.find_element(By.CSS_SELECTOR, "div.styles_title__jvEgi a")
                    title = title_element.text.strip()
                    
                    company_element = job.find_element(By.CSS_SELECTOR, "div.styles_company__MywSN")
                    company = company_element.text.strip()
                    
                    apply_link = title_element.get_attribute("href")
                    
                    # Generate a unique job ID
                    job_id = f"angellist-{len(results)}"
                    
                    results.append({
                        "source": "AngelList/Wellfound",
                        "job_id": job_id,
                        "title": title,
                        "company": company,
                        "description": "Click to view full description",
                        "url": apply_link
                    })
                except Exception as e:
                    logger.error(f"Error parsing AngelList/Wellfound job card: {str(e)}")
            
            logger.info(f"Found {len(results)} jobs on AngelList/Wellfound for {job_title}")
            return results
            
        except Exception as e:
            logger.error(f"Error scraping AngelList/Wellfound: {str(e)}")
            return []
        finally:
            if 'driver' in locals():
                driver.quit()
    
    async def get_jobs(self, job_title: str, location: str = "remote") -> List[Dict]:
        """
        Get jobs from multiple sources in parallel with priority for "hiring now" positions.
        
        Args:
            job_title: The job title to search for
            location: Job location, defaults to "remote"
            
        Returns:
            List of combined job postings prioritizing actively hiring positions
        """
        start_time = time.time()
        logger.info(f"Searching for {job_title} jobs in {location}")
        
        # Define sources to search with a weighting for quality
        # Put Google Jobs first since we've enhanced it with "hiring now" keyword
        sources = [
            (self.search_google_jobs, 1.0),  # Google Jobs with "hiring now" - highest priority
            (self.search_indeed, 0.9),       # Indeed is reliable but doesn't specifically target "hiring now"
            (self.search_linkedin, 0.8),     
            (self.search_glassdoor, 0.7),
            (self.search_ziprecruiter, 0.7),
            (self.search_monster, 0.6),
            (self.search_simplyhired, 0.6),
            (self.search_dice, 0.7),
            (self.search_angellist, 0.6)
        ]
        
        # Create tasks for all sources to run in parallel
        tasks = []
        for search_func, _ in sources:
            tasks.append(self._search_with_timeout(search_func, job_title, location))
        
        # Run all search tasks concurrently
        results = await asyncio.gather(*tasks)
        
        # Combine and deduplicate results with source weighting and urgency prioritization
        all_jobs = []
        seen_jobs = set()
        
        # First, process Google Jobs results to prioritize "hiring now" jobs
        google_jobs_results = next((r for r, f in results if f.__name__ == 'search_google_jobs'), [])
        
        # Add urgent jobs first
        for job in google_jobs_results:
            if job.get("is_urgent", False):
                job_key = f"{job.get('company', '')}-{job.get('title', '')}"
                if job_key not in seen_jobs:
                    # Boost score for urgent jobs
                    job["quality_score"] = 1.2  # Higher than any other source
                    job["hiring_now"] = True
                    all_jobs.append(job)
                    seen_jobs.add(job_key)
        
        # Then process all remaining jobs from all sources
        for (source_jobs, search_func), (source_func, weight) in zip(results, sources):
            if not source_jobs:
                continue
                
            for job in source_jobs:
                # Create a unique identifier for deduplication
                job_key = f"{job.get('company', '')}-{job.get('title', '')}"
                
                if job_key not in seen_jobs:
                    # Add a quality score based on source weighting
                    job["quality_score"] = weight
                    
                    # Boost score for jobs that mention "hiring now" in description
                    description = job.get("description", "").lower()
                    if any(keyword in description for keyword in ["hiring now", "urgently hiring", "immediate start", "immediate opening"]):
                        job["quality_score"] += 0.2
                        job["hiring_now"] = True
                    
                    # Boost score for jobs with contact email (easier to apply)
                    if job.get("contact_email"):
                        job["quality_score"] += 0.1
                    
                    all_jobs.append(job)
                    seen_jobs.add(job_key)
        
        # Sort first by hiring_now flag, then by quality score, then by company name
        all_jobs.sort(key=lambda x: (
            0 if x.get("hiring_now") else 1,  # Hiring now jobs first
            -x.get("quality_score", 0),       # Then by quality score (descending)
            x.get("company", "")              # Then alphabetically by company
        ))
        
        elapsed_time = time.time() - start_time
        logger.info(f"Found {len(all_jobs)} unique jobs for {job_title} in {location} in {elapsed_time:.2f} seconds")
        
        return all_jobs
        
    async def _search_with_timeout(self, search_func, job_title: str, location: str):
        """Run a search function with timeout and caching."""
        source_name = search_func.__name__.replace("search_", "")
        
        try:
            # Check cache first
            cache_hit, cached_jobs = await self._get_cached_jobs(source_name, job_title, location)
            if cache_hit:
                return cached_jobs, search_func
            
            # Run the search with a timeout
            source_jobs = await asyncio.wait_for(
                search_func(job_title, location),
                timeout=self.scrape_timeout
            )
            
            # Cache the results
            await self._save_to_cache(source_name, job_title, location, source_jobs)
            
            return source_jobs, search_func
            
        except asyncio.TimeoutError:
            logger.warning(f"Timeout while searching {source_name} for {job_title}")
            return [], search_func
        except Exception as e:
            logger.error(f"Error in {source_name} search: {str(e)}")
            return [], search_func
            
    async def get_job_description(self, job_url: str) -> Optional[str]:
        """
        Get the full job description from a job listing URL.
        
        Args:
            job_url: The URL of the job listing
            
        Returns:
            str: The job description or None if not found
        """
        try:
            driver = self._setup_selenium()
            driver.get(job_url)
            
            # Wait for page to load
            time.sleep(3)
            
            # Different selectors for different job boards
            selectors = [
                "div.job-description",  # Indeed
                "div.description__text",  # LinkedIn
                "div.jobDescriptionText",  # Indeed alternative
                "div#jobDescriptionText",  # Indeed alternative
                "div.show-more-less-html__markup",  # LinkedIn alternative
                "div.jobDescriptionContent",  # Glassdoor
                "div.job_description",  # ZipRecruiter
                "div.job-description-content",  # Monster
                "span.HBvzbc",  # Google Jobs
                "div.viewjob-description",  # SimplyHired
                "div[data-testid='jobDescription']",  # Dice
                "div.styles_component__vhR_y"  # AngelList/Wellfound
            ]
            
            for selector in selectors:
                try:
                    description_element = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    return description_element.text.strip()
                except:
                    continue
            
            # If none of the selectors worked, try getting the entire body
            body = driver.find_element(By.TAG_NAME, "body")
            return body.text
            
        except Exception as e:
            logger.error(f"Error getting job description: {str(e)}")
            return None
        finally:
            if 'driver' in locals():
                driver.quit()
    
    def _parse_job_date(self, date_text: str) -> Optional[datetime]:
        """
        Parse job posting date from various formats.
        
        Args:
            date_text: The date text from job posting
            
        Returns:
            datetime: Parsed date or None if parsing fails
        """
        if not date_text:
            return None
            
        date_text = date_text.lower().strip()
        now = datetime.now()
        
        try:
            # Handle relative dates
            if 'today' in date_text or 'just posted' in date_text:
                return now
            elif 'yesterday' in date_text:
                return now - timedelta(days=1)
            elif 'days ago' in date_text or 'day ago' in date_text:
                # Extract number of days
                days_match = re.search(r'(\d+)\s*days?\s+ago', date_text)
                if days_match:
                    days = int(days_match.group(1))
                    return now - timedelta(days=days)
            elif 'hours ago' in date_text or 'hour ago' in date_text:
                # Extract number of hours
                hours_match = re.search(r'(\d+)\s*hours?\s+ago', date_text)
                if hours_match:
                    hours = int(hours_match.group(1))
                    return now - timedelta(hours=hours)
            elif 'minutes ago' in date_text or 'minute ago' in date_text:
                # Extract number of minutes
                minutes_match = re.search(r'(\d+)\s*minutes?\s+ago', date_text)
                if minutes_match:
                    minutes = int(minutes_match.group(1))
                    return now - timedelta(minutes=minutes)
            elif 'weeks ago' in date_text or 'week ago' in date_text:
                # Extract number of weeks
                weeks_match = re.search(r'(\d+)\s*weeks?\s+ago', date_text)
                if weeks_match:
                    weeks = int(weeks_match.group(1))
                    return now - timedelta(weeks=weeks)
            elif 'months ago' in date_text or 'month ago' in date_text:
                # Extract number of months (approximate)
                months_match = re.search(r'(\d+)\s*months?\s+ago', date_text)
                if months_match:
                    months = int(months_match.group(1))
                    return now - timedelta(days=months * 30)
            
            # Try to parse absolute dates
            date_patterns = [
                '%Y-%m-%d',
                '%m/%d/%Y',
                '%d/%m/%Y',
                '%b %d, %Y',
                '%B %d, %Y',
                '%d %b %Y',
                '%d %B %Y'
            ]
            
            for pattern in date_patterns:
                try:
                    return datetime.strptime(date_text, pattern)
                except ValueError:
                    continue
                    
        except Exception as e:
            logger.error(f"Error parsing date '{date_text}': {str(e)}")
            
        return None
    
    def _is_recent_job(self, job_date: Optional[datetime], max_age_hours: int = 48) -> bool:
        """
        Check if a job was posted within the specified time frame.
        
        Args:
            job_date: The date the job was posted
            max_age_hours: Maximum age in hours (default 48 hours)
            
        Returns:
            bool: True if job is recent, False otherwise
        """
        if not job_date:
            # If we can't determine the date, assume it's recent to be safe
            return True
            
        cutoff_date = datetime.now() - timedelta(hours=max_age_hours)
        return job_date >= cutoff_date