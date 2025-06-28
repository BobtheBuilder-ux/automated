import os
import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import List, Optional, Dict, Tuple
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='email_service.log'
)
logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending emails for the automated job application system."""
    
    def __init__(self):
        # Load email settings from environment variables
        self.smtp_server = os.getenv("EMAIL_HOST", os.getenv("SMTP_HOST", "smtp.hostinger.com"))
        self.smtp_port = int(os.getenv("EMAIL_PORT", os.getenv("SMTP_PORT", "587")))
        self.sender_email = os.getenv("EMAIL_HOST_USER", os.getenv("SMTP_USERNAME", "clients@bobbieberry.com"))
        self.sender_password = os.getenv("EMAIL_HOST_PASSWORD", os.getenv("SMTP_PASSWORD", ""))
        
        if not self.sender_email or not self.sender_password:
            logger.warning("Email credentials not set. Email service will not work properly.")
        else:
            logger.info(f"Email service initialized successfully with email: {self.sender_email}")
    
    async def send_email(
        self,
        recipient_email: str,
        subject: str,
        text_content: str,
        html_content: Optional[str] = None,
        attachments: Optional[List[str]] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> Tuple[bool, str]:
        """
        Send an email to the specified recipient.
        
        Args:
            recipient_email: Email address of the recipient
            subject: Email subject
            text_content: Plain text content of the email
            html_content: Optional HTML content of the email
            attachments: Optional list of file paths to attach
            cc: Optional list of CC recipients
            bcc: Optional list of BCC recipients
            
        Returns:
            Tuple of (success boolean, message)
        """
        if not self.sender_email or not self.sender_password:
            return False, "Email service not configured. Please set SMTP credentials."
        
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = self.sender_email
            message["To"] = recipient_email
            
            # Add CC if provided
            if cc:
                message["Cc"] = ", ".join(cc)
                
            # Set text and HTML content
            message.attach(MIMEText(text_content, "plain"))
            if html_content:
                message.attach(MIMEText(html_content, "html"))
            
            # Add attachments if provided
            if attachments:
                for attachment_path in attachments:
                    if not os.path.exists(attachment_path):
                        logger.warning(f"Attachment not found: {attachment_path}")
                        continue
                        
                    with open(attachment_path, "rb") as file:
                        attachment = MIMEApplication(file.read())
                        attachment_name = Path(attachment_path).name
                        attachment.add_header(
                            "Content-Disposition", 
                            f"attachment; filename={attachment_name}"
                        )
                        message.attach(attachment)
            
            # Create list of all recipients
            all_recipients = [recipient_email]
            if cc:
                all_recipients.extend(cc)
            if bcc:
                all_recipients.extend(bcc)
            
            # Create a secure SSL context
            context = ssl.create_default_context()
            
            # Connect to server and send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.ehlo()  # Can be omitted
                server.starttls(context=context)
                server.ehlo()  # Can be omitted
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, all_recipients, message.as_string())
            
            logger.info(f"Email sent successfully to {recipient_email}")
            return True, "Email sent successfully"
            
        except Exception as e:
            logger.error(f"Error sending email to {recipient_email}: {str(e)}")
            return False, f"Error sending email: {str(e)}"
    
    async def send_application_confirmation(
        self,
        recipient_email: str,
        name: str,
        job_title: str,
        company: str,
        cover_letter_path: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Send application confirmation email.
        
        Args:
            recipient_email: Email address of the recipient
            name: Applicant's name
            job_title: Job title applied for
            company: Company applied to
            cover_letter_path: Optional path to cover letter PDF
            
        Returns:
            Tuple of (success boolean, message)
        """
        subject = f"Job Application Submitted: {job_title} at {company}"
        
        text_content = f"""
Hello {name},

Your job application for the {job_title} position at {company} has been submitted successfully.

A custom cover letter has been generated and submitted along with your CV.

Thank you for using our Automated Job Application System.

Best regards,
Automated Job Application System
        """
        
        html_content = f"""
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }}
        .header {{
            background-color: #4285F4;
            color: white;
            padding: 10px;
            text-align: center;
            border-radius: 5px 5px 0 0;
        }}
        .content {{
            padding: 20px;
        }}
        .footer {{
            background-color: #f5f5f5;
            padding: 10px;
            text-align: center;
            font-size: 12px;
            border-radius: 0 0 5px 5px;
        }}
        .button {{
            display: inline-block;
            background-color: #4285F4;
            color: white;
            padding: 10px 20px;
            text-decoration: none;
            border-radius: 5px;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Application Confirmation</h1>
        </div>
        <div class="content">
            <p>Hello {name},</p>
            <p>Your job application for the <strong>{job_title}</strong> position at <strong>{company}</strong> has been submitted successfully.</p>
            <p>A custom cover letter has been generated and submitted along with your CV.</p>
            <p>Thank you for using our Automated Job Application System.</p>
        </div>
        <div class="footer">
            &copy; 2025 Automated Job Application System
        </div>
    </div>
</body>
</html>
        """
        
        attachments = []
        if cover_letter_path and os.path.exists(cover_letter_path):
            attachments.append(cover_letter_path)
        
        return await self.send_email(
            recipient_email=recipient_email,
            subject=subject,
            text_content=text_content,
            html_content=html_content,
            attachments=attachments
        )
    
    async def send_scheduled_job_notification(
        self,
        recipient_email: str,
        name: str,
        job_title: str,
        job_id: str,
        schedule_type: str,
        next_run: str
    ) -> Tuple[bool, str]:
        """
        Send notification about a scheduled job.
        
        Args:
            recipient_email: Email address of the recipient
            name: User's name
            job_title: Job title to search for
            job_id: ID of the scheduled job
            schedule_type: Type of schedule (once or recurring)
            next_run: Time of next scheduled run
            
        Returns:
            Tuple of (success boolean, message)
        """
        subject = f"Job Search Scheduled: {job_title}"
        
        schedule_text = "one-time" if schedule_type == "once" else "recurring"
        
        text_content = f"""
Hello {name},

Your automated job search for "{job_title}" positions has been scheduled successfully.

Job ID: {job_id}
Schedule Type: {schedule_text}
Next Run: {next_run}

You will receive email notifications when applications are submitted on your behalf.

Thank you for using our Automated Job Application System.

Best regards,
Automated Job Application System
        """
        
        html_content = f"""
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }}
        .header {{
            background-color: #4285F4;
            color: white;
            padding: 10px;
            text-align: center;
            border-radius: 5px 5px 0 0;
        }}
        .content {{
            padding: 20px;
        }}
        .footer {{
            background-color: #f5f5f5;
            padding: 10px;
            text-align: center;
            font-size: 12px;
            border-radius: 0 0 5px 5px;
        }}
        .job-details {{
            background-color: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Job Search Scheduled</h1>
        </div>
        <div class="content">
            <p>Hello {name},</p>
            <p>Your automated job search for <strong>"{job_title}"</strong> positions has been scheduled successfully.</p>
            
            <div class="job-details">
                <p><strong>Job ID:</strong> {job_id}</p>
                <p><strong>Schedule Type:</strong> {schedule_text}</p>
                <p><strong>Next Run:</strong> {next_run}</p>
            </div>
            
            <p>You will receive email notifications when applications are submitted on your behalf.</p>
            <p>Thank you for using our Automated Job Application System.</p>
        </div>
        <div class="footer">
            &copy; 2025 Automated Job Application System
        </div>
    </div>
</body>
</html>
        """
        
        return await self.send_email(
            recipient_email=recipient_email,
            subject=subject,
            text_content=text_content,
            html_content=html_content
        )
    
    async def send_application_summary(
        self,
        recipient_email: str,
        name: str,
        applications: List[Dict],
        job_title: str
    ) -> Tuple[bool, str]:
        """
        Send a summary of applications submitted.
        
        Args:
            recipient_email: Email address of the recipient
            name: User's name
            applications: List of job applications
            job_title: Job title that was searched for
            
        Returns:
            Tuple of (success boolean, message)
        """
        num_applications = len(applications)
        subject = f"Job Application Summary: {num_applications} Applications Submitted"
        
        # Create text content
        text_content = f"""
Hello {name},

Our automated system has submitted {num_applications} job applications for "{job_title}" positions on your behalf.

Applications:
"""
        
        for i, app in enumerate(applications, 1):
            text_content += f"""
{i}. {app.get('title')} at {app.get('company')}
   Source: {app.get('source')}
"""
        
        text_content += """
You can check the status of your applications by visiting our web application.

Thank you for using our Automated Job Application System.

Best regards,
Automated Job Application System
"""
        
        # Create HTML content
        html_content = f"""
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }}
        .header {{
            background-color: #4285F4;
            color: white;
            padding: 10px;
            text-align: center;
            border-radius: 5px 5px 0 0;
        }}
        .content {{
            padding: 20px;
        }}
        .footer {{
            background-color: #f5f5f5;
            padding: 10px;
            text-align: center;
            font-size: 12px;
            border-radius: 0 0 5px 5px;
        }}
        .application-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        .application-table th, .application-table td {{
            padding: 8px;
            border: 1px solid #ddd;
            text-align: left;
        }}
        .application-table th {{
            background-color: #f5f5f5;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Job Application Summary</h1>
        </div>
        <div class="content">
            <p>Hello {name},</p>
            <p>Our automated system has submitted <strong>{num_applications} job applications</strong> for "{job_title}" positions on your behalf.</p>
            
            <h3>Applications:</h3>
            <table class="application-table">
                <tr>
                    <th>#</th>
                    <th>Position</th>
                    <th>Company</th>
                    <th>Source</th>
                </tr>
"""

        for i, app in enumerate(applications, 1):
            html_content += f"""
                <tr>
                    <td>{i}</td>
                    <td>{app.get('title')}</td>
                    <td>{app.get('company')}</td>
                    <td>{app.get('source')}</td>
                </tr>
"""
            
        html_content += """
            </table>
            
            <p>You can check the status of your applications by visiting our web application.</p>
            <p>Thank you for using our Automated Job Application System.</p>
        </div>
        <div class="footer">
            &copy; 2025 Automated Job Application System
        </div>
    </div>
</body>
 wh</html>
"""
        
        return await self.send_email(
            recipient_email=recipient_email,
            subject=subject,
            text_content=text_content,
            html_content=html_content
        )
        
    async def send_status_update(
        self,
        recipient_email: str,
        name: str,
        application: Dict,
        status: str,
        status_message: str = None
    ) -> Tuple[bool, str]:
        """
        Send an email notification about a status update for a job application.
        
        Args:
            recipient_email: Email address of the recipient
            name: Applicant's name
            application: Dictionary containing application details
            status: New status of the application (e.g., "Received", "Under Review", "Rejected", "Interview")
            status_message: Optional additional message explaining the status update
            
        Returns:
            Tuple of (success boolean, message)
        """
        # Extract application details
        job_title = application.get('title', 'Unknown Position')
        company = application.get('company', 'Unknown Company')
        
        subject = f"Application Status Update: {job_title} at {company}"
        
        status_emoji = {
            "submitted": "📤",
            "received": "📥",
            "under_review": "🔍",
            "interview": "🗓️",
            "rejected": "❌",
            "accepted": "✅",
            "offer": "🎉",
            "waiting": "⏳"
        }.get(status.lower(), "📋")
        
        # Plain text email content
        text_content = f"""
Hello {name},

There has been an update to your application for {job_title} at {company}.

Status: {status} {status_emoji}
"""
        
        if status_message:
            text_content += f"""
Additional Information:
{status_message}
"""
            
        text_content += """
You can check all your application statuses on our platform.

Thank you for using our Automated Job Application System.

Best regards,
Automated Job Application System
"""
        
        # HTML content
        html_content = f"""
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }}
        .header {{
            background-color: #4285F4;
            color: white;
            padding: 10px;
            text-align: center;
            border-radius: 5px 5px 0 0;
        }}
        .content {{
            padding: 20px;
        }}
        .footer {{
            background-color: #f5f5f5;
            padding: 10px;
            text-align: center;
            font-size: 12px;
            border-radius: 0 0 5px 5px;
        }}
        .status-box {{
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
            background-color: #f8f9fa;
            border-left: 5px solid #4285F4;
        }}
        .status-title {{
            font-size: 18px;
            margin-bottom: 10px;
        }}
        .status-emoji {{
            font-size: 24px;
            margin-right: 10px;
        }}
        .additional-info {{
            background-color: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            margin-top: 15px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Application Status Update</h1>
        </div>
        <div class="content">
            <p>Hello {name},</p>
            <p>There has been an update to your application for <strong>{job_title}</strong> at <strong>{company}</strong>.</p>
            
            <div class="status-box">
                <div class="status-title">
                    <span class="status-emoji">{status_emoji}</span> Status: <strong>{status}</strong>
                </div>
"""
        
        if status_message:
            html_content += f"""
                <div class="additional-info">
                    <h4>Additional Information:</h4>
                    <p>{status_message}</p>
                </div>
"""
            
        html_content += """
            </div>
            
            <p>You can check all your application statuses on our platform.</p>
            <p>Thank you for using our Automated Job Application System.</p>
        </div>
        <div class="footer">
            &copy; 2025 Automated Job Application System
        </div>
    </div>
</body>
</html>
"""
        
        return await self.send_email(
            recipient_email=recipient_email,
            subject=subject,
            text_content=text_content,
            html_content=html_content
        )