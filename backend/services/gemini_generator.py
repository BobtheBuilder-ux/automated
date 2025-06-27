import os
from typing import Dict, Optional
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class GeminiGenerator:
    def __init__(self):
        # Set Google Gemini API key from environment variables
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            print("Warning: Gemini API key not found in environment variables")
        else:
            genai.configure(api_key=self.api_key)
    
    def _create_prompt(self, cv_text: str, job_title: str, job_description: str, name: str) -> str:
        """
        Create a prompt for the Gemini model to generate a cover letter.
        
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
1. Is MINIMUM 200 words (this is mandatory - the cover letter must exceed 200 words)
2. Highlights the most relevant skills and experiences from the CV that match the job requirements
3. Shows enthusiasm for the specific role and company
4. Demonstrates deep understanding of the job requirements
5. Uses specific examples from the CV that align with job requirements
6. Has a professional yet engaging tone
7. Includes industry-specific terminology relevant to the role
8. Shows knowledge of current trends in the field
9. Addresses potential gaps or explains career progression
10. Concludes with a strong call to action requesting an interview
11. Does not include date, address, or formatting - focus only on the body content

IMPORTANT REQUIREMENTS:
- The cover letter MUST be at least 200 words long
- Use specific examples and achievements from the CV
- Tailor the content specifically to the job description provided
- Show genuine interest in the company and role
- Include measurable achievements when possible

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
        Generate a cover letter using Gemini model.
        
        Args:
            cv_text: Text extracted from the CV
            job_title: The job title
            name: The applicant's name
            job_description: Optional job description (will generate dummy if not provided)
            
        Returns:
            dict: Generation result with status and content
        """
        try:
            # Check if API key is set
            if not self.api_key or self.api_key == "your_valid_gemini_api_key_here":
                print("⚠️  Gemini API key not configured. Using fallback cover letter generation.")
                return self._generate_fallback_cover_letter(cv_text, job_title, name, job_description)
                
            # If no job description provided, generate a dummy one
            if not job_description:
                job_description = self._get_dummy_job_description(job_title)
            
            # Create the prompt
            prompt = self._create_prompt(cv_text, job_title, job_description, name)
            
            # Configure the Gemini model - updated to use gemini-2.0-flash
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            # Generate content
            response = await model.generate_content_async(prompt)
            
            # Extract the generated content
            cover_letter = response.text.strip()
            
            return {
                "success": True,
                "cover_letter": cover_letter,
                "job_description": job_description
            }
            
        except Exception as e:
            print(f"Error generating cover letter with Gemini: {e}")
            print("🔄 Falling back to template-based cover letter generation...")
            return self._generate_fallback_cover_letter(cv_text, job_title, name, job_description)
    
    def _generate_fallback_cover_letter(self, cv_text: str, job_title: str, name: str, job_description: Optional[str] = None) -> Dict:
        """
        Generate a fallback cover letter when Gemini API is not available.
        Ensures minimum 200 words.
        """
        try:
            # Extract some basic info from CV
            cv_lines = cv_text.split('\n')
            skills = []
            experience_years = "several years of"
            
            # Simple keyword extraction for skills
            skill_keywords = ['python', 'javascript', 'react', 'node', 'sql', 'aws', 'docker', 'git', 'java', 'typescript', 'html', 'css', 'mongodb', 'postgresql', 'kubernetes', 'jenkins', 'angular', 'vue', 'django', 'flask']
            for line in cv_lines:
                line_lower = line.lower()
                for skill in skill_keywords:
                    if skill in line_lower and skill not in [s.lower() for s in skills]:
                        skills.append(skill.title())
            
            skills_text = ", ".join(skills[:8]) if skills else "various technical and analytical skills"
            
            # Generate enhanced template cover letter (200+ words)
            cover_letter = f"""Dear Hiring Manager,

I am writing to express my strong interest in the {job_title} position at your esteemed organization. With {experience_years} experience in the field and a demonstrated passion for delivering innovative solutions, I am confident that I would be a valuable addition to your dynamic team.

My professional background encompasses extensive expertise in {skills_text}, which I believe directly aligns with the core requirements for this role. Throughout my career, I have consistently demonstrated the ability to tackle complex challenges, deliver high-quality results, and collaborate effectively with cross-functional teams to achieve ambitious project goals and drive organizational success.

Key highlights from my professional experience include:

• Strong technical foundation with hands-on experience in modern development practices and industry best practices
• Proven track record of working effectively in fast-paced, collaborative environments while maintaining attention to detail
• Unwavering commitment to continuous learning and staying current with emerging industry trends and technologies
• Extensive experience in analytical thinking, problem-solving, and delivering innovative solutions that meet critical business objectives
• Strong communication skills and ability to work seamlessly with diverse teams and stakeholders

What particularly excites me about this opportunity is the chance to contribute to your organization's continued growth and success. I am eager to bring my unique blend of technical expertise, creative problem-solving abilities, and collaborative mindset to help drive your team's initiatives forward.

I would welcome the opportunity to discuss in detail how my skills, experience, and enthusiasm can contribute to your organization's objectives. Thank you for considering my application, and I look forward to hearing from you soon.

Best regards,
{name}"""

            # Verify word count (minimum 200 words)
            word_count = len(cover_letter.split())
            if word_count < 200:
                # Add additional content if needed
                additional_content = f"""

Additionally, I am particularly drawn to this role because it offers the opportunity to work with cutting-edge technologies and contribute to meaningful projects that make a real impact. My experience has taught me the importance of adaptability, continuous improvement, and maintaining a growth mindset in today's rapidly evolving technological landscape.

I am confident that my combination of technical skills, professional experience, and enthusiasm for innovation would enable me to make meaningful contributions to your team from day one."""
                
                cover_letter += additional_content

            return {
                "success": True,
                "cover_letter": cover_letter,
                "job_description": job_description or self._get_dummy_job_description(job_title),
                "note": f"Generated using enhanced fallback template (Gemini API not available) - {len(cover_letter.split())} words"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Both Gemini API and fallback generation failed: {str(e)}",
                "cover_letter": None
            }