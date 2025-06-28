'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Alert, AlertDescription } from '../components/ui/alert';

const MonitoringDashboard = () => {
  const [emailLogs, setEmailLogs] = useState([]);
  const [emailStats, setEmailStats] = useState({});
  const [applicationStats, setApplicationStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [testEmail, setTestEmail] = useState('');
  const [sendingTest, setSendingTest] = useState(false);
  const [sendSuccess, setSendSuccess] = useState(false);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      
      // Fetch email logs
      const emailLogsResponse = await fetch('/api/email-logs?limit=50');
      const emailLogsData = await emailLogsResponse.json();
      
      // Fetch email stats
      const emailStatsResponse = await fetch('/api/email-stats');
      const emailStatsData = await emailStatsResponse.json();
      
      // Fetch application stats
      const appStatsResponse = await fetch('/api/application-stats');
      const appStatsData = await appStatsResponse.json();
      
      if (emailLogsData.success) {
        setEmailLogs(emailLogsData.data || []);
      }
      
      if (emailStatsData.success) {
        setEmailStats(emailStatsData.data || {});
      }
      
      if (appStatsData.success) {
        setApplicationStats(appStatsData.data || {});
      }
      
      setError('');
    } catch (err) {
      setError('Failed to fetch dashboard data: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const sendTestNotification = async () => {
    if (!testEmail) {
      setError('Please enter an email address');
      return;
    }

    try {
      setSendingTest(true);
      setSendSuccess(false);
      setError('');
      
      const response = await fetch('/api/send-test-notification', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: testEmail }),
      });

      const data = await response.json();
      
      if (data.success) {
        setSendSuccess(true);
        setError('');
        setTestEmail('');
        // Refresh email logs to show the new test email
        fetchDashboardData();
      } else {
        setError('Failed to send test notification: ' + (data.error || 'Unknown error'));
      }
    } catch (err) {
      setError('Failed to send test notification: ' + err.message);
    } finally {
      setSendingTest(false);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const getStatusBadgeColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'sent': return 'bg-green-500';
      case 'delivered': return 'bg-blue-500';
      case 'failed': return 'bg-red-500';
      case 'pending': return 'bg-yellow-500';
      default: return 'bg-gray-500';
    }
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[1, 2, 3].map(i => (
              <div key={i} className="h-32 bg-gray-200 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 text-black">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">System Monitoring Dashboard</h1>
        <Button onClick={fetchDashboardData} className="bg-blue-600 hover:bg-blue-700">
          Refresh Data
        </Button>
      </div>

      {error && (
        <Alert className="border-red-200 bg-red-50">
          <AlertDescription className="text-red-800">{error}</AlertDescription>
        </Alert>
      )}

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader className="text-black">
            <CardTitle className="text-lg">Email Activity</CardTitle>
            <CardDescription>Email sending statistics</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-black">
              <div className="flex justify-between">
                <span>Total Sent:</span>
                <span className="font-semibold">{emailStats.total_sent || 0}</span>
              </div>
              <div className="flex justify-between">
                <span>Success Rate:</span>
                <span className="font-semibold text-green-600">
                  {emailStats.success_rate ? `${emailStats.success_rate}%` : 'N/A'}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Failed:</span>
                <span className="font-semibold text-red-600">{emailStats.failed || 0}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Job Applications</CardTitle>
            <CardDescription>Application statistics</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span>Total Applied:</span>
                <span className="font-semibold">{applicationStats.total_applications || 0}</span>
              </div>
              <div className="flex justify-between">
                <span>This Week:</span>
                <span className="font-semibold">{applicationStats.weekly_applications || 0}</span>
              </div>
              <div className="flex justify-between">
                <span>Success Rate:</span>
                <span className="font-semibold text-blue-600">
                  {applicationStats.success_rate ? `${applicationStats.success_rate}%` : 'N/A'}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">System Health</CardTitle>
            <CardDescription>Current system status</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span>Auto Apply:</span>
                <Badge className="bg-green-500">Active</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span>Email Service:</span>
                <Badge className="bg-green-500">Online</Badge>
              </div>
              <div className="flex justify-between items-center">
                <span>Scheduler:</span>
                <Badge className="bg-green-500">Running</Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Test Notification Section */}
      <Card>
        <CardHeader>
          <CardTitle>Test Email Notification</CardTitle>
          <CardDescription>Send a test notification to verify email functionality</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <Input
              type="email"
              placeholder="Enter email address"
              value={testEmail}
              onChange={(e) => setTestEmail(e.target.value)}
              className="flex-1"
            />
            <Button 
              onClick={sendTestNotification}
              disabled={sendingTest || !testEmail}
              className="bg-green-600 hover:bg-green-700"
            >
              {sendingTest ? 'Sending...' : 'Send Test'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Email Logs */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Email Activity</CardTitle>
          <CardDescription>Latest email notifications and communications</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {emailLogs.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No email logs available</p>
            ) : (
              <div className="space-y-2">
                {emailLogs
                  // Filter out test emails
                  .filter(log => {
                    // Skip emails with test domains, test subjects or test types
                    const isTestEmail = 
                      (log.email_type === 'test' || 
                       log.type === 'test' || 
                       (log.recipient_email && log.recipient_email.includes('test')) ||
                       (log.subject && log.subject.toLowerCase().includes('test')));
                    
                    return !isTestEmail;
                  })
                  .map((log, index) => (
                    <div key={index} className="border rounded-lg p-4 hover:bg-gray-50">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <Badge className={getStatusBadgeColor(log.status)}>
                              {log.status || 'Unknown'}
                            </Badge>
                            <span className="font-medium">{log.email_type || 'General'}</span>
                          </div>
                          <p className="text-sm text-gray-600 mb-1">
                            To: {log.recipient_email || 'N/A'}
                          </p>
                          <p className="text-sm font-medium">{log.subject || 'No Subject'}</p>
                          {log.error && (
                            <p className="text-sm text-red-600 mt-1">Error: {log.error}</p>
                          )}
                        </div>
                        <div className="text-right text-sm text-gray-500">
                          {formatDate(log.timestamp || log.created_at)}
                        </div>
                      </div>
                    </div>
                  ))}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default MonitoringDashboard;