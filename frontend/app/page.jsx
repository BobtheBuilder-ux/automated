'use client';

import { useState } from 'react';
import { applicationService } from '../lib/firebaseService';
import { ApiService } from '../lib/apiService';
import { FiUpload, FiFileText, FiMail, FiUser, FiLoader } from 'react-icons/fi';

export default function Home() {
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    job_title: ''
  });
  const [files, setFiles] = useState({
    cv: null,
    certificate: null
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleInputChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };

  const handleFileChange = (e) => {
    setFiles({
      ...files,
      [e.target.name]: e.target.files[0]
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      // Create FormData for backend submission
      const formDataToSend = new FormData();
      formDataToSend.append('full_name', formData.full_name);
      formDataToSend.append('email', formData.email);
      formDataToSend.append('job_title', formData.job_title);
      
      if (files.cv) {
        formDataToSend.append('cv', files.cv);
      }
      if (files.certificate) {
        formDataToSend.append('certificate', files.certificate);
      }

      // Submit to backend using ApiService
      const result = await ApiService.submitApplication(formDataToSend);

      if (result.success) {
        setMessage('Cover letter generated successfully! Check your dashboard for the results.');
        
        // Reset form
        setFormData({ full_name: '', email: '', job_title: '' });
        setFiles({ cv: null, certificate: null });
        
        // Reset file inputs
        const cvInput = document.getElementById('cv');
        const certInput = document.getElementById('certificate');
        if (cvInput) cvInput.value = '';
        if (certInput) certInput.value = '';
      } else {
        setMessage(`Error: ${result.error || 'Failed to generate cover letter'}`);
      }
    } catch (error) {
      console.error('Error:', error);
      setMessage('Error connecting to server. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-8">
        <div className="flex items-center gap-3 mb-6">
          <FiFileText className="h-8 w-8 text-blue-600" />
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
            Cover Letter Generator
          </h1>
        </div>

        <p className="text-gray-600 dark:text-gray-400 mb-8">
          Upload your CV and provide job details to generate a personalized cover letter using AI.
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
          <div>
            <label htmlFor="full_name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <FiUser className="inline mr-2" />
              Full Name *
            </label>
            <input
              type="text"
              id="full_name"
              name="full_name"
              value={formData.full_name}
              onChange={handleInputChange}
              required
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-gray-900 dark:text-gray-100"
              placeholder="Enter your full name"
            />
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <FiMail className="inline mr-2" />
              Email Address *
            </label>
            <input
              type="email"
              id="email"
              name="email"
              value={formData.email}
              onChange={handleInputChange}
              required
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-gray-900 dark:text-gray-100"
              placeholder="your.email@example.com"
            />
          </div>

          <div>
            <label htmlFor="job_title" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <FiFileText className="inline mr-2" />
              Job Title *
            </label>
            <input
              type="text"
              id="job_title"
              name="job_title"
              value={formData.job_title}
              onChange={handleInputChange}
              required
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-gray-900 dark:text-gray-100"
              placeholder="e.g., Frontend Developer"
            />
          </div>

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
            {files.cv && (
              <p className="mt-1 text-sm text-gray-500">Selected: {files.cv.name}</p>
            )}
          </div>

          <div>
            <label htmlFor="certificate" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              <FiUpload className="inline mr-2" />
              Certificate (optional)
            </label>
            <input
              type="file"
              id="certificate"
              name="certificate"
              accept=".pdf,.zip"
              onChange={handleFileChange}
              className="w-full px-3 py-2 bg-gray-50 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-gray-900 dark:text-gray-100 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
            {files.certificate && (
              <p className="mt-1 text-sm text-gray-500">Selected: {files.certificate.name}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-semibold rounded-md flex items-center justify-center gap-2"
          >
            {loading ? <FiLoader className="animate-spin" /> : <FiFileText />}
            {loading ? 'Generating...' : 'Generate Cover Letter'}
          </button>
        </form>

        <div className="mt-8 p-6 bg-gray-50 dark:bg-gray-700 rounded-lg">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3">
            How it works
          </h3>
          <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-1">•</span>
              <span>Upload your CV and any relevant certificates</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-1">•</span>
              <span>AI analyzes your CV and extracts key information</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-1">•</span>
              <span>Generates a personalized cover letter for the job title</span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-blue-600 mt-1">•</span>
              <span>Download your cover letter and track all applications in the dashboard</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
