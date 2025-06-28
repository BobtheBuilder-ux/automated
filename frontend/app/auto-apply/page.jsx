'use client';

import { useState } from 'react';
import { autoApplyService } from '../../lib/firebaseService';
import { apiService } from '../../lib/apiService';
import { FiPlay, FiClock, FiMapPin, FiLoader, FiUpload, FiMail, FiCheck } from 'react-icons/fi';

export default function AutoApply() {
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    job_title: '',
    location: '',
    max_applications: 5,
    schedule_type: 'once',
    frequency_days: 7,
    total_runs: null
  });
  const [cvFile, setCvFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [sendingEmail, setSendingEmail] = useState(false);
  const [emailSent, setEmailSent] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');
    setEmailSent(false);

    try {
      // Create FormData to match backend expectations
      const formDataToSend = new FormData();
      formDataToSend.append('full_name', formData.full_name);
      formDataToSend.append('email', formData.email);
      formDataToSend.append('job_title', formData.job_title);
      formDataToSend.append('location', formData.location || 'remote');
      formDataToSend.append('max_applications', formData.max_applications.toString());
      formDataToSend.append('schedule_type', formData.schedule_type);
      formDataToSend.append('frequency_days', formData.frequency_days.toString());
      
      if (formData.total_runs) {
        formDataToSend.append('total_runs', formData.total_runs.toString());
      }
      
      if (cvFile) {
        formDataToSend.append('cv', cvFile);
      } else {
        setMessage('Please upload your CV file');
        setLoading(false);
        return;
      }

      // Submit to backend - Use the JSON API endpoint
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'https://automated-uayp.onrender.com'}/api/auto-apply`, {
        method: 'POST',
        body: formDataToSend,
      });

      // Log the response for debugging
      console.log('Response status:', response.status);
      console.log('Response headers:', response.headers);

      if (response.ok) {
        // Try to parse as JSON first, fall back to text
        let result;
        try {
          result = await response.json();
        } catch (e) {
          result = await response.text();
        }
        
        console.log('Response result:', result);
        setMessage('✅ Auto-apply job scheduled successfully! Check your dashboard for updates.');
        
        // Send email notification for successful scheduling
        setSendingEmail(true);
        try {
          const emailResult = await apiService.sendAutoApplyConfirmation({
            email: formData.email,
            fullName: formData.full_name,
            jobTitle: formData.job_title,
            location: formData.location || 'remote',
            scheduleType: formData.schedule_type,
            maxApplications: formData.max_applications,
            frequencyDays: formData.frequency_days,
            totalRuns: formData.total_runs
          });
          
          if (emailResult.success) {
            setEmailSent(true);
            console.log('Confirmation email sent successfully');
          } else {
            console.error('Failed to send confirmation email:', emailResult.error);
          }
        } catch (emailError) {
          console.error('Error sending confirmation email:', emailError);
        } finally {
          setSendingEmail(false);
        }
        
        // Reset form
        setFormData({
          full_name: '',
          email: '',
          job_title: '',
          location: '',
          max_applications: 5,
          schedule_type: 'once',
          frequency_days: 7,
          total_runs: null
        });
        setCvFile(null);
        
        // Reset file input
        const fileInput = document.getElementById('cv');
        if (fileInput) fileInput.value = '';
      } else {
        let errorText;
        try {
          const errorData = await response.json();
          errorText = errorData.error || errorData.message || 'Unknown error';
        } catch (e) {
          errorText = await response.text();
        }
        console.error('Error response:', errorText);
        setMessage(`❌ Error: ${errorText || 'Failed to schedule auto-apply job'}`);
      }
    } catch (error) {
      console.error('Error:', error);
      setMessage('Error connecting to server. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value, type } = e.target;
    setFormData({
      ...formData,
      [name]: type === 'number' ? parseInt(value) || 0 : value
    });
  };

  const handleFileChange = (e) => {
    setCvFile(e.target.files[0]);
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-8">
        <div className="flex items-center gap-3 mb-6">
          <FiPlay className="h-8 w-8 text-blue-600" />
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
            Automated Job Applications
          </h1>
        </div>

        <p className="text-gray-600 dark:text-gray-400 mb-8">
          Set up automated job applications based on your criteria. The system will search for jobs 
          and apply on your behalf using your CV and generated cover letters.
        </p>

        {message && (
          <div className={`p-4 rounded-md mb-6 ${
            message.includes('Error') 
              ? 'bg-red-50 text-red-700 border border-red-200' 
              : 'bg-green-50 text-green-700 border border-green-200'
          }`}>
            {message}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label htmlFor="full_name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Full Name *
              </label>
              <input
                type="text"
                id="full_name"
                name="full_name"
                value={formData.full_name}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-gray-900 dark:text-gray-100"
                placeholder="Enter your full name"
              />
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Email Address *
              </label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-gray-900 dark:text-gray-100"
                placeholder="your.email@example.com"
              />
            </div>

            <div>
              <label htmlFor="job_title" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Job Title *
              </label>
              <input
                type="text"
                id="job_title"
                name="job_title"
                value={formData.job_title}
                onChange={handleChange}
                required
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-gray-900 dark:text-gray-100"
                placeholder="e.g., Frontend Developer"
              />
            </div>

            <div>
              <label htmlFor="location" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Location
              </label>
              <input
                type="text"
                id="location"
                name="location"
                value={formData.location}
                onChange={handleChange}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-gray-900 dark:text-gray-100"
                placeholder="e.g., Remote, New York, London"
              />
            </div>

            <div>
              <label htmlFor="schedule_type" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Schedule Type
              </label>
              <select
                id="schedule_type"
                name="schedule_type"
                value={formData.schedule_type}
                onChange={handleChange}
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-gray-900 dark:text-gray-100"
              >
                <option value="once">Run Once</option>
                <option value="recurring">Recurring</option>
              </select>
            </div>

            <div>
              <label htmlFor="max_applications" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Max Applications per Run
              </label>
              <input
                type="number"
                id="max_applications"
                name="max_applications"
                value={formData.max_applications}
                onChange={handleChange}
                min="1"
                max="50"
                className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-gray-900 dark:text-gray-100"
              />
            </div>
          </div>

          {formData.schedule_type === 'recurring' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label htmlFor="frequency_days" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Frequency (days)
                </label>
                <input
                  type="number"
                  id="frequency_days"
                  name="frequency_days"
                  value={formData.frequency_days}
                  onChange={handleChange}
                  min="1"
                  max="30"
                  className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-gray-900 dark:text-gray-100"
                />
              </div>

              <div>
                <label htmlFor="total_runs" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Total Runs (optional)
                </label>
                <input
                  type="number"
                  id="total_runs"
                  name="total_runs"
                  value={formData.total_runs || ''}
                  onChange={handleChange}
                  min="1"
                  className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-gray-900 dark:text-gray-100"
                  placeholder="Leave empty for unlimited"
                />
              </div>
            </div>
          )}

          <div>
            <label htmlFor="cv" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <FiUpload className="inline mr-2" />
              CV (PDF only) *
            </label>
            <input
              type="file"
              id="cv"
              name="cv"
              accept=".pdf"
              onChange={handleFileChange}
              required
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-gray-900 dark:text-gray-100 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
            {cvFile && (
              <p className="mt-1 text-sm text-gray-500">Selected: {cvFile.name}</p>
            )}
          </div>

          <div className="flex justify-end">
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-semibold rounded-md flex items-center gap-2"
            >
              {loading ? <FiLoader className="animate-spin" /> : <FiClock />}
              {loading ? 'Scheduling...' : 'Start Auto Apply'}
            </button>
          </div>
        </form>

        <div className="mt-8 p-6 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3">
            How Auto Apply Works
          </h3>
          <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-1">•</span>
              <span>System searches for jobs matching your criteria on various job boards</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-1">•</span>
              <span>Generates personalized cover letters for each job using AI</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-1">•</span>
              <span>Automatically submits applications with your CV and cover letter</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-1">•</span>
              <span>Tracks application status and saves all data to your dashboard</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}