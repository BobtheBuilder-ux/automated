'use client';

import { useState, useEffect } from 'react';
import { ApiService } from '../../lib/apiService';
import { 
  FiFileText, 
  FiDownload, 
  FiTrash2, 
  FiClock, 
  FiCheckCircle, 
  FiXCircle, 
  FiSearch,
  FiFilter,
  FiRefreshCw,
  FiTrendingUp,
  FiUsers,
  FiTarget,
  FiActivity,
  FiEye,
  FiX,
  FiCalendar,
  FiMail
} from 'react-icons/fi';

export default function Dashboard() {
  const [applications, setApplications] = useState([]);
  const [filteredApplications, setFilteredApplications] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [sortBy, setSortBy] = useState('newest');
  const [selectedApplication, setSelectedApplication] = useState(null);
  const [showCoverLetterModal, setShowCoverLetterModal] = useState(false);
  const [showDetailsModal, setShowDetailsModal] = useState(false);
  const [coverLetterContent, setCoverLetterContent] = useState('');
  const [activeTab, setActiveTab] = useState('all'); // 'all', 'successful', 'cover-letters', 'emails'

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    filterAndSortApplications();
  }, [applications, searchTerm, statusFilter, sortBy]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [applicationsResult, statsResult] = await Promise.all([
        ApiService.getApplications().catch(error => {
          console.error('Applications API error:', error);
          return { success: false, error: error.message };
        }),
        ApiService.getStats().catch(error => {
          console.error('Stats API error:', error);
          return { success: false, error: error.message };
        })
      ]);

      if (applicationsResult && applicationsResult.success) {
        setApplications(applicationsResult.data || []);
      } else {
        console.warn('Applications API failed:', applicationsResult?.error || 'Unknown error');
        setApplications([]);
      }

      if (statsResult && statsResult.success) {
        setStats(statsResult.data);
      } else {
        console.warn('Stats API failed:', statsResult?.error || 'Unknown error');
        // Set default stats
        setStats({
          totalApplications: 0,
          completedApplications: 0,
          pendingApplications: 0,
          failedApplications: 0,
          successRate: 0
        });
      }
    } catch (error) {
      console.error('Error loading dashboard data:', error);
      setApplications([]);
      setStats({
        totalApplications: 0,
        completedApplications: 0,
        pendingApplications: 0,
        failedApplications: 0,
        successRate: 0
      });
    } finally {
      setLoading(false);
    }
  };

  const filterAndSortApplications = () => {
    let filtered = [...applications];

    // Filter by search term
    if (searchTerm) {
      filtered = filtered.filter(app =>
        app.full_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        app.job_title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        app.email?.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Filter by status
    if (statusFilter !== 'all') {
      filtered = filtered.filter(app => app.status === statusFilter);
    }

    // Sort applications
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'newest':
          return new Date(b.createdAt) - new Date(a.createdAt);
        case 'oldest':
          return new Date(a.createdAt) - new Date(b.createdAt);
        case 'name':
          return (a.full_name || '').localeCompare(b.full_name || '');
        case 'job_title':
          return (a.job_title || '').localeCompare(b.job_title || '');
        default:
          return 0;
      }
    });

    setFilteredApplications(filtered);
  };

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this application?')) {
      const result = await ApiService.deleteApplication(id);
      if (result.success) {
        setApplications(prev => prev.filter(app => app.id !== id));
      }
    }
  };

  const downloadFile = async (filePath, fileName) => {
    try {
      // Clean the file path - remove any leading slashes and handle different path formats
      let cleanPath = filePath;
      if (cleanPath.startsWith('/')) {
        cleanPath = cleanPath.substring(1);
      }
      
      // If the path doesn't start with static/uploads, it might just be a filename
      if (!cleanPath.startsWith('static/uploads/')) {
        // Check if it's a full path that needs to be extracted
        const uploadIndex = cleanPath.indexOf('static/uploads/');
        if (uploadIndex !== -1) {
          cleanPath = cleanPath.substring(uploadIndex);
        }
      }
      
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/download/${cleanPath}`);
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        alert('Error downloading file');
      }
    } catch (error) {
      console.error('Download error:', error);
      alert('Error downloading file');
    }
  };

  const viewCoverLetter = async (application) => {
    setSelectedApplication(application);
    setShowCoverLetterModal(true);
    setCoverLetterContent('Loading...');
    
    try {
      // Try to fetch the cover letter content from the backend
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/cover-letter/${application.id}`);
      if (response.ok) {
        const data = await response.json();
        setCoverLetterContent(data.content || 'Cover letter content not available');
      } else {
        // Fallback: generate a preview based on application data
        setCoverLetterContent(generateCoverLetterPreview(application));
      }
    } catch (error) {
      console.error('Error fetching cover letter:', error);
      setCoverLetterContent(generateCoverLetterPreview(application));
    }
  };

  const generateCoverLetterPreview = (application) => {
    return `Dear Hiring Manager,

I am writing to express my strong interest in the ${application.job_title} position at your company. 

[This is a preview of the cover letter generated for ${application.full_name}]

With my background and experience, I believe I would be a valuable addition to your team. I have attached my CV for your review and would welcome the opportunity to discuss how my skills can contribute to your organization.

Thank you for considering my application. I look forward to hearing from you.

Best regards,
${application.full_name}

---
Generated on: ${new Date(application.createdAt).toLocaleDateString()}
Status: ${application.status}`;
  };

  const getSuccessfulApplications = () => {
    return applications.filter(app => app.status === 'completed');
  };

  const getCoverLetterApplications = () => {
    return applications.filter(app => app.coverLetterPath);
  };

  const getFilteredApplicationsByTab = () => {
    let filtered = [...applications];
    
    switch (activeTab) {
      case 'successful':
        filtered = getSuccessfulApplications();
        break;
      case 'cover-letters':
        filtered = getCoverLetterApplications();
        break;
      default:
        filtered = [...applications];
    }

    // Apply existing filters
    if (searchTerm) {
      filtered = filtered.filter(app =>
        app.full_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        app.job_title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        app.email?.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    if (statusFilter !== 'all') {
      filtered = filtered.filter(app => app.status === statusFilter);
    }

    // Sort applications
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'newest':
          return new Date(b.createdAt) - new Date(a.createdAt);
        case 'oldest':
          return new Date(a.createdAt) - new Date(b.createdAt);
        case 'name':
          return (a.full_name || '').localeCompare(b.full_name || '');
        case 'job_title':
          return (a.job_title || '').localeCompare(b.job_title || '');
        default:
          return 0;
      }
    });

    return filtered;
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <FiCheckCircle className="w-5 h-5 text-green-500" />;
      case 'processing':
        return <FiClock className="w-5 h-5 text-yellow-500" />;
      case 'failed':
        return <FiXCircle className="w-5 h-5 text-red-500" />;
      default:
        return <FiClock className="w-5 h-5 text-gray-500" />;
    }
  };

  const getStatusBadge = (status) => {
    const baseClasses = "px-2 py-1 text-xs font-medium rounded-full";
    switch (status) {
      case 'completed':
        return `${baseClasses} bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300`;
      case 'processing':
        return `${baseClasses} bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300`;
      case 'failed':
        return `${baseClasses} bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300`;
      default:
        return `${baseClasses} bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-300`;
    }
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto p-6">
        <div className="flex items-center justify-center h-64">
          <FiRefreshCw className="w-8 h-8 animate-spin text-blue-600" />
          <span className="ml-2 text-lg text-gray-600 dark:text-gray-400">Loading dashboard...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Dashboard</h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              Track your job applications and monitor performance
            </p>
          </div>
          <button
            onClick={loadData}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <FiRefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Statistics Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center">
              <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
                <FiUsers className="w-6 h-6 text-blue-600 dark:text-blue-400" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Total Applications</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stats.totalApplications}</p>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center">
              <div className="p-2 bg-green-100 dark:bg-green-900 rounded-lg">
                <FiCheckCircle className="w-6 h-6 text-green-600 dark:text-green-400" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Completed</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stats.completedApplications}</p>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center">
              <div className="p-2 bg-yellow-100 dark:bg-yellow-900 rounded-lg">
                <FiClock className="w-6 h-6 text-yellow-600 dark:text-yellow-400" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Processing</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stats.pendingApplications}</p>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center">
              <div className="p-2 bg-purple-100 dark:bg-purple-900 rounded-lg">
                <FiTrendingUp className="w-6 h-6 text-purple-600 dark:text-purple-400" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">Success Rate</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">{stats.successRate}%</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 mb-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div className="flex flex-col sm:flex-row gap-4 flex-1">
            {/* Search */}
            <div className="relative flex-1 max-w-md">
              <FiSearch className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
              <input
                type="text"
                placeholder="Search by name, job title, or email..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Status Filter */}
            <div className="flex items-center gap-2">
              <FiFilter className="w-4 h-4 text-gray-500" />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Status</option>
                <option value="completed">Completed</option>
                <option value="processing">Processing</option>
                <option value="failed">Failed</option>
              </select>
            </div>
          </div>

          {/* Sort */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600 dark:text-gray-400">Sort by:</span>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="newest">Newest First</option>
              <option value="oldest">Oldest First</option>
              <option value="name">Name (A-Z)</option>
              <option value="job_title">Job Title (A-Z)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 mb-6">
        <div className="px-6 py-4">
          <nav className="flex space-x-8">
            <button
              onClick={() => setActiveTab('all')}
              className={`flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${
                activeTab === 'all'
                  ? 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                  : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
              }`}
            >
              <FiFileText className="w-4 h-4" />
              All Applications ({applications.length})
            </button>
            <button
              onClick={() => setActiveTab('successful')}
              className={`flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${
                activeTab === 'successful'
                  ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                  : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
              }`}
            >
              <FiCheckCircle className="w-4 h-4" />
              Successful Applications ({getSuccessfulApplications().length})
            </button>
            <button
              onClick={() => setActiveTab('cover-letters')}
              className={`flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${
                activeTab === 'cover-letters'
                  ? 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300'
                  : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200'
              }`}
            >
              <FiEye className="w-4 h-4" />
              Cover Letters ({getCoverLetterApplications().length})
            </button>
          </nav>
        </div>
      </div>

      {/* Applications Table */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Applications ({filteredApplications.length})
          </h2>
        </div>

        {filteredApplications.length === 0 ? (
          <div className="p-8 text-center">
            <FiFileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
              No applications found
            </h3>
            <p className="text-gray-600 dark:text-gray-400">
              {applications.length === 0 
                ? "You haven't created any applications yet. Start by generating your first cover letter!"
                : "No applications match your current filters. Try adjusting your search criteria."
              }
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Application Details
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Company & Job
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Email Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Job Board
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {filteredApplications.map((application) => (
                  <tr key={application.id} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                    <td className="px-6 py-4">
                      <div className="flex items-center">
                        <div className="flex-shrink-0 h-10 w-10">
                          <div className="h-10 w-10 rounded-full bg-gradient-to-r from-blue-400 to-purple-500 flex items-center justify-center">
                            <span className="text-white font-medium text-sm">
                              {application.full_name?.charAt(0) || 'A'}
                            </span>
                          </div>
                        </div>
                        <div className="ml-4">
                          <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                            {application.full_name}
                          </div>
                          <div className="text-sm text-gray-500 dark:text-gray-400">
                            {application.job_title}
                          </div>
                          <div className="flex items-center gap-2 mt-1">
                            {getStatusIcon(application.status)}
                            <span className={getStatusBadge(application.status)}>
                              {application.status}
                            </span>
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div>
                        <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {application.type === 'auto_apply' || application.status === 'auto_apply_scheduled' ? 
                            'Auto Apply' : 
                            (application.job_board || 'Manual')}
                        </div>
                        {application.application_url && (
                          <a 
                            href={application.application_url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-xs text-blue-500 hover:text-blue-700 truncate block max-w-xs"
                          >
                            View Job Posting
                          </a>
                        )}
                        {/* Display progress for auto-apply applications */}
                        {(application.type === 'auto_apply' || application.status === 'auto_apply_scheduled') && (
                          <div className="mt-1">
                            {application.max_applications > 0 && (
                              <div className="flex flex-col gap-1">
                                <div className="flex justify-between items-center text-xs">
                                  <span className="text-gray-600 dark:text-gray-400">Progress:</span>
                                  <span className="font-medium">
                                    {application.applications_submitted || 0}/{application.max_applications}
                                  </span>
                                </div>
                                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                                  <div 
                                    className="bg-blue-600 h-1.5 rounded-full" 
                                    style={{ 
                                      width: `${Math.min(100, Math.max(0, 
                                        ((application.applications_submitted || 0) / application.max_applications) * 100
                                      ))}%` 
                                    }}
                                  ></div>
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                        <div className="text-xs text-gray-400 dark:text-gray-500">
                          {new Date(application.createdAt).toLocaleDateString()}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div>
                        {application.email_sent ? (
                          <div className="flex items-center gap-1 text-green-600">
                            <FiMail className="w-4 h-4" />
                            <span className="text-sm">Email Sent</span>
                          </div>
                        ) : (
                          <div className="flex items-center gap-1 text-gray-400">
                            <FiMail className="w-4 h-4" />
                            <span className="text-sm">No Email</span>
                          </div>
                        )}
                        {application.email_sent_to && (
                          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                            To: {application.email_sent_to}
                          </div>
                        )}
                        {application.email_sent_at && (
                          <div className="text-xs text-gray-400 dark:text-gray-500">
                            {new Date(application.email_sent_at).toLocaleDateString()}
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div>
                        <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                          {application.type === 'auto_apply' || application.status === 'auto_apply_scheduled' ? 
                            'Auto Apply' : 
                            (application.job_board || 'Manual')}
                        </div>
                        {application.application_url && (
                          <a 
                            href={application.application_url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-xs text-blue-500 hover:text-blue-700 truncate block max-w-xs"
                          >
                            View Job Posting
                          </a>
                        )}
                        {/* Display progress for auto-apply applications */}
                        {(application.type === 'auto_apply' || application.status === 'auto_apply_scheduled') && (
                          <div className="mt-1">
                            {application.max_applications > 0 && (
                              <div className="flex flex-col gap-1">
                                <div className="flex justify-between items-center text-xs">
                                  <span className="text-gray-600 dark:text-gray-400">Progress:</span>
                                  <span className="font-medium">
                                    {application.applications_submitted || 0}/{application.max_applications}
                                  </span>
                                </div>
                                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                                  <div 
                                    className="bg-blue-600 h-1.5 rounded-full" 
                                    style={{ 
                                      width: `${Math.min(100, Math.max(0, 
                                        ((application.applications_submitted || 0) / application.max_applications) * 100
                                      ))}%` 
                                    }}
                                  ></div>
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                        <div className="text-xs text-gray-400 dark:text-gray-500">
                          {new Date(application.createdAt).toLocaleDateString()}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col gap-2">
                        <button
                          onClick={() => {
                            setSelectedApplication(application);
                            setShowDetailsModal(true);
                          }}
                          className="flex items-center gap-1 text-blue-600 hover:text-blue-800 text-sm"
                        >
                          <FiEye className="w-3 h-3" />
                          View Details
                        </button>
                        {application.coverLetterPath && (
                          <button
                            onClick={() => viewCoverLetter(application)}
                            className="flex items-center gap-1 text-green-600 hover:text-green-800 text-sm"
                          >
                            <FiFileText className="w-3 h-3" />
                            Cover Letter
                          </button>
                        )}
                        <div className="flex items-center gap-2">
                          {application.cvPath && (
                            <button
                              onClick={() => downloadFile(application.cvPath, `cv_${application.full_name}.pdf`)}
                              className="text-purple-600 hover:text-purple-800 text-xs"
                              title="Download CV"
                            >
                              <FiDownload className="w-3 h-3" />
                            </button>
                          )}
                          <button
                            onClick={() => handleDelete(application.id)}
                            className="text-red-600 hover:text-red-900 text-xs"
                            title="Delete Application"
                          >
                            <FiTrash2 className="w-3 h-3" />
                          </button>
                        </div>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Cover Letter Modal */}
      {showCoverLetterModal && (
        <div className="fixed inset-0 flex items-center justify-center z-50">
          <div className="bg-black opacity-50 absolute inset-0"></div>
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden max-w-lg w-full z-10">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Cover Letter Preview
                </h3>
                <button
                  onClick={() => setShowCoverLetterModal(false)}
                  className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                >
                  <FiX className="w-5 h-5" />
                </button>
              </div>
            </div>
            <div className="p-6">
              <div className="prose dark:prose-invert">
                {coverLetterContent}
              </div>
            </div>
            <div className="px-6 py-4 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700">
              <div className="flex justify-end gap-4">
                <button
                  onClick={() => setShowCoverLetterModal(false)}
                  className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
                >
                  Close
                </button>
                {selectedApplication && (
                  <button
                    onClick={() => downloadFile(selectedApplication.coverLetterPath, `cover_letter_${selectedApplication.full_name}_${selectedApplication.job_title}.pdf`)}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                  >
                    <FiDownload className="w-4 h-4 mr-2" />
                    Download Cover Letter
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Application Details Modal */}
      {showDetailsModal && selectedApplication && (
        <div className="fixed inset-0 flex items-center justify-center z-50">
          <div className="bg-black opacity-50 absolute inset-0"></div>
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg overflow-hidden max-w-4xl w-full z-10 max-h-[90vh] overflow-y-auto">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
                  Complete Application Details
                </h3>
                <button
                  onClick={() => setShowDetailsModal(false)}
                  className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                >
                  <FiX className="w-5 h-5" />
                </button>
              </div>
            </div>
            <div className="p-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Basic Information */}
                <div className="space-y-4">
                  <h4 className="text-lg font-semibold text-gray-900 dark:text-gray-100 border-b pb-2">
                    Basic Information
                  </h4>
                  <div>
                    <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Applicant Name:</span>
                    <p className="text-gray-900 dark:text-gray-100">{selectedApplication.full_name}</p>
                  </div>
                  <div>
                    <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Email:</span>
                    <p className="text-gray-900 dark:text-gray-100">{selectedApplication.email}</p>
                  </div>
                  <div>
                    <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Job Title:</span>
                    <p className="text-gray-900 dark:text-gray-100">{selectedApplication.job_title}</p>
                  </div>
                  <div>
                    <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Status:</span>
                    <div className="flex items-center gap-2 mt-1">
                      {getStatusIcon(selectedApplication.status)}
                      <span className={getStatusBadge(selectedApplication.status)}>
                        {selectedApplication.status}
                      </span>
                    </div>
                  </div>
                  <div>
                    <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Application Date:</span>
                    <p className="text-gray-900 dark:text-gray-100">
                      {new Date(selectedApplication.createdAt).toLocaleString()}
                    </p>
                  </div>
                </div>

                {/* Company Information */}
                <div className="space-y-4">
                  <h4 className="text-lg font-semibold text-gray-900 dark:text-gray-100 border-b pb-2">
                    Company Information
                  </h4>
                  <div>
                    <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Company Name:</span>
                    <p className="text-gray-900 dark:text-gray-100">
                      {selectedApplication.company_name || 'Unknown Company'}
                    </p>
                  </div>
                  <div>
                    <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Company Email:</span>
                    <p className="text-gray-900 dark:text-gray-100">
                      {selectedApplication.company_email || 'No email provided'}
                    </p>
                  </div>
                  <div>
                    <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Job Board:</span>
                    <p className="text-gray-900 dark:text-gray-100">
                      {selectedApplication.job_board || 'Manual Application'}
                    </p>
                  </div>
                  {selectedApplication.application_url && (
                    <div>
                      <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Job Posting URL:</span>
                      <a 
                        href={selectedApplication.application_url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-blue-500 hover:text-blue-700 break-all"
                      >
                        {selectedApplication.application_url}
                      </a>
                    </div>
                  )}
                </div>
              </div>

              {/* Job Description */}
              {selectedApplication.job_description && (
                <div className="mt-6 space-y-4">
                  <h4 className="text-lg font-semibold text-gray-900 dark:text-gray-100 border-b pb-2">
                    Job Description
                  </h4>
                  <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg">
                    <p className="text-gray-900 dark:text-gray-100 whitespace-pre-wrap">
                      {selectedApplication.job_description}
                    </p>
                  </div>
                </div>
              )}

              {/* Email Information */}
              <div className="mt-6 space-y-4">
                <h4 className="text-lg font-semibold text-gray-900 dark:text-gray-100 border-b pb-2">
                  Email Details
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Email Status:</span>
                    <div className="flex items-center gap-2 mt-1">
                      {selectedApplication.email_sent ? (
                        <>
                          <FiMail className="w-4 h-4 text-green-600" />
                          <span className="text-green-600 font-medium">Email Sent Successfully</span>
                        </>
                      ) : (
                        <>
                          <FiMail className="w-4 h-4 text-gray-400" />
                          <span className="text-gray-400">No Email Sent</span>
                        </>
                      )}
                    </div>
                  </div>
                  
                  {selectedApplication.email_sent && (
                    <>
                      <div>
                        <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Sent To:</span>
                        <p className="text-gray-900 dark:text-gray-100">
                          {selectedApplication.email_sent_to || 'N/A'}
                        </p>
                      </div>
                      
                      <div>
                        <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Email Subject:</span>
                        <p className="text-gray-900 dark:text-gray-100">
                          {selectedApplication.email_subject || 'N/A'}
                        </p>
                      </div>
                      
                      <div>
                        <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Sent Date:</span>
                        <p className="text-gray-900 dark:text-gray-100">
                          {selectedApplication.email_sent_at 
                            ? new Date(selectedApplication.email_sent_at).toLocaleString()
                            : 'N/A'
                          }
                        </p>
                      </div>
                    </>
                  )}
                </div>

                {/* Email Body */}
                {selectedApplication.email_body && (
                  <div className="mt-4">
                    <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Email Content:</span>
                    <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg mt-2">
                      <p className="text-gray-900 dark:text-gray-100 whitespace-pre-wrap text-sm">
                        {selectedApplication.email_body}
                      </p>
                    </div>
                  </div>
                )}
              </div>

              {/* Response & Interview Information */}
              {(selectedApplication.response_received || selectedApplication.interview_scheduled) && (
                <div className="mt-6 space-y-4">
                  <h4 className="text-lg font-semibold text-gray-900 dark:text-gray-100 border-b pb-2">
                    Response & Interview Status
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {selectedApplication.response_received && (
                      <>
                        <div>
                          <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Response Status:</span>
                          <div className="flex items-center gap-2 mt-1">
                            <FiCheckCircle className="w-4 h-4 text-green-600" />
                            <span className="text-green-600 font-medium">Response Received</span>
                          </div>
                        </div>
                        
                        {selectedApplication.response_date && (
                          <div>
                            <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Response Date:</span>
                            <p className="text-gray-900 dark:text-gray-100">
                              {new Date(selectedApplication.response_date).toLocaleString()}
                            </p>
                          </div>
                        )}
                      </>
                    )}
                    
                    {selectedApplication.interview_scheduled && (
                      <>
                        <div>
                          <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Interview Status:</span>
                          <div className="flex items-center gap-2 mt-1">
                            <FiCalendar className="w-4 h-4 text-blue-600" />
                            <span className="text-blue-600 font-medium">Interview Scheduled</span>
                          </div>
                        </div>
                        
                        {selectedApplication.interview_date && (
                          <div>
                            <span className="text-sm font-medium text-gray-600 dark:text-gray-400">Interview Date:</span>
                            <p className="text-gray-900 dark:text-gray-100">
                              {new Date(selectedApplication.interview_date).toLocaleString()}
                            </p>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>
              )}

              {/* Application Notes */}
              {selectedApplication.application_notes && (
                <div className="mt-6 space-y-4">
                  <h4 className="text-lg font-semibold text-gray-900 dark:text-gray-100 border-b pb-2">
                    Application Notes
                  </h4>
                  <div className="bg-yellow-50 dark:bg-yellow-900/20 p-4 rounded-lg">
                    <p className="text-gray-900 dark:text-gray-100">
                      {selectedApplication.application_notes}
                    </p>
                  </div>
                </div>
              )}

              {/* Files */}
              <div className="mt-6 space-y-4">
                <h4 className="text-lg font-semibold text-gray-900 dark:text-gray-100 border-b pb-2">
                  Application Files
                </h4>
                <div className="flex flex-wrap gap-4">
                  {selectedApplication.coverLetterPath && (
                    <div className="flex items-center gap-2 bg-green-50 dark:bg-green-900/20 px-3 py-2 rounded-lg">
                      <FiFileText className="w-4 h-4 text-green-600" />
                      <span className="text-sm text-green-700 dark:text-green-300">Cover Letter</span>
                      <div className="flex gap-1 ml-2">
                        <button
                          onClick={() => viewCoverLetter(selectedApplication)}
                          className="text-green-600 hover:text-green-800 text-xs"
                          title="View Cover Letter"
                        >
                          <FiEye className="w-3 h-3" />
                        </button>
                        <button
                          onClick={() => downloadFile(selectedApplication.coverLetterPath, `cover_letter_${selectedApplication.full_name}_${selectedApplication.job_title}.pdf`)}
                          className="text-green-600 hover:text-green-800 text-xs"
                          title="Download Cover Letter"
                        >
                          <FiDownload className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                  )}
                  
                  {selectedApplication.cvPath && (
                    <div className="flex items-center gap-2 bg-blue-50 dark:bg-blue-900/20 px-3 py-2 rounded-lg">
                      <FiFileText className="w-4 h-4 text-blue-600" />
                      <span className="text-sm text-blue-700 dark:text-blue-300">CV</span>
                      <button
                        onClick={() => downloadFile(selectedApplication.cvPath, `cv_${selectedApplication.full_name}.pdf`)}
                        className="text-blue-600 hover:text-blue-800 text-xs ml-2"
                        title="Download CV"
                      >
                        <FiDownload className="w-3 h-3" />
                      </button>
                    </div>
                  )}
                  
                  {selectedApplication.certificatePath && (
                    <div className="flex items-center gap-2 bg-purple-50 dark:bg-purple-900/20 px-3 py-2 rounded-lg">
                      <FiFileText className="w-4 h-4 text-purple-600" />
                      <span className="text-sm text-purple-700 dark:text-purple-300">Certificate</span>
                      <button
                        onClick={() => downloadFile(selectedApplication.certificatePath, `certificate_${selectedApplication.full_name}.pdf`)}
                        className="text-purple-600 hover:text-purple-800 text-xs ml-2"
                        title="Download Certificate"
                      >
                        <FiDownload className="w-3 h-3" />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
            
            <div className="px-6 py-4 bg-gray-50 dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700">
              <div className="flex justify-end gap-4">
                <button
                  onClick={() => setShowDetailsModal(false)}
                  className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-md hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
                >
                  Close
                </button>
                <button
                  onClick={() => handleDelete(selectedApplication.id)}
                  className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
                >
                  <FiTrash2 className="w-4 h-4 mr-2 inline" />
                  Delete Application
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}