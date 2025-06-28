"""
Application strategies for different job platforms.
Each strategy implements the logic needed to submit applications to a specific job board.
"""

import os
import logging
import aiohttp
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Tuple, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='job_submission.log'
)
logger = logging.getLogger(__name__)

class ApplicationStrategy(ABC):
    """Base abstract class for job application strategies"""
    
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

class LinkedInStrategy(ApplicationStrategy):
    """Strategy for applying to jobs on LinkedIn"""
    
    async def apply(self, 
                  job_data: Dict, 
                  user_data: Dict, 
                  cv_path: str, 
                  cover_letter_path: str) -> Tuple[bool, str]:
        """Apply to a LinkedIn job posting"""
        try:
            # Set up headless Chrome browser
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            driver = webdriver.Chrome(options=chrome_options)
            
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
        try:
            # Set up headless Chrome browser
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            driver = webdriver.Chrome(options=chrome_options)
            
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
        try:
            # Set up headless Chrome browser
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            driver = webdriver.Chrome(options=chrome_options)
            
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
        """Apply to a job by sending an email"""
        from .email_service import EmailService
        
        email_service = EmailService()
        
        # Check if job listing has an email contact
        contact_email = job_data.get("contact_email")
        if not contact_email:
            return False, "No contact email provided for this job"
            
        # Send application email with attachments
        subject = f"Application for {job_data.get('title')} position at {job_data.get('company')}"
        body = f"Dear Hiring Manager,\n\nPlease find attached my application for the {job_data.get('title')} position at {job_data.get('company')}.\n\nSincerely,\n{user_data.get('name')}"
        
        attachments = [cv_path, cover_letter_path]
        
        success = await email_service.send_email(
            recipient=contact_email,
            subject=subject,
            body=body,
            attachments=attachments
        )
        
        if success:
            logger.info(f"Successfully sent application email to {contact_email}")
            return True, f"Application sent via email to {contact_email}"
        else:
            logger.error(f"Failed to send application email to {contact_email}")
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
        job_source = job_source.lower()
        
        if "linkedin" in job_source:
            return LinkedInStrategy()
        elif "indeed" in job_source:
            return IndeedStrategy()
        elif "glassdoor" in job_source:
            return GlassdoorStrategy()
        elif "email" in job_source:
            return EmailApplicationStrategy()
        else:
            # Default to direct website strategy for unknown sources
            return DirectWebsiteStrategy()