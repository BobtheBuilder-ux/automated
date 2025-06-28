from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, EmailStr
from services.email_service import EmailService
from typing import Optional

# Create API router
router = APIRouter(tags=["email"])
email_service = EmailService()

# Pydantic models for request validation
class TestEmailRequest(BaseModel):
    email: EmailStr
    subject: Optional[str] = "Test Email from Automated Job System"
    message: Optional[str] = "This is a test email from your Automated Job Application System."

@router.post("/api/send-test-email")
async def send_test_email(request: TestEmailRequest):
    """Send a test email notification."""
    try:
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
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Test Notification</h1>
                </div>
                <div class="content">
                    <p>This is a test email from your Automated Job Application System.</p>
                    <p>If you received this email, it means your email notification system is working correctly.</p>
                </div>
                <div class="footer">
                    &copy; 2025 Automated Job Application System
                </div>
            </div>
        </body>
        </html>
        """
        
        # Send email
        success, message_result = await email_service.send_email(
            recipient_email=request.email,
            subject=request.subject, # type: ignore
            text_content=request.message, # type: ignore
            html_content=html_content
        )
        
        if success:
            return {"success": True, "message": f"Test email sent to {request.email}"}
        else:
            raise HTTPException(status_code=500, detail=message_result)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))