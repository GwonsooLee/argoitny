import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Paper,
  Chip,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  IconButton
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Refresh as RefreshIcon,
  Download as DownloadIcon,
  ExpandMore as ExpandMoreIcon
} from '@mui/icons-material';
import { apiGet, apiPost } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';

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
            Job Details
          </Typography>
          <Button
            variant="outlined"
            startIcon={<ArrowBackIcon />}
            onClick={onBack}
            sx={{ fontSize: { xs: '0.813rem', sm: '0.875rem' } }}
          >
            Back to Jobs
          </Button>
        </Box>
        <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', py: 8 }}>
          <CircularProgress />
          <Typography variant="body1" sx={{ ml: 2 }}>
            Loading job details...
          </Typography>
        </Box>
      </Box>
    );
  }

  if (error) {
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
            Job Details
          </Typography>
          <Button
            variant="outlined"
            startIcon={<ArrowBackIcon />}
            onClick={onBack}
            sx={{ fontSize: { xs: '0.813rem', sm: '0.875rem' } }}
          >
            Back to Jobs
          </Button>
        </Box>
        <Paper sx={{ p: { xs: 2, sm: 3 }, backgroundColor: 'error.lighter', border: '1px solid', borderColor: 'error.light' }}>
          <Typography color="error">{error}</Typography>
        </Paper>
      </Box>
    );
  }

  if (!job) {
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
            Job Details
          </Typography>
          <Button
            variant="outlined"
            startIcon={<ArrowBackIcon />}
            onClick={onBack}
            sx={{ fontSize: { xs: '0.813rem', sm: '0.875rem' } }}
          >
            Back to Jobs
          </Button>
        </Box>
        <Paper sx={{ p: { xs: 2, sm: 3 } }}>
          <Typography>Job not found</Typography>
        </Paper>
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
          Job Details
        </Typography>
        <Box sx={{
          display: 'flex',
          flexDirection: { xs: 'column', sm: 'row' },
          gap: 1,
          width: { xs: '100%', sm: 'auto' }
        }}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={handleRegenerateScript}
            disabled={regenerating}
            sx={{
              fontSize: { xs: '0.75rem', sm: '0.813rem' }
            }}
          >
            {regenerating ? 'Regenerating...' : 'Regenerate Script'}
          </Button>
          <Button
            variant="outlined"
            startIcon={<ArrowBackIcon />}
            onClick={onBack}
            sx={{ fontSize: { xs: '0.75rem', sm: '0.813rem' } }}
          >
            Back to Jobs
          </Button>
        </Box>
      </Box>

      <Paper sx={{ p: { xs: 2, sm: 3 }, mb: 3 }}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <Box>
            <Typography variant="caption" color="text.secondary" sx={{
              fontWeight: 600,
              textTransform: 'uppercase',
              fontSize: { xs: '0.688rem', sm: '0.75rem' }
            }}>
              Job ID
            </Typography>
            <Typography variant="body2" sx={{ fontSize: { xs: '0.875rem', sm: '1rem' } }}>
              {job.id}
            </Typography>
          </Box>

          <Box>
            <Typography variant="caption" color="text.secondary" sx={{
              fontWeight: 600,
              textTransform: 'uppercase',
              fontSize: { xs: '0.688rem', sm: '0.75rem' }
            }}>
              Problem
            </Typography>
            <Typography variant="body2" sx={{ fontSize: { xs: '0.875rem', sm: '1rem' } }}>
              {job.title} ({job.platform} - {job.problem_id})
            </Typography>
          </Box>

          <Box>
            <Typography variant="caption" color="text.secondary" sx={{
              fontWeight: 600,
              textTransform: 'uppercase',
              fontSize: { xs: '0.688rem', sm: '0.75rem' },
              mb: 0.5,
              display: 'block'
            }}>
              Status
            </Typography>
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

          <Box sx={{
            display: 'flex',
            flexDirection: { xs: 'column', sm: 'row' },
            gap: { xs: 2, sm: 4 }
          }}>
            <Box>
              <Typography variant="caption" color="text.secondary" sx={{
                fontWeight: 600,
                textTransform: 'uppercase',
                fontSize: { xs: '0.688rem', sm: '0.75rem' }
              }}>
                Created
              </Typography>
              <Typography variant="body2" sx={{ fontSize: { xs: '0.875rem', sm: '1rem' } }}>
                {new Date(job.created_at).toLocaleString()}
              </Typography>
            </Box>

            <Box>
              <Typography variant="caption" color="text.secondary" sx={{
                fontWeight: 600,
                textTransform: 'uppercase',
                fontSize: { xs: '0.688rem', sm: '0.75rem' }
              }}>
                Updated
              </Typography>
              <Typography variant="body2" sx={{ fontSize: { xs: '0.875rem', sm: '1rem' } }}>
                {new Date(job.updated_at).toLocaleString()}
              </Typography>
            </Box>
          </Box>

          {job.tags && job.tags.length > 0 && (
            <Box>
              <Typography variant="caption" color="text.secondary" sx={{
                fontWeight: 600,
                textTransform: 'uppercase',
                fontSize: { xs: '0.688rem', sm: '0.75rem' },
                mb: 0.5,
                display: 'block'
              }}>
                Tags
              </Typography>
              <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
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
            </Box>
          )}
        </Box>
      </Paper>

      {job.error_message && (
        <Paper sx={{
          p: { xs: 2, sm: 3 },
          mb: 3,
          backgroundColor: 'error.lighter',
          border: '1px solid',
          borderColor: 'error.light'
        }}>
          <Typography variant="h6" sx={{
            fontWeight: 600,
            mb: 2,
            fontSize: { xs: '1rem', sm: '1.125rem', md: '1.25rem' }
          }}>
            Error
          </Typography>
          <Paper sx={{
            p: { xs: 1, sm: 1.5 },
            backgroundColor: 'white',
            fontFamily: 'monospace',
            fontSize: { xs: '0.75rem', sm: '0.875rem' },
            overflowX: 'auto'
          }}>
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
              {job.error_message}
            </pre>
          </Paper>
        </Paper>
      )}

      {job.generator_code && (
        <Paper sx={{ p: { xs: 2, sm: 3 }, mb: 3 }}>
          <Box sx={{
            display: 'flex',
            flexDirection: { xs: 'column', sm: 'row' },
            justifyContent: 'space-between',
            alignItems: { xs: 'flex-start', sm: 'center' },
            mb: 2,
            gap: 1
          }}>
            <Typography variant="h6" sx={{
              fontWeight: 600,
              fontSize: { xs: '1rem', sm: '1.125rem', md: '1.25rem' }
            }}>
              Generator Script
            </Typography>
            <Button
              variant="outlined"
              size="small"
              startIcon={<DownloadIcon />}
              onClick={downloadGeneratorCode}
              sx={{ fontSize: { xs: '0.75rem', sm: '0.813rem' } }}
            >
              Download Script
            </Button>
          </Box>
          <Paper sx={{
            p: { xs: 1, sm: 1.5 },
            backgroundColor: '#f5f5f5',
            border: '1px solid',
            borderColor: 'divider',
            maxHeight: 400,
            overflow: 'auto'
          }}>
            <pre style={{
              margin: 0,
              fontFamily: 'monospace',
              fontSize: window.innerWidth < 600 ? '0.7rem' : '0.85rem',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word'
            }}>
              {job.generator_code}
            </pre>
          </Paper>
        </Paper>
      )}

      {job.test_cases && job.test_cases.length > 0 && (
        <Paper sx={{ p: { xs: 2, sm: 3 }, mb: 3 }}>
          <Box sx={{
            display: 'flex',
            flexDirection: { xs: 'column', sm: 'row' },
            justifyContent: 'space-between',
            alignItems: { xs: 'flex-start', sm: 'center' },
            mb: 2,
            gap: 1
          }}>
            <Typography variant="h6" sx={{
              fontWeight: 600,
              fontSize: { xs: '1rem', sm: '1.125rem', md: '1.25rem' }
            }}>
              Generated Test Cases ({job.test_cases.length})
            </Typography>
            <Button
              variant="outlined"
              size="small"
              startIcon={<DownloadIcon />}
              onClick={downloadAllTestCases}
              sx={{ fontSize: { xs: '0.75rem', sm: '0.813rem' } }}
            >
              Download All
            </Button>
          </Box>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {job.test_cases.map((testCase, idx) => (
              <Accordion key={idx}>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography sx={{
                    fontWeight: 600,
                    fontSize: { xs: '0.875rem', sm: '1rem' }
                  }}>
                    Test Case {idx + 1}
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <Box sx={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    mb: 1
                  }}>
                    <Typography variant="caption" sx={{
                      fontSize: { xs: '0.688rem', sm: '0.75rem' }
                    }}>
                      Preview (truncated at 200 characters)
                    </Typography>
                    <IconButton
                      size="small"
                      onClick={() => downloadTestCase(testCase, idx)}
                    >
                      <DownloadIcon fontSize="small" />
                    </IconButton>
                  </Box>
                  <Paper sx={{
                    p: { xs: 1, sm: 1.5 },
                    backgroundColor: '#f5f5f5',
                    border: '1px solid',
                    borderColor: 'divider'
                  }}>
                    <pre style={{
                      margin: 0,
                      fontFamily: 'monospace',
                      fontSize: window.innerWidth < 600 ? '0.7rem' : '0.8rem',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word'
                    }}>
                      {truncateText(testCase, 200)}
                      {testCase.length > 200 && (
                        <Typography component="span" variant="caption" color="text.secondary">
                          {' '}(truncated)
                        </Typography>
                      )}
                    </pre>
                  </Paper>
                </AccordionDetails>
              </Accordion>
            ))}
          </Box>
        </Paper>
      )}

      {job.test_case_error && (
        <Paper sx={{
          p: { xs: 2, sm: 3 },
          mb: 3,
          backgroundColor: 'error.lighter',
          border: '1px solid',
          borderColor: 'error.light'
        }}>
          <Typography variant="h6" sx={{
            fontWeight: 600,
            mb: 2,
            fontSize: { xs: '1rem', sm: '1.125rem', md: '1.25rem' }
          }}>
            Test Case Generation Error
          </Typography>
          <Paper sx={{
            p: { xs: 1, sm: 1.5 },
            backgroundColor: 'white',
            fontFamily: 'monospace',
            fontSize: { xs: '0.75rem', sm: '0.875rem' },
            overflowX: 'auto'
          }}>
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
              {job.test_case_error}
            </pre>
          </Paper>
        </Paper>
      )}
    </Box>
  );
}

export default JobDetail;
