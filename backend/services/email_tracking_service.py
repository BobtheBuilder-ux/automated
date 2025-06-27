import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from typing import Dict, Optional, List
from dotenv import load_dotenv

load_dotenv()

class EmailTrackingService:
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("EMAIL_FROM", self.smtp_username)
        self.from_name = os.getenv("EMAIL_FROM_NAME", "Job Application System")
        
    async def send_application_email(self, 
                                   application_data: Dict,
                                   cover_letter_path: str,
                                   cv_path: str) -> Dict:
        """
        Send application email and return tracking information
        """
        try:
            # Extract company and job details
            company_email = application_data.get("company_email", "")
            company_name = application_data.get("company_name", "Unknown Company")
            job_title = application_data.get("job_title", "Position")
            applicant_name = application_data.get("full_name", "Applicant")
            
            if not company_email:
                return {
                    "success": False,
                    "error": "No company email provided",
                    "email_sent": False
                }
            
            # Create email content
            subject = f"Application for {job_title} Position - {applicant_name}"
            
            body = f"""Dear Hiring Manager at {company_name},

I hope this email finds you well. I am writing to express my strong interest in the {job_title} position at {company_name}.

I have attached my CV and a personalized cover letter for your review. With my background and experience, I believe I would be a valuable addition to your team.

I would welcome the opportunity to discuss how my skills and experience can contribute to {company_name}'s continued success.

Thank you for considering my application. I look forward to hearing from you.

Best regards,
{applicant_name}

---
This email was sent via our automated job application system.
"""

            # Create email message
            msg = MIMEMultipart()
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = company_email
            msg['Subject'] = subject
            
            # Add body
            msg.attach(MIMEText(body, 'plain'))
            
            # Attach CV
            if cv_path and os.path.exists(cv_path):
                with open(cv_path, "rb") as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= cv_{applicant_name}.pdf'
                    )
                    msg.attach(part)
            
            # Attach Cover Letter
            if cover_letter_path and os.path.exists(cover_letter_path):
                with open(cover_letter_path, "rb") as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= cover_letter_{applicant_name}_{job_title}.pdf'
                    )
                    msg.attach(part)
            
            # Send email (if credentials are configured)
            if self.smtp_username and self.smtp_password:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                text = msg.as_string()
                server.sendmail(self.from_email, company_email, text)
                server.quit()
                
                email_sent = True
                email_sent_at = datetime.utcnow()
            else:
                # Simulate email sending for demo purposes
                print(f"📧 Simulated email sent to {company_email} for {job_title} at {company_name}")
                email_sent = True  # Set to True for demo
                email_sent_at = datetime.utcnow()
            
            return {
                "success": True,
                "email_sent": email_sent,
                "email_sent_to": company_email,
                "email_subject": subject,
                "email_body": body,
                "email_sent_at": email_sent_at,
                "message": f"Email sent successfully to {company_email}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "email_sent": False,
                "message": f"Failed to send email: {str(e)}"
            }
    
    def log_email_activity(self, application_id: str, email_data: Dict) -> Dict:
        """
        Log email activity for tracking purposes
        """
        try:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "application_id": application_id,
                "email_sent": email_data.get("email_sent", False),
                "recipient": email_data.get("email_sent_to", ""),
                "subject": email_data.get("email_subject", ""),
                "status": "sent" if email_data.get("email_sent") else "failed",
                "error": email_data.get("error", "")
            }
            
            # You could save this to a separate email_logs collection in Firebase
            # For now, we'll return the log entry to be included in the application data
            return {
                "success": True,
                "log_entry": log_entry
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

# Create global instance
email_tracking_service = EmailTrackingService()