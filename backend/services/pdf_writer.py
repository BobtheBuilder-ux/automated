import os
from xhtml2pdf import pisa
from datetime import datetime
from typing import Tuple, Optional, Dict, Any
import asyncio
import aiofiles  # Add this import for async file operations

# Import the firebase service
from .firebase_service import firebase_service


class PDFWriter:
    def __init__(self, output_dir: str = "backend/static/uploads"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
    
    def text_to_pdf(self, text: str, output_path: str) -> bool:
        """
        Convert text to PDF using xhtml2pdf.
        
        Args:
            text: Text content for the PDF
            output_path: Path where the PDF will be saved
            
        Returns:
            bool: Success status
        """
        # Create a simple HTML wrapper for the text
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; font-size: 12px; line-height: 1.5; }}
                h1 {{ font-size: 18px; margin-bottom: 15px; }}
                p {{ margin-bottom: 10px; }}
            </style>
        </head>
        <body>
            {text.replace('\n', '<br/>')}
        </body>
        </html>
        """
        
        try:
            with open(output_path, "wb") as out_file:
                # Convert HTML to PDF
                pisa_status = pisa.CreatePDF(html, dest=out_file)
            
            # Return True if success
            return pisa_status.err == 0 # type: ignore
            
        except Exception as e:
            print(f"Error creating PDF: {e}")
            return False
    
    async def create_cover_letter_pdf(
        self,
        cover_letter_text: str,
        output_path: str,
        applicant_name: str,
        job_title: str,
        company_name: str
    ) -> bool:
        """
        Create a cover letter PDF and save it to the specified path.
        
        Args:
            cover_letter_text: Text content of the cover letter
            output_path: Path where the PDF will be saved
            applicant_name: Name of the applicant
            job_title: Job title being applied for
            company_name: Company name
            
        Returns:
            bool: Success status
        """
        try:
            # Format cover letter for PDF
            formatted_content = self._format_cover_letter_html(
                cover_letter_text, applicant_name, job_title, company_name
            )
            
            # Create PDF file - Use synchronous method since xhtml2pdf doesn't support async
            success = self.text_to_pdf(formatted_content, output_path)
            
            if success:
                # Extract just the filename from the path for display purposes
                filename = os.path.basename(output_path)
                
                # Store in Firebase database
                relative_path = f"static/uploads/{filename}"
                
                # Prepare data for storage
                cover_letter_data = {
                    "user_name": applicant_name,
                    "job_title": job_title,
                    "company_name": company_name,
                    "content": cover_letter_text,
                    "file_path": output_path,
                    "relative_path": relative_path,
                    "filename": filename,
                    "timestamp": datetime.utcnow(),
                    "download_url": f"/download/{relative_path}"
                }
                
                # Save to Firebase
                await firebase_service.store_cover_letter(cover_letter_data)
                
            return success
            
        except Exception as e:
            print(f"Error creating cover letter PDF: {e}")
            return False
    
    def generate_cover_letter_pdf(self, 
                                content: str, 
                                user_name: str,
                                job_title: str,
                                company_name: str = "") -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Generate a PDF cover letter from text content.
        
        Args:
            content: The cover letter content
            user_name: The user's name
            job_title: The job title
            company_name: The company name
            
        Returns:
            Tuple[bool, Optional[str], Optional[Dict]]: (success, file path if successful, cover letter data)
        """
        try:
            # Format the cover letter content
            formatted_content = self._format_cover_letter(content, user_name, job_title)
            
            # Generate output path
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            sanitized_name = user_name.replace(" ", "_")
            sanitized_job = job_title.replace(" ", "_")
            
            filename = f"cover_letter_{sanitized_name}_{sanitized_job}_{timestamp}.pdf"
            output_path = os.path.join(self.output_dir, filename)
            
            # Create cover letter data for database
            cover_letter_data = {
                "content": content,
                "formatted_content": formatted_content,
                "user_name": user_name,
                "job_title": job_title,
                "company_name": company_name,
                "timestamp": timestamp,
                "filename": filename,
                "file_path": output_path,
                "relative_path": f"static/uploads/{filename}",
                "download_url": f"/download/static/uploads/{filename}"
            }
            
            # Convert to PDF
            success = self.text_to_pdf(formatted_content, output_path)
            
            # Ensure the file exists and is readable
            if not os.path.exists(output_path):
                print(f"Warning: PDF file was not created at {output_path}")
                success = False
            
            # Save to Firebase database asynchronously
            if success:
                print(f"✅ Cover letter PDF created successfully at {output_path}")
                # Start the asyncio task to save to Firebase
                asyncio.create_task(firebase_service.store_cover_letter(cover_letter_data))
                return True, output_path, cover_letter_data
            return False, None, None
            
        except Exception as e:
            print(f"Error generating cover letter PDF: {e}")
            return False, None, None
    
    def _format_cover_letter(self, content: str, user_name: str, job_title: str) -> str:
        """
        Format the cover letter with proper structure.
        
        Args:
            content: Raw cover letter content
            user_name: The user's name
            job_title: The job title
            
        Returns:
            str: Formatted cover letter
        """
        today = datetime.now().strftime("%B %d, %Y")
        
        # Enhance formatting for better PDF appearance
        formatted_letter = f"""
        <h1>Cover Letter - {job_title}</h1>
        <p style="color: #666;">{today}</p>
        <hr style="margin: 20px 0;">
        <p>Dear Hiring Manager,</p>
        
        {content}
        
        <p style="margin-top: 20px;">Sincerely,</p>
        <p><strong>{user_name}</strong></p>
        <hr style="margin: 20px 0;">
        <p style="color: #999; font-size: 10px;">Generated by Automated Job Application System</p>
        """
        
        return formatted_letter
        
    def _format_cover_letter_html(self, content: str, user_name: str, job_title: str, company_name: str) -> str:
        """
        Format the cover letter with proper HTML structure for PDF generation.
        
        Args:
            content: Raw cover letter content
            user_name: The user's name
            job_title: The job title
            company_name: The company name
            
        Returns:
            str: Formatted HTML for cover letter
        """
        today = datetime.now().strftime("%B %d, %Y")
        
        # Create a well-formatted HTML document for the cover letter - Fix CSS syntax issues
        html = f"""
        <html>
        <head>
            <style>
                @page {{ size: letter; margin: 1in; }}
                body {{ 
                    font-family: Arial, sans-serif; 
                    font-size: 12pt; 
                    line-height: 1.5;
                    color: #333;
                }}
                .header {{ margin-bottom: 30px; }}
                .date {{ color: #666; margin-bottom: 20px; }}
                .company {{ margin-bottom: 20px; }}
                .greeting {{ margin-bottom: 20px; }}
                .content {{ margin-bottom: 30px; }}
                .signature {{ margin-top: 30px; }}
                .footer {{ 
                    margin-top: 50px;
                    font-size: 9pt;
                    color: #999;
                    text-align: center;
                }}
                h1 {{ font-size: 18pt; color: #2c3e50; }}
                hr {{ border: none; border-top: 1px solid #ddd; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Cover Letter: {job_title}</h1>
            </div>
            
            <div class="date">{today}</div>
            
            <div class="company">
                <p><strong>{company_name}</strong></p>
            </div>
            
            <div class="greeting">
                <p>Dear Hiring Manager,</p>
            </div>
            
            <div class="content">
                {content.replace('\n', '<br/>')}
            </div>
            
            <div class="signature">
                <p>Sincerely,</p>
                <p><strong>{user_name}</strong></p>
            </div>
            
            <hr>
            
            <div class="footer">
                <p>Generated by Automated Job Application System</p>
            </div>
        </body>
        </html>
        """
        
        return html