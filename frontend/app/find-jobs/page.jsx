'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Search, 
  MapPin, 
  Building2, 
  Clock, 
  ExternalLink, 
  RefreshCw, 
  Play, 
  Square, 
  Filter,
  TrendingUp,
  Users,
  Calendar
} from 'lucide-react';
import { ApiService } from '@/lib/apiService';

export default function FindJobsPage() {
  const [discoveredJobs, setDiscoveredJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);
  const [filters, setFilters] = useState({
    jobTitle: '',
    source: '',
    jobType: '',
    location: '',
    limit: 50
  });
  const [discoveryRunning, setDiscoveryRunning] = useState(false);
  const [customSearching, setCustomSearching] = useState(false);
  const [availableJobTitles, setAvailableJobTitles] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Fetch discovered jobs
  const fetchDiscoveredJobs = async () => {
    try {
      setLoading(true);
      const result = await ApiService.getDiscoveredJobs(filters);

      if (result.success) {
        setDiscoveredJobs(result.data || []);
        setError(null);
      } else {
        setError(result.error || 'Failed to fetch jobs');
      }
    } catch (err) {
      setError(`Error fetching jobs: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Fetch discovery statistics
  const fetchStats = async () => {
    try {
      const result = await ApiService.getDiscoveryStats();

      if (result.success) {
        setStats(result.data);
        setDiscoveryRunning(result.data.is_discovery_running);
      }
    } catch (err) {
      console.error('Error fetching stats:', err);
    }
  };

  // Start automated job discovery
  const startDiscovery = async () => {
    try {
      const result = await ApiService.startJobDiscovery(2);

      if (result.success) {
        setDiscoveryRunning(true);
        alert('Auto job discovery started!');
        fetchStats();
      } else {
        alert(`Error: ${result.error}`);
      }
    } catch (err) {
      alert(`Error starting discovery: ${err.message}`);
    }
  };

  // Stop automated job discovery
  const stopDiscovery = async () => {
    try {
      const result = await ApiService.stopJobDiscovery();

      if (result.success) {
        setDiscoveryRunning(false);
        alert('Auto job discovery stopped!');
        fetchStats();
      } else {
        alert(`Error: ${result.error}`);
      }
    } catch (err) {
      alert(`Error stopping discovery: ${err.message}`);
    }
  };

  // Trigger manual job discovery
  const triggerDiscovery = async () => {
    try {
      setLoading(true);
      const result = await ApiService.triggerJobDiscovery();

      if (result.success) {
        alert('Job discovery triggered! Check back in a few minutes.');
        setTimeout(() => {
          fetchDiscoveredJobs();
          fetchStats();
        }, 5000);
      } else {
        alert(`Error: ${result.error}`);
      }
    } catch (err) {
      alert(`Error triggering discovery: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Apply filters
  const applyFilters = () => {
    fetchDiscoveredJobs();
  };

  // Reset filters
  const resetFilters = () => {
    setFilters({
      jobTitle: '',
      source: '',
      jobType: '',
      location: '',
      limit: 50
    });
  };

  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return 'Invalid date';
    }
  };

  // Get time ago
  const getTimeAgo = (dateString) => {
    if (!dateString) return '';
    try {
      const now = new Date();
      const jobDate = new Date(dateString);
      const diffMs = now - jobDate;
      const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
      const diffDays = Math.floor(diffHours / 24);

      if (diffHours < 1) return 'Just posted';
      if (diffHours < 24) return `${diffHours}h ago`;
      if (diffDays < 7) return `${diffDays}d ago`;
      return formatDate(dateString);
    } catch {
      return '';
    }
  };

  // Auto-refresh jobs every 2 minutes to show newly discovered jobs
  useEffect(() => {
    if (!autoRefresh) return;
    
    const interval = setInterval(() => {
      fetchDiscoveredJobs();
      fetchStats();
    }, 120000); // 2 minutes
    
    return () => clearInterval(interval);
  }, [autoRefresh, filters]);

  // Fetch available tech job titles for autocomplete
  const fetchJobTitles = async () => {
    try {
      const result = await ApiService.getTechJobTitles();
      if (result.success) {
        setAvailableJobTitles(result.data || []);
      }
    } catch (err) {
      console.error('Error fetching job titles:', err);
    }
  };

  // Custom job search
  const searchCustomJob = async () => {
    if (!filters.jobTitle.trim()) {
      setError('Please enter a job title to search for');
      return;
    }

    try {
      setCustomSearching(true);
      setError(null);

      const locations = filters.location ? [filters.location] : 
        ["remote", "San Francisco, CA", "New York, NY", "Seattle, WA", "Austin, TX"];
      const jobTypes = filters.jobType ? [filters.jobType] : 
        ["full-time", "contract", "remote"];

      const result = await ApiService.searchCustomJob({
        job_title: filters.jobTitle,
        locations: locations,
        job_types: jobTypes
      });

      if (result.success) {
        // Refresh the discovered jobs list to include new results
        setTimeout(() => {
          fetchDiscoveredJobs();
          fetchStats();
        }, 3000); // Wait 3 seconds for backend to process and store results
        
        setError(null);
        alert(`Custom search initiated for "${filters.jobTitle}"! Results will appear shortly.`);
      } else {
        setError(result.error || 'Failed to search for jobs');
      }
    } catch (err) {
      setError(`Error searching for jobs: ${err.message}`);
    } finally {
      setCustomSearching(false);
    }
  };

  // Filter job title suggestions
  const getFilteredSuggestions = () => {
    if (!filters.jobTitle || filters.jobTitle.length < 2) return [];
    return availableJobTitles.filter(title =>
      title.toLowerCase().includes(filters.jobTitle.toLowerCase())
    ).slice(0, 8);
  };

  // Handle job title input change with suggestions
  const handleJobTitleChange = (value) => {
    setFilters(prev => ({...prev, jobTitle: value}));
    setShowSuggestions(value.length >= 2);
  };

  // Select suggestion
  const selectSuggestion = (title) => {
    setFilters(prev => ({...prev, jobTitle: title}));
    setShowSuggestions(false);
  };

  useEffect(() => {
    fetchDiscoveredJobs();
    fetchStats();
    fetchJobTitles();
  }, []);

  useEffect(() => {
    fetchDiscoveredJobs();
  }, [filters]);

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Find Jobs</h1>
          <p className="text-gray-600 mt-2">
            Automatically discovered fresh job opportunities from multiple job boards
          </p>
        </div>
        
        <div className="flex gap-2">
          <Button 
            onClick={triggerDiscovery} 
            variant="outline"
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh Jobs
          </Button>
          
          {discoveryRunning ? (
            <Button onClick={stopDiscovery} variant="destructive">
              <Square className="h-4 w-4 mr-2" />
              Stop Auto Discovery
            </Button>
          ) : (
            <Button onClick={startDiscovery}>
              <Play className="h-4 w-4 mr-2" />
              Start Auto Discovery
            </Button>
          )}
        </div>
      </div>

      {/* Statistics Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Jobs</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_jobs}</div>
              <p className="text-xs text-muted-foreground">Discovered so far</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Last 24h</CardTitle>
              <Calendar className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.jobs_last_24h}</div>
              <p className="text-xs text-muted-foreground">Fresh opportunities</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Job Sources</CardTitle>
              <Building2 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{Object.keys(stats.sources || {}).length}</div>
              <p className="text-xs text-muted-foreground">Job boards monitored</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Auto Discovery</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {discoveryRunning ? 'ON' : 'OFF'}
              </div>
              <p className="text-xs text-muted-foreground">
                {discoveryRunning ? 'Running every 2h' : 'Stopped'}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
            {/* Job Title Filter */}
            <div className="flex-1">
              <label className="text-sm font-medium text-gray-700 mb-1 block">Job Title</label>
              <Input
                placeholder="e.g., Frontend Developer"
                value={filters.jobTitle}
                onChange={(e) => handleJobTitleChange(e.target.value)}
                className="text-black placeholder:text-gray-400"
              />
              
              {/* Job Title Suggestions */}
              {showSuggestions && (
                <div className="mt-1 rounded-md border bg-white shadow-md max-h-60 overflow-auto">
                  {getFilteredSuggestions().length === 0 && (
                    <div className="px-4 py-2 text-sm text-gray-500">
                      No suggestions found
                    </div>
                  )}
                  
                  {getFilteredSuggestions().map((title) => (
                    <div
                      key={title}
                      className="cursor-pointer select-none px-4 py-2 text-sm text-black hover:bg-gray-100"
                      onClick={() => selectSuggestion(title)}
                    >
                      {title}
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            {/* Job Type Filter */}
            <div>
              <label className="text-sm font-medium text-gray-700 mb-1 block">Job Type</label>
              <Select 
                value={filters.jobType} 
                onValueChange={(value) => setFilters(prev => ({...prev, jobType: value}))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All Types" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All Types</SelectItem>
                  <SelectItem value="full-time">Full-time</SelectItem>
                  <SelectItem value="part-time">Part-time</SelectItem>
                  <SelectItem value="contract">Contract</SelectItem>
                  <SelectItem value="intern">Internship</SelectItem>
                  <SelectItem value="remote">Remote</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            {/* Location Filter */}
            <div>
              <label className="text-sm font-medium text-gray-700 mb-1 block">Location</label>
              <Select 
                value={filters.location} 
                onValueChange={(value) => setFilters(prev => ({...prev, location: value}))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All Locations" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All Locations</SelectItem>
                  <SelectItem value="remote">Remote</SelectItem>
                  <SelectItem value="New York, NY">New York, NY</SelectItem>
                  <SelectItem value="San Francisco, CA">San Francisco, CA</SelectItem>
                  <SelectItem value="Los Angeles, CA">Los Angeles, CA</SelectItem>
                  <SelectItem value="Chicago, IL">Chicago, IL</SelectItem>
                  <SelectItem value="Austin, TX">Austin, TX</SelectItem>
                  <SelectItem value="Seattle, WA">Seattle, WA</SelectItem>
                  <SelectItem value="Boston, MA">Boston, MA</SelectItem>
                  <SelectItem value="Denver, CO">Denver, CO</SelectItem>
                  <SelectItem value="Miami, FL">Miami, FL</SelectItem>
                  <SelectItem value="Atlanta, GA">Atlanta, GA</SelectItem>
                  <SelectItem value="Phoenix, AZ">Phoenix, AZ</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            {/* Source Filter */}
            <div>
              <label className="text-sm font-medium text-gray-700 mb-1 block">Source</label>
              <Select 
                value={filters.source} 
                onValueChange={(value) => setFilters(prev => ({...prev, source: value}))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="All Sources" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">All Sources</SelectItem>
                  <SelectItem value="linkedin">LinkedIn</SelectItem>
                  <SelectItem value="indeed">Indeed</SelectItem>
                  <SelectItem value="google jobs">Google Jobs</SelectItem>
                  <SelectItem value="glassdoor">Glassdoor</SelectItem>
                  <SelectItem value="ziprecruiter">ZipRecruiter</SelectItem>
                  <SelectItem value="monster">Monster</SelectItem>
                  <SelectItem value="dice">Dice</SelectItem>
                  <SelectItem value="angellist">AngelList</SelectItem>
                  <SelectItem value="simplyhired">SimplyHired</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            {/* Results Limit */}
            <div>
              <label className="text-sm font-medium text-gray-700 mb-1 block">Results</label>
              <Select 
                value={filters.limit.toString()} 
                onValueChange={(value) => setFilters(prev => ({...prev, limit: parseInt(value)}))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="25">25 jobs</SelectItem>
                  <SelectItem value="50">50 jobs</SelectItem>
                  <SelectItem value="100">100 jobs</SelectItem>
                  <SelectItem value="200">200 jobs</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          
          {/* Filter Action Buttons */}
          <div className="flex gap-2 mt-4 pt-4 border-t">
            <Button onClick={applyFilters} size="sm">
              <Search className="h-4 w-4 mr-2" />
              Apply Filters
            </Button>
            <Button 
              onClick={searchCustomJob} 
              size="sm" 
              variant="default"
              disabled={customSearching || !filters.jobTitle.trim()}
            >
              {customSearching ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Searching...
                </>
              ) : (
                <>
                  <Search className="h-4 w-4 mr-2" />
                  Search Custom Job
                </>
              )}
            </Button>
            <Button onClick={resetFilters} variant="outline" size="sm">
              Reset All
            </Button>
            
            {/* Auto-refresh toggle */}
            <div className="flex items-center gap-2 ml-auto">
              <label className="text-sm text-gray-600">Auto-refresh:</label>
              <Button
                size="sm"
                variant={autoRefresh ? "default" : "outline"}
                onClick={() => setAutoRefresh(!autoRefresh)}
              >
                {autoRefresh ? "ON" : "OFF"}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>
            {error}
          </AlertDescription>
        </Alert>
      )}

      {/* Jobs List */}
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="text-xl font-semibold">
            {loading ? 'Loading...' : `${discoveredJobs.length} Jobs Found`}
          </h2>
          
          {discoveredJobs.length > 0 && (
            <Badge variant="secondary">
              Last updated: {getTimeAgo(discoveredJobs[0]?.discovered_at)}
            </Badge>
          )}
        </div>

        {loading && (
          <div className="flex justify-center py-8">
            <RefreshCw className="h-8 w-8 animate-spin text-gray-500" />
          </div>
        )}

        {!loading && discoveredJobs.length === 0 && (
          <Card>
            <CardContent className="text-center py-8">
              <Search className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No jobs found</h3>
              <p className="text-gray-600 mb-4">
                Try adjusting your filters or trigger a new job discovery.
              </p>
              <Button onClick={triggerDiscovery}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Discover Jobs Now
              </Button>
            </CardContent>
          </Card>
        )}

        {!loading && discoveredJobs.map((job, index) => (
          <Card key={job.unique_id || index} className="hover:shadow-md transition-shadow">
            <CardHeader>
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <CardTitle className="text-lg mb-2">{job.title}</CardTitle>
                  <CardDescription className="flex items-center gap-4 text-sm">
                    <span className="flex items-center gap-1">
                      <Building2 className="h-4 w-4" />
                      {job.company}
                    </span>
                    {job.location && (
                      <span className="flex items-center gap-1">
                        <MapPin className="h-4 w-4" />
                        {job.location}
                      </span>
                    )}
                    <span className="flex items-center gap-1">
                      <Clock className="h-4 w-4" />
                      {getTimeAgo(job.discovered_at)}
                    </span>
                  </CardDescription>
                </div>
                
                <div className="flex gap-2">
                  <Badge variant="outline">{job.source}</Badge>
                  {job.is_recent && (
                    <Badge variant="default">Fresh</Badge>
                  )}
                </div>
              </div>
            </CardHeader>
            
            <CardContent>
              <div className="space-y-3">
                {job.description && (
                  <p className="text-sm text-gray-700 line-clamp-3">
                    {job.description.length > 200 
                      ? `${job.description.substring(0, 200)}...` 
                      : job.description
                    }
                  </p>
                )}
                
                <div className="flex justify-between items-center">
                  <div className="flex gap-2 text-xs text-gray-500">
                    <span>Search: {job.search_title}</span>
                    {job.company_email && (
                      <span>• Email: {job.company_email}</span>
                    )}
                  </div>
                  
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => window.open(job.url, '_blank')}
                    >
                      <ExternalLink className="h-4 w-4 mr-1" />
                      View Job
                    </Button>
                    
                    <Button
                      size="sm"
                      onClick={() => {
                        // Navigate to auto-apply with pre-filled job info
                        const params = new URLSearchParams({
                          job_title: job.title,
                          company: job.company,
                          job_url: job.url
                        });
                        window.location.href = `/auto-apply?${params}`;
                      }}
                    >
                      Quick Apply
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}