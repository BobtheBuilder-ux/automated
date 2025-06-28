import { NextResponse } from 'next/server';

// This is a mock implementation - replace with actual API call to your backend
export async function GET() {
  try {
    // Mock data - in production, fetch this from your backend
    const mockEmailStats = {
      total_sent: 256,
      success_rate: 94.5,
      failed: 14,
      delivered: 242,
      opened: 189
    };

    // In production, you would fetch the data from your backend:
    // const response = await fetch('http://your-backend-url/api/email-stats');
    // const data = await response.json();
    
    return NextResponse.json({ 
      success: true, 
      data: mockEmailStats
    });
  } catch (error) {
    console.error('Error fetching email stats:', error);
    return NextResponse.json({ 
      success: false, 
      error: error.message || 'Failed to fetch email statistics' 
    }, { status: 500 });
  }
}