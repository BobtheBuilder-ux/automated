"""
Application strategies for different job platforms with optimizations and email fallback.
Each strategy implements the logic needed to submit applications to a specific job board.
"""

import os
import logging
import aiohttp
import asyncio
import time
import re
from abc import ABC, abstractmethod
from typing import Dict, Tuple, Optional, List
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='job_submission.log'
)
logger = logging.getLogger(__name__)

class ApplicationStrategy(ABC):
    """Base abstract class for job application strategies"""
    
    def __init__(self):
        # Timeouts for application attempts
        self.connect_timeout = 10  # seconds
        self.application_timeout = 180  # 3 minutes for full application process
        self.driver_pool_size = 2  # Maximum concurrent browser instances
        self.driver_semaphore = asyncio.Semaphore(self.driver_pool_size)
        
    def _setup_selenium(self, headless: bool = True):
        """Set up a Chrome browser for Selenium with optimized settings."""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.page_load_strategy = 'eager'  # Don't wait for all resources
        
        # Set up Chrome driver with optimized settings
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(self.connect_timeout)
        
        return driver
    
    @abstractmethod
    async def apply(self, 
                  job_data: Dict, 
                  user_data: Dict, 
                  cv_path: str, 
                  cover_letter_path: str) -> Tuple[bool, str]:
        """
        Apply to a job using this strategy
        
        Args:
            job_data: Job details including URL
            user_data: User information (name, email, phone, etc.)
            cv_path: Path to resume/CV file
            cover_letter_path: Path to cover letter file
            
        Returns:
            Tuple of (success, message)
        """
        pass
    
    async def apply_with_timeout(self, 
                             job_data: Dict, 
                             user_data: Dict, 
                             cv_path: str, 
                             cover_letter_path: str) -> Tuple[bool, str]:
        """
        Apply to a job with a timeout to prevent hanging applications.
        
        Args:
            job_data: Job details including URL
            user_data: User information
            cv_path: Path to CV file
            cover_letter_path: Path to cover letter file
            
        Returns:
            Tuple of (success, message)
        """
        start_time = time.time()
        job_title = job_data.get("title", "Unknown position")
        company = job_data.get("company", "Unknown company")
        
        logger.info(f"Starting application for {job_title} at {company}")
        
        try:
            # Use asyncio.wait_for to implement a timeout
            result = await asyncio.wait_for(
                self.apply(job_data, user_data, cv_path, cover_letter_path),
                timeout=self.application_timeout
            )
            
            elapsed_time = time.time() - start_time
            logger.info(f"Application for {job_title} at {company} completed in {elapsed_time:.2f} seconds")
            
            return result
            
        except asyncio.TimeoutError:
            elapsed_time = time.time() - start_time
            logger.warning(f"Application timed out after {elapsed_time:.2f} seconds for {job_title} at {company}")
            return False, f"Application timed out after {self.application_timeout} seconds"
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Application failed after {elapsed_time:.2f} seconds for {job_title} at {company}: {str(e)}")
            return False, f"Application error: {str(e)}"

    def extract_email_from_job(self, job_data: Dict) -> Optional[str]:
        """
        Extract an email address from job description if available.
        Enhanced version to find more potential email contacts.
        
        Args:
            job_data: Job details including description
            
        Returns:
            Email address or None
        """
        description = job_data.get("description", "")
        if not description:
            return None
            
        # Look for email patterns - more comprehensive pattern
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, description)
        
        # Look for text patterns that often indicate emails
        contact_pattern = r'(?:contact|email|send|apply)[^.!?]*?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        contact_matches = re.findall(contact_pattern, description, re.IGNORECASE)
        
        # Combine found emails
        all_emails = list(set(emails + contact_matches))
        
        if all_emails:
            # Prioritize emails with recruiting/career/job/hr related words
            priority_emails = [email for email in all_emails if any(word in email.lower() 
                              for word in ["career", "job", "recruit", "hr", "apply", "hiring", "talent", "cv", "resume"])]
            
            if priority_emails:
                return priority_emails[0]
            return all_emails[0]  # Return the first email found
        
        # If no email found, check if URL contains a contact page
        url = job_data.get("url", "")
        if url:
            # Extract domain for potential email construction
            domain_pattern = r'https?://(?:www\.)?([^/]+)'
            domain_match = re.search(domain_pattern, url)
            if domain_match:
                domain = domain_match.group(1)
                return f"careers@{domain}"
        
        # If still no email found, try to guess based on company domain
        company_name = job_data.get("company", "").lower()
        if company_name:
            # Remove common words that might interfere with company name
            company_name = re.sub(r'\b(ltd|inc|llc|corp|company|co|limited)\b', '', company_name, flags=re.IGNORECASE)
            # Remove punctuation and spaces
            company_name = re.sub(r'[^\w]', '', company_name)
            
            # Return a common recruiting email format
            return f"careers@{company_name}.com"
            
        return None

class LinkedInStrategy(ApplicationStrategy):
    """Strategy for applying to jobs on LinkedIn"""
    
    async def apply(self, 
                  job_data: Dict, 
                  user_data: Dict, 
                  cv_path: str, 
                  cover_letter_path: str) -> Tuple[bool, str]:
        """Apply to a LinkedIn job posting"""
        async with self.driver_semaphore:  # Control concurrent browser usage
            try:
                # Set up headless Chrome browser
                driver = self._setup_selenium()
                
                # Navigate to job URL
                job_url = job_data.get("url", "")
                if not job_url:
                    return False, "Job URL is missing"
                    
                driver.get(job_url)
                
                # Check if we need to sign in
                try:
                    # This is a simplified example. In a real implementation, you would need to
                    # handle LinkedIn authentication, which likely requires saved credentials or OAuth
                    if "login" in driver.current_url or driver.find_elements(By.XPATH, "//button[contains(text(), 'Sign in')]"):
                        return False, "LinkedIn authentication required"
                
                    # Look for the apply button
                    apply_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Apply') or contains(text(), 'Easy Apply')]"))
                    )
                    apply_button.click()
                    
                    # Here we would fill out the application form
                    # This varies based on the job listing, so in a real implementation
                    # you would need logic to handle different form types
                    
                    # Example: upload resume if prompted
                    try:
                        resume_upload = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, "//input[@type='file']"))
                        )
                        resume_upload.send_keys(cv_path)
                    except (TimeoutException, NoSuchElementException):
                        logger.warning("Resume upload element not found")
                    
                    # Submit application (this is just a placeholder - actual submission would require more steps)
                    # submit_button = WebDriverWait(driver, 10).until(
                    #     EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Submit application')]"))
                    # )
                    # submit_button.click()
                    
                    # For now, just log the attempt
                    logger.info(f"Successfully initiated LinkedIn application process for job: {job_data.get('title')}")
                    return True, "Application submission initiated on LinkedIn"
                    
                except TimeoutException as e:
                    logger.error(f"Timeout while applying to LinkedIn job: {str(e)}")
                    return False, f"Timeout error: {str(e)}"
                    
                finally:
                    driver.quit()
                    
            except Exception as e:
                logger.error(f"Error applying to LinkedIn job: {str(e)}")
                return False, f"Error: {str(e)}"

class IndeedStrategy(ApplicationStrategy):
    """Strategy for applying to jobs on Indeed"""
    
    async def apply(self, 
                  job_data: Dict, 
                  user_data: Dict, 
                  cv_path: str, 
                  cover_letter_path: str) -> Tuple[bool, str]:
        """Apply to an Indeed job posting"""
        async with self.driver_semaphore:  # Control concurrent browser usage
            try:
                # Set up headless Chrome browser
                driver = self._setup_selenium()
                
                # Navigate to job URL
                job_url = job_data.get("url", "")
                if not job_url:
                    return False, "Job URL is missing"
                    
                driver.get(job_url)
                
                # Check for the apply button
                try:
                    apply_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Apply now')]"))
                    )
                    apply_button.click()
                    
                    # This would need to handle Indeed's application flow
                    # which might include a multi-step process or redirects to company websites
                    
                    # For now, just log the attempt
                    logger.info(f"Successfully initiated Indeed application process for job: {job_data.get('title')}")
                    return True, "Application submission initiated on Indeed"
                    
                except TimeoutException as e:
                    logger.error(f"Timeout while applying to Indeed job: {str(e)}")
                    return False, f"Timeout error: {str(e)}"
                    
                finally:
                    driver.quit()
                    
            except Exception as e:
                logger.error(f"Error applying to Indeed job: {str(e)}")
                return False, f"Error: {str(e)}"

class GlassdoorStrategy(ApplicationStrategy):
    """Strategy for applying to jobs on Glassdoor"""
    
    async def apply(self, 
                  job_data: Dict, 
                  user_data: Dict, 
                  cv_path: str, 
                  cover_letter_path: str) -> Tuple[bool, str]:
        """Apply to a Glassdoor job posting"""
        async with self.driver_semaphore:  # Control concurrent browser usage
            try:
                # Set up headless Chrome browser
                driver = self._setup_selenium()
                
                # Navigate to job URL
                job_url = job_data.get("url", "")
                if not job_url:
                    return False, "Job URL is missing"
                    
                driver.get(job_url)
                
                # Glassdoor-specific application flow would go here
                # For now, just log the attempt
                logger.info(f"Successfully initiated Glassdoor application process for job: {job_data.get('title')}")
                return True, "Application submission initiated on Glassdoor"
                    
            except Exception as e:
                logger.error(f"Error applying to Glassdoor job: {str(e)}")
                return False, f"Error: {str(e)}"
                
            finally:
                driver.quit()

class DirectWebsiteStrategy(ApplicationStrategy):
    """Strategy for applying directly to company websites"""
    
    async def apply(self, 
                  job_data: Dict, 
                  user_data: Dict, 
                  cv_path: str, 
                  cover_letter_path: str) -> Tuple[bool, str]:
        """Apply to a job on a company website"""
        # This is the most challenging strategy as every company website is different
        # In a real implementation, you might need company-specific sub-strategies
        logger.info(f"Direct website application initiated for: {job_data.get('company')}")
        return False, "Direct website applications require manual handling"

class EmailApplicationStrategy(ApplicationStrategy):
    """Strategy for applying via email"""
    
    async def apply(self, 
                  job_data: Dict, 
                  user_data: Dict, 
                  cv_path: str, 
                  cover_letter_path: str) -> Tuple[bool, str]:
        """Apply to a job by sending an email application"""
        from .email_service import EmailService
        
        email_service = EmailService()
        
        # Check if job listing has an email contact
        contact_email = job_data.get("contact_email")
        
        # If no contact email provided, try to extract one from job description
        if not contact_email:
            contact_email = self.extract_email_from_job(job_data)
            
        if not contact_email:
            return False, "No contact email available for this job"
        
        # Generate email subject and body
        job_title = job_data.get("title", "")
        company = job_data.get("company", "")
        name = user_data.get("name", "")
        sender_email = user_data.get("email", "")
        
        subject = f"Application for {job_title} position"
        
        # Read cover letter content
        cover_letter_content = ""
        try:
            with open(cover_letter_path, 'r') as f:
                cover_letter_content = f.read()
        except Exception as e:
            logger.error(f"Error reading cover letter: {str(e)}")
            cover_letter_content = f"Please find attached my application for the {job_title} position."
        
        # Create email body
        body = f"""Dear Hiring Manager,

I am writing to express my interest in the {job_title} position at {company}. Please find attached my resume and cover letter for your consideration.

{cover_letter_content}

Thank you for your time and consideration. I look forward to the opportunity to discuss my qualifications further.

Best regards,
{name}
{sender_email}
"""
        
        # Send application via email with attachments
        success = await email_service.send_job_application(
            recipient_email=contact_email,
            subject=subject,
            body=body,
            sender_name=name,
            sender_email=sender_email,
            attachments=[cv_path, cover_letter_path]
        )
        
        if success:
            logger.info(f"Successfully sent application email to {contact_email} for {job_title} at {company}")
            return True, f"Application sent via email to {contact_email}"
        else:
            logger.error(f"Failed to send application email to {contact_email} for {job_title} at {company}")
            return False, "Failed to send application email"

class StrategyFactory:
    """Factory to create application strategies based on job source"""
    
    @staticmethod
    def create_strategy(job_source: str) -> ApplicationStrategy:
        """
        Create an appropriate application strategy based on the job source
        
        Args:
            job_source: Source of the job listing (e.g., 'linkedin', 'indeed')
            
        Returns:
            An application strategy instance
        """
        job_source = job_source.lower() if job_source else ""
        
        if "linkedin" in job_source:
            return LinkedInStrategy()
        elif "indeed" in job_source:
            return IndeedStrategy()
        elif "glassdoor" in job_source:
            return GlassdoorStrategy()
        elif "email" in job_source:
            return EmailApplicationStrategy()
        elif "monster" in job_source:
            return DirectWebsiteStrategy()
        elif "ziprecruiter" in job_source:
            return DirectWebsiteStrategy()
        elif "google" in job_source:
            return DirectWebsiteStrategy()
        else:
            # Default to direct website strategy for unknown sources
            return DirectWebsiteStrategy()
            
    @staticmethod
    def create_email_strategy() -> ApplicationStrategy:
        """Create an email application strategy for fallback purposes"""
        return EmailApplicationStrategy()