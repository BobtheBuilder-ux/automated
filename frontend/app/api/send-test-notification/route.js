import { NextResponse } from 'next/server';

export async function POST(request) {
  try {
    const body = await request.json();
    const { email } = body;

    if (!email) {
      return NextResponse.json({ 
        success: false, 
        error: 'Email address is required' 
      }, { status: 400 });
    }

    // Send real email via Mailtrap sending API
    console.log(`Sending real email to: ${email}`);
    
    try {
      // Use Mailtrap's Email Sending API with the live API key
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
          subject: "Test Notification from Automated Job System",
          text: "This is a test email from your Automated Job Application System. If you received this email, it means your email notification system is working correctly.",
          html: `
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
              <div style="background-color: #4285F4; color: white; padding: 10px; text-align: center; border-radius: 5px 5px 0 0;">
                <h1>Test Notification</h1>
              </div>
              <div style="padding: 20px;">
                <p>This is a test email from your Automated Job Application System.</p>
                <p>If you received this email, it means your email notification system is working correctly.</p>
                <p>Thank you for using our Automated Job Application System.</p>
              </div>
              <div style="background-color: #f5f5f5; padding: 10px; text-align: center; font-size: 12px; border-radius: 0 0 5px 5px;">
                &copy; 2025 Automated Job Application System
              </div>
            </div>
          `,
          category: "Production Email"
        })
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Mailtrap API error:', errorText);
        throw new Error(`Mailtrap API responded with status ${response.status}: ${errorText}`);
      }
      
      const data = await response.json();
      console.log('Email sent successfully to real recipient:', data);
      
      return NextResponse.json({ 
        success: true, 
        message: `Test notification sent to ${email}`,
        provider: "Mailtrap"
      });
    } catch (mailError) {
      console.error('Error sending email:', mailError);
      throw new Error(`Failed to send email: ${mailError.message}`);
    }
  } catch (error) {
    console.error('Error sending test notification:', error);
    return NextResponse.json({ 
      success: false, 
      error: error.message || 'Failed to send test notification' 
    }, { status: 500 });
  }
}