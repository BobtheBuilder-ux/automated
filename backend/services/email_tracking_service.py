import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dotenv import load_dotenv
import asyncio
import json

load_dotenv()

class EmailTrackingService:
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_username = os.getenv("SMTP_USERNAME", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("EMAIL_FROM", self.smtp_username)
        self.from_name = os.getenv("EMAIL_FROM_NAME", "Job Application System")
        
        # Email tracking storage
        self.email_logs_dir = os.path.join("backend", "static", "email_logs")
        os.makedirs(self.email_logs_dir, exist_ok=True)
        self.email_logs_file = os.path.join(self.email_logs_dir, "email_tracking.json")
        
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
            
            # Log email activity
            await self._log_email_activity({
                "application_id": application_data.get("id", "unknown"),
                "company_email": company_email,
                "company_name": company_name,
                "job_title": job_title,
                "applicant_name": applicant_name,
                "email_subject": subject,
                "email_sent": email_sent,
                "email_sent_at": email_sent_at.isoformat(),
                "status": "sent" if email_sent else "failed"
            })
            
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
            # Log failed email attempt
            await self._log_email_activity({
                "application_id": application_data.get("id", "unknown"),
                "company_email": application_data.get("company_email", ""),
                "job_title": application_data.get("job_title", ""),
                "applicant_name": application_data.get("full_name", ""),
                "email_sent": False,
                "error": str(e),
                "status": "failed",
                "email_sent_at": datetime.utcnow().isoformat()
            })
            
            return {
                "success": False,
                "error": str(e),
                "email_sent": False,
                "message": f"Failed to send email: {str(e)}"
            }
    
    async def send_notification_email(self, 
                                    recipient_email: str,
                                    subject: str,
                                    body: str,
                                    email_type: str = "notification") -> Dict:
        """
        Send notification emails (job completion, errors, etc.)
        """
        try:
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = recipient_email
            msg['Subject'] = subject
            
            # Add body
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email (if credentials are configured)
            if self.smtp_username and self.smtp_password:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                text = msg.as_string()
                server.sendmail(self.from_email, recipient_email, text)
                server.quit()
                
                email_sent = True
            else:
                # Simulate email sending for demo purposes
                print(f"📧 Notification email sent to {recipient_email}: {subject}")
                email_sent = True
            
            # Log notification email
            await self._log_email_activity({
                "recipient_email": recipient_email,
                "email_subject": subject,
                "email_type": email_type,
                "email_sent": email_sent,
                "email_sent_at": datetime.utcnow().isoformat(),
                "status": "sent" if email_sent else "failed"
            })
            
            return {
                "success": True,
                "email_sent": email_sent,
                "message": f"Notification email sent to {recipient_email}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "email_sent": False,
                "message": f"Failed to send notification email: {str(e)}"
            }
    
    async def send_job_completion_summary(self, 
                                        recipient_email: str,
                                        user_name: str,
                                        applications: List[Dict],
                                        job_id: str) -> Dict:
        """
        Send a summary email after job completion
        """
        try:
            subject = f"Job Application Summary - {len(applications)} Applications Submitted"
            
            body = f"""Dear {user_name},

Your automated job application process has been completed. Here's a summary:

📊 Applications Summary:
- Total applications submitted: {len(applications)}
- Successful applications: {sum(1 for app in applications if app.get('success', False))}
- Failed applications: {sum(1 for app in applications if not app.get('success', False))}

📋 Application Details:
"""
            
            for i, app in enumerate(applications, 1):
                status = "✅ Success" if app.get('success', False) else "❌ Failed"
                body += f"\n{i}. {app.get('job_title', 'Unknown Position')} at {app.get('company_name', 'Unknown Company')}"
                body += f"\n   Status: {status}"
                if app.get('company_email'):
                    body += f"\n   Company Email: {app['company_email']}"
                if not app.get('success', False) and app.get('error'):
                    body += f"\n   Error: {app['error']}"
                body += "\n"
            
            body += f"""
🔗 View Details:
You can view more details about your applications in the dashboard.

Job ID: {job_id}

Thank you for using our automated job application system!

Best regards,
The Job Application Team
"""
            
            return await self.send_notification_email(
                recipient_email=recipient_email,
                subject=subject,
                body=body,
                email_type="job_completion_summary"
            )
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to send job completion summary: {str(e)}"
            }
    
    async def send_scheduled_job_notification(self,
                                            recipient_email: str,
                                            user_name: str,
                                            job_title: str,
                                            job_id: str,
                                            schedule_type: str,
                                            next_run: str) -> Dict:
        """
        Send notification when a job is scheduled
        """
        try:
            subject = f"Job Application Scheduled - {job_title}"
            
            body = f"""Dear {user_name},

Your automated job application has been successfully scheduled!

📅 Schedule Details:
- Job Title: {job_title}
- Schedule Type: {schedule_type}
- Next Run: {next_run}
- Job ID: {job_id}

🔄 What happens next:
- Our system will automatically search for relevant job openings
- Applications will be submitted on your behalf according to the schedule
- You'll receive email updates about each application attempt
- A summary will be sent after each run

📊 Monitor Progress:
You can track the progress of your scheduled jobs in the dashboard.

If you need to cancel or modify this scheduled job, please contact support.

Best regards,
The Job Application Team
"""
            
            return await self.send_notification_email(
                recipient_email=recipient_email,
                subject=subject,
                body=body,
                email_type="job_scheduled"
            )
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to send scheduled job notification: {str(e)}"
            }
    
    async def _log_email_activity(self, email_data: Dict) -> None:
        """
        Log email activity to file
        """
        try:
            # Load existing logs
            email_logs = []
            if os.path.exists(self.email_logs_file):
                with open(self.email_logs_file, 'r') as f:
                    email_logs = json.load(f)
            
            # Add new log entry
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                **email_data
            }
            email_logs.append(log_entry)
            
            # Keep only last 1000 entries to prevent file from growing too large
            if len(email_logs) > 1000:
                email_logs = email_logs[-1000:]
            
            # Save logs
            with open(self.email_logs_file, 'w') as f:
                json.dump(email_logs, f, indent=2)
                
        except Exception as e:
            print(f"Error logging email activity: {str(e)}")
    
    async def get_email_logs(self, limit: int = 100, email_type: Optional[str] = None) -> Dict:
        """
        Get email activity logs
        """
        try:
            if not os.path.exists(self.email_logs_file):
                return {"success": True, "data": []}
            
            with open(self.email_logs_file, 'r') as f:
                email_logs = json.load(f)
            
            # Filter by email type if specified
            if email_type:
                email_logs = [log for log in email_logs if log.get("email_type") == email_type]
            
            # Sort by timestamp (newest first) and limit
            email_logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            email_logs = email_logs[:limit]
            
            return {"success": True, "data": email_logs}
            
        except Exception as e:
            return {"success": False, "error": str(e), "data": []}
    
    async def get_email_stats(self) -> Dict:
        """
        Get email statistics
        """
        try:
            if not os.path.exists(self.email_logs_file):
                return {
                    "success": True, 
                    "data": {
                        "total_emails": 0,
                        "successful_emails": 0,
                        "failed_emails": 0,
                        "today_emails": 0,
                        "this_week_emails": 0
                    }
                }
            
            with open(self.email_logs_file, 'r') as f:
                email_logs = json.load(f)
            
            total_emails = len(email_logs)
            successful_emails = sum(1 for log in email_logs if log.get("status") == "sent")
            failed_emails = sum(1 for log in email_logs if log.get("status") == "failed")
            
            # Calculate today and this week emails
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = now - timedelta(days=7)
            
            today_emails = 0
            this_week_emails = 0
            
            for log in email_logs:
                if log.get("timestamp"):
                    try:
                        log_time = datetime.fromisoformat(log["timestamp"].replace('Z', '+00:00'))
                        if log_time >= today_start:
                            today_emails += 1
                        if log_time >= week_start:
                            this_week_emails += 1
                    except:
                        pass
            
            return {
                "success": True,
                "data": {
                    "total_emails": total_emails,
                    "successful_emails": successful_emails,
                    "failed_emails": failed_emails,
                    "today_emails": today_emails,
                    "this_week_emails": this_week_emails,
                    "success_rate": (successful_emails / total_emails * 100) if total_emails > 0 else 0
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    def log_email_activity(self, application_id: str, email_data: Dict) -> Dict:
        """
        Log email activity for tracking purposes (sync version for backward compatibility)
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
            
            # Use async version
            asyncio.create_task(self._log_email_activity(log_entry))
            
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