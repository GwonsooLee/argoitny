import { useState, useEffect } from 'react';
import { apiGet, apiPost } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';
import './Jobs.css';

function Jobs({ onBack }) {
  const [jobs, setJobs] = useState([]);
  const [drafts, setDrafts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('jobs'); // 'jobs' or 'drafts'
  const [executingJobs, setExecutingJobs] = useState({});

  // Fetch jobs and drafts
  const fetchData = async () => {
    try {
      const [jobsResponse, draftsResponse] = await Promise.all([
        apiGet(API_ENDPOINTS.jobs),
        apiGet(API_ENDPOINTS.drafts)
      ]);

      if (jobsResponse.ok) {
        const jobsData = await jobsResponse.json();
        setJobs(jobsData.jobs || []);
      }

      if (draftsResponse.ok) {
        const draftsData = await draftsResponse.json();
        setDrafts(draftsData.drafts || []);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();

    // Poll for updates every 5 seconds
    const interval = setInterval(fetchData, 5000);

    return () => clearInterval(interval);
  }, []);

  const handleExecuteScript = async (job) => {
    const numCases = prompt('How many test cases to generate?', '10');
    if (!numCases || numCases < 1) return;

    setExecutingJobs({ ...executingJobs, [job.id]: true });

    try {
      const response = await apiPost(API_ENDPOINTS.executeTestCases, {
        generator_code: job.generator_code,
        num_cases: parseInt(numCases)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to execute script');
      }

      const data = await response.json();

      // Redirect to register page with test cases
      const params = new URLSearchParams({
        platform: job.platform,
        problem_id: job.problem_id,
        title: job.title,
        problem_url: job.problem_url || '',
        tags: JSON.stringify(job.tags || []),
        solution_code: job.solution_code || '',
        language: job.language,
        constraints: job.constraints,
        test_cases: JSON.stringify(data.test_cases)
      });

      window.location.href = `/register-problem?${params.toString()}`;
    } catch (error) {
      console.error('Error executing script:', error);
      alert('An error occurred while executing script: ' + error.message);
    } finally {
      setExecutingJobs({ ...executingJobs, [job.id]: false });
    }
  };

  const handleLoadDraft = (draft) => {
    // Only pass draft_id, let ProblemRegister fetch the data from server
    window.location.href = `/register?draft_id=${draft.id}`;
  };

  const handleGenerateScript = async (draft) => {
    if (!draft.solution_code || !draft.constraints) {
      alert('Draft must have solution code and constraints to generate script');
      return;
    }

    setExecutingJobs({ ...executingJobs, [`draft-${draft.id}`]: true });

    try {
      const response = await apiPost(API_ENDPOINTS.generateTestCases, {
        platform: draft.platform,
        problem_id: draft.problem_id,
        title: draft.title,
        problem_url: draft.problem_url || '',
        tags: draft.tags || [],
        solution_code: draft.solution_code,
        language: draft.language || 'python',
        constraints: draft.constraints,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to create job');
      }

      const data = await response.json();

      // Redirect to job detail page
      window.location.href = `/jobs?job_id=${data.job_id}`;
    } catch (error) {
      console.error('Error generating script:', error);
      alert('An error occurred while generating script: ' + error.message);
    } finally {
      setExecutingJobs({ ...executingJobs, [`draft-${draft.id}`]: false });
    }
  };

  const getStatusBadge = (status) => {
    const statusClasses = {
      PENDING: 'status-pending',
      PROCESSING: 'status-processing',
      COMPLETED: 'status-completed',
      FAILED: 'status-failed'
    };

    return <span className={`status-badge ${statusClasses[status]}`}>{status}</span>;
  };

  if (loading) {
    return (
      <div className="jobs-container">
        <div className="jobs-header">
          <h2>Jobs & Drafts</h2>
          <button onClick={onBack} className="back-button">← Back</button>
        </div>
        <div className="loading">Loading...</div>
      </div>
    );
  }

  return (
    <div className="jobs-container">
      <div className="jobs-header">
        <h2>Jobs & Drafts</h2>
        <button onClick={onBack} className="back-button">← Back</button>
      </div>

      <div className="tabs">
        <button
          className={`tab ${activeTab === 'jobs' ? 'active' : ''}`}
          onClick={() => setActiveTab('jobs')}
        >
          Script Generation Jobs ({jobs.length})
        </button>
        <button
          className={`tab ${activeTab === 'drafts' ? 'active' : ''}`}
          onClick={() => setActiveTab('drafts')}
        >
          Drafts ({drafts.length})
        </button>
      </div>

      {activeTab === 'jobs' && (
        <div className="jobs-list">
          {jobs.length === 0 ? (
            <div className="empty-state">No jobs found</div>
          ) : (
            jobs.map((job) => (
              <div key={job.id} className="job-card">
                <div className="job-header">
                  <div className="job-title">
                    <h3>{job.title}</h3>
                    <span className="job-meta">
                      {job.platform} - {job.problem_id}
                    </span>
                  </div>
                  {getStatusBadge(job.status)}
                </div>

                {job.tags && job.tags.length > 0 && (
                  <div className="job-tags">
                    {job.tags.map((tag, idx) => (
                      <span key={idx} className="tag">{tag}</span>
                    ))}
                  </div>
                )}

                <div className="job-info">
                  <div className="info-item">
                    <span className="label">Language:</span>
                    <span className="value">{job.language}</span>
                  </div>
                  <div className="info-item">
                    <span className="label">Created:</span>
                    <span className="value">{new Date(job.created_at).toLocaleString()}</span>
                  </div>
                </div>

                {job.status === 'COMPLETED' && (
                  <div className="job-actions">
                    <button
                      onClick={() => window.location.href = `/jobs?job_id=${job.id}`}
                      className="view-detail-button"
                    >
                      View Details
                    </button>
                  </div>
                )}

                {job.status === 'FAILED' && job.error_message && (
                  <div className="error-message">
                    <strong>Error:</strong> {job.error_message}
                  </div>
                )}

                {job.status === 'PROCESSING' && (
                  <div className="processing-indicator">
                    <div className="spinner"></div>
                    <span>Processing... (This may take up to 60 seconds)</span>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === 'drafts' && (
        <div className="drafts-list">
          {drafts.length === 0 ? (
            <div className="empty-state">No drafts found</div>
          ) : (
            drafts.map((draft) => (
              <div key={draft.id} className="draft-card">
                <div className="draft-header">
                  <div className="draft-title">
                    <h3>{draft.title}</h3>
                    <span className="draft-meta">
                      {draft.platform} - {draft.problem_id}
                    </span>
                  </div>
                </div>

                {draft.tags && draft.tags.length > 0 && (
                  <div className="draft-tags">
                    {draft.tags.map((tag, idx) => (
                      <span key={idx} className="tag">{tag}</span>
                    ))}
                  </div>
                )}

                <div className="draft-info">
                  <div className="info-item">
                    <span className="label">Language:</span>
                    <span className="value">{draft.language || 'N/A'}</span>
                  </div>
                  <div className="info-item">
                    <span className="label">Created:</span>
                    <span className="value">{new Date(draft.created_at).toLocaleString()}</span>
                  </div>
                </div>

                <div className="draft-actions">
                  <button
                    onClick={() => handleLoadDraft(draft)}
                    className="load-button"
                  >
                    Continue Editing
                  </button>
                  <button
                    onClick={() => handleGenerateScript(draft)}
                    className="generate-button"
                    disabled={executingJobs[`draft-${draft.id}`] || !draft.solution_code || !draft.constraints}
                  >
                    {executingJobs[`draft-${draft.id}`] ? 'Generating...' : 'Generate Script'}
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

export default Jobs;
