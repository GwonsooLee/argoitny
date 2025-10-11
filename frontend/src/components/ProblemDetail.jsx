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
  TextField,
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio,
  Select,
  MenuItem,
  InputLabel,
  FormHelperText,
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
  Refresh as RefreshIcon,
  OpenInNew as OpenInNewIcon,
  Add as AddIcon
} from '@mui/icons-material';
import { apiGet, apiPost, apiDelete } from '../utils/api-client';
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
  const [lastRefreshTime, setLastRefreshTime] = useState(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editedSamples, setEditedSamples] = useState([]);
  const [editedSolutionCode, setEditedSolutionCode] = useState('');
  const [editedTags, setEditedTags] = useState([]);
  const [tagInput, setTagInput] = useState('');
  const [saving, setSaving] = useState(false);

  // LLM Configuration State for Regenerate Solution
  const [llmModel, setLlmModel] = useState('gpt-5');
  const [reasoningEffort, setReasoningEffort] = useState('medium');
  const [maxOutputTokens, setMaxOutputTokens] = useState(8192);

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

        // Fetch testcases separately
        try {
          const testcasesResponse = await apiGet(`${API_ENDPOINTS.problems}${platform}/${problemId}/testcases/`, { requireAuth: true });
          if (testcasesResponse.ok) {
            const testcasesData = await testcasesResponse.json();
            problemData.test_cases = testcasesData.testcases || [];
          }
        } catch (testcaseError) {
          console.error('Error fetching testcases:', testcaseError);
        }

        // Check if test case generation is complete
        if (executingScript) {
          const count = problemData.test_case_count || 0;
          const targetCount = 10;

          if (count >= targetCount) {
            // Generation complete - stop executing state and close dialog
            setExecutingScript(false);
            setShowScript(false);
          }
        }

        // Backend already decodes solution_code from base64, no need to decode again
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
      setLastRefreshTime(new Date());
    }
  };

  useEffect(() => {
    fetchProblemAndJobs();

    // Dynamic polling: 2 seconds during test case generation, 10 seconds otherwise
    const pollInterval = executingScript ? 2000 : 10000;
    const interval = setInterval(fetchProblemAndJobs, pollInterval);
    return () => clearInterval(interval);
  }, [platform, problemId, problem?.metadata?.extraction_status, executingScript]);

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

    showSnackbar('Test case generation job created!', 'success');

    try {
      setExecutingScript(true);

      // Generate difficulties: 5 small + 5 medium
      const difficulties = [
        'small', 'small', 'small', 'small', 'small',
        'medium', 'medium', 'medium', 'medium', 'medium'
      ];

      // Start async execution
      const executeResponse = await apiPost(API_ENDPOINTS.executeTestCases, {
        generator_code: selectedJob.generator_code,
        num_cases: 10,
        difficulties: difficulties,
        platform: problem.platform,
        problem_id: problem.problem_id
      });

      if (!executeResponse.ok) {
        const errorData = await executeResponse.json();
        throw new Error(errorData.error || 'Failed to start execution');
      }

      setShowScript(false);

    } catch (error) {
      console.error('Error executing script:', error);
      showSnackbar('Failed to execute script: ' + error.message, 'error');
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

  const handleReasoningEffortChange = (value) => {
    setReasoningEffort(value);
    // Auto-adjust tokens for high reasoning
    if (value === 'high' && maxOutputTokens < 96000) {
      setMaxOutputTokens(128000);
    }
  };

  const handleResetLlmConfig = () => {
    setLlmModel('gpt-5');
    setReasoningEffort('medium');
    setMaxOutputTokens(8192);
  };

  const handleRegenerateSolution = async () => {
    setRegenerating(true);
    try {
      // Use platform/problem_id URL format
      const response = await apiPost(`/register/problems/${problem.platform}/${problem.problem_id}/regenerate-solution/`, {
        additional_context: additionalContext,
        llm_config: {
          model: llmModel,
          reasoning_effort: reasoningEffort,
          max_output_tokens: maxOutputTokens
        }
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

  const handleOpenEditDialog = () => {
    // Initialize with current values
    setEditedSamples(problem.metadata?.user_samples || []);
    setEditedSolutionCode(problem.solution_code || '');
    setEditedTags(problem.tags || []);
    setTagInput('');
    setEditDialogOpen(true);
  };

  const handleAddEditSample = () => {
    setEditedSamples([...editedSamples, { input: '', output: '' }]);
  };

  const handleRemoveEditSample = (index) => {
    setEditedSamples(editedSamples.filter((_, i) => i !== index));
  };

  const handleEditSampleChange = (index, field, value) => {
    const newSamples = [...editedSamples];
    newSamples[index][field] = value;
    setEditedSamples(newSamples);
  };

  const handleAddTag = () => {
    const trimmedTag = tagInput.trim().toLowerCase();
    if (trimmedTag && !editedTags.includes(trimmedTag)) {
      setEditedTags([...editedTags, trimmedTag]);
      setTagInput('');
    }
  };

  const handleRemoveTag = (tagToRemove) => {
    setEditedTags(editedTags.filter(tag => tag !== tagToRemove));
  };

  const handleTagInputKeyPress = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddTag();
    }
  };

  const handleSaveEdit = async () => {
    setSaving(true);
    try {
      // Filter out empty samples
      const validSamples = editedSamples.filter(s => s.input.trim() || s.output.trim());

      const response = await apiPost(`${API_ENDPOINTS.problems}${problem.platform}/${problem.problem_id}/`, {
        user_samples: validSamples,
        solution_code: editedSolutionCode,
        tags: editedTags
      }, { requireAuth: true });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to update problem');
      }

      showSnackbar('Problem updated successfully!', 'success');
      setEditDialogOpen(false);
      fetchProblemAndJobs();
    } catch (error) {
      console.error('Error updating problem:', error);
      showSnackbar('Failed to update problem: ' + error.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      const response = await apiDelete(`${API_ENDPOINTS.problems}${platform}/${problemId}/`, { requireAuth: true });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || errorData.detail || 'Failed to delete problem');
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
      { key: 'extracting', label: 'Step 1: Extracting Metadata', description: '📄 Extracting problem details from webpage', icon: '📄' },
      { key: 'solving', label: 'Step 2: Generating Solution', description: '🧠 AI is solving the problem', icon: '🧠' },
      { key: 'validating', label: 'Step 3: Validating Solution', description: '✓ Testing solution with sample cases', icon: '✓' },
      { key: 'completed', label: 'Completed', description: 'Extraction successful' }
    ];

    const extractionStatus = problem?.metadata?.extraction_status;
    const progress = problem?.metadata?.progress || '';

    if (extractionStatus === ExtractionStatus.FAILED) {
      return { stages, currentStage: 'failed', allCompleted: false, progressMessage: progress };
    }

    // Check if extraction is completed - only if status is explicitly COMPLETED
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
    }
    // Step 1: Extracting metadata (with 📄 emoji)
    else if (progress.includes('📄') || progress.includes('Step 1/2') || progress.includes('Extracting problem metadata')) {
      currentStageIndex = 1;
      const cleanProgress = progress.replace('📄', '').trim();
      progressMessage = cleanProgress || 'Extracting problem metadata...';
    }
    // Step 2: Generating solution (with 🧠 emoji)
    else if (progress.includes('🧠') || progress.includes('Step 2/2') || progress.includes('Generating solution')) {
      currentStageIndex = 2;
      const cleanProgress = progress.replace('🧠', '').trim();
      progressMessage = cleanProgress + attemptInfo || progress || `Generating solution...${attemptInfo}`;
    }
    // Step 3: Validating solution (with ✓ emoji or "verified" text)
    else if (progress.includes('✓') || progress.includes('verified with') || progress.includes('Testing solution')) {
      currentStageIndex = 3;
      const cleanProgress = progress.replace('✓', '').trim();
      progressMessage = cleanProgress || 'Testing solution with sample cases...';
    }
    // Legacy progress messages
    else if (progress.includes('Fetching webpage')) {
      currentStageIndex = 1;
      progressMessage = 'Fetching web content...';
    }
    else if (progress.includes('Analyzing problem') || progress.includes('AI Processing')) {
      currentStageIndex = 2;
      progressMessage = `AI is solving the problem...${attemptInfo}`;
    }
    else if (extractionStatus === ExtractionStatus.PENDING) {
      currentStageIndex = 0;
      progressMessage = 'Queued for processing...';
    }

    return { stages, currentStage: currentStageIndex, allCompleted: false, progressMessage };
  };

  const extractionInfo = getExtractionStages();
  const isExtracting = problem?.metadata?.extraction_status === ExtractionStatus.PROCESSING || problem?.metadata?.extraction_status === ExtractionStatus.PENDING;

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
          {problem.problem_url && (
            <Button
              variant="outlined"
              startIcon={<OpenInNewIcon sx={{ fontSize: { xs: '1.125rem', sm: '1.25rem' } }} />}
              onClick={() => window.open(problem.problem_url, '_blank')}
              sx={{
                fontSize: { xs: '0.813rem', sm: '0.875rem' },
                py: { xs: 1, sm: 0.75 }
              }}
            >
              Open Problem
            </Button>
          )}
          <Button
            variant="outlined"
            startIcon={<EditIcon sx={{ fontSize: { xs: '1.125rem', sm: '1.25rem' } }} />}
            onClick={handleOpenEditDialog}
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
          {!isDraft && !isCompleted && !isExtracting && (
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
          {!isDraft && problem.test_cases && problem.test_cases.length > 0 && !isCompleted && !isExtracting && (
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
          {isDraft && !isCompleted && !isExtracting && (
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
          {!isDraft && !isCompleted && !isExtracting && (
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
          {isDraft && !isCompleted && !isExtracting && (
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
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2.5 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <CircularProgress size={18} thickness={4} sx={{ color: 'grey.600' }} />
              <Typography variant="subtitle1" sx={{ fontWeight: 600, color: 'text.primary' }}>
                Extraction in Progress
              </Typography>
              <Chip
                label={refreshing ? "🔄 Refreshing..." : "Updating..."}
                size="small"
                sx={{ height: 24, fontSize: '0.75rem' }}
              />
            </Box>
            {lastRefreshTime && (
              <Typography variant="caption" color="text.secondary">
                Last updated: {lastRefreshTime.toLocaleTimeString()}
              </Typography>
            )}
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
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
          <Typography variant="h4" sx={{
            color: 'text.primary',
            fontWeight: 600,
            fontSize: { xs: '1.5rem', sm: '1.75rem', md: '2.125rem' }
          }}>
            {problem.title}
          </Typography>
          {problem.needs_review && (
            <Chip
              label="Needs Review"
              color="warning"
              size="small"
              sx={{
                fontSize: { xs: '0.688rem', sm: '0.75rem' },
                fontWeight: 600
              }}
            />
          )}
        </Box>
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

        {problem.metadata?.user_samples && problem.metadata.user_samples.length > 0 && (
          <>
            <Divider sx={{ my: 2 }} />
            <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600, color: 'text.primary' }}>
              User-Provided Samples ({problem.metadata.user_samples.length}):
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
              These are the sample test cases you provided during problem registration.
            </Typography>
            {problem.metadata.user_samples.map((sample, idx) => {
              const truncatedInput = truncateText(sample.input);
              const truncatedOutput = truncateText(sample.output);

              return (
                <Accordion
                  key={idx}
                  sx={{ mb: 1, '&:before': { display: 'none' } }}
                >
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography>Sample #{idx + 1}</Typography>
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
                            onClick={() => downloadText(sample.input, `user_sample_${idx + 1}_input.txt`)}
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
                            onClick={() => downloadText(sample.output, `user_sample_${idx + 1}_output.txt`)}
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
            sx={{ mb: 3 }}
          />

          <Divider sx={{ my: 3 }} />

          {/* LLM Configuration Section */}
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2 }}>
            LLM Configuration
          </Typography>
          <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 3 }}>
            Configure the AI model settings for solution regeneration.
          </Typography>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {/* Model Selection */}
            <FormControl component="fieldset">
              <FormLabel component="legend" sx={{ mb: 1, fontSize: '0.875rem', fontWeight: 600 }}>
                AI Model
              </FormLabel>
              <RadioGroup
                row
                value={llmModel}
                onChange={(e) => setLlmModel(e.target.value)}
                disabled={regenerating}
              >
                <FormControlLabel
                  value="gpt-5"
                  control={<Radio />}
                  label="GPT-5"
                  disabled={regenerating}
                />
                <FormControlLabel
                  value="gemini"
                  control={<Radio />}
                  label="Gemini"
                  disabled={regenerating}
                />
              </RadioGroup>
              <FormHelperText>Select the AI model to use for solution regeneration</FormHelperText>
            </FormControl>

            {/* GPT-5 Specific Configuration */}
            {llmModel === 'gpt-5' && (
              <>
                {/* Reasoning Effort */}
                <FormControl fullWidth>
                  <InputLabel id="regen-reasoning-effort-label">Reasoning Effort</InputLabel>
                  <Select
                    labelId="regen-reasoning-effort-label"
                    value={reasoningEffort}
                    label="Reasoning Effort"
                    onChange={(e) => handleReasoningEffortChange(e.target.value)}
                    disabled={regenerating}
                  >
                    <MenuItem value="low">Low</MenuItem>
                    <MenuItem value="medium">Medium</MenuItem>
                    <MenuItem value="high">High</MenuItem>
                  </Select>
                  <FormHelperText>
                    Higher reasoning uses more tokens but may produce better solutions
                  </FormHelperText>
                </FormControl>

                {/* Max Output Tokens */}
                <FormControl fullWidth>
                  <TextField
                    type="number"
                    label="Max Output Tokens"
                    value={maxOutputTokens}
                    onChange={(e) => {
                      const value = parseInt(e.target.value, 10);
                      if (value >= 1024 && value <= 128000) {
                        setMaxOutputTokens(value);
                      }
                    }}
                    disabled={regenerating}
                    inputProps={{ min: 1024, max: 128000, step: 1024 }}
                    helperText={
                      reasoningEffort === 'high' && maxOutputTokens < 96000
                        ? 'Warning: High reasoning requires more tokens. Recommended: 128000'
                        : 'Recommended: 8192 for medium, 128000 for high reasoning (Range: 1024-128000)'
                    }
                    error={reasoningEffort === 'high' && maxOutputTokens < 96000}
                  />
                </FormControl>
              </>
            )}

            {/* Gemini Information */}
            {llmModel === 'gemini' && (
              <Box sx={{
                p: 2,
                bgcolor: 'info.lighter',
                borderRadius: 1,
                border: '1px solid',
                borderColor: 'info.light'
              }}>
                <Typography variant="body2" color="info.dark">
                  Gemini uses fixed optimization settings (temperature and top_p) for consistent results. No additional configuration is required.
                </Typography>
              </Box>
            )}

            {/* Reset Button - Only show for GPT-5 */}
            {llmModel === 'gpt-5' && (
              <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={handleResetLlmConfig}
                  disabled={regenerating}
                >
                  Reset to Defaults
                </Button>
              </Box>
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRegenerateDialogOpen(false)} disabled={regenerating}>
            Cancel
          </Button>
          <Button
            onClick={handleRegenerateSolution}
            variant="contained"
            color="warning"
            disabled={regenerating}
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

      {/* Edit Dialog */}
      <Dialog
        open={editDialogOpen}
        onClose={() => !saving && setEditDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Edit Problem
          <IconButton
            onClick={() => setEditDialogOpen(false)}
            disabled={saving}
            sx={{ position: 'absolute', right: 8, top: 8 }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          <Typography variant="body1" sx={{ mb: 2 }}>
            Edit Tags, User-Provided Samples, and Solution Code
          </Typography>

          {/* Tags Section */}
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
              Tags:
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
              Add algorithm/category tags for this problem (e.g., "dp", "greedy", "graphs")
            </Typography>

            {/* Display current tags */}
            {editedTags.length > 0 && (
              <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mb: 2 }}>
                {editedTags.map((tag, idx) => (
                  <Chip
                    key={idx}
                    label={tag}
                    size="small"
                    color="primary"
                    variant="outlined"
                    onDelete={() => handleRemoveTag(tag)}
                    disabled={saving}
                  />
                ))}
              </Box>
            )}

            {/* Tag input */}
            <Box sx={{ display: 'flex', gap: 1 }}>
              <TextField
                fullWidth
                size="small"
                label="Add Tag"
                placeholder="e.g., dp, greedy, graphs"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyPress={handleTagInputKeyPress}
                disabled={saving}
              />
              <Button
                variant="outlined"
                onClick={handleAddTag}
                disabled={saving || !tagInput.trim()}
              >
                Add
              </Button>
            </Box>
          </Box>

          <Divider sx={{ my: 2 }} />

          {/* Solution Code Section */}
          <Box sx={{ mb: 3 }}>
            <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
              Solution Code:
            </Typography>
            <TextField
              fullWidth
              multiline
              rows={12}
              value={editedSolutionCode}
              onChange={(e) => setEditedSolutionCode(e.target.value)}
              disabled={saving}
              placeholder="Enter solution code..."
              sx={{
                fontFamily: 'monospace',
                '& .MuiInputBase-input': {
                  fontFamily: 'monospace',
                  fontSize: '0.875rem'
                }
              }}
            />
          </Box>

          <Divider sx={{ my: 2 }} />

          {/* User-Provided Samples Section */}
          <Box>
            <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
              User-Provided Samples:
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
              These are sample test cases to validate the generated solution.
            </Typography>

            {editedSamples.length === 0 ? (
              <Box sx={{ textAlign: 'center', py: 3, bgcolor: 'grey.50', borderRadius: 1, mb: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  No samples added yet
                </Typography>
              </Box>
            ) : (
              editedSamples.map((sample, index) => (
                <Box key={index} sx={{ mb: 2, p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                    <Typography variant="subtitle2">Sample #{index + 1}</Typography>
                    <Button
                      size="small"
                      color="error"
                      onClick={() => handleRemoveEditSample(index)}
                      disabled={saving}
                    >
                      Remove
                    </Button>
                  </Box>
                  <TextField
                    fullWidth
                    label="Input"
                    placeholder="Sample input (e.g., 3\n1 2 3)"
                    value={sample.input}
                    onChange={(e) => handleEditSampleChange(index, 'input', e.target.value)}
                    disabled={saving}
                    multiline
                    rows={3}
                    sx={{ mb: 1 }}
                  />
                  <TextField
                    fullWidth
                    label="Expected Output"
                    placeholder="Expected output (e.g., 6)"
                    value={sample.output}
                    onChange={(e) => handleEditSampleChange(index, 'output', e.target.value)}
                    disabled={saving}
                    multiline
                    rows={2}
                  />
                </Box>
              ))
            )}

            <Button
              variant="outlined"
              startIcon={<AddIcon />}
              onClick={handleAddEditSample}
              disabled={saving}
              sx={{ mb: 2 }}
            >
              Add Sample
            </Button>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDialogOpen(false)} disabled={saving}>
            Cancel
          </Button>
          <Button
            onClick={handleSaveEdit}
            variant="contained"
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
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
