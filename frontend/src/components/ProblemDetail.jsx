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
  IconButton
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
  Close as CloseIcon
} from '@mui/icons-material';
import { apiGet, apiPost } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';

function ProblemDetail({ platform, problemId, onBack }) {
  const [problem, setProblem] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generatingScript, setGeneratingScript] = useState(false);
  const [selectedJob, setSelectedJob] = useState(null);
  const [showTestCases, setShowTestCases] = useState(false);

  const fetchProblemAndJobs = async () => {
    try {
      // Fetch all problems and filter by platform and problem_id
      const problemsResponse = await apiGet(API_ENDPOINTS.problems);
      if (problemsResponse.ok) {
        const data = await problemsResponse.json();
        const allProblems = data.problems || [];
        const foundProblem = allProblems.find(
          p => p.platform === platform && p.problem_id === problemId
        );
        setProblem(foundProblem);
      }

      // Fetch jobs filtered by platform and problem_id
      const jobsResponse = await apiGet(`${API_ENDPOINTS.jobs}?platform=${platform}&problem_id=${problemId}`);
      if (jobsResponse.ok) {
        const data = await jobsResponse.json();
        setJobs(data.jobs || []);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProblemAndJobs();
    const interval = setInterval(fetchProblemAndJobs, 5000);
    return () => clearInterval(interval);
  }, [platform, problemId]);

  const handleGenerateScript = async () => {
    if (!problem.solution_code || !problem.constraints) {
      alert('Problem must have solution code and constraints to generate script');
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
      alert('Script generation job created successfully!');
      fetchProblemAndJobs();
    } catch (error) {
      console.error('Error generating script:', error);
      alert('An error occurred while generating script: ' + error.message);
    } finally {
      setGeneratingScript(false);
    }
  };

  const handleViewTestCases = async (job) => {
    try {
      const response = await apiGet(API_ENDPOINTS.jobDetail(job.id));
      if (response.ok) {
        const data = await response.json();
        setSelectedJob(data);
        setShowTestCases(true);
      }
    } catch (error) {
      console.error('Error fetching job details:', error);
      alert('Failed to load test cases');
    }
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
        <CircularProgress sx={{ color: 'white' }} />
      </Box>
    );
  }

  if (!problem) {
    return (
      <Box>
        <Button startIcon={<ArrowBackIcon />} onClick={onBack} sx={{ mb: 2, color: 'white' }}>
          Back
        </Button>
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography variant="h6">Problem not found</Typography>
        </Paper>
      </Box>
    );
  }

  const isDraft = !problem.test_case_count || problem.test_case_count === 0;

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Button startIcon={<ArrowBackIcon />} onClick={onBack} sx={{ color: 'white' }}>
          Back to Problems
        </Button>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<EditIcon />}
            onClick={() => window.location.href = `/register?draft_id=${problem.id}`}
            sx={{ color: 'white', borderColor: 'white' }}
          >
            Edit Problem
          </Button>
          <Button
            variant="contained"
            startIcon={<PlayArrowIcon />}
            onClick={handleGenerateScript}
            disabled={generatingScript || !problem.solution_code || !problem.constraints}
            sx={{ backgroundColor: 'primary.main' }}
          >
            {generatingScript ? 'Generating...' : 'Generate Script'}
          </Button>
        </Box>
      </Box>

      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h4" gutterBottom sx={{ color: 'white', fontWeight: 600 }}>
          {problem.title}
        </Typography>
        <Typography variant="body1" sx={{ color: 'rgba(255, 255, 255, 0.7)', mb: 2 }}>
          {problem.platform === 'baekjoon' ? 'Baekjoon' : 'Codeforces'} - {problem.problem_id}
        </Typography>

        {problem.tags && problem.tags.length > 0 && (
          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mb: 2 }}>
            {problem.tags.map((tag, idx) => (
              <Chip
                key={idx}
                label={tag}
                sx={{
                  backgroundColor: 'rgba(102, 126, 234, 0.3)',
                  color: 'white'
                }}
              />
            ))}
          </Box>
        )}

        <Divider sx={{ my: 2, borderColor: 'rgba(255, 255, 255, 0.1)' }} />

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
            <Divider sx={{ my: 2, borderColor: 'rgba(255, 255, 255, 0.1)' }} />
            <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
              Constraints:
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-wrap' }}>
              {problem.constraints}
            </Typography>
          </>
        )}

        {problem.solution_code && (
          <>
            <Divider sx={{ my: 2, borderColor: 'rgba(255, 255, 255, 0.1)' }} />
            <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
              Solution Code:
            </Typography>
            <Paper
              sx={{
                p: 2,
                backgroundColor: 'rgba(0, 0, 0, 0.3)',
                fontFamily: 'monospace',
                fontSize: '0.875rem',
                overflowX: 'auto'
              }}
            >
              <pre style={{ margin: 0, color: 'rgba(255, 255, 255, 0.9)' }}>
                {problem.solution_code}
              </pre>
            </Paper>
          </>
        )}
      </Paper>

      {!isDraft && problem.test_cases && problem.test_cases.length > 0 && (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
            Registered Test Cases
          </Typography>
          {problem.test_cases.map((tc, idx) => (
            <Accordion
              key={idx}
              sx={{
                backgroundColor: 'rgba(0, 0, 0, 0.2)',
                mb: 1,
                '&:before': { display: 'none' }
              }}
            >
              <AccordionSummary expandIcon={<ExpandMoreIcon sx={{ color: 'white' }} />}>
                <Typography sx={{ color: 'white' }}>Test Case #{idx + 1}</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" gutterBottom>Input:</Typography>
                    <Paper sx={{ p: 1.5, backgroundColor: 'rgba(0, 0, 0, 0.3)' }}>
                      <pre style={{ margin: 0, fontSize: '0.875rem', whiteSpace: 'pre-wrap' }}>
                        {tc.input}
                      </pre>
                    </Paper>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" gutterBottom>Expected Output:</Typography>
                    <Paper sx={{ p: 1.5, backgroundColor: 'rgba(0, 0, 0, 0.3)' }}>
                      <pre style={{ margin: 0, fontSize: '0.875rem', whiteSpace: 'pre-wrap' }}>
                        {tc.output}
                      </pre>
                    </Paper>
                  </Grid>
                </Grid>
              </AccordionDetails>
            </Accordion>
          ))}
        </Paper>
      )}

      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
          Script Generation Jobs
        </Typography>

        {jobs.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <CodeIcon sx={{ fontSize: 48, color: 'rgba(255, 255, 255, 0.2)', mb: 1 }} />
            <Typography color="text.secondary">
              No script generation jobs yet for this problem
            </Typography>
          </Box>
        ) : (
          jobs.map((job) => (
            <Card
              key={job.id}
              sx={{
                mb: 2,
                backgroundColor: 'rgba(255, 255, 255, 0.03)',
                '&:last-child': { mb: 0 }
              }}
            >
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {getStatusIcon(job.status)}
                    <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                      {job.status}
                    </Typography>
                  </Box>
                  <Typography variant="caption" color="text.secondary">
                    {new Date(job.created_at).toLocaleString()}
                  </Typography>
                </Box>

                {job.error_message && (
                  <Box sx={{ mt: 1, p: 1.5, backgroundColor: 'rgba(211, 47, 47, 0.1)', borderRadius: 1 }}>
                    <Typography variant="body2" color="error.light">
                      Error: {job.error_message}
                    </Typography>
                  </Box>
                )}

                {job.status === 'COMPLETED' && (
                  <Button
                    variant="outlined"
                    size="small"
                    sx={{ mt: 2, color: 'white', borderColor: 'white' }}
                    onClick={() => handleViewTestCases(job)}
                  >
                    View Test Cases
                  </Button>
                )}
              </CardContent>
            </Card>
          ))
        )}
      </Paper>

      {/* Test Cases Dialog */}
      <Dialog
        open={showTestCases}
        onClose={() => setShowTestCases(false)}
        maxWidth="md"
        fullWidth
        PaperProps={{
          sx: {
            backgroundColor: 'rgba(255, 255, 255, 0.05)',
            backdropFilter: 'blur(10px)'
          }
        }}
      >
        <DialogTitle sx={{ color: 'white' }}>
          Generated Test Cases
          <IconButton
            onClick={() => setShowTestCases(false)}
            sx={{ position: 'absolute', right: 8, top: 8, color: 'white' }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          {selectedJob && selectedJob.test_cases && selectedJob.test_cases.map((tc, idx) => (
            <Accordion
              key={idx}
              sx={{
                backgroundColor: 'rgba(0, 0, 0, 0.2)',
                mb: 1,
                '&:before': { display: 'none' }
              }}
            >
              <AccordionSummary expandIcon={<ExpandMoreIcon sx={{ color: 'white' }} />}>
                <Typography sx={{ color: 'white' }}>Test Case #{idx + 1}</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" gutterBottom>Input:</Typography>
                    <Paper sx={{ p: 1.5, backgroundColor: 'rgba(0, 0, 0, 0.3)' }}>
                      <pre style={{ margin: 0, fontSize: '0.875rem', whiteSpace: 'pre-wrap' }}>
                        {tc.input}
                      </pre>
                    </Paper>
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" gutterBottom>Output:</Typography>
                    <Paper sx={{ p: 1.5, backgroundColor: 'rgba(0, 0, 0, 0.3)' }}>
                      <pre style={{ margin: 0, fontSize: '0.875rem', whiteSpace: 'pre-wrap' }}>
                        {tc.output}
                      </pre>
                    </Paper>
                  </Grid>
                </Grid>
              </AccordionDetails>
            </Accordion>
          ))}
        </DialogContent>
      </Dialog>
    </Box>
  );
}

export default ProblemDetail;
