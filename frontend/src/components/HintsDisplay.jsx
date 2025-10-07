import { useState } from 'react';
import {
  Box,
  Typography,
  Paper,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Button,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Card,
  CardContent,
  Chip,
  Alert,
  CircularProgress,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Lightbulb as LightbulbIcon,
  LightbulbOutlined as LightbulbOutlinedIcon,
  NavigateNext as NavigateNextIcon,
  NavigateBefore as NavigateBeforeIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon
} from '@mui/icons-material';

/**
 * HintsDisplay Component
 *
 * Displays hints for failed test cases in multiple formats:
 * - Step-by-step stepper (default)
 * - All-at-once accordion
 * - Card-based layout
 *
 * @param {Object} props
 * @param {Array} props.hints - Array of hint strings or hint objects
 * @param {boolean} props.loading - Whether hints are being loaded
 * @param {string} props.error - Error message if hint loading failed
 * @param {string} props.displayMode - 'stepper', 'accordion', or 'cards' (default: 'stepper')
 */
function HintsDisplay({ hints = [], loading = false, error = null, displayMode = 'accordion' }) {
  // Normalize hints to array of objects
  const normalizedHints = (hints || []).map((hint, index) => {
    if (typeof hint === 'string') {
      return {
        title: `힌트 ${index + 1}`,
        content: hint
      };
    }
    return hint;
  });

  const [activeStep, setActiveStep] = useState(0);
  const [revealedHints, setRevealedHints] = useState(new Set([0]));

  const handleNext = () => {
    const nextStep = activeStep + 1;
    setActiveStep(nextStep);
    setRevealedHints(prev => new Set([...prev, nextStep]));
  };

  const handleBack = () => {
    setActiveStep(prev => prev - 1);
  };

  const handleStepClick = (step) => {
    setActiveStep(step);
    setRevealedHints(prev => new Set([...prev, step]));
  };

  const handleRevealAll = () => {
    setRevealedHints(new Set(normalizedHints.map((_, index) => index)));
  };

  const handleHideAll = () => {
    setRevealedHints(new Set([0]));
    setActiveStep(0);
  };

  if (loading) {
    return (
      <Paper sx={{ p: 3, mt: 3, textAlign: 'center' }}>
        <CircularProgress sx={{ mb: 2 }} />
        <Typography variant="body1" color="text.secondary">
          Generating hints for your code...
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          This may take a few moments
        </Typography>
      </Paper>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 3 }}>
        <Typography variant="body2" sx={{ fontWeight: 600 }}>
          Failed to load hints
        </Typography>
        <Typography variant="body2">
          {error}
        </Typography>
      </Alert>
    );
  }

  if (!normalizedHints || normalizedHints.length === 0) {
    return (
      <Alert severity="info" sx={{ mt: 3 }}>
        No hints available for this execution
      </Alert>
    );
  }

  // Stepper Mode (Step-by-step revelation)
  if (displayMode === 'stepper') {
    return (
      <Paper sx={{ p: { xs: 2, sm: 3 }, mt: 3, backgroundColor: '#fef9e7' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <LightbulbIcon sx={{ color: '#f57c00', fontSize: { xs: '1.5rem', sm: '1.75rem' } }} />
            <Typography variant="h6" sx={{
              fontWeight: 600,
              color: '#e65100',
              fontSize: { xs: '1.125rem', sm: '1.25rem' }
            }}>
              Debugging Hints
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Tooltip title="Reveal all hints">
              <IconButton
                size="small"
                onClick={handleRevealAll}
                disabled={revealedHints.size === hints.length}
                sx={{ color: '#f57c00' }}
              >
                <VisibilityIcon fontSize="small" />
              </IconButton>
            </Tooltip>
            <Tooltip title="Hide all hints">
              <IconButton
                size="small"
                onClick={handleHideAll}
                disabled={revealedHints.size === 1 && revealedHints.has(0)}
                sx={{ color: '#f57c00' }}
              >
                <VisibilityOffIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          </Box>
        </Box>

        <Alert severity="info" sx={{ mb: 3, backgroundColor: '#e3f2fd' }}>
          <Typography variant="body2">
            Click on each step to reveal hints progressively. Try to solve the problem yourself before revealing all hints!
          </Typography>
        </Alert>

        <Stepper activeStep={activeStep} orientation="vertical">
          {normalizedHints.map((hint, index) => (
            <Step key={index} expanded={revealedHints.has(index)}>
              <StepLabel
                onClick={() => handleStepClick(index)}
                sx={{
                  cursor: 'pointer',
                  '& .MuiStepLabel-label': {
                    fontWeight: 600,
                    fontSize: { xs: '0.875rem', sm: '1rem' },
                    color: revealedHints.has(index) ? '#e65100' : 'text.secondary'
                  }
                }}
                StepIconComponent={() => (
                  <Box sx={{
                    width: 32,
                    height: 32,
                    borderRadius: '50%',
                    backgroundColor: revealedHints.has(index) ? '#f57c00' : '#e0e0e0',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white',
                    fontWeight: 600,
                    fontSize: '0.875rem'
                  }}>
                    {revealedHints.has(index) ? (
                      <LightbulbIcon sx={{ fontSize: '1.125rem' }} />
                    ) : (
                      <LightbulbOutlinedIcon sx={{ fontSize: '1.125rem' }} />
                    )}
                  </Box>
                )}
              >
                {hint.title}
              </StepLabel>
              <StepContent>
                <Paper
                  elevation={0}
                  sx={{
                    p: { xs: 1.5, sm: 2 },
                    backgroundColor: 'white',
                    border: '2px solid #ffe0b2',
                    borderRadius: 1,
                    mb: 2
                  }}
                >
                  <Typography
                    variant="body2"
                    sx={{
                      whiteSpace: 'pre-wrap',
                      lineHeight: 1.6,
                      fontSize: { xs: '0.875rem', sm: '0.938rem' }
                    }}
                  >
                    {hint.content}
                  </Typography>
                </Paper>
                <Box sx={{ mb: 2, display: 'flex', gap: 1 }}>
                  {index < normalizedHints.length - 1 && (
                    <Button
                      variant="contained"
                      onClick={handleNext}
                      size="small"
                      endIcon={<NavigateNextIcon />}
                      sx={{
                        backgroundColor: '#f57c00',
                        '&:hover': { backgroundColor: '#e65100' },
                        fontSize: { xs: '0.75rem', sm: '0.813rem' }
                      }}
                    >
                      Next Hint
                    </Button>
                  )}
                  {index > 0 && (
                    <Button
                      variant="outlined"
                      onClick={handleBack}
                      size="small"
                      startIcon={<NavigateBeforeIcon />}
                      sx={{
                        borderColor: '#f57c00',
                        color: '#f57c00',
                        fontSize: { xs: '0.75rem', sm: '0.813rem' }
                      }}
                    >
                      Previous
                    </Button>
                  )}
                </Box>
              </StepContent>
            </Step>
          ))}
        </Stepper>

        {activeStep === normalizedHints.length - 1 && revealedHints.has(normalizedHints.length - 1) && (
          <Alert severity="success" sx={{ mt: 2 }}>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              You've reviewed all hints!
            </Typography>
            <Typography variant="body2">
              Try to apply these suggestions to fix your code.
            </Typography>
          </Alert>
        )}
      </Paper>
    );
  }

  // Accordion Mode (All hints visible, can expand/collapse)
  if (displayMode === 'accordion') {
    return (
      <Paper sx={{ p: { xs: 2, sm: 3 }, mt: 3, backgroundColor: '#fef9e7' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
          <LightbulbIcon sx={{ color: '#f57c00', fontSize: { xs: '1.5rem', sm: '1.75rem' } }} />
          <Typography variant="h6" sx={{
            fontWeight: 600,
            color: '#e65100',
            fontSize: { xs: '1.125rem', sm: '1.25rem' }
          }}>
            Debugging Hints
          </Typography>
          <Chip
            label={`${normalizedHints.length} hints`}
            size="small"
            sx={{
              backgroundColor: '#f57c00',
              color: 'white',
              fontWeight: 600,
              ml: 'auto'
            }}
          />
        </Box>

        {normalizedHints.map((hint, index) => (
          <Accordion
            key={index}
            sx={{
              mb: 1,
              backgroundColor: 'white',
              border: '2px solid #ffe0b2',
              borderRadius: 1,
              '&:before': { display: 'none' },
              '&.Mui-expanded': {
                margin: '0 0 8px 0'
              }
            }}
          >
            <AccordionSummary
              expandIcon={<ExpandMoreIcon sx={{ color: '#f57c00' }} />}
              sx={{
                '&:hover': { backgroundColor: '#fff8e1' },
                minHeight: 48,
                '&.Mui-expanded': { minHeight: 48 }
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                <Box sx={{
                  width: 28,
                  height: 28,
                  borderRadius: '50%',
                  backgroundColor: '#f57c00',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'white',
                  fontWeight: 700,
                  fontSize: '0.875rem'
                }}>
                  {index + 1}
                </Box>
                <Typography sx={{
                  fontWeight: 600,
                  color: '#e65100',
                  fontSize: { xs: '0.875rem', sm: '1rem' }
                }}>
                  {hint.title}
                </Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails sx={{
              backgroundColor: '#fffbf0',
              borderTop: '1px solid #ffe0b2',
              p: { xs: 1.5, sm: 2 }
            }}>
              <Typography
                variant="body2"
                sx={{
                  whiteSpace: 'pre-wrap',
                  lineHeight: 1.6,
                  fontSize: { xs: '0.875rem', sm: '0.938rem' }
                }}
              >
                {hint.content}
              </Typography>
            </AccordionDetails>
          </Accordion>
        ))}
      </Paper>
    );
  }

  // Card Mode (All hints visible as cards)
  if (displayMode === 'cards') {
    return (
      <Paper sx={{ p: { xs: 2, sm: 3 }, mt: 3, backgroundColor: '#fef9e7' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
          <LightbulbIcon sx={{ color: '#f57c00', fontSize: { xs: '1.5rem', sm: '1.75rem' } }} />
          <Typography variant="h6" sx={{
            fontWeight: 600,
            color: '#e65100',
            fontSize: { xs: '1.125rem', sm: '1.25rem' }
          }}>
            Debugging Hints
          </Typography>
          <Chip
            label={`${normalizedHints.length} hints`}
            size="small"
            sx={{
              backgroundColor: '#f57c00',
              color: 'white',
              fontWeight: 600,
              ml: 'auto'
            }}
          />
        </Box>

        <Box sx={{
          display: 'grid',
          gridTemplateColumns: {
            xs: '1fr',
            md: normalizedHints.length > 1 ? 'repeat(2, 1fr)' : '1fr'
          },
          gap: 2
        }}>
          {normalizedHints.map((hint, index) => (
            <Card
              key={index}
              sx={{
                border: '2px solid #ffe0b2',
                backgroundColor: 'white',
                transition: 'all 0.3s ease',
                '&:hover': {
                  boxShadow: 3,
                  borderColor: '#f57c00'
                }
              }}
            >
              <CardContent sx={{ p: { xs: 2, sm: 2.5 } }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
                  <Box sx={{
                    width: 36,
                    height: 36,
                    borderRadius: '50%',
                    backgroundColor: '#f57c00',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}>
                    <LightbulbIcon sx={{ color: 'white', fontSize: '1.25rem' }} />
                  </Box>
                  <Typography variant="h6" sx={{
                    fontWeight: 600,
                    color: '#e65100',
                    fontSize: { xs: '0.938rem', sm: '1.063rem' }
                  }}>
                    {hint.title}
                  </Typography>
                </Box>
                <Typography
                  variant="body2"
                  sx={{
                    whiteSpace: 'pre-wrap',
                    lineHeight: 1.6,
                    fontSize: { xs: '0.875rem', sm: '0.938rem' },
                    color: 'text.primary'
                  }}
                >
                  {hint.content}
                </Typography>
              </CardContent>
            </Card>
          ))}
        </Box>
      </Paper>
    );
  }

  return null;
}

export default HintsDisplay;
