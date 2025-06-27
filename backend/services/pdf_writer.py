import os
from xhtml2pdf import pisa
from datetime import datetime
from typing import Tuple, Optional


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
            return pisa_status.err == 0
            
        except Exception as e:
            print(f"Error creating PDF: {e}")
            return False
    
    def generate_cover_letter_pdf(self, 
                                content: str, 
                                user_name: str,
                                job_title: str) -> Tuple[bool, Optional[str]]:
        """
        Generate a PDF cover letter from text content.
        
        Args:
            content: The cover letter content
            user_name: The user's name
            job_title: The job title
            
        Returns:
            Tuple[bool, Optional[str]]: (success, file path if successful)
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
            
            # Convert to PDF
            success = self.text_to_pdf(formatted_content, output_path)
            
            if success:
                return True, output_path
            return False, None
            
        except Exception as e:
            print(f"Error generating cover letter PDF: {e}")
            return False, None
    
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
        
        # Simple formatting - in real app, we'd have more sophisticated templates
        formatted_letter = f"""
        <h1>Cover Letter - {job_title}</h1>
        <p>{today}</p>
        <p>Dear Hiring Manager,</p>
        
        {content}
        
        <p>Sincerely,</p>
        <p>{user_name}</p>
        """
        
        return formatted_letter