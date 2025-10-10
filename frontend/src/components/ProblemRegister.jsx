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
  Accordion,
  AccordionSummary,
  AccordionDetails,
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
import { Add as AddIcon, CheckCircle as CheckCircleIcon, ExpandMore as ExpandMoreIcon } from '@mui/icons-material';
import { apiPost, apiGet, apiPatch } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';

function ProblemRegister({ onBack }) {
  const [problemUrl, setProblemUrl] = useState('');
  const [samples, setSamples] = useState([{ input: '', output: '' }]);
  const [submitting, setSubmitting] = useState(false);
  const [submittedJobs, setSubmittedJobs] = useState([]);
  const [error, setError] = useState('');

  // LLM Configuration State
  const [llmModel, setLlmModel] = useState('gpt-5');
  const [reasoningEffort, setReasoningEffort] = useState('medium');
  const [maxOutputTokens, setMaxOutputTokens] = useState(8192);

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
        samples: validSamples.length > 0 ? validSamples : [],
        llm_config: {
          model: llmModel,
          reasoning_effort: reasoningEffort,
          max_output_tokens: maxOutputTokens
        }
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
            Supported platform: Codeforces
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

          <Divider sx={{ my: 3 }} />

          {/* LLM Configuration Section */}
          <Accordion sx={{ mb: 2, boxShadow: 'none', border: '1px solid', borderColor: 'divider' }}>
            <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              sx={{ bgcolor: 'grey.50' }}
            >
              <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                LLM Configuration (Advanced Settings)
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', mb: 2 }}>
                Configure the AI model settings for problem extraction and solution generation.
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
                    disabled={submitting}
                  >
                    <FormControlLabel
                      value="gpt-5"
                      control={<Radio />}
                      label="GPT-5"
                      disabled={submitting}
                    />
                    <FormControlLabel
                      value="gemini"
                      control={<Radio />}
                      label="Gemini"
                      disabled={submitting}
                    />
                  </RadioGroup>
                  <FormHelperText>Select the AI model to use for problem extraction</FormHelperText>
                </FormControl>

                {/* GPT-5 Specific Configuration */}
                {llmModel === 'gpt-5' && (
                  <>
                    {/* Reasoning Effort */}
                    <FormControl fullWidth>
                      <InputLabel id="reasoning-effort-label">Reasoning Effort</InputLabel>
                      <Select
                        labelId="reasoning-effort-label"
                        value={reasoningEffort}
                        label="Reasoning Effort"
                        onChange={(e) => handleReasoningEffortChange(e.target.value)}
                        disabled={submitting}
                      >
                        <MenuItem value="low">Low</MenuItem>
                        <MenuItem value="medium">Medium</MenuItem>
                        <MenuItem value="high">High</MenuItem>
                      </Select>
                      <FormHelperText>
                        Higher reasoning uses more tokens but may produce better solutions. High reasoning is recommended for complex problems.
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
                        disabled={submitting}
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
                      disabled={submitting}
                    >
                      Reset to Defaults
                    </Button>
                  </Box>
                )}
              </Box>
            </AccordionDetails>
          </Accordion>
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
                        Codeforces - {job.problem_identifier}
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
