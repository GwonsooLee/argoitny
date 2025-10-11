import { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio,
  Select,
  MenuItem,
  InputLabel,
  FormHelperText,
  Chip,
  Alert,
  Skeleton,
  Tooltip,
  IconButton,
  Collapse,
  Card,
  CardContent,
  Grid,
  Divider,
} from '@mui/material';
import {
  Info as InfoIcon,
  Speed as SpeedIcon,
  AttachMoney as MoneyIcon,
  Psychology as ReasoningIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  CheckCircle as CheckCircleIcon,
} from '@mui/icons-material';
import { apiGet } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';

function ModelSelector({ selectedModel, onModelChange, reasoningEffort, onReasoningEffortChange, maxOutputTokens, onMaxOutputTokensChange, disabled = false }) {
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    fetchModels();
  }, []);

  const fetchModels = async () => {
    try {
      const response = await apiGet(API_ENDPOINTS.availableModels);
      if (!response.ok) {
        throw new Error('Failed to fetch available models');
      }
      const data = await response.json();
      setModels(data.models || []);
    } catch (error) {
      console.error('Error fetching models:', error);
      setError('Failed to load model options. Using defaults.');
    } finally {
      setLoading(false);
    }
  };

  const getModelDetails = (modelId) => {
    return models.find(m => m.id === modelId);
  };

  const currentModel = getModelDetails(selectedModel);

  const getDifficultyColor = (difficulty) => {
    if (difficulty.includes('1000')) return 'success';
    if (difficulty.includes('1500')) return 'info';
    if (difficulty.includes('2000')) return 'warning';
    return 'default';
  };

  const handleReasoningEffortChange = (value) => {
    onReasoningEffortChange(value);
    // Auto-adjust tokens for high reasoning
    if (value === 'high' && maxOutputTokens < 96000) {
      onMaxOutputTokensChange(128000);
    }
  };

  if (loading) {
    return (
      <Box>
        <Skeleton variant="text" width="40%" height={40} sx={{ mb: 2 }} />
        <Skeleton variant="rectangular" height={200} sx={{ borderRadius: 1 }} />
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1 }}>
        <Typography variant="h6" sx={{ fontWeight: 600 }}>
          Model Selection for Solution Generation
        </Typography>
        <Tooltip title="Choose the AI model that will generate your solution. Different models have different capabilities and costs.">
          <IconButton size="small">
            <InfoIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Box>

      {error && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Alert severity="info" sx={{ mb: 3, display: 'flex', alignItems: 'center' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <CheckCircleIcon fontSize="small" />
          <Typography variant="body2">
            <strong>Note:</strong> Problem metadata extraction always uses Gemini Flash (most cost-effective). The model selected here is used only for solution generation.
          </Typography>
        </Box>
      </Alert>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        {models.map((model) => {
          const isSelected = selectedModel === model.id;
          const isDefault = model.is_default;

          return (
            <Grid item xs={12} key={model.id}>
              <Card
                sx={{
                  cursor: disabled ? 'not-allowed' : 'pointer',
                  border: 2,
                  borderColor: isSelected ? 'primary.main' : 'divider',
                  bgcolor: isSelected ? 'primary.light' : 'background.paper',
                  transition: 'all 0.2s',
                  opacity: disabled ? 0.6 : 1,
                  '&:hover': disabled ? {} : {
                    borderColor: 'primary.main',
                    boxShadow: 2,
                  },
                }}
                onClick={() => !disabled && onModelChange(model.id)}
              >
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                    <Box sx={{ flex: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                        <Radio
                          checked={isSelected}
                          disabled={disabled}
                          sx={{ p: 0 }}
                        />
                        <Typography variant="h6" sx={{ fontWeight: 600 }}>
                          {model.name}
                        </Typography>
                        {isDefault && (
                          <Chip
                            label="Default"
                            size="small"
                            color="primary"
                            variant="outlined"
                          />
                        )}
                        <Chip
                          label={model.provider}
                          size="small"
                          variant="outlined"
                        />
                      </Box>

                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2, ml: 4 }}>
                        {model.description}
                      </Typography>

                      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', ml: 4 }}>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <MoneyIcon fontSize="small" color="primary" />
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {model.cost?.estimated_per_problem || 'N/A'}/problem
                          </Typography>
                        </Box>

                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <SpeedIcon fontSize="small" color="action" />
                          <Typography variant="body2" color="text.secondary">
                            {model.features?.speed || 'fast'}
                          </Typography>
                        </Box>

                        {model.features?.reasoning_effort && (
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <ReasoningIcon fontSize="small" color="action" />
                            <Typography variant="body2" color="text.secondary">
                              Reasoning: {model.features.reasoning_effort.join(', ')}
                            </Typography>
                          </Box>
                        )}
                      </Box>

                      <Box sx={{ mt: 2, ml: 4 }}>
                        <Typography variant="caption" color="text.secondary" sx={{ mr: 1 }}>
                          Best for:
                        </Typography>
                        {model.recommended_for?.map((difficulty, idx) => (
                          <Chip
                            key={idx}
                            label={difficulty}
                            size="small"
                            color={getDifficultyColor(difficulty)}
                            sx={{ mr: 0.5, mb: 0.5 }}
                          />
                        ))}
                      </Box>
                    </Box>
                  </Box>
                </CardContent>
              </Card>
            </Grid>
          );
        })}
      </Grid>

      {currentModel && selectedModel === 'gpt-5' && (
        <Paper
          sx={{
            p: 3,
            bgcolor: 'grey.50',
            border: '1px solid',
            borderColor: 'divider',
          }}
        >
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              cursor: 'pointer',
              mb: showDetails ? 2 : 0,
            }}
            onClick={() => setShowDetails(!showDetails)}
          >
            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
              GPT-5 Advanced Configuration
            </Typography>
            <IconButton size="small">
              {showDetails ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Box>

          <Collapse in={showDetails}>
            <Divider sx={{ mb: 2 }} />

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
              <FormControl fullWidth>
                <InputLabel id="reasoning-effort-label">Reasoning Effort</InputLabel>
                <Select
                  labelId="reasoning-effort-label"
                  value={reasoningEffort}
                  label="Reasoning Effort"
                  onChange={(e) => handleReasoningEffortChange(e.target.value)}
                  disabled={disabled}
                >
                  <MenuItem value="low">
                    <Box>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>Low</Typography>
                      <Typography variant="caption" color="text.secondary">
                        Fastest, uses fewer tokens
                      </Typography>
                    </Box>
                  </MenuItem>
                  <MenuItem value="medium">
                    <Box>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>Medium</Typography>
                      <Typography variant="caption" color="text.secondary">
                        Balanced performance (Recommended)
                      </Typography>
                    </Box>
                  </MenuItem>
                  <MenuItem value="high">
                    <Box>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>High</Typography>
                      <Typography variant="caption" color="text.secondary">
                        Most thorough, uses more tokens
                      </Typography>
                    </Box>
                  </MenuItem>
                </Select>
                <FormHelperText>
                  Higher reasoning uses more tokens but may produce better solutions for complex problems.
                </FormHelperText>
              </FormControl>

              <FormControl fullWidth>
                <InputLabel id="max-tokens-label">Max Output Tokens</InputLabel>
                <Select
                  labelId="max-tokens-label"
                  value={maxOutputTokens}
                  label="Max Output Tokens"
                  onChange={(e) => onMaxOutputTokensChange(e.target.value)}
                  disabled={disabled}
                >
                  <MenuItem value={4096}>4,096 tokens</MenuItem>
                  <MenuItem value={8192}>8,192 tokens (Default)</MenuItem>
                  <MenuItem value={16384}>16,384 tokens</MenuItem>
                  <MenuItem value={32768}>32,768 tokens</MenuItem>
                  <MenuItem value={65536}>65,536 tokens</MenuItem>
                  <MenuItem value={128000}>128,000 tokens (High Reasoning)</MenuItem>
                </Select>
                <FormHelperText
                  error={reasoningEffort === 'high' && maxOutputTokens < 96000}
                >
                  {reasoningEffort === 'high' && maxOutputTokens < 96000
                    ? 'Warning: High reasoning effort requires at least 96,000 tokens. Consider using 128,000.'
                    : 'Controls the maximum length of the generated solution. Higher values allow for more detailed solutions.'}
                </FormHelperText>
              </FormControl>
            </Box>
          </Collapse>
        </Paper>
      )}

      {currentModel && selectedModel !== 'gpt-5' && (
        <Alert severity="info" sx={{ mt: 2 }}>
          <Typography variant="body2">
            <strong>{currentModel.name}</strong> uses optimized settings for consistent results. No additional configuration is required.
          </Typography>
        </Alert>
      )}
    </Box>
  );
}

export default ModelSelector;
