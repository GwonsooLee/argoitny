import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  Tabs,
  Tab,
  TextField,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  InputAdornment,
  Grid,
  IconButton
} from '@mui/material';
import {
  Search as SearchIcon,
  ArrowBack as ArrowBackIcon,
  Edit as EditIcon,
  PlayArrow as PlayArrowIcon,
  Code as CodeIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import { apiGet, apiPost } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';

function Problems({ onViewProblem }) {
  const [activeTab, setActiveTab] = useState(0); // 0: Drafts, 1: Registered
  const [drafts, setDrafts] = useState([]);
  const [registered, setRegistered] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [executingJobs, setExecutingJobs] = useState({});
  const [retryingJobs, setRetryingJobs] = useState({});

  const fetchData = async () => {
    try {
      const [draftsResponse, registeredResponse] = await Promise.all([
        apiGet(API_ENDPOINTS.problemDrafts, { requireAuth: true }),
        apiGet(API_ENDPOINTS.problemRegistered, { requireAuth: true })
      ]);

      if (draftsResponse.ok) {
        const data = await draftsResponse.json();
        setDrafts(data.drafts || data.problems || []);
      }

      if (registeredResponse.ok) {
        const data = await registeredResponse.json();
        setRegistered(data.registered || data.problems || []);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  const filterItems = (items) => {
    if (!searchQuery.trim()) return items;

    const query = searchQuery.toLowerCase();
    return items.filter(item =>
      item.title?.toLowerCase().includes(query) ||
      item.problem_id?.toLowerCase().includes(query) ||
      item.platform?.toLowerCase().includes(query) ||
      item.tags?.some(tag => tag.toLowerCase().includes(query))
    );
  };

  const handleEditProblem = (problem) => {
    window.location.href = `/register?draft_id=${problem.id}`;
  };

  const handleGenerateScript = async (problem) => {
    if (!problem.solution_code || !problem.constraints) {
      alert('Problem must have solution code and constraints to generate script');
      return;
    }

    setExecutingJobs({ ...executingJobs, [problem.id]: true });

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
      fetchData();
    } catch (error) {
      console.error('Error generating script:', error);
      alert('An error occurred while generating script: ' + error.message);
    } finally {
      setExecutingJobs({ ...executingJobs, [problem.id]: false });
    }
  };

  const handleRetryExtraction = async (jobId) => {
    setRetryingJobs({ ...retryingJobs, [jobId]: true });

    try {
      const response = await apiPost(API_ENDPOINTS.jobRetry(jobId), {});

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to retry extraction');
      }

      alert('Extraction job retry initiated successfully!');
      fetchData(); // Refresh the list
    } catch (error) {
      console.error('Error retrying extraction:', error);
      alert('An error occurred while retrying extraction: ' + error.message);
    } finally {
      setRetryingJobs({ ...retryingJobs, [jobId]: false });
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      PENDING: 'warning',
      PROCESSING: 'info',
      COMPLETED: 'success',
      FAILED: 'error'
    };
    return colors[status] || 'default';
  };

  const renderProblemCard = (problem, isDraft = false) => {
    const isExtracting = problem.extraction_status === 'PROCESSING' || problem.extraction_status === 'PENDING' || problem.is_extracting;

    return (
      <Card
        key={problem.id}
        sx={{
          mb: 2,
          '&:hover': {
            boxShadow: 3,
            transform: 'translateY(-2px)',
            transition: 'all 0.3s ease'
          },
          cursor: 'pointer',
          border: isExtracting ? '2px solid' : '1px solid',
          borderColor: isExtracting ? 'info.main' : 'divider',
          position: 'relative',
          overflow: 'hidden'
        }}
        onClick={() => !isExtracting && onViewProblem(problem.platform, problem.problem_id)}
      >
        {/* Animated progress bar for extracting state */}
        {isExtracting && (
          <Box
            sx={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              height: 4,
              background: 'linear-gradient(90deg, transparent, #2196f3, transparent)',
              animation: 'shimmer 2s infinite',
              '@keyframes shimmer': {
                '0%': { transform: 'translateX(-100%)' },
                '100%': { transform: 'translateX(100%)' }
              }
            }}
          />
        )}

        <CardContent sx={{ p: { xs: 2, sm: 2.5, md: 3 } }}>
          <Box sx={{
            display: 'flex',
            flexDirection: { xs: 'column', sm: 'row' },
            justifyContent: 'space-between',
            alignItems: { xs: 'flex-start', sm: 'flex-start' },
            mb: 1,
            gap: { xs: 1, sm: 0 }
          }}>
            <Box sx={{ flexGrow: 1, width: { xs: '100%', sm: 'auto' } }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                {isExtracting && (
                  <CircularProgress
                    size={20}
                    thickness={4}
                    sx={{ color: 'info.main' }}
                  />
                )}
                <Typography
                  variant="h6"
                  sx={{
                    fontWeight: 600,
                    fontSize: { xs: '1rem', sm: '1.125rem', md: '1.25rem' },
                    color: isExtracting ? 'info.main' : 'text.primary',
                    fontStyle: isExtracting ? 'italic' : 'normal'
                  }}
                >
                  {problem.title}
                </Typography>
                {problem.extraction_status && (
                  <Chip
                    label={problem.extraction_status}
                    color={getStatusColor(problem.extraction_status)}
                    size="small"
                    sx={{
                      fontSize: { xs: '0.688rem', sm: '0.75rem' },
                      animation: isExtracting ? 'pulse 2s infinite' : 'none',
                      '@keyframes pulse': {
                        '0%, 100%': { opacity: 1 },
                        '50%': { opacity: 0.6 }
                      }
                    }}
                  />
                )}
              </Box>
            <Typography variant="body2" color="text.secondary" sx={{
              mb: 1,
              fontSize: { xs: '0.813rem', sm: '0.875rem' }
            }}>
              {problem.platform === 'baekjoon' ? 'Baekjoon' : 'Codeforces'} - {problem.problem_id}
            </Typography>
          </Box>
          <Box sx={{
            display: 'flex',
            gap: 1,
            width: { xs: '100%', sm: 'auto' },
            justifyContent: { xs: 'flex-end', sm: 'flex-start' }
          }}>
            {problem.extraction_status === 'FAILED' && problem.extraction_job_id && (
              <IconButton
                size="small"
                color="error"
                onClick={(e) => {
                  e.stopPropagation();
                  handleRetryExtraction(problem.extraction_job_id);
                }}
                disabled={retryingJobs[problem.extraction_job_id]}
                sx={{
                  p: { xs: 1, sm: 1 }
                }}
                title="Retry extraction"
              >
                {retryingJobs[problem.extraction_job_id] ? (
                  <CircularProgress size={18} />
                ) : (
                  <RefreshIcon sx={{ fontSize: { xs: '1.125rem', sm: '1.25rem' } }} />
                )}
              </IconButton>
            )}
            <IconButton
              size="small"
              color="primary"
              onClick={(e) => {
                e.stopPropagation();
                handleEditProblem(problem);
              }}
              disabled={problem.is_extracting || problem.extraction_status === 'PROCESSING' || problem.extraction_status === 'PENDING'}
              sx={{
                p: { xs: 1, sm: 1 }
              }}
            >
              <EditIcon sx={{ fontSize: { xs: '1.125rem', sm: '1.25rem' } }} />
            </IconButton>
            {isDraft && (
              <IconButton
                size="small"
                color="secondary"
                onClick={(e) => {
                  e.stopPropagation();
                  handleGenerateScript(problem);
                }}
                disabled={executingJobs[problem.id] || !problem.solution_code || !problem.constraints || problem.is_extracting || problem.extraction_status === 'PROCESSING' || problem.extraction_status === 'PENDING'}
                sx={{
                  p: { xs: 1, sm: 1 }
                }}
              >
                <PlayArrowIcon sx={{ fontSize: { xs: '1.125rem', sm: '1.25rem' } }} />
              </IconButton>
            )}
          </Box>
        </Box>

        {/* Progress indicator for extracting problems */}
        {isExtracting && (
          <Box sx={{
            mt: 1,
            p: 1.5,
            bgcolor: 'info.lighter',
            borderRadius: 1,
            border: '1px solid',
            borderColor: 'info.light'
          }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <CircularProgress size={16} thickness={5} />
              <Typography variant="body2" color="info.main" sx={{ fontWeight: 500 }}>
                {problem.extraction_status === 'PENDING' ? 'Queued for extraction...' : 'Extracting problem information...'}
              </Typography>
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
              This may take 30-60 seconds. The page will update automatically.
            </Typography>
          </Box>
        )}

        {problem.tags && problem.tags.length > 0 && (
          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mb: 1 }}>
            {problem.tags.map((tag, idx) => (
              <Chip
                key={idx}
                label={tag}
                size="small"
                color="primary"
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
          mt: 2
        }}>
          <Typography variant="caption" color="text.secondary" sx={{
            fontSize: { xs: '0.75rem', sm: '0.813rem' }
          }}>
            Language: {problem.language || 'N/A'}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{
            fontSize: { xs: '0.75rem', sm: '0.813rem' }
          }}>
            Created: {new Date(problem.created_at).toLocaleDateString()}
          </Typography>
          {!isDraft && problem.test_case_count !== undefined && (
            <Typography variant="caption" color="text.secondary" sx={{
              fontSize: { xs: '0.75rem', sm: '0.813rem' }
            }}>
              Test Cases: {problem.test_case_count}
            </Typography>
          )}
        </Box>
      </CardContent>
    </Card>
  );
};

  const renderJobCard = (job) => (
    <Card
      key={job.id}
      sx={{
        mb: 2,
        '&:hover': {
          boxShadow: 3,
          transform: 'translateY(-2px)',
          transition: 'all 0.3s ease'
        }
      }}
    >
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
              {job.title}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              {job.platform === 'baekjoon' ? 'Baekjoon' : 'Codeforces'} - {job.problem_id}
            </Typography>
          </Box>
          <Chip
            label={job.status}
            color={getStatusColor(job.status)}
            size="small"
          />
        </Box>

        {job.tags && job.tags.length > 0 && (
          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mb: 1 }}>
            {job.tags.map((tag, idx) => (
              <Chip
                key={idx}
                label={tag}
                size="small"
                color="primary"
                variant="outlined"
                sx={{ fontSize: '0.75rem' }}
              />
            ))}
          </Box>
        )}

        <Box sx={{ display: 'flex', gap: 2, mt: 2, alignItems: 'center' }}>
          <Typography variant="caption" color="text.secondary">
            Language: {job.language}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Created: {new Date(job.created_at).toLocaleDateString()}
          </Typography>
          {job.status === 'PROCESSING' && (
            <CircularProgress size={16} color="info" />
          )}
        </Box>

        {job.status === 'FAILED' && job.error_message && (
          <Box sx={{ mt: 2, p: 1, bgcolor: 'error.lighter', borderRadius: 1 }}>
            <Typography variant="caption" color="error">
              Error: {job.error_message}
            </Typography>
          </Box>
        )}

        {job.status === 'COMPLETED' && (
          <Button
            variant="outlined"
            size="small"
            sx={{ mt: 2 }}
            onClick={() => window.location.href = `/jobs?job_id=${job.id}`}
          >
            View Details
          </Button>
        )}
      </CardContent>
    </Card>
  );

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  const filteredDrafts = filterItems(drafts);
  const filteredRegistered = filterItems(registered);

  return (
    <Box>
      <Typography variant="h4" sx={{
        color: 'text.primary',
        fontWeight: 600,
        mb: 3,
        fontSize: { xs: '1.75rem', sm: '2rem', md: '2.125rem' }
      }}>
        Problems
      </Typography>

      <TextField
        fullWidth
        placeholder="Search by title, problem ID, platform, or tags..."
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        sx={{ mb: 3 }}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon sx={{ fontSize: { xs: '1.25rem', sm: '1.5rem' } }} />
            </InputAdornment>
          ),
          sx: {
            fontSize: { xs: '0.875rem', sm: '1rem' }
          }
        }}
      />

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          variant="fullWidth"
          sx={{
            '& .MuiTab-root': {
              fontSize: { xs: '0.813rem', sm: '0.875rem', md: '1rem' },
              minWidth: { xs: 'auto', sm: 120 }
            }
          }}
        >
          <Tab label={`Drafts (${drafts.length})`} />
          <Tab label={`Registered (${registered.length})`} />
        </Tabs>
      </Box>

      {activeTab === 0 && (
        <Box>
          {filteredDrafts.length === 0 ? (
            <Box sx={{ textAlign: 'center', py: 8 }}>
              <CodeIcon sx={{ fontSize: 64, color: 'action.disabled', mb: 2 }} />
              <Typography variant="h6" color="text.secondary">
                {searchQuery ? 'No drafts found matching your search' : 'No drafts yet'}
              </Typography>
            </Box>
          ) : (
            filteredDrafts.map(draft => renderProblemCard(draft, true))
          )}
        </Box>
      )}

      {activeTab === 1 && (
        <Box>
          {filteredRegistered.length === 0 ? (
            <Box sx={{ textAlign: 'center', py: 8 }}>
              <CodeIcon sx={{ fontSize: 64, color: 'action.disabled', mb: 2 }} />
              <Typography variant="h6" color="text.secondary">
                {searchQuery ? 'No registered problems found matching your search' : 'No registered problems yet'}
              </Typography>
            </Box>
          ) : (
            filteredRegistered.map(problem => renderProblemCard(problem, false))
          )}
        </Box>
      )}
    </Box>
  );
}

export default Problems;
