import { NextResponse } from 'next/server';

export async function POST(request) {
  try {
    const body = await request.json();
    const { email, subject, message, type = 'notification', html } = body;

    if (!email) {
      return NextResponse.json({ 
        success: false, 
        error: 'Email address is required' 
      }, { status: 400 });
    }

    // Send real email via Mailtrap
    console.log(`Sending ${type} email to: ${email}`);
    
    try {
      // Generate HTML content if not provided
      const htmlContent = html || `
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
          <div style="background-color: #4285F4; color: white; padding: 10px; text-align: center; border-radius: 5px 5px 0 0;">
            <h1>${subject}</h1>
          </div>
          <div style="padding: 20px;">
            ${message.split('\n').map(line => `<p>${line}</p>`).join('')}
          </div>
          <div style="background-color: #f5f5f5; padding: 10px; text-align: center; font-size: 12px; border-radius: 0 0 5px 5px;">
            &copy; 2025 Automated Job Application System
          </div>
        </div>
      `;

      // Use Mailtrap's Email Sending API
      const response = await fetch('https://send.api.mailtrap.io/api/send', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer 2a514f0914c08c12dbaa167e7c463e01'
        },
        body: JSON.stringify({
          from: { 
            email: "notifications@bobbieberry.com", 
            name: "Automated Job Application System" 
          },
          to: [{ email }],
          subject: subject,
          text: message,
          html: htmlContent,
          category: type || "Notification"
        })
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Mailtrap API error:', errorText);
        throw new Error(`Mailtrap API responded with status ${response.status}: ${errorText}`);
      }
      
      const data = await response.json();
      console.log(`Email (${type}) sent successfully to ${email}:`, data);
      
      return NextResponse.json({ 
        success: true, 
        message: `${type || 'Notification'} sent to ${email}`,
        data
      });
    } catch (mailError) {
      console.error('Error sending email:', mailError);
      throw new Error(`Failed to send email: ${mailError.message}`);
    }
  } catch (error) {
    console.error('Error sending notification:', error);
    return NextResponse.json({ 
      success: false, 
      error: error.message || 'Failed to send notification' 
    }, { status: 500 });
  }
}