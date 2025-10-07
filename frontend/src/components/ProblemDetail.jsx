import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Paper,
  Chip,
  CircularProgress,
  Card,
  CardContent,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Divider,
  Grid,
  Dialog,
  DialogTitle,
  DialogContent,
  IconButton,
  Snackbar,
  Alert
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  Edit as EditIcon,
  PlayArrow as PlayArrowIcon,
  ExpandMore as ExpandMoreIcon,
  Code as CodeIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Schedule as ScheduleIcon,
  Close as CloseIcon,
  Download as DownloadIcon,
  Delete as DeleteIcon,
  ContentCopy as ContentCopyIcon
} from '@mui/icons-material';
import { apiGet, apiPost } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';

function ProblemDetail({ platform, problemId, onBack }) {
  const [problem, setProblem] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generatingScript, setGeneratingScript] = useState(false);
  const [selectedJob, setSelectedJob] = useState(null);
  const [showScript, setShowScript] = useState(false);
  const [executingScript, setExecutingScript] = useState(false);
  const [generatingOutputs, setGeneratingOutputs] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteJobDialogOpen, setDeleteJobDialogOpen] = useState(false);
  const [jobToDelete, setJobToDelete] = useState(null);
  const [deletingJob, setDeletingJob] = useState(false);
  const [deletingJobIds, setDeletingJobIds] = useState(new Set());

  const fetchProblemAndJobs = async () => {
    try {
      // Fetch problem by platform and problem_id
      const problemResponse = await apiGet(`${API_ENDPOINTS.problems}${platform}/${problemId}/`);
      if (problemResponse.ok) {
        const data = await problemResponse.json();
        // Decode base64 solution code
        if (data.solution_code) {
          try {
            data.solution_code = atob(data.solution_code);
          } catch (e) {
            console.error('Failed to decode solution code:', e);
          }
        }
        setProblem(data);
      } else {
        setProblem(null);
      }

      // Fetch jobs filtered by platform and problem_id
      const jobsResponse = await apiGet(`${API_ENDPOINTS.jobs}?platform=${platform}&problem_id=${problemId}`);
      if (jobsResponse.ok) {
        const data = await jobsResponse.json();
        setJobs(data.jobs || []);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
      setProblem(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProblemAndJobs();
    const interval = setInterval(fetchProblemAndJobs, 5000);
    return () => clearInterval(interval);
  }, [platform, problemId]);

  const showSnackbar = (message, severity = 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  const handleGenerateScript = async () => {
    if (!problem.solution_code || !problem.constraints) {
      showSnackbar('Problem must have solution code and constraints to generate script', 'warning');
      return;
    }

    setGeneratingScript(true);

    try {
      const response = await apiPost(API_ENDPOINTS.generateTestCases, {
        platform: problem.platform,
        problem_id: problem.problem_id,
        title: problem.title,
        problem_url: problem.problem_url || '',
        tags: problem.tags || [],
        solution_code: problem.solution_code,
        language: problem.language || 'python',
        constraints: problem.constraints,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to create job');
      }

      const data = await response.json();
      showSnackbar('Script generation job created successfully!', 'success');
      fetchProblemAndJobs();
    } catch (error) {
      console.error('Error generating script:', error);
      showSnackbar('An error occurred while generating script: ' + error.message, 'error');
    } finally {
      setGeneratingScript(false);
    }
  };

  const handleViewScript = async (job) => {
    try {
      const response = await apiGet(API_ENDPOINTS.jobDetail(job.id));
      if (response.ok) {
        const data = await response.json();
        setSelectedJob(data);
        setShowScript(true);
      }
    } catch (error) {
      console.error('Error fetching job details:', error);
      showSnackbar('Failed to load script', 'error');
    }
  };

  const handleExecuteScript = async () => {
    if (!selectedJob || !selectedJob.generator_code) return;

    setExecutingScript(true);
    try {
      // First, execute the script to get test inputs
      const executeResponse = await apiPost(API_ENDPOINTS.executeTestCases, {
        generator_code: selectedJob.generator_code,
        num_cases: 20
      });

      if (!executeResponse.ok) {
        const errorData = await executeResponse.json();
        throw new Error(errorData.error || 'Failed to execute script');
      }

      const executeData = await executeResponse.json();

      // Then save the test inputs to the problem
      const saveResponse = await apiPost('/register/save-test-inputs/', {
        platform: problem.platform,
        problem_id: problem.problem_id,
        test_inputs: executeData.test_cases
      });

      if (!saveResponse.ok) {
        const errorData = await saveResponse.json();
        throw new Error(errorData.error || 'Failed to save test cases');
      }

      // If solution code exists, generate outputs immediately
      if (problem.solution_code) {
        const outputResponse = await apiPost('/register/generate-outputs/', {
          platform: problem.platform,
          problem_id: problem.problem_id
        });

        if (!outputResponse.ok) {
          const errorData = await outputResponse.json();
          throw new Error(errorData.error || 'Failed to generate outputs');
        }

        showSnackbar(`Successfully generated ${executeData.count} test cases with outputs`, 'success');
      } else {
        showSnackbar(`Successfully generated ${executeData.count} test case inputs (outputs can be generated later)`, 'success');
      }

      setShowScript(false);
      fetchProblemAndJobs();
    } catch (error) {
      console.error('Error executing script:', error);
      showSnackbar('Failed to execute script: ' + error.message, 'error');
    } finally {
      setExecutingScript(false);
    }
  };

  const handleGenerateOutputs = async () => {
    if (!problem || !problem.solution_code) {
      showSnackbar('Need solution code to generate outputs', 'warning');
      return;
    }

    setGeneratingOutputs(true);
    try {
      // Start the async task
      const response = await apiPost('/register/generate-outputs/', {
        platform: problem.platform,
        problem_id: problem.problem_id
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to start output generation');
      }

      const data = await response.json();
      const taskId = data.task_id;

      showSnackbar('Output generation started...', 'info');

      // Poll for task completion
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await apiGet(`/tasks/${taskId}/`);
          if (!statusResponse.ok) {
            clearInterval(pollInterval);
            setGeneratingOutputs(false);
            return;
          }

          const statusData = await statusResponse.json();

          if (statusData.status === 'COMPLETED') {
            clearInterval(pollInterval);
            setGeneratingOutputs(false);
            showSnackbar(`Outputs generated successfully for ${statusData.result.count} test cases`, 'success');
            fetchProblemAndJobs();
          } else if (statusData.status === 'FAILED') {
            clearInterval(pollInterval);
            setGeneratingOutputs(false);
            showSnackbar(`Failed to generate outputs: ${statusData.error}`, 'error');
          }
        } catch (pollError) {
          clearInterval(pollInterval);
          setGeneratingOutputs(false);
          showSnackbar('Error checking task status', 'error');
        }
      }, 2000); // Poll every 2 seconds

    } catch (error) {
      console.error('Error generating outputs:', error);
      showSnackbar('Failed to generate outputs: ' + error.message, 'error');
      setGeneratingOutputs(false);
    }
  };

  const handleRegenerateScript = async () => {
    if (!problem.solution_code || !problem.constraints) {
      showSnackbar('Problem must have solution code and constraints to generate script', 'warning');
      return;
    }

    setGeneratingScript(true);

    try {
      const response = await apiPost(API_ENDPOINTS.generateTestCases, {
        platform: problem.platform,
        problem_id: problem.problem_id,
        title: problem.title,
        problem_url: problem.problem_url || '',
        tags: problem.tags || [],
        solution_code: problem.solution_code,
        language: problem.language || 'python',
        constraints: problem.constraints,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to create job');
      }

      const data = await response.json();
      showSnackbar('New script generation job created successfully!', 'success');
      fetchProblemAndJobs();
    } catch (error) {
      console.error('Error generating script:', error);
      showSnackbar('An error occurred while generating script: ' + error.message, 'error');
    } finally {
      setGeneratingScript(false);
    }
  };

  const handleComplete = async () => {
    if (!problem || !problem.test_cases || problem.test_cases.length === 0) {
      showSnackbar('Need test cases with outputs to complete registration', 'warning');
      return;
    }

    // Check if all test cases have outputs
    const hasEmptyOutputs = problem.test_cases.some(tc => !tc.output || tc.output.trim() === '');
    if (hasEmptyOutputs) {
      showSnackbar('Please generate outputs for all test cases first', 'warning');
      return;
    }

    try {
      const response = await apiPost('/problems/toggle-completion/', {
        platform: problem.platform,
        problem_id: problem.problem_id,
        is_completed: true
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to complete problem');
      }

      showSnackbar('Problem marked as completed!', 'success');
      fetchProblemAndJobs();
    } catch (error) {
      console.error('Error completing problem:', error);
      showSnackbar('Failed to complete problem: ' + error.message, 'error');
    }
  };

  const handleMakeDraft = async () => {
    try {
      const response = await apiPost('/problems/toggle-completion/', {
        platform: problem.platform,
        problem_id: problem.problem_id,
        is_completed: false
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to make draft');
      }

      showSnackbar('Problem marked as draft!', 'success');
      fetchProblemAndJobs();
    } catch (error) {
      console.error('Error making draft:', error);
      showSnackbar('Failed to make draft: ' + error.message, 'error');
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/problems/${platform}/${problemId}/`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to delete problem');
      }

      showSnackbar('Problem deleted successfully!', 'success');
      setDeleteDialogOpen(false);

      // Navigate back after successful deletion
      setTimeout(() => {
        if (onBack) {
          onBack();
        } else {
          window.location.href = '/problems';
        }
      }, 1000);
    } catch (error) {
      console.error('Error deleting problem:', error);
      showSnackbar('Failed to delete problem: ' + error.message, 'error');
      setDeleting(false);
      setDeleteDialogOpen(false);
    }
  };

  const handleDeleteJob = async () => {
    if (!jobToDelete) return;

    const jobId = jobToDelete.id;
    setDeletingJob(true);

    // Add to deleting set immediately
    setDeletingJobIds(prev => new Set(prev).add(jobId));

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/register/jobs/${jobId}/`, {
        method: 'DELETE',
        credentials: 'include'
      });

      if (!response.ok) {
        let errorMessage = 'Failed to delete job';
        try {
          const errorData = await response.json();
          errorMessage = errorData.error || errorMessage;
        } catch (jsonError) {
          console.error('Failed to parse error response:', jsonError);
          errorMessage = `HTTP ${response.status}: ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }

      showSnackbar('Generator script deleted successfully!', 'success');
      setDeleteJobDialogOpen(false);
      setJobToDelete(null);

      // Refresh jobs list
      await fetchProblemAndJobs();
    } catch (error) {
      console.error('Error deleting job:', error);
      showSnackbar(error.message || 'Failed to delete job', 'error');

      // Remove from deleting set on error
      setDeletingJobIds(prev => {
        const newSet = new Set(prev);
        newSet.delete(jobId);
        return newSet;
      });
    } finally {
      setDeletingJob(false);
    }
  };

  const handleCopyScript = (script) => {
    navigator.clipboard.writeText(script).then(() => {
      showSnackbar('Script copied to clipboard!', 'success');
    }).catch((error) => {
      console.error('Failed to copy script:', error);
      showSnackbar('Failed to copy script to clipboard', 'error');
    });
  };

  const truncateText = (text, maxLines = 10, maxChars = 1000) => {
    if (!text) return { text: '', isTruncated: false };

    // First check character limit
    if (text.length > maxChars) {
      return {
        text: text.substring(0, maxChars) + '\n...',
        isTruncated: true
      };
    }

    // Then check line limit
    const lines = text.split('\n');
    if (lines.length <= maxLines) {
      return { text, isTruncated: false };
    }

    return {
      text: lines.slice(0, maxLines).join('\n') + '\n...',
      isTruncated: true
    };
  };

  const downloadText = (text, filename) => {
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'COMPLETED':
        return <CheckCircleIcon color="success" />;
      case 'FAILED':
        return <ErrorIcon color="error" />;
      case 'PROCESSING':
        return <CircularProgress size={20} />;
      default:
        return <ScheduleIcon color="warning" />;
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!problem) {
    return (
      <Box>
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6" color="text.primary">Problem not found</Typography>
        </Paper>
      </Box>
    );
  }

  const isDraft = !problem.test_case_count || problem.test_case_count === 0;
  const isCompleted = problem.is_completed;

  return (
    <Box>
      <Box sx={{
        display: 'flex',
        flexDirection: { xs: 'column', sm: 'row' },
        justifyContent: 'space-between',
        alignItems: { xs: 'stretch', sm: 'center' },
        mb: 3,
        gap: 2
      }}>
        <Box sx={{
          display: 'flex',
          flexDirection: { xs: 'column', sm: 'row' },
          gap: 1,
          ml: { xs: 0, sm: 'auto' }
        }}>
          <Button
            variant="outlined"
            startIcon={<EditIcon sx={{ fontSize: { xs: '1.125rem', sm: '1.25rem' } }} />}
            onClick={() => window.location.href = `/register?draft_id=${problem.id}`}
            sx={{
              fontSize: { xs: '0.813rem', sm: '0.875rem' },
              py: { xs: 1, sm: 0.75 }
            }}
          >
            Edit Problem
          </Button>
          <Button
            variant="outlined"
            color="error"
            startIcon={<DeleteIcon sx={{ fontSize: { xs: '1.125rem', sm: '1.25rem' } }} />}
            onClick={() => setDeleteDialogOpen(true)}
            sx={{
              fontSize: { xs: '0.813rem', sm: '0.875rem' },
              py: { xs: 1, sm: 0.75 }
            }}
          >
            Delete
          </Button>
          {!isDraft && !isCompleted && (
            <Button
              variant="outlined"
              startIcon={<PlayArrowIcon sx={{ fontSize: { xs: '1.125rem', sm: '1.25rem' } }} />}
              onClick={handleRegenerateScript}
              disabled={generatingScript || !problem.solution_code || !problem.constraints}
              sx={{
                fontSize: { xs: '0.813rem', sm: '0.875rem' },
                py: { xs: 1, sm: 0.75 }
              }}
            >
              {generatingScript ? 'Generating...' : 'Regenerate Script'}
            </Button>
          )}
          {!isDraft && problem.test_cases && problem.test_cases.length > 0 && !isCompleted && (
            <Button
              variant="outlined"
              onClick={handleGenerateOutputs}
              disabled={generatingOutputs || !problem.solution_code}
              sx={{
                fontSize: { xs: '0.813rem', sm: '0.875rem' },
                py: { xs: 1, sm: 0.75 }
              }}
            >
              {generatingOutputs ? 'Generating Outputs...' : 'Regenerate Outputs'}
            </Button>
          )}
          {isDraft && !isCompleted && (
            <Button
              variant="contained"
              startIcon={<PlayArrowIcon sx={{ fontSize: { xs: '1.125rem', sm: '1.25rem' } }} />}
              onClick={handleGenerateScript}
              disabled={generatingScript || !problem.solution_code || !problem.constraints}
              sx={{
                fontSize: { xs: '0.813rem', sm: '0.875rem' },
                py: { xs: 1, sm: 0.75 }
              }}
            >
              {generatingScript ? 'Generating...' : 'Generate Script'}
            </Button>
          )}
          {!isDraft && !isCompleted && (
            <Button
              variant="contained"
              color="success"
              onClick={handleComplete}
              sx={{
                fontSize: { xs: '0.813rem', sm: '0.875rem' },
                py: { xs: 1, sm: 0.75 }
              }}
            >
              Complete
            </Button>
          )}
          {isCompleted && (
            <Button
              variant="outlined"
              onClick={handleMakeDraft}
              sx={{
                fontSize: { xs: '0.813rem', sm: '0.875rem' },
                py: { xs: 1, sm: 0.75 }
              }}
            >
              Make Draft
            </Button>
          )}
        </Box>
      </Box>

      <Paper sx={{ p: { xs: 2, sm: 3 }, mb: 3 }}>
        <Typography variant="h4" gutterBottom sx={{
          color: 'text.primary',
          fontWeight: 600,
          fontSize: { xs: '1.5rem', sm: '1.75rem', md: '2.125rem' }
        }}>
          {problem.title}
        </Typography>
        <Typography variant="body1" sx={{
          color: 'text.secondary',
          mb: 2,
          fontSize: { xs: '0.875rem', sm: '1rem' }
        }}>
          {problem.platform === 'baekjoon' ? 'Baekjoon' : 'Codeforces'} - {problem.problem_id}
        </Typography>

        {problem.tags && problem.tags.length > 0 && (
          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mb: 2 }}>
            {problem.tags.map((tag, idx) => (
              <Chip
                key={idx}
                label={tag}
                size="small"
                color="primary"
                variant="outlined"
              />
            ))}
          </Box>
        )}

        <Divider sx={{ my: 2 }} />

        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <Typography variant="body2" color="text.secondary">
              <strong>Platform:</strong> {problem.platform === 'baekjoon' ? 'Baekjoon' : 'Codeforces'}
            </Typography>
          </Grid>
          <Grid item xs={12} md={6}>
            <Typography variant="body2" color="text.secondary">
              <strong>Problem ID:</strong> {problem.problem_id}
            </Typography>
          </Grid>
          <Grid item xs={12} md={6}>
            <Typography variant="body2" color="text.secondary">
              <strong>Language:</strong> {problem.language || 'N/A'}
            </Typography>
          </Grid>
          <Grid item xs={12} md={6}>
            <Typography variant="body2" color="text.secondary">
              <strong>Test Cases:</strong> {problem.test_case_count || 0}
              {isDraft && <Chip label="Draft" size="small" color="warning" sx={{ ml: 1 }} />}
            </Typography>
          </Grid>
        </Grid>

        {problem.constraints && (
          <>
            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600, color: 'text.primary' }}>
              Constraints:
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-wrap' }}>
              {problem.constraints}
            </Typography>
          </>
        )}

        {problem.solution_code && (
          <>
            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600, color: 'text.primary' }}>
              Solution Code:
            </Typography>
            <Paper
              sx={{
                p: 2,
                backgroundColor: '#f5f5f5',
                fontFamily: 'monospace',
                fontSize: '0.875rem',
                overflowX: 'auto',
                border: '1px solid',
                borderColor: 'divider'
              }}
            >
              <pre style={{ margin: 0, color: '#333' }}>
                {problem.solution_code}
              </pre>
            </Paper>
          </>
        )}

        {!isDraft && problem.test_cases && problem.test_cases.length > 0 && (
          <>
            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600, color: 'text.primary' }}>
              Test Cases ({problem.test_cases.length}):
            </Typography>
            {problem.test_cases.map((tc, idx) => {
              const truncatedInput = truncateText(tc.input);
              const truncatedOutput = truncateText(tc.output);

              return (
                <Accordion
                  key={idx}
                  sx={{ mb: 1, '&:before': { display: 'none' } }}
                >
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography>Test Case #{idx + 1}</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Box sx={{
                      display: 'flex',
                      flexDirection: { xs: 'column', md: 'row' },
                      gap: 2
                    }}>
                      <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 50%' }, minWidth: 0 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                          <Typography variant="subtitle2" color="text.primary" sx={{
                            fontSize: { xs: '0.813rem', sm: '0.875rem' }
                          }}>Input:</Typography>
                          <IconButton
                            size="small"
                            onClick={() => downloadText(tc.input, `test_${idx + 1}_input.txt`)}
                            title="Download Input"
                          >
                            <DownloadIcon fontSize="small" />
                          </IconButton>
                        </Box>
                        <Paper sx={{
                          p: { xs: 1, sm: 1.5 },
                          backgroundColor: '#f5f5f5',
                          border: '1px solid',
                          borderColor: 'divider',
                          maxHeight: '200px',
                          minHeight: '100px',
                          overflow: 'auto'
                        }}>
                          <pre style={{
                            margin: 0,
                            fontSize: window.innerWidth < 600 ? '0.75rem' : '0.875rem',
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-word',
                            color: '#333',
                            overflowWrap: 'break-word'
                          }}>
                            {truncatedInput.text}
                          </pre>
                          {truncatedInput.isTruncated && (
                            <Typography variant="caption" color="text.secondary" sx={{
                              mt: 1,
                              display: 'block',
                              fontSize: { xs: '0.688rem', sm: '0.75rem' }
                            }}>
                              (Truncated - download to see full content)
                            </Typography>
                          )}
                        </Paper>
                      </Box>
                      <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 50%' }, minWidth: 0 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                          <Typography variant="subtitle2" color="text.primary" sx={{
                            fontSize: { xs: '0.813rem', sm: '0.875rem' }
                          }}>Expected Output:</Typography>
                          <IconButton
                            size="small"
                            onClick={() => downloadText(tc.output, `test_${idx + 1}_output.txt`)}
                            title="Download Output"
                          >
                            <DownloadIcon fontSize="small" />
                          </IconButton>
                        </Box>
                        <Paper sx={{
                          p: { xs: 1, sm: 1.5 },
                          backgroundColor: '#f5f5f5',
                          border: '1px solid',
                          borderColor: 'divider',
                          maxHeight: '200px',
                          minHeight: '100px',
                          overflow: 'auto'
                        }}>
                          <pre style={{
                            margin: 0,
                            fontSize: window.innerWidth < 600 ? '0.75rem' : '0.875rem',
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-word',
                            color: '#333',
                            overflowWrap: 'break-word'
                          }}>
                            {truncatedOutput.text}
                          </pre>
                          {truncatedOutput.isTruncated && (
                            <Typography variant="caption" color="text.secondary" sx={{
                              mt: 1,
                              display: 'block',
                              fontSize: { xs: '0.688rem', sm: '0.75rem' }
                            }}>
                              (Truncated - download to see full content)
                            </Typography>
                          )}
                        </Paper>
                      </Box>
                    </Box>
                  </AccordionDetails>
                </Accordion>
              );
            })}
          </>
        )}
      </Paper>

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, color: 'text.primary' }}>
          Script Generation History
        </Typography>

        {jobs.filter(job => !deletingJobIds.has(job.id)).length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <CodeIcon sx={{ fontSize: 48, color: 'action.disabled', mb: 1 }} />
            <Typography color="text.secondary">
              No script generation jobs yet
            </Typography>
          </Box>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {jobs.filter(job => !deletingJobIds.has(job.id)).map((job) => (
              <Card key={job.id} variant="outlined">
                <CardContent sx={{ py: 1.5, px: 2, '&:last-child': { pb: 1.5 } }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      {getStatusIcon(job.status)}
                      <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                        {new Date(job.created_at).toLocaleString()}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                      {job.status === 'COMPLETED' && (
                        <Button
                          variant="outlined"
                          size="small"
                          startIcon={<CodeIcon />}
                          onClick={() => handleViewScript(job)}
                        >
                          View Script
                        </Button>
                      )}
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => {
                          setJobToDelete(job);
                          setDeleteJobDialogOpen(true);
                        }}
                        title="Delete Job"
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Box>
                    {job.error_message && (
                      <Typography variant="caption" color="error" sx={{ width: '100%' }}>
                        Error: {job.error_message}
                      </Typography>
                    )}
                  </Box>
                </CardContent>
              </Card>
            ))}
          </Box>
        )}
      </Paper>

      {/* Script Dialog */}
      <Dialog
        open={showScript}
        onClose={() => setShowScript(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Generator Script
          <IconButton
            onClick={() => setShowScript(false)}
            sx={{ position: 'absolute', right: 8, top: 8 }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          {selectedJob && selectedJob.generator_code && (
            <>
              <Paper
                sx={{
                  p: 2,
                  backgroundColor: '#f5f5f5',
                  fontFamily: 'monospace',
                  fontSize: '0.875rem',
                  overflowX: 'auto',
                  border: '1px solid',
                  borderColor: 'divider',
                  mt: 2,
                  mb: 2
                }}
              >
                <pre style={{ margin: 0, color: '#333' }}>
                  {selectedJob.generator_code}
                </pre>
              </Paper>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1, flexWrap: 'wrap' }}>
                <Button
                  variant="outlined"
                  startIcon={<ContentCopyIcon />}
                  onClick={() => handleCopyScript(selectedJob.generator_code)}
                >
                  Copy to Clipboard
                </Button>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Button
                    variant="outlined"
                    onClick={() => setShowScript(false)}
                  >
                    Close
                  </Button>
                  <Button
                    variant="contained"
                    startIcon={<PlayArrowIcon />}
                    onClick={handleExecuteScript}
                    disabled={executingScript}
                  >
                    {executingScript ? 'Executing...' : 'Execute Script'}
                  </Button>
                </Box>
              </Box>
            </>
          )}
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => !deleting && setDeleteDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          Confirm Delete
          <IconButton
            onClick={() => setDeleteDialogOpen(false)}
            disabled={deleting}
            sx={{ position: 'absolute', right: 8, top: 8 }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          <Typography variant="body1" sx={{ mb: 2 }}>
            Are you sure you want to delete this problem?
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            <strong>{problem?.title}</strong> ({problem?.platform} - {problem?.problem_id})
          </Typography>
          <Typography variant="body2" color="error">
            This action cannot be undone. All test cases and associated data will be permanently deleted.
          </Typography>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, mt: 3 }}>
            <Button
              variant="outlined"
              onClick={() => setDeleteDialogOpen(false)}
              disabled={deleting}
            >
              Cancel
            </Button>
            <Button
              variant="contained"
              color="error"
              startIcon={<DeleteIcon />}
              onClick={handleDelete}
              disabled={deleting}
            >
              {deleting ? 'Deleting...' : 'Delete Problem'}
            </Button>
          </Box>
        </DialogContent>
      </Dialog>

      {/* Delete Job Confirmation Dialog */}
      <Dialog
        open={deleteJobDialogOpen}
        onClose={() => !deletingJob && setDeleteJobDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          Confirm Delete Job
          <IconButton
            onClick={() => setDeleteJobDialogOpen(false)}
            disabled={deletingJob}
            sx={{ position: 'absolute', right: 8, top: 8 }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          <Typography variant="body1" sx={{ mb: 2 }}>
            Are you sure you want to delete this generator script job?
          </Typography>
          {jobToDelete && (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Created: <strong>{new Date(jobToDelete.created_at).toLocaleString()}</strong>
              <br />
              Status: <strong>{jobToDelete.status}</strong>
            </Typography>
          )}
          <Typography variant="body2" color="error">
            This action cannot be undone. The generator script will be permanently deleted.
          </Typography>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, mt: 3 }}>
            <Button
              variant="outlined"
              onClick={() => {
                setDeleteJobDialogOpen(false);
                setJobToDelete(null);
              }}
              disabled={deletingJob}
            >
              Cancel
            </Button>
            <Button
              variant="contained"
              color="error"
              startIcon={<DeleteIcon />}
              onClick={handleDeleteJob}
              disabled={deletingJob}
            >
              {deletingJob ? 'Deleting...' : 'Delete Job'}
            </Button>
          </Box>
        </DialogContent>
      </Dialog>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}

export default ProblemDetail;
