import os
from typing import Dict, Optional
import openai
from dotenv import load_dotenv

load_dotenv()

class GPTGenerator:
    def __init__(self):
        # Set OpenAI API key from environment variables
        openai.api_key = os.getenv("OPENAI_API_KEY")
        if not openai.api_key:
            print("Warning: OpenAI API key not found in environment variables")
    
    def _create_prompt(self, cv_text: str, job_title: str, job_description: str, name: str) -> str:
        """
        Create a prompt for the GPT model to generate a cover letter.
        
        Args:
            cv_text: Extracted text from the user's CV
            job_title: The job title
            job_description: The job description
            name: The applicant's name
            
        Returns:
            str: The formatted prompt
        """
        return f"""
You are a professional cover letter writer helping {name} create a compelling cover letter for a {job_title} position.

Here is the job description:
{job_description}

Here is {name}'s CV/resume:
{cv_text}

Based on the above information, write a professional cover letter that:
1. Highlights the most relevant skills and experiences from the CV that match the job requirements
2. Shows enthusiasm for the specific role and company
3. Demonstrates understanding of the job requirements
4. Has a professional tone and is no longer than 400 words
5. Does not include the date, address, or other formatting elements - focus only on the body content
6. Concludes with a call to action requesting an interview

Write the cover letter in first person from {name}'s perspective.
"""
    
    def _get_dummy_job_description(self, job_title: str) -> str:
        """
        Generate a dummy job description based on the job title.
        In a real application, this would be replaced by a web scraper
        that gets actual job descriptions.
        
        Args:
            job_title: The job title
            
        Returns:
            str: A generated job description
        """
        # Basic templates for different job categories
        tech_description = f"""
Job Title: {job_title}

About the Role:
We're looking for an experienced {job_title} to join our dynamic team. The ideal candidate will have strong technical skills, problem-solving abilities, and experience working in collaborative environments.

Key Responsibilities:
- Design, develop, and maintain software applications
- Collaborate with cross-functional teams to define and implement new features
- Write clean, efficient, and maintainable code
- Troubleshoot and debug issues as they arise
- Participate in code reviews and ensure code quality
- Stay updated with emerging trends and technologies

Requirements:
- Bachelor's degree in Computer Science, Engineering, or related field
- 3+ years of experience in software development
- Proficiency in modern programming languages and frameworks
- Strong understanding of software design principles
- Experience with version control systems and agile methodologies
- Excellent problem-solving and communication skills
"""

        business_description = f"""
Job Title: {job_title}

About the Role:
We're seeking a talented {job_title} to help drive our business forward. The successful candidate will be strategic, data-driven, and possess strong interpersonal skills.

Key Responsibilities:
- Develop and implement business strategies to meet company goals
- Analyze market trends and identify new business opportunities
- Build and maintain relationships with key stakeholders
- Prepare reports and presentations for senior management
- Lead and mentor team members
- Drive continuous improvement initiatives

Requirements:
- Bachelor's degree in Business, Finance, or related field
- 5+ years of relevant industry experience
- Strong analytical and problem-solving skills
- Excellent communication and leadership abilities
- Proficiency in data analysis and reporting tools
- Strategic thinking and commercial awareness
"""

        # Select description based on job title keywords
        tech_keywords = ["developer", "engineer", "programmer", "analyst", "architect", "technical", "data scientist"]
        business_keywords = ["manager", "consultant", "analyst", "director", "coordinator", "specialist", "officer", "assistant"]
        
        job_title_lower = job_title.lower()
        
        if any(keyword in job_title_lower for keyword in tech_keywords):
            return tech_description
        elif any(keyword in job_title_lower for keyword in business_keywords):
            return business_description
        else:
            # Generic description for other job types
            return f"""
Job Title: {job_title}

About the Role:
We are looking for a dedicated {job_title} to join our growing team. The ideal candidate is passionate, detail-oriented, and committed to excellence.

Key Responsibilities:
- Execute core functions related to the {job_title} position
- Collaborate with team members to achieve organizational goals
- Ensure high-quality standards in all deliverables
- Communicate effectively with internal and external stakeholders
- Contribute to process improvements and innovation

Requirements:
- Relevant degree or certification in the field
- Previous experience in a similar role
- Strong organizational and time management skills
- Excellent communication abilities
- Problem-solving mindset
- Adaptability and willingness to learn
"""
    
    async def generate_cover_letter(self, 
                                 cv_text: str, 
                                 job_title: str, 
                                 name: str,
                                 job_description: Optional[str] = None) -> Dict:
        """
        Generate a cover letter using GPT model.
        
        Args:
            cv_text: Text extracted from the CV
            job_title: The job title
            name: The applicant's name
            job_description: Optional job description (will generate dummy if not provided)
            
        Returns:
            dict: Generation result with status and content
        """
        try:
            # If no job description provided, generate a dummy one
            if not job_description:
                job_description = self._get_dummy_job_description(job_title)
            
            # Create the prompt
            prompt = self._create_prompt(cv_text, job_title, job_description, name)
            
            # Call OpenAI API
            response = await openai.ChatCompletion.acreate(
                model="gpt-4",  # You can change this to a different model as needed
                messages=[
                    {"role": "system", "content": "You are a professional cover letter writer."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.7
            )
            
            # Extract the generated content
            cover_letter = response.choices[0].message.content.strip()
            
            return {
                "success": True,
                "cover_letter": cover_letter,
                "job_description": job_description,
                "token_usage": response.usage
            }
            
        except Exception as e:
            print(f"Error generating cover letter: {e}")
            return {
                "success": False,
                "error": str(e),
                "cover_letter": None
            }