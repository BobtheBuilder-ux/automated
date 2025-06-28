'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/app/components/ui/card';
import { Badge } from '@/app/components/ui/badge';
import { Alert, AlertDescription } from '@/app/components/ui/alert';
import { Button } from '@/app/components/ui/button';

export default function SystemStatusDashboard() {
  const [systemHealth, setSystemHealth] = useState(null);
  const [emailStats, setEmailStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchSystemHealth = async () => {
    try {
      setRefreshing(true);
      const response = await fetch('/api/system-health');
      const data = await response.json();
      
      if (data.status === 'success') {
        setSystemHealth(data.health);
      } else {
        throw new Error('Failed to fetch system health');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setRefreshing(false);
    }
  };

  const fetchEmailStats = async () => {
    try {
      const response = await fetch('/api/email-stats');
      const data = await response.json();
      
      if (data.status === 'success') {
        setEmailStats(data.stats);
      }
    } catch (err) {
      console.error('Failed to fetch email stats:', err);
    }
  };

  const clearEmailLogs = async () => {
    try {
      setRefreshing(true);
      const response = await fetch('/api/clear-email-logs', {
        method: 'POST',
      });
      const data = await response.json();
      
      if (data.status === 'success') {
        await fetchSystemHealth();
        await fetchEmailStats();
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      await Promise.all([fetchSystemHealth(), fetchEmailStats()]);
      setLoading(false);
    };

    loadData();

    // Auto-refresh every 30 seconds
    const interval = setInterval(() => {
      if (!refreshing) {
        fetchSystemHealth();
        fetchEmailStats();
      }
    }, 30000);

    return () => clearInterval(interval);
  }, [refreshing]);

  const getServiceStatus = (isHealthy) => {
    return isHealthy ? (
      <Badge variant="default" className="bg-green-100 text-black">
        Healthy
      </Badge>
    ) : (
      <Badge variant="destructive">
        Down
      </Badge>
    );
  };

  const getSuccessRateColor = (rate) => {
    if (rate >= 90) return 'text-gray-600';
    if (rate >= 70) return 'text-black-600';
    return 'text-red-600';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-64">
        <div className="text-lg">Loading system status...</div>
      </div>
    );
  }

  if (error) {
    return (
      <Alert className="max-w-4xl mx-auto">
        <AlertDescription>
          Error loading system status: {error}
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6 max-w-6xl mx-auto p-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">System Status Dashboard</h1>
        <div className="flex gap-2">
          <Button 
            onClick={() => { fetchSystemHealth(); fetchEmailStats(); }}
            disabled={refreshing}
            variant="outline"
          >
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </Button>
          <Button 
            onClick={clearEmailLogs}
            disabled={refreshing}
            variant="outline"
          >
            Clear Old Logs
          </Button>
        </div>
      </div>

      {/* System Services Status */}
      <Card>
        <CardHeader>
          <CardTitle>System Services</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {systemHealth?.services && Object.entries(systemHealth.services).map(([service, status]) => (
              <div key={service} className="flex items-center justify-between p-3 border rounded-lg">
                <span className="font-medium capitalize">{service.replace('_', ' ')}</span>
                {getServiceStatus(status)}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Email Statistics */}
      {emailStats && (
        <Card>
          <CardHeader>
            <CardTitle>Email Performance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-4 border rounded-lg">
                <div className="text-2xl font-bold text-blue-600">{emailStats.total_emails}</div>
                <div className="text-sm text-gray-600">Total Emails</div>
              </div>
              <div className="text-center p-4 border rounded-lg">
                <div className="text-2xl font-bold text-green-600">{emailStats.sent_emails}</div>
                <div className="text-sm text-gray-600">Sent Successfully</div>
              </div>
              <div className="text-center p-4 border rounded-lg">
                <div className="text-2xl font-bold text-red-600">{emailStats.failed_emails}</div>
                <div className="text-sm text-gray-600">Failed</div>
              </div>
              <div className="text-center p-4 border rounded-lg">
                <div className={`text-2xl font-bold ${getSuccessRateColor(emailStats.success_rate)}`}>
                  {emailStats.success_rate.toFixed(1)}%
                </div>
                <div className="text-sm text-gray-600">Success Rate</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* System Metrics */}
      {systemHealth?.system_metrics && (
        <Card>
          <CardHeader>
            <CardTitle>System Metrics</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 border rounded-lg">
                <div className="font-medium">Uptime</div>
                <div className="text-sm text-gray-600">{systemHealth.system_metrics.uptime}</div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="font-medium">Last Auto Apply</div>
                <div className="text-sm text-gray-600">{systemHealth.system_metrics.last_auto_apply}</div>
              </div>
              <div className="p-4 border rounded-lg">
                <div className="font-medium">Pending Jobs</div>
                <div className="text-sm text-gray-600">{systemHealth.system_metrics.pending_jobs}</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent Email Logs */}
      {systemHealth?.recent_logs && (
        <Card>
          <CardHeader>
            <CardTitle>Recent Email Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {systemHealth.recent_logs.map((log, index) => (
                <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex-1">
                    <div className="font-medium">{log.recipient || 'Unknown recipient'}</div>
                    <div className="text-sm text-gray-600">{log.subject || 'No subject'}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={log.status === 'sent' ? 'default' : 'destructive'}>
                      {log.status}
                    </Badge>
                    <div className="text-sm text-gray-500">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              ))}
              {systemHealth.recent_logs.length === 0 && (
                <div className="text-center text-gray-500 py-4">
                  No recent email activity
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Last Updated */}
      <div className="text-center text-sm text-gray-500">
        Last updated: {systemHealth?.timestamp ? new Date(systemHealth.timestamp).toLocaleString() : 'Unknown'}
      </div>
    </div>
  );
}