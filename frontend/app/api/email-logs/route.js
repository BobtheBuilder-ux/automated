import { NextResponse } from 'next/server';

// This is a mock implementation - replace with actual API call to your backend
export async function GET(request) {
  try {
    // Extract the limit parameter from the URL
    const { searchParams } = new URL(request.url);
    const limit = searchParams.get('limit') || 50;
    
    // Mock data - in production, fetch this from your backend
    const mockEmailLogs = Array.from({ length: 10 }, (_, i) => ({
      id: i + 1,
      recipient_email: `test${i + 1}@example.com`,
      subject: `Test Email ${i + 1}`,
      status: ['sent', 'delivered', 'failed', 'pending'][Math.floor(Math.random() * 4)],
      email_type: ['notification', 'application', 'confirmation', 'test'][Math.floor(Math.random() * 4)],
      timestamp: new Date(Date.now() - Math.random() * 10000000000).toISOString(),
      error: Math.random() > 0.8 ? 'Connection timeout' : null
    }));

    // In production, you would fetch the data from your backend:
    // const response = await fetch('http://your-backend-url/api/email-logs?limit=' + limit);
    // const data = await response.json();
    
    return NextResponse.json({ 
      success: true, 
      data: mockEmailLogs
    });
  } catch (error) {
    console.error('Error fetching email logs:', error);
    return NextResponse.json({ 
      success: false, 
      error: error.message || 'Failed to fetch email logs' 
    }, { status: 500 });
  }
}