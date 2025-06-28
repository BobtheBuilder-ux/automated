import os
import json
import hashlib
import asyncio
from typing import Dict, Optional, List, Tuple
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
            
        # Initialize cache for cover letters
        self.cache_dir = os.path.join("backend", "static", "cover_letter_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Semaphore to limit concurrent API calls
        self.api_semaphore = asyncio.Semaphore(5)  # Allow up to 5 concurrent API calls
        
        # Cache settings
        self.cache_enabled = True
        self.cache_expiry = 86400 * 7  # Cache cover letters for 7 days
    
    def _create_prompt(self, cv_text: str, job_title: str, company_name: str, job_description: str, applicant_name: str) -> str:
        """
        Create an optimized prompt for faster generation.
        """
        # Condense CV text to reduce token usage - focus on most relevant sections
        condensed_cv = self._extract_key_cv_sections(cv_text)
        
        return f"""
You are a professional cover letter writer helping {applicant_name} create a compelling cover letter for a {job_title} position at {company_name}.

Job description: {job_description}

Candidate CV highlights: {condensed_cv}

Write a concise professional cover letter (200-300 words) that:
1. Matches key skills from CV to job requirements
2. Shows enthusiasm for the role at {company_name}
3. Includes specific achievements relevant to the position
4. Has a professional tone
5. Concludes with a call to action

Format as a complete cover letter body from {applicant_name}'s perspective.
"""
    
    def _extract_key_cv_sections(self, cv_text: str) -> str:
        """
        Extract only the most relevant parts of the CV to reduce token count
        """
        if not cv_text or len(cv_text) < 1000:
            return cv_text
            
        # Split CV into sections
        sections = cv_text.split('\n\n')
        
        # Get top 40% of content to focus on most important parts typically at the top
        important_sections = sections[:max(3, len(sections) // 2)]
        
        # Join the selected sections
        condensed = '\n\n'.join(important_sections)
        
        # If still too long, truncate
        if len(condensed) > 1500:
            condensed = condensed[:1500] + "..."
            
        return condensed
    
    def _get_cache_key(self, job_title: str, company_name: str, cv_hash: str) -> str:
        """Generate a cache key for a cover letter."""
        key_string = f"{job_title}_{company_name}_{cv_hash}"
        return hashlib.md5(key_string.encode()).hexdigest() + ".json"
    
    def _get_cv_hash(self, cv_text: str) -> str:
        """Generate a hash of the CV text."""
        return hashlib.md5(cv_text.encode()).hexdigest()[:10]
    
    async def _get_cached_cover_letter(self, job_title: str, company_name: str, cv_text: str) -> Tuple[bool, Optional[Dict]]:
        """
        Get cached cover letter if available.
        
        Returns:
            Tuple of (cache_hit, cover_letter_dict)
        """
        if not self.cache_enabled:
            return False, None
            
        try:
            cv_hash = self._get_cv_hash(cv_text)
            cache_key = self._get_cache_key(job_title, company_name, cv_hash)
            cache_path = os.path.join(self.cache_dir, cache_key)
            
            # Check if cache exists
            if os.path.exists(cache_path):
                # Check if cache is still valid
                cache_time = os.path.getmtime(cache_path)
                current_time = os.time.time() if hasattr(os, 'time') else __import__('time').time()
                
                if current_time - cache_time < self.cache_expiry:
                    async with open(cache_path, 'r') as f:
                        result = json.loads(await f.read())
                    print(f"Using cached cover letter for {job_title} at {company_name}")
                    return True, result
        except Exception as e:
            print(f"Error reading cache: {e}")
            
        return False, None
    
    async def _save_to_cache(self, job_title: str, company_name: str, cv_text: str, result: Dict) -> None:
        """Save cover letter to cache."""
        if not self.cache_enabled or not result or not result.get('success', False):
            return
            
        try:
            cv_hash = self._get_cv_hash(cv_text)
            cache_key = self._get_cache_key(job_title, company_name, cv_hash)
            cache_path = os.path.join(self.cache_dir, cache_key)
            
            # Save to file
            async with open(cache_path, 'w') as f:
                await f.write(json.dumps(result))
                
            print(f"Cached cover letter for {job_title} at {company_name}")
        except Exception as e:
            print(f"Error saving to cache: {e}")
    
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
                               job_title: str,
                               company_name: str,
                               job_description: Optional[str] = None,
                               cv_text: Optional[str] = None,
                               applicant_name: str = "the applicant") -> Dict:
        """
        Generate a cover letter using Gemini model with caching and optimizations.
        """
        try:
            # Initialize response
            if cv_text is None:
                cv_text = f"Experienced professional with background in {job_title} roles."
                
            # If no job description provided, generate a dummy one
            if not job_description:
                job_description = self._get_dummy_job_description(job_title)
                
            # Check cache first
            cache_hit, cached_result = await self._get_cached_cover_letter(job_title, company_name, cv_text)
            if cache_hit:
                return cached_result
                
            # Check if API key is set
            if not self.api_key or self.api_key == "your_valid_gemini_api_key_here":
                print("⚠️  Gemini API key not configured. Using fallback cover letter generation.")
                result = await self._generate_fallback_cover_letter(cv_text, job_title, company_name, applicant_name, job_description)
                await self._save_to_cache(job_title, company_name, cv_text, result)
                return result
                
            # Use semaphore to limit concurrent API calls
            async with self.api_semaphore:
                # Create the prompt
                prompt = self._create_prompt(cv_text, job_title, company_name, job_description, applicant_name)
                
                # Configure the Gemini model - use the fastest available model
                model = genai.GenerativeModel('gemini-2.0-flash')
                
                # Generate content with optimized settings
                generation_config = {
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 800,  # Limit output size for faster generation
                }
                
                response = await model.generate_content_async(
                    prompt,
                    generation_config=generation_config,
                )
                
                # Extract the generated content
                cover_letter = response.text.strip()
                
                result = {
                    "success": True,
                    "cover_letter": cover_letter,
                    "job_description": job_description
                }
                
                # Cache the result
                await self._save_to_cache(job_title, company_name, cv_text, result)
                
                return result
                
        except Exception as e:
            print(f"Error generating cover letter with Gemini: {e}")
            print("🔄 Falling back to template-based cover letter generation...")
            result = await self._generate_fallback_cover_letter(cv_text, job_title, company_name, applicant_name, job_description)
            await self._save_to_cache(job_title, company_name, cv_text, result)
            return result
    
    async def _generate_fallback_cover_letter(self, 
                                        cv_text: str, 
                                        job_title: str, 
                                        company_name: str,
                                        applicant_name: str,
                                        job_description: Optional[str] = None) -> Dict:
        """
        Generate a fallback cover letter when Gemini API is not available.
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

I am writing to express my strong interest in the {job_title} position at {company_name}. With {experience_years} experience in the field and a demonstrated passion for delivering innovative solutions, I am confident that I would be a valuable addition to your dynamic team.

My professional background encompasses extensive expertise in {skills_text}, which I believe directly aligns with the core requirements for this role. Throughout my career, I have consistently demonstrated the ability to tackle complex challenges, deliver high-quality results, and collaborate effectively with cross-functional teams to achieve ambitious project goals and drive organizational success.

Key highlights from my professional experience include:

• Strong technical foundation with hands-on experience in modern development practices and industry best practices
• Proven track record of working effectively in fast-paced, collaborative environments while maintaining attention to detail
• Unwavering commitment to continuous learning and staying current with emerging industry trends and technologies
• Extensive experience in analytical thinking, problem-solving, and delivering innovative solutions that meet critical business objectives
• Strong communication skills and ability to work seamlessly with diverse teams and stakeholders

What particularly excites me about this opportunity is the chance to contribute to {company_name}'s continued growth and success. I am eager to bring my unique blend of technical expertise, creative problem-solving abilities, and collaborative mindset to help drive your team's initiatives forward.

I would welcome the opportunity to discuss in detail how my skills, experience, and enthusiasm can contribute to your organization's objectives. Thank you for considering my application, and I look forward to hearing from you soon.

Best regards,
{applicant_name}"""

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
                "note": f"Generated using enhanced fallback template - {len(cover_letter.split())} words"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Both Gemini API and fallback generation failed: {str(e)}",
                "cover_letter": None
            }
            
    async def generate_multiple_cover_letters(self, jobs: List[Dict], cv_text: str, applicant_name: str) -> List[Tuple[Dict, Dict]]:
        """
        Generate multiple cover letters in parallel for a batch of jobs.
        
        Args:
            jobs: List of job dictionaries with title, company, and description
            cv_text: The applicant's CV text
            applicant_name: The applicant's name
            
        Returns:
            List of tuples: (job, cover_letter_result)
        """
        tasks = []
        
        for job in jobs:
            job_title = job.get("title", "")
            company_name = job.get("company", "")
            job_description = job.get("description", "")
            
            task = asyncio.create_task(self.generate_cover_letter(
                job_title=job_title,
                company_name=company_name,
                job_description=job_description,
                cv_text=cv_text,
                applicant_name=applicant_name
            ))
            tasks.append((job, task))
        
        results = []
        for job, task in tasks:
            cover_letter_result = await task
            results.append((job, cover_letter_result))
            
        return results