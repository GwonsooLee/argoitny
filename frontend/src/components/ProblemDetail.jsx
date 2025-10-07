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
  DialogActions,
  IconButton,
  Snackbar,
  Alert,
  TextField
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
  ContentCopy as ContentCopyIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import { apiGet, apiPost } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';

// Status enums
const ExtractionStatus = {
  PENDING: 'PENDING',
  PROCESSING: 'PROCESSING',
  COMPLETED: 'COMPLETED',
  FAILED: 'FAILED'
};

const JobStatus = {
  PENDING: 'PENDING',
  PROCESSING: 'PROCESSING',
  COMPLETED: 'COMPLETED',
  FAILED: 'FAILED'
};

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
  const [retryingExtraction, setRetryingExtraction] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [progressHistory, setProgressHistory] = useState([]);
  const [redirecting, setRedirecting] = useState(false);
  const [regenerateDialogOpen, setRegenerateDialogOpen] = useState(false);
  const [additionalContext, setAdditionalContext] = useState('');
  const [regenerating, setRegenerating] = useState(false);

  const fetchProblemAndJobs = async () => {
    // Don't show refreshing indicator on initial load
    if (!loading) {
      setRefreshing(true);
    }

    try {
      // Fetch problem by platform and problem_id
      const problemResponse = await apiGet(`${API_ENDPOINTS.problems}${platform}/${problemId}/`, { requireAuth: true });
      let problemData = null;

      if (problemResponse.ok) {
        problemData = await problemResponse.json();
        // Decode base64 solution code
        if (problemData.solution_code) {
          try {
            problemData.solution_code = atob(problemData.solution_code);
          } catch (e) {
            console.error('[ProblemDetail] Failed to decode solution code:', e);
          }
        }
        setProblem(problemData);
      } else if (problemResponse.status === 403) {
        // Access denied - redirect immediately
        onBack();
        return; // Don't continue with other requests
      } else {
        setProblem(null);
      }

      // Fetch jobs filtered by platform and problem_id
      const jobsResponse = await apiGet(`${API_ENDPOINTS.jobs}?platform=${platform}&problem_id=${problemId}`);
      if (jobsResponse.ok) {
        const data = await jobsResponse.json();
        setJobs(data.jobs || []);
      }

      // Fetch progress history if extraction job is processing
      if (problemData) {
        const extractionJobId = problemData?.metadata?.extraction_job_id;
        const extractionStatus = problemData?.metadata?.extraction_status;

        if (extractionJobId && extractionStatus === 'PROCESSING') {
          try {
            const progressResponse = await apiGet(API_ENDPOINTS.jobProgress(extractionJobId, 'extraction'));
            if (progressResponse.ok) {
              const progressData = await progressResponse.json();
              setProgressHistory(progressData.history || []);
            }
          } catch (progressError) {
            console.error('Error fetching progress history:', progressError);
          }
        } else {
          setProgressHistory([]);
        }
      }
    } catch (error) {
      console.error('Error fetching data:', error);
      setProblem(null);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchProblemAndJobs();
    // Auto-refresh every 10 seconds to avoid rate limiting
    const interval = setInterval(fetchProblemAndJobs, 10000);
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

          if (statusData.status === JobStatus.COMPLETED) {
            clearInterval(pollInterval);
            setGeneratingOutputs(false);
            showSnackbar(`Outputs generated successfully for ${statusData.result.count} test cases`, 'success');
            fetchProblemAndJobs();
          } else if (statusData.status === JobStatus.FAILED) {
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

  const handleRetryExtraction = async () => {
    if (!problem.metadata || !problem.metadata.extraction_job_id) {
      showSnackbar('No extraction job to retry', 'warning');
      return;
    }

    setRetryingExtraction(true);
    try {
      const response = await apiPost(API_ENDPOINTS.jobRetry(problem.metadata.extraction_job_id), {});

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to retry extraction');
      }

      showSnackbar('Extraction job retry initiated successfully!', 'success');
      fetchProblemAndJobs();
    } catch (error) {
      console.error('Error retrying extraction:', error);
      showSnackbar('An error occurred while retrying extraction: ' + error.message, 'error');
    } finally {
      setRetryingExtraction(false);
    }
  };

  const handleRegenerateSolution = async () => {
    if (!additionalContext.trim()) {
      showSnackbar('Please provide additional context for solution regeneration', 'warning');
      return;
    }

    setRegenerating(true);
    try {
      const response = await apiPost(`/register/problems/${problem.id}/regenerate-solution/`, {
        additional_context: additionalContext
      }, { requireAuth: true });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to regenerate solution');
      }

      const data = await response.json();
      showSnackbar('Solution regeneration started! Job ID: ' + data.job_id, 'success');
      setRegenerateDialogOpen(false);
      setAdditionalContext('');

      // Refresh to show new job
      fetchProblemAndJobs();
    } catch (error) {
      console.error('Error regenerating solution:', error);
      showSnackbar('Failed to regenerate solution: ' + error.message, 'error');
    } finally {
      setRegenerating(false);
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
      case JobStatus.COMPLETED:
        return <CheckCircleIcon color="success" />;
      case JobStatus.FAILED:
        return <ErrorIcon color="error" />;
      case JobStatus.PROCESSING:
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

  // If redirecting due to access denied, don't show anything
  if (redirecting) {
    return null;
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

  // Helper to get extraction stages
  const getExtractionStages = () => {
    const stages = [
      { key: 'queued', label: 'Queued', description: 'Waiting to start' },
      { key: 'fetching', label: 'Fetching Web Content', description: 'Downloading problem page from website' },
      { key: 'analyzing', label: 'AI Processing', description: 'Analyzing problem and generating solution' },
      { key: 'validating', label: 'Validating Solution', description: 'Testing solution with sample test cases' },
      { key: 'completed', label: 'Completed', description: 'Extraction successful' }
    ];

    const extractionStatus = problem?.metadata?.extraction_status;
    const progress = problem?.metadata?.progress || '';

    if (extractionStatus === ExtractionStatus.FAILED) {
      return { stages, currentStage: 'failed', allCompleted: false, progressMessage: progress };
    }

    // Check if extraction is completed - only if status is explicitly COMPLETED
    // Don't consider constraints alone, as they may exist during regeneration
    if (extractionStatus === ExtractionStatus.COMPLETED) {
      return { stages, currentStage: 4, allCompleted: true, progressMessage: 'Extraction completed' };
    }

    // Determine current stage based on progress message
    let currentStageIndex = 0;
    let progressMessage = progress;

    // Extract attempt number if present
    const attemptMatch = progress.match(/attempt (\d+)\/(\d+)/i);
    const attemptInfo = attemptMatch ? ` (Attempt ${attemptMatch[1]}/${attemptMatch[2]})` : '';

    if (progress.includes('Loading from cache')) {
      currentStageIndex = 2;
      progressMessage = 'Loading cached data...';
    } else if (progress.includes('Fetching webpage') || progress.includes('Retrying fetch')) {
      currentStageIndex = 1;
      progressMessage = progress.includes('Retrying') ? `Retrying web fetch...${attemptInfo}` : 'Fetching web content...';
    } else if (progress.includes('Analyzing problem') || progress.includes('Generating solution') || progress.includes('Regenerating solution')) {
      currentStageIndex = 2;
      progressMessage = progress.includes('Regenerating')
        ? `AI is retrying...${attemptInfo}`
        : `AI is processing the problem...${attemptInfo}`;
    } else if (progress.includes('Testing solution') || progress.includes('Sample test failed')) {
      currentStageIndex = 3;
      progressMessage = progress.includes('failed')
        ? `Solution validation failed, retrying...${attemptInfo}`
        : `Validating solution...${attemptInfo}`;
    } else if (progress.includes('verified with')) {
      currentStageIndex = 3;
      progressMessage = progress;
    } else if (extractionStatus === ExtractionStatus.PENDING) {
      currentStageIndex = 0;
      progressMessage = 'Queued for processing...';
    }

    return { stages, currentStage: currentStageIndex, allCompleted: false, progressMessage };
  };

  const extractionInfo = getExtractionStages();
  const isExtracting = problem?.metadata?.extraction_status === ExtractionStatus.PROCESSING || problem?.metadata?.extraction_status === ExtractionStatus.PENDING;

  return (
    <Box>
      {/* Refresh indicator */}
      {refreshing && (
        <Box sx={{
          position: 'fixed',
          top: 16,
          right: 16,
          zIndex: 1000,
          display: 'flex',
          alignItems: 'center',
          gap: 1,
          bgcolor: 'background.paper',
          px: 2,
          py: 1,
          borderRadius: 2,
          boxShadow: 2
        }}>
          <CircularProgress size={16} />
          <Typography variant="caption" color="text.secondary">
            Refreshing...
          </Typography>
        </Box>
      )}

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
            disabled={isCompleted}
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
            disabled={isCompleted}
            sx={{
              fontSize: { xs: '0.813rem', sm: '0.875rem' },
              py: { xs: 1, sm: 0.75 }
            }}
          >
            Delete
          </Button>
          {problem.metadata && (problem.metadata.extraction_status === 'FAILED' || problem.metadata.extraction_status === 'PROCESSING') && problem.metadata.extraction_job_id && (
            <Button
              variant="contained"
              color={problem.metadata.extraction_status === 'FAILED' ? 'warning' : 'info'}
              startIcon={<RefreshIcon sx={{ fontSize: { xs: '1.125rem', sm: '1.25rem' } }} />}
              onClick={handleRetryExtraction}
              disabled={retryingExtraction}
              sx={{
                fontSize: { xs: '0.813rem', sm: '0.875rem' },
                py: { xs: 1, sm: 0.75 }
              }}
            >
              {retryingExtraction ? 'Retrying...' : (problem.metadata.extraction_status === 'PROCESSING' ? 'Cancel & Retry' : 'Retry Extraction')}
            </Button>
          )}
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
          {isDraft && !isCompleted && (
            <Button
              variant="contained"
              color="warning"
              onClick={() => setRegenerateDialogOpen(true)}
              sx={{
                fontSize: { xs: '0.813rem', sm: '0.875rem' },
                py: { xs: 1, sm: 0.75 }
              }}
            >
              Regenerate Solution
            </Button>
          )}
        </Box>
      </Box>

      {/* Extraction Progress Stages */}
      {isExtracting && (
        <Paper sx={{
          p: 2.5,
          mb: 3,
          bgcolor: 'grey.50',
          borderLeft: '3px solid',
          borderColor: 'grey.400',
          position: 'relative'
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2.5 }}>
            <CircularProgress size={18} thickness={4} sx={{ color: 'grey.600' }} />
            <Typography variant="subtitle1" sx={{ fontWeight: 600, color: 'text.primary' }}>
              Extraction in Progress
            </Typography>
          </Box>

          <Typography variant="body2" color="text.secondary" sx={{ mb: 2.5, pl: 4.5 }}>
            {extractionInfo.progressMessage}
          </Typography>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, pl: 4.5 }}>
            {extractionInfo.stages.map((stage, index) => {
              const isCompleted = typeof extractionInfo.currentStage === 'number' && index < extractionInfo.currentStage;
              const isCurrent = extractionInfo.currentStage === index;
              const isPending = typeof extractionInfo.currentStage === 'number' && index > extractionInfo.currentStage;

              return (
                <Box
                  key={stage.key}
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1.5,
                    opacity: isPending ? 0.35 : 1
                  }}
                >
                  <Box sx={{ minWidth: 20, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    {isCompleted && <CheckCircleIcon sx={{ fontSize: 20, color: 'success.main' }} />}
                    {isCurrent && <CircularProgress size={20} thickness={5} />}
                    {isPending && <Box sx={{ width: 8, height: 8, borderRadius: '50%', bgcolor: 'grey.300' }} />}
                  </Box>
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: isCurrent ? 600 : 400,
                      color: isCurrent ? 'text.primary' : isCompleted ? 'success.dark' : 'text.secondary'
                    }}
                  >
                    {stage.label}
                  </Typography>
                </Box>
              );
            })}
          </Box>

          {/* Progress History Details */}
          {progressHistory.length > 0 && (
            <Box sx={{ mt: 2.5, pl: 4.5 }}>
              <Accordion sx={{ boxShadow: 'none', '&:before': { display: 'none' } }}>
                <AccordionSummary
                  expandIcon={<ExpandMoreIcon />}
                  sx={{
                    minHeight: 40,
                    '&.Mui-expanded': { minHeight: 40 },
                    px: 1.5
                  }}
                >
                  <Typography variant="caption" color="text.secondary">
                    Detailed log ({progressHistory.length} steps)
                  </Typography>
                </AccordionSummary>
                <AccordionDetails sx={{ px: 1.5 }}>
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                    {progressHistory.map((item, index) => (
                      <Box
                        key={item.id}
                        sx={{
                          pb: 1,
                          borderBottom: index < progressHistory.length - 1 ? '1px solid' : 'none',
                          borderColor: 'divider'
                        }}
                      >
                        <Typography variant="caption" sx={{ fontWeight: 600, display: 'block', mb: 0.5 }}>
                          {item.step}
                        </Typography>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', fontSize: '0.7rem' }}>
                          {item.message}
                        </Typography>
                        <Typography variant="caption" color="text.disabled" sx={{ display: 'block', mt: 0.5, fontSize: '0.65rem' }}>
                          {new Date(item.created_at).toLocaleTimeString()}
                        </Typography>
                      </Box>
                    ))}
                  </Box>
                </AccordionDetails>
              </Accordion>
            </Box>
          )}
        </Paper>
      )}

      {/* Failed extraction message */}
      {problem?.metadata?.extraction_status === ExtractionStatus.FAILED && (
        <Paper sx={{ p: 3, mb: 3, bgcolor: 'error.light', borderLeft: '4px solid', borderColor: 'error.main' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <ErrorIcon color="error" />
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              Extraction Failed
            </Typography>
          </Box>
          <Typography variant="body2" color="text.secondary">
            The problem extraction process encountered an error. You can retry the extraction using the "Retry Extraction" button above.
          </Typography>
        </Paper>
      )}

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
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="body2" color="text.secondary" component="span">
                <strong>Test Cases:</strong> {problem.test_case_count || 0}
              </Typography>
              {isDraft && <Chip label="Draft" size="small" color="warning" />}
            </Box>
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
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'text.primary' }}>
                Solution Code:
              </Typography>
              <IconButton
                size="small"
                onClick={() => {
                  navigator.clipboard.writeText(problem.solution_code).then(() => {
                    showSnackbar('Solution code copied to clipboard!', 'success');
                  }).catch((error) => {
                    console.error('Failed to copy solution code:', error);
                    showSnackbar('Failed to copy solution code to clipboard', 'error');
                  });
                }}
                title="Copy Solution Code"
              >
                <ContentCopyIcon fontSize="small" />
              </IconButton>
            </Box>
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
                      gap: 2,
                      alignItems: 'stretch'
                    }}>
                      <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 50%' }, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
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
                          height: '200px',
                          overflow: 'auto',
                          flex: 1
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
                      <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 50%' }, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
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
                          height: '200px',
                          overflow: 'auto',
                          flex: 1
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
                      {job.status === JobStatus.COMPLETED && (
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

      {/* Regenerate Solution Dialog */}
      <Dialog
        open={regenerateDialogOpen}
        onClose={() => !regenerating && setRegenerateDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Regenerate Solution with Additional Context
          <IconButton
            onClick={() => setRegenerateDialogOpen(false)}
            disabled={regenerating}
            sx={{ position: 'absolute', right: 8, top: 8 }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          <Typography variant="body1" sx={{ mb: 2 }}>
            Provide additional context to help AI generate a better solution. For example:
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            - Counterexamples where the current solution fails
            <br />
            - Edge cases that need to be handled
            <br />
            - Specific requirements or constraints
            <br />
            - Expected behavior for certain inputs
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={8}
            label="Additional Context"
            placeholder="Example: The solution fails for n=1000000. Expected output should be 500000 but got timeout. Please optimize for large inputs and handle edge case when n=1."
            value={additionalContext}
            onChange={(e) => setAdditionalContext(e.target.value)}
            disabled={regenerating}
            sx={{ mb: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRegenerateDialogOpen(false)} disabled={regenerating}>
            Cancel
          </Button>
          <Button
            onClick={handleRegenerateSolution}
            variant="contained"
            color="warning"
            disabled={regenerating || !additionalContext.trim()}
          >
            {regenerating ? 'Regenerating...' : 'Regenerate Solution'}
          </Button>
        </DialogActions>
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
