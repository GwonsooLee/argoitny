import { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Alert,
  CircularProgress,
  Link,
  List,
  ListItem,
  ListItemText,
  Chip,
  Divider,
} from '@mui/material';
import { Add as AddIcon, CheckCircle as CheckCircleIcon } from '@mui/icons-material';
import { apiPost, apiGet, apiPatch } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';

function ProblemRegister({ onBack }) {
  const [problemUrl, setProblemUrl] = useState('');
  const [samples, setSamples] = useState([{ input: '', output: '' }]);
  const [submitting, setSubmitting] = useState(false);
  const [submittedJobs, setSubmittedJobs] = useState([]);
  const [error, setError] = useState('');

  // Edit mode state
  const [editMode, setEditMode] = useState(false);
  const [editDraft, setEditDraft] = useState(null);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    title: '',
    problem_url: '',
    tags: '',
    solution_code: '',
    language: 'python',
    constraints: ''
  });

  // Check for draft_id in URL
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const draftId = urlParams.get('draft_id');

    if (draftId) {
      loadDraft(draftId);
    }
  }, []);

  const loadDraft = async (draftId) => {
    setLoading(true);
    try {
      const response = await apiGet(`${API_ENDPOINTS.problems}${draftId}/`, { requireAuth: true });

      if (!response.ok) {
        throw new Error('Failed to load draft');
      }

      const data = await response.json();
      setEditDraft(data);
      setEditMode(true);

      // Populate form with existing data
      setFormData({
        title: data.title || '',
        problem_url: data.problem_url || '',
        tags: Array.isArray(data.tags) ? data.tags.join(', ') : '',
        solution_code: data.solution_code || '',
        language: data.language || 'python',
        constraints: data.constraints || ''
      });
    } catch (error) {
      console.error('Error loading draft:', error);
      setError('Failed to load draft problem');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!problemUrl.trim()) {
      setError('Please enter a problem URL');
      return;
    }

    setSubmitting(true);
    setError('');

    try {
      // Filter out empty samples
      const validSamples = samples.filter(s => s.input.trim() && s.output.trim());

      const response = await apiPost(API_ENDPOINTS.extractProblemInfo, {
        problem_url: problemUrl.trim(),
        samples: validSamples.length > 0 ? validSamples : []
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to submit problem URL');
      }

      const data = await response.json();

      // Add to submitted jobs list
      setSubmittedJobs([
        {
          url: problemUrl.trim(),
          problem_id: data.problem_id,
          problem_identifier: data.problem_identifier,
          job_id: data.job_id,
          platform: data.platform,
          timestamp: new Date().toISOString(),
          already_exists: data.already_exists || false,
          message: data.message
        },
        ...submittedJobs
      ]);

      // Clear inputs
      setProblemUrl('');
      setSamples([{ input: '', output: '' }]);
    } catch (error) {
      console.error('Error submitting problem URL:', error);
      setError(error.message || 'Failed to submit problem URL');
    } finally {
      setSubmitting(false);
    }
  };

  const handleAddSample = () => {
    setSamples([...samples, { input: '', output: '' }]);
  };

  const handleRemoveSample = (index) => {
    if (samples.length > 1) {
      setSamples(samples.filter((_, i) => i !== index));
    }
  };

  const handleSampleChange = (index, field, value) => {
    const newSamples = [...samples];
    newSamples[index][field] = value;
    setSamples(newSamples);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !submitting) {
      handleSubmit();
    }
  };

  const handleFormChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const handleSaveEdit = async () => {
    if (!formData.title.trim()) {
      setError('Title is required');
      return;
    }

    setSubmitting(true);
    setError('');

    try {
      // Convert tags string to array
      const tagsArray = formData.tags
        .split(',')
        .map(tag => tag.trim())
        .filter(tag => tag.length > 0);

      const updateData = {
        title: formData.title,
        problem_url: formData.problem_url,
        tags: tagsArray,
        solution_code: formData.solution_code,
        language: formData.language,
        constraints: formData.constraints
      };

      const response = await apiPost(API_ENDPOINTS.saveProblem, {
        id: editDraft.id,
        ...updateData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to update problem');
      }

      // Redirect back to problem detail page
      window.location.href = `/problems/${editDraft.platform}/${editDraft.problem_id}`;
    } catch (error) {
      console.error('Error updating problem:', error);
      setError(error.message || 'Failed to update problem');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" sx={{
        color: 'text.primary',
        fontWeight: 600,
        mb: 3,
        fontSize: { xs: '1.75rem', sm: '2rem', md: '2.125rem' }
      }}>
        {editMode ? 'Edit Problem' : 'Register New Problem'}
      </Typography>

      {editMode ? (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="body1" sx={{ mb: 3, color: 'text.secondary' }}>
            Edit problem metadata. Test cases cannot be modified here.
          </Typography>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              fullWidth
              label="Title"
              value={formData.title}
              onChange={(e) => handleFormChange('title', e.target.value)}
              disabled={submitting}
              required
            />

            <TextField
              fullWidth
              label="Problem URL"
              value={formData.problem_url}
              onChange={(e) => handleFormChange('problem_url', e.target.value)}
              disabled={submitting}
            />

            <TextField
              fullWidth
              label="Tags (comma-separated)"
              value={formData.tags}
              onChange={(e) => handleFormChange('tags', e.target.value)}
              disabled={submitting}
              placeholder="dynamic-programming, graphs, greedy"
            />

            <TextField
              fullWidth
              label="Language"
              value={formData.language}
              onChange={(e) => handleFormChange('language', e.target.value)}
              disabled={submitting}
            />

            <TextField
              fullWidth
              label="Solution Code"
              value={formData.solution_code}
              onChange={(e) => handleFormChange('solution_code', e.target.value)}
              disabled={submitting}
              multiline
              rows={10}
            />

            <TextField
              fullWidth
              label="Constraints"
              value={formData.constraints}
              onChange={(e) => handleFormChange('constraints', e.target.value)}
              disabled={submitting}
              multiline
              rows={4}
              placeholder="1 <= n <= 10^5"
            />

            {error && (
              <Alert severity="error">{error}</Alert>
            )}

            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
              <Button
                variant="outlined"
                onClick={() => window.history.back()}
                disabled={submitting}
              >
                Cancel
              </Button>
              <Button
                variant="contained"
                onClick={handleSaveEdit}
                disabled={submitting || !formData.title.trim()}
                startIcon={submitting ? <CircularProgress size={20} /> : null}
              >
                {submitting ? 'Saving...' : 'Save Changes'}
              </Button>
            </Box>
          </Box>
        </Paper>
      ) : (
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="body1" sx={{ mb: 2, color: 'text.secondary' }}>
            Enter a problem URL to start extraction. The problem will be added as a draft and processed in the background.
          </Typography>

          <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
            <TextField
              fullWidth
              label="Problem URL"
              placeholder="https://codeforces.com/problemset/problem/1520/E"
              value={problemUrl}
              onChange={(e) => setProblemUrl(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={submitting}
              error={!!error}
              helperText={error}
            />
            <Button
              variant="contained"
              onClick={handleSubmit}
              disabled={submitting || !problemUrl.trim()}
              startIcon={submitting ? <CircularProgress size={20} /> : <AddIcon />}
              sx={{ minWidth: 120, height: 56 }}
            >
              {submitting ? 'Adding...' : 'Add'}
            </Button>
          </Box>

          <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 2 }}>
            Supported platforms: Codeforces, Baekjoon
          </Typography>

          <Divider sx={{ my: 2 }} />

          <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
            Sample Test Cases (Optional)
          </Typography>
          <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 2 }}>
            Provide sample input/output pairs to validate the generated solution. Leave empty to extract from the problem page.
          </Typography>

          {samples.map((sample, index) => (
            <Box key={index} sx={{ mb: 2, p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 1 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                <Typography variant="subtitle2">Sample {index + 1}</Typography>
                {samples.length > 1 && (
                  <Button
                    size="small"
                    color="error"
                    onClick={() => handleRemoveSample(index)}
                    disabled={submitting}
                  >
                    Remove
                  </Button>
                )}
              </Box>
              <TextField
                fullWidth
                label="Input"
                placeholder="Sample input (e.g., 3\n1 2 3)"
                value={sample.input}
                onChange={(e) => handleSampleChange(index, 'input', e.target.value)}
                disabled={submitting}
                multiline
                rows={3}
                sx={{ mb: 1 }}
              />
              <TextField
                fullWidth
                label="Expected Output"
                placeholder="Expected output (e.g., 6)"
                value={sample.output}
                onChange={(e) => handleSampleChange(index, 'output', e.target.value)}
                disabled={submitting}
                multiline
                rows={2}
              />
            </Box>
          ))}

          <Button
            variant="outlined"
            startIcon={<AddIcon />}
            onClick={handleAddSample}
            disabled={submitting}
            sx={{ mb: 2 }}
          >
            Add Sample
          </Button>
        </Paper>
      )}

      {!editMode && submittedJobs.length > 0 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
            Submitted Jobs
          </Typography>

          <List>
            {submittedJobs.map((job, index) => (
              <ListItem
                key={index}
                sx={{
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                  mb: 1,
                  bgcolor: 'background.paper'
                }}
              >
                <CheckCircleIcon sx={{ color: job.already_exists ? 'success.main' : 'info.main', mr: 2 }} />
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                      <Typography variant="body1" sx={{ fontWeight: 500 }}>
                        {job.platform === 'baekjoon' ? 'Baekjoon' : 'Codeforces'} - {job.problem_identifier}
                      </Typography>
                      <Chip
                        label={
                          job.already_exists && job.status === 'COMPLETED'
                            ? "Already Registered"
                            : job.already_exists
                            ? "Already Exists"
                            : "Processing"
                        }
                        color={
                          job.already_exists && job.status === 'COMPLETED'
                            ? "success"
                            : job.already_exists
                            ? "warning"
                            : "info"
                        }
                        size="small"
                      />
                    </Box>
                  }
                  secondary={
                    <Box>
                      <Typography variant="body2" sx={{ color: 'text.secondary', mb: 0.5 }}>
                        {job.url}
                      </Typography>
                      <Link
                        href={`/problems/${job.platform}/${job.problem_identifier}`}
                        sx={{ fontSize: '0.875rem' }}
                      >
                        View Draft →
                      </Link>
                    </Box>
                  }
                />
              </ListItem>
            ))}
          </List>

          <Alert severity="info" sx={{ mt: 2 }}>
            Problems are being processed in the background. You can view them in the Problems page.
          </Alert>
        </Paper>
      )}
    </Box>
  );
}

export default ProblemRegister;
