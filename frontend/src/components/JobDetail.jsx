import { useState, useEffect } from 'react';
import { apiGet, apiPost } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';
import './JobDetail.css';

function JobDetail({ jobId, onBack }) {
  const [job, setJob] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [regenerating, setRegenerating] = useState(false);

  useEffect(() => {
    fetchJobDetail();
  }, [jobId]);

  const fetchJobDetail = async () => {
    try {
      setLoading(true);
      const response = await apiGet(API_ENDPOINTS.jobDetail(jobId));

      if (response.ok) {
        const data = await response.json();
        setJob(data);
      } else {
        const errorData = await response.json();
        setError(errorData.error || 'Failed to fetch job details');
      }
    } catch (err) {
      setError('An error occurred while fetching job details: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const truncateText = (text, maxLength = 100) => {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  const downloadTestCase = (testCase, index) => {
    const blob = new Blob([testCase], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `test_case_${index + 1}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const downloadAllTestCases = () => {
    if (!job || !job.test_cases || job.test_cases.length === 0) return;

    const content = job.test_cases.map((tc, idx) =>
      `=== Test Case ${idx + 1} ===\n${tc}\n`
    ).join('\n');

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `all_test_cases_${job.platform}_${job.problem_id}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const downloadGeneratorCode = () => {
    if (!job || !job.generator_code) return;

    const blob = new Blob([job.generator_code], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `generator_${job.platform}_${job.problem_id}.py`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleRegenerateScript = async () => {
    if (!confirm('Are you sure you want to regenerate the script? This will create a new job.')) {
      return;
    }

    setRegenerating(true);

    try {
      const response = await apiPost(API_ENDPOINTS.generateTestCases, {
        platform: job.platform,
        problem_id: job.problem_id,
        title: job.title,
        problem_url: job.problem_url || '',
        tags: job.tags || [],
        solution_code: job.solution_code || '',
        language: job.language,
        constraints: job.constraints,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to create job');
      }

      const data = await response.json();

      // Redirect to new job detail page
      window.location.href = `/jobs?job_id=${data.job_id}`;
    } catch (error) {
      console.error('Error regenerating script:', error);
      alert('An error occurred while regenerating script: ' + error.message);
    } finally {
      setRegenerating(false);
    }
  };

  if (loading) {
    return (
      <div className="job-detail-container">
        <div className="job-detail-header">
          <h2>Job Details</h2>
          <button onClick={onBack} className="back-button">← Back to Jobs</button>
        </div>
        <div className="loading">Loading job details...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="job-detail-container">
        <div className="job-detail-header">
          <h2>Job Details</h2>
          <button onClick={onBack} className="back-button">← Back to Jobs</button>
        </div>
        <div className="error-message">{error}</div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="job-detail-container">
        <div className="job-detail-header">
          <h2>Job Details</h2>
          <button onClick={onBack} className="back-button">← Back to Jobs</button>
        </div>
        <div className="error-message">Job not found</div>
      </div>
    );
  }

  return (
    <div className="job-detail-container">
      <div className="job-detail-header">
        <h2>Job Details</h2>
        <div className="header-actions">
          <button
            onClick={handleRegenerateScript}
            className="regenerate-button"
            disabled={regenerating}
          >
            {regenerating ? 'Regenerating...' : 'Regenerate Script'}
          </button>
          <button onClick={onBack} className="back-button">← Back to Jobs</button>
        </div>
      </div>

      <div className="job-info-card">
        <div className="job-info-row">
          <span className="label">Job ID:</span>
          <span className="value">{job.id}</span>
        </div>
        <div className="job-info-row">
          <span className="label">Problem:</span>
          <span className="value">{job.title} ({job.platform} - {job.problem_id})</span>
        </div>
        <div className="job-info-row">
          <span className="label">Status:</span>
          <span className={`status-badge status-${job.status.toLowerCase()}`}>{job.status}</span>
        </div>
        <div className="job-info-row">
          <span className="label">Created:</span>
          <span className="value">{new Date(job.created_at).toLocaleString()}</span>
        </div>
        <div className="job-info-row">
          <span className="label">Updated:</span>
          <span className="value">{new Date(job.updated_at).toLocaleString()}</span>
        </div>
        {job.tags && job.tags.length > 0 && (
          <div className="job-info-row">
            <span className="label">Tags:</span>
            <div className="tags">
              {job.tags.map((tag, idx) => (
                <span key={idx} className="tag">{tag}</span>
              ))}
            </div>
          </div>
        )}
      </div>

      {job.error_message && (
        <div className="error-card">
          <h3>Error</h3>
          <pre>{job.error_message}</pre>
        </div>
      )}

      {job.generator_code && (
        <div className="generator-code-card">
          <div className="card-header">
            <h3>Generator Script</h3>
            <button onClick={downloadGeneratorCode} className="download-button">
              Download Script
            </button>
          </div>
          <pre className="code-block">{job.generator_code}</pre>
        </div>
      )}

      {job.test_cases && job.test_cases.length > 0 && (
        <div className="test-cases-card">
          <div className="card-header">
            <h3>Generated Test Cases ({job.test_cases.length})</h3>
            <button onClick={downloadAllTestCases} className="download-button">
              Download All Test Cases
            </button>
          </div>
          <div className="test-cases-list">
            {job.test_cases.map((testCase, idx) => (
              <div key={idx} className="test-case-item">
                <div className="test-case-header">
                  <span className="test-case-number">Test Case {idx + 1}</span>
                  <button
                    onClick={() => downloadTestCase(testCase, idx)}
                    className="download-link"
                  >
                    Download
                  </button>
                </div>
                <pre className="test-case-content">
                  {truncateText(testCase, 200)}
                  {testCase.length > 200 && (
                    <span className="truncate-indicator"> (truncated)</span>
                  )}
                </pre>
              </div>
            ))}
          </div>
        </div>
      )}

      {job.test_case_error && (
        <div className="error-card">
          <h3>Test Case Generation Error</h3>
          <pre>{job.test_case_error}</pre>
        </div>
      )}
    </div>
  );
}

export default JobDetail;
