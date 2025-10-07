import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Tabs,
  Tab,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  IconButton,
  Paper
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  PlayArrow as PlayArrowIcon,
  Edit as EditIcon,
  Visibility as VisibilityIcon
} from '@mui/icons-material';
import { apiGet, apiPost } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';

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

  if (loading) {
    return (
      <Box sx={{ px: { xs: 2, sm: 3 } }}>
        <Box sx={{
          display: 'flex',
          flexDirection: { xs: 'column', sm: 'row' },
          justifyContent: 'space-between',
          alignItems: { xs: 'flex-start', sm: 'center' },
          mb: 3,
          gap: 2
        }}>
          <Typography variant="h4" sx={{
            fontWeight: 600,
            fontSize: { xs: '1.5rem', sm: '1.75rem', md: '2.125rem' }
          }}>
            Jobs & Drafts
          </Typography>
          <Button
            variant="outlined"
            startIcon={<ArrowBackIcon />}
            onClick={onBack}
            sx={{ fontSize: { xs: '0.813rem', sm: '0.875rem' } }}
          >
            Back
          </Button>
        </Box>
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{ px: { xs: 2, sm: 3 } }}>
      <Box sx={{
        display: 'flex',
        flexDirection: { xs: 'column', sm: 'row' },
        justifyContent: 'space-between',
        alignItems: { xs: 'flex-start', sm: 'center' },
        mb: 3,
        gap: 2
      }}>
        <Typography variant="h4" sx={{
          fontWeight: 600,
          fontSize: { xs: '1.5rem', sm: '1.75rem', md: '2.125rem' }
        }}>
          Jobs & Drafts
        </Typography>
        <Button
          variant="outlined"
          startIcon={<ArrowBackIcon />}
          onClick={onBack}
          sx={{ fontSize: { xs: '0.813rem', sm: '0.875rem' } }}
        >
          Back
        </Button>
      </Box>

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs
          value={activeTab === 'jobs' ? 0 : 1}
          onChange={(e, newValue) => setActiveTab(newValue === 0 ? 'jobs' : 'drafts')}
          variant="fullWidth"
          sx={{
            '& .MuiTab-root': {
              fontSize: { xs: '0.813rem', sm: '0.875rem', md: '1rem' }
            }
          }}
        >
          <Tab label={`Script Generation Jobs (${jobs.length})`} />
          <Tab label={`Drafts (${drafts.length})`} />
        </Tabs>
      </Box>

      {activeTab === 'jobs' && (
        <Box>
          {jobs.length === 0 ? (
            <Paper sx={{ p: { xs: 3, sm: 4 }, textAlign: 'center' }}>
              <Typography variant="body1" color="text.secondary">
                No jobs found
              </Typography>
            </Paper>
          ) : (
            jobs.map((job) => (
              <Card key={job.id} sx={{ mb: 2 }}>
                <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
                  <Box sx={{
                    display: 'flex',
                    flexDirection: { xs: 'column', sm: 'row' },
                    justifyContent: 'space-between',
                    alignItems: { xs: 'flex-start', sm: 'center' },
                    mb: 2,
                    gap: 1
                  }}>
                    <Box>
                      <Typography variant="h6" sx={{
                        fontWeight: 600,
                        fontSize: { xs: '1rem', sm: '1.125rem', md: '1.25rem' }
                      }}>
                        {job.title}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" sx={{
                        fontSize: { xs: '0.813rem', sm: '0.875rem' }
                      }}>
                        {job.platform} - {job.problem_id}
                      </Typography>
                    </Box>
                    <Chip
                      label={job.status}
                      color={
                        job.status === 'COMPLETED' ? 'success' :
                        job.status === 'FAILED' ? 'error' :
                        job.status === 'PROCESSING' ? 'info' : 'warning'
                      }
                      size="small"
                      sx={{ fontSize: { xs: '0.75rem', sm: '0.813rem' } }}
                    />
                  </Box>

                  {job.tags && job.tags.length > 0 && (
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mb: 2 }}>
                      {job.tags.map((tag, idx) => (
                        <Chip
                          key={idx}
                          label={tag}
                          size="small"
                          variant="outlined"
                          sx={{ fontSize: { xs: '0.688rem', sm: '0.75rem' } }}
                        />
                      ))}
                    </Box>
                  )}

                  <Box sx={{
                    display: 'flex',
                    flexDirection: { xs: 'column', sm: 'row' },
                    gap: { xs: 0.5, sm: 2 },
                    mb: 2
                  }}>
                    <Typography variant="caption" color="text.secondary" sx={{
                      fontSize: { xs: '0.75rem', sm: '0.813rem' }
                    }}>
                      <strong>Language:</strong> {job.language}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{
                      fontSize: { xs: '0.75rem', sm: '0.813rem' }
                    }}>
                      <strong>Created:</strong> {new Date(job.created_at).toLocaleString()}
                    </Typography>
                  </Box>

                  {job.status === 'COMPLETED' && (
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={() => window.location.href = `/jobs?job_id=${job.id}`}
                      sx={{
                        fontSize: { xs: '0.75rem', sm: '0.813rem' }
                      }}
                    >
                      View Details
                    </Button>
                  )}

                  {job.status === 'FAILED' && job.error_message && (
                    <Paper sx={{
                      p: { xs: 1, sm: 1.5 },
                      backgroundColor: 'error.lighter',
                      border: '1px solid',
                      borderColor: 'error.light'
                    }}>
                      <Typography variant="caption" color="error" sx={{
                        fontSize: { xs: '0.75rem', sm: '0.813rem' }
                      }}>
                        <strong>Error:</strong> {job.error_message}
                      </Typography>
                    </Paper>
                  )}

                  {job.status === 'PROCESSING' && (
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <CircularProgress size={16} />
                      <Typography variant="caption" sx={{
                        fontSize: { xs: '0.75rem', sm: '0.813rem' }
                      }}>
                        Processing... (This may take up to 60 seconds)
                      </Typography>
                    </Box>
                  )}
                </CardContent>
              </Card>
            ))
          )}
        </Box>
      )}

      {activeTab === 'drafts' && (
        <Box>
          {drafts.length === 0 ? (
            <Paper sx={{ p: { xs: 3, sm: 4 }, textAlign: 'center' }}>
              <Typography variant="body1" color="text.secondary">
                No drafts found
              </Typography>
            </Paper>
          ) : (
            drafts.map((draft) => (
              <Card key={draft.id} sx={{ mb: 2 }}>
                <CardContent sx={{ p: { xs: 2, sm: 3 } }}>
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="h6" sx={{
                      fontWeight: 600,
                      fontSize: { xs: '1rem', sm: '1.125rem', md: '1.25rem' }
                    }}>
                      {draft.title}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{
                      fontSize: { xs: '0.813rem', sm: '0.875rem' }
                    }}>
                      {draft.platform} - {draft.problem_id}
                    </Typography>
                  </Box>

                  {draft.tags && draft.tags.length > 0 && (
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mb: 2 }}>
                      {draft.tags.map((tag, idx) => (
                        <Chip
                          key={idx}
                          label={tag}
                          size="small"
                          variant="outlined"
                          sx={{ fontSize: { xs: '0.688rem', sm: '0.75rem' } }}
                        />
                      ))}
                    </Box>
                  )}

                  <Box sx={{
                    display: 'flex',
                    flexDirection: { xs: 'column', sm: 'row' },
                    gap: { xs: 0.5, sm: 2 },
                    mb: 2
                  }}>
                    <Typography variant="caption" color="text.secondary" sx={{
                      fontSize: { xs: '0.75rem', sm: '0.813rem' }
                    }}>
                      <strong>Language:</strong> {draft.language || 'N/A'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" sx={{
                      fontSize: { xs: '0.75rem', sm: '0.813rem' }
                    }}>
                      <strong>Created:</strong> {new Date(draft.created_at).toLocaleString()}
                    </Typography>
                  </Box>

                  <Box sx={{
                    display: 'flex',
                    flexDirection: { xs: 'column', sm: 'row' },
                    gap: 1
                  }}>
                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={<EditIcon sx={{ fontSize: { xs: '1rem', sm: '1.125rem' } }} />}
                      onClick={() => handleLoadDraft(draft)}
                      sx={{
                        fontSize: { xs: '0.75rem', sm: '0.813rem' },
                        flex: { xs: 1, sm: 'auto' }
                      }}
                    >
                      Continue Editing
                    </Button>
                    <Button
                      variant="contained"
                      size="small"
                      startIcon={<PlayArrowIcon sx={{ fontSize: { xs: '1rem', sm: '1.125rem' } }} />}
                      onClick={() => handleGenerateScript(draft)}
                      disabled={executingJobs[`draft-${draft.id}`] || !draft.solution_code || !draft.constraints}
                      sx={{
                        fontSize: { xs: '0.75rem', sm: '0.813rem' },
                        flex: { xs: 1, sm: 'auto' }
                      }}
                    >
                      {executingJobs[`draft-${draft.id}`] ? 'Generating...' : 'Generate Script'}
                    </Button>
                  </Box>
                </CardContent>
              </Card>
            ))
          )}
        </Box>
      )}
    </Box>
  );
}

export default Jobs;
