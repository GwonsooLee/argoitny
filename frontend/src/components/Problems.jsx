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
  Code as CodeIcon
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

  const fetchData = async () => {
    try {
      const [draftsResponse, registeredResponse] = await Promise.all([
        apiGet(API_ENDPOINTS.problemDrafts),
        apiGet(API_ENDPOINTS.problemRegistered)
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

  const getStatusColor = (status) => {
    const colors = {
      PENDING: 'warning',
      PROCESSING: 'info',
      COMPLETED: 'success',
      FAILED: 'error'
    };
    return colors[status] || 'default';
  };

  const renderProblemCard = (problem, isDraft = false) => (
    <Card
      key={problem.id}
      sx={{
        mb: 2,
        '&:hover': {
          boxShadow: 3,
          transform: 'translateY(-2px)',
          transition: 'all 0.3s ease'
        },
        cursor: 'pointer'
      }}
      onClick={() => onViewProblem(problem.platform, problem.problem_id)}
    >
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
              {problem.title}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              {problem.platform === 'baekjoon' ? 'Baekjoon' : 'Codeforces'} - {problem.problem_id}
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <IconButton
              size="small"
              color="primary"
              onClick={(e) => {
                e.stopPropagation();
                handleEditProblem(problem);
              }}
            >
              <EditIcon />
            </IconButton>
            {isDraft && (
              <IconButton
                size="small"
                color="secondary"
                onClick={(e) => {
                  e.stopPropagation();
                  handleGenerateScript(problem);
                }}
                disabled={executingJobs[problem.id] || !problem.solution_code || !problem.constraints}
              >
                <PlayArrowIcon />
              </IconButton>
            )}
          </Box>
        </Box>

        {problem.tags && problem.tags.length > 0 && (
          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mb: 1 }}>
            {problem.tags.map((tag, idx) => (
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

        <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
          <Typography variant="caption" color="text.secondary">
            Language: {problem.language || 'N/A'}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Created: {new Date(problem.created_at).toLocaleDateString()}
          </Typography>
          {!isDraft && problem.test_case_count !== undefined && (
            <Typography variant="caption" color="text.secondary">
              Test Cases: {problem.test_case_count}
            </Typography>
          )}
        </Box>
      </CardContent>
    </Card>
  );

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
      <Typography variant="h4" sx={{ color: 'text.primary', fontWeight: 600, mb: 3 }}>
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
              <SearchIcon />
            </InputAdornment>
          ),
        }}
      />

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
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
