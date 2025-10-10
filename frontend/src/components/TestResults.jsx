import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Grid,
  Alert,
  IconButton,
  Button,
  Snackbar,
  CircularProgress
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Download as DownloadIcon,
  Lightbulb as LightbulbIcon
} from '@mui/icons-material';
import { apiPost, apiGet } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';
import HintsDisplay from './HintsDisplay';

function TestResults({ results, executionId, onHintsLoadingChange }) {
  // Handle both old format (array) and new format (object with results and summary)
  const testResults = Array.isArray(results) ? results : (results?.results || []);
  const summary = results?.summary || {
    passed: testResults.filter(r => r.passed).length,
    failed: testResults.filter(r => !r.passed).length,
    total: testResults.length,
  };

  // Hints state
  const [hints, setHints] = useState(null);
  const [hintsLoading, setHintsLoading] = useState(false);
  const [hintsError, setHintsError] = useState(null);
  const [hintsRequested, setHintsRequested] = useState(false);
  const [pollingInterval, setPollingInterval] = useState(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });

  // Check if test cases have failed (to show "Get Hints" button)
  const hasFailedTests = summary.failed > 0;

  // Clean up polling on unmount
  useEffect(() => {
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, [pollingInterval]);

  // Notify parent when hints loading state changes
  useEffect(() => {
    if (onHintsLoadingChange) {
      onHintsLoadingChange(hintsLoading);
    }
  }, [hintsLoading, onHintsLoadingChange]);

  const showSnackbar = (message, severity = 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  const requestHints = async () => {
    if (!executionId) {
      showSnackbar('Cannot request hints: No execution ID available', 'error');
      return;
    }

    setHintsLoading(true);
    setHintsError(null);
    setHintsRequested(true);

    try {
      // Request hints generation
      const response = await apiPost(
        API_ENDPOINTS.requestHints(executionId),
        {},
        { requireAuth: true }
      );

      if (!response.ok) {
        // Check if it's a rate limit error (429)
        if (response.status === 429) {
          const errorData = await response.json();
          throw new Error('RATE_LIMIT_EXCEEDED');
        }
        // Check if feature is not implemented (501)
        if (response.status === 501) {
          throw new Error('FEATURE_NOT_IMPLEMENTED');
        }
        throw new Error('Failed to request hints');
      }

      const data = await response.json();

      // If hints are immediately available
      if (data.hints && data.hints.length > 0) {
        setHints(data.hints);
        setHintsLoading(false);
        showSnackbar('Hints loaded successfully!', 'success');
      } else {
        // Start polling for hints
        showSnackbar('Generating hints... This may take a moment', 'info');
        startPollingForHints();
      }
    } catch (error) {
      console.error('Error requesting hints:', error);

      // Show user-friendly message for rate limit
      if (error.message === 'RATE_LIMIT_EXCEEDED') {
        setHintsError('You have reached your plan limit for hints. Please upgrade your plan to continue.');
        showSnackbar('Plan limit reached. Please upgrade to get more hints.', 'warning');
      } else if (error.message === 'FEATURE_NOT_IMPLEMENTED') {
        setHintsError('Hint generation is currently disabled. This feature will be available soon.');
        showSnackbar('Hint feature is temporarily disabled', 'info');
      } else {
        setHintsError(error.message || 'Failed to request hints');
        showSnackbar('Failed to request hints', 'error');
      }

      setHintsLoading(false);
      setHintsRequested(false); // Reset so button reappears
    }
  };

  const startPollingForHints = () => {
    let pollCount = 0;
    const maxPolls = 36; // Poll for up to 180 seconds (36 * 5s = 3 minutes)

    const interval = setInterval(async () => {
      pollCount++;

      try {
        const response = await apiGet(
          API_ENDPOINTS.getHints(executionId),
          { requireAuth: true }
        );

        if (!response.ok) {
          throw new Error('Failed to fetch hints');
        }

        const data = await response.json();

        if (data.hints && data.hints.length > 0) {
          setHints(data.hints);
          setHintsLoading(false);
          clearInterval(interval);
          setPollingInterval(null);
          showSnackbar('Hints loaded successfully!', 'success');
        } else if (pollCount >= maxPolls) {
          // Stop polling after max attempts
          clearInterval(interval);
          setPollingInterval(null);
          setHintsLoading(false);
          setHintsRequested(false); // Reset so button reappears
          setHintsError('Hint generation timed out. Please try again later.');
          showSnackbar('Hint generation timed out. Please try again.', 'warning');
        }
      } catch (error) {
        console.error('Error polling for hints:', error);
        clearInterval(interval);
        setPollingInterval(null);
        setHintsLoading(false);
        setHintsRequested(false); // Reset so button reappears
        setHintsError(error.message || 'Failed to fetch hints');
        showSnackbar('Failed to fetch hints. Please try again.', 'error');
      }
    }, 5000); // Poll every 5 seconds

    setPollingInterval(interval);
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

  return (
    <Paper sx={{ p: { xs: 2, sm: 3 }, backgroundColor: 'white' }}>
      <Typography variant="h6" gutterBottom sx={{
        color: 'text.primary',
        fontWeight: 600,
        fontSize: { xs: '1.125rem', sm: '1.25rem' }
      }}>
        Test Case Validation Results
      </Typography>

      <Box sx={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: { xs: 1, sm: 2 },
        mb: 3
      }}>
        <Chip
          label={`Passed: ${summary.passed}`}
          sx={{
            fontWeight: 500,
            fontSize: { xs: '0.75rem', sm: '0.813rem' },
            backgroundColor: summary.passed > 0 ? '#e8f5e9' : 'transparent',
            color: summary.passed > 0 ? '#2e7d32' : 'text.secondary',
            border: '1px solid',
            borderColor: summary.passed > 0 ? '#a5d6a7' : 'divider'
          }}
        />
        <Chip
          label={`Failed: ${summary.failed}`}
          sx={{
            fontWeight: 500,
            fontSize: { xs: '0.75rem', sm: '0.813rem' },
            backgroundColor: summary.failed > 0 ? '#ffebee' : 'transparent',
            color: summary.failed > 0 ? '#c62828' : 'text.secondary',
            border: '1px solid',
            borderColor: summary.failed > 0 ? '#ef9a9a' : 'divider'
          }}
        />
        <Chip
          label={`Total: ${summary.total}`}
          sx={{
            fontWeight: 500,
            fontSize: { xs: '0.75rem', sm: '0.813rem' },
            backgroundColor: '#f5f5f5',
            color: 'text.primary',
            border: '1px solid',
            borderColor: 'divider'
          }}
        />
      </Box>

      {/* Get Hints Button - Only show when there are failed tests */}
      {hasFailedTests && executionId && !hintsRequested && (
        <Box sx={{ mb: 3 }}>
          <Button
            variant="contained"
            startIcon={<LightbulbIcon />}
            onClick={requestHints}
            disabled={hintsLoading}
            sx={{
              backgroundColor: '#f57c00',
              '&:hover': { backgroundColor: '#e65100' },
              fontSize: { xs: '0.875rem', sm: '1rem' },
              px: { xs: 2, sm: 3 },
              py: { xs: 1, sm: 1.25 },
              fontWeight: 600,
              boxShadow: 2,
              '&:hover': {
                boxShadow: 4
              }
            }}
          >
            Get Hints to Fix Failing Tests
          </Button>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1, fontSize: { xs: '0.75rem', sm: '0.813rem' } }}>
            Get AI-powered hints to help debug your failing test cases
          </Typography>
        </Box>
      )}

      {/* Hints Display */}
      {(hintsLoading || hints) && (
        <HintsDisplay
          hints={hints}
          loading={hintsLoading}
          error={null}
          displayMode="accordion"
        />
      )}

      {testResults.length > 0 ? (
        <>
          <Typography variant="subtitle1" gutterBottom sx={{ color: 'text.primary', fontWeight: 600, mt: 2, mb: 2 }}>
            Test Cases
          </Typography>
          {testResults.map((result, index) => {
            return (
              <Accordion
                key={result.testCaseId || index}
                sx={{
                  mb: 1,
                  backgroundColor: 'white',
                  border: '1px solid',
                  borderColor: 'divider',
                  borderRadius: 1,
                  '&:before': { display: 'none' },
                  boxShadow: 'none'
                }}
              >
                <AccordionSummary
                  expandIcon={<ExpandMoreIcon />}
                  sx={{
                    minHeight: 48,
                    '&.Mui-expanded': {
                      minHeight: 48
                    },
                    '&:hover': {
                      backgroundColor: '#f5f5f5',
                    }
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    <Box sx={{
                      width: 6,
                      height: 6,
                      borderRadius: '50%',
                      backgroundColor: result.passed ? '#4caf50' : '#f44336'
                    }} />
                    <Typography sx={{ color: 'text.primary', fontWeight: 500, fontSize: '0.9rem' }}>
                      Test Case #{index + 1}
                    </Typography>
                    <Chip
                      label={result.passed ? 'PASS' : 'FAIL'}
                      size="small"
                      sx={{
                        height: 20,
                        fontSize: '0.7rem',
                        fontWeight: 600,
                        backgroundColor: result.passed ? '#e8f5e9' : '#ffebee',
                        color: result.passed ? '#2e7d32' : '#c62828',
                        border: 'none'
                      }}
                    />
                  </Box>
                </AccordionSummary>
                <AccordionDetails sx={{
                  backgroundColor: '#fafafa',
                  borderTop: '1px solid',
                  borderColor: 'divider',
                  p: { xs: 1.5, sm: 2 }
                }}>
                  <Box sx={{
                    display: 'flex',
                    flexDirection: { xs: 'column', md: 'row' },
                    gap: 2
                  }}>
                    {/* Input */}
                    <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 33.33%' }, minWidth: 0 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                        <Typography variant="caption" sx={{
                          fontWeight: 600,
                          color: 'text.secondary',
                          textTransform: 'uppercase',
                          fontSize: { xs: '0.65rem', sm: '0.7rem' }
                        }}>
                          Input
                        </Typography>
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            downloadText(result.input, `test_case_${index + 1}_input.txt`);
                          }}
                          sx={{ color: 'text.secondary', p: { xs: 0.5, sm: 1 } }}
                          title="Download Input"
                        >
                          <DownloadIcon sx={{ fontSize: { xs: '1rem', sm: '1.125rem' } }} />
                        </IconButton>
                      </Box>
                      <Paper elevation={0} sx={{
                        p: { xs: 1, sm: 1.5 },
                        backgroundColor: 'white',
                        border: '1px solid',
                        borderColor: 'divider',
                        height: { xs: '180px', sm: '200px' },
                        overflow: 'auto',
                        display: 'flex',
                        flexDirection: 'column'
                      }}>
                        <pre style={{
                          margin: 0,
                          fontSize: window.innerWidth < 600 ? '0.7rem' : '0.8rem',
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-word',
                          color: '#333',
                          overflowWrap: 'break-word',
                          fontFamily: 'monospace',
                          flex: 1
                        }}>
                          {result.input}
                        </pre>
                      </Paper>
                    </Box>

                    {/* Expected Output */}
                    <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 33.33%' }, minWidth: 0 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                        <Typography variant="caption" sx={{
                          fontWeight: 600,
                          color: 'text.secondary',
                          textTransform: 'uppercase',
                          fontSize: { xs: '0.65rem', sm: '0.7rem' }
                        }}>
                          Expected
                        </Typography>
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            downloadText(result.expected || result.expectedOutput, `test_case_${index + 1}_expected.txt`);
                          }}
                          sx={{ color: 'text.secondary', p: { xs: 0.5, sm: 1 } }}
                          title="Download Expected Output"
                        >
                          <DownloadIcon sx={{ fontSize: { xs: '1rem', sm: '1.125rem' } }} />
                        </IconButton>
                      </Box>
                      <Paper elevation={0} sx={{
                        p: { xs: 1, sm: 1.5 },
                        backgroundColor: 'white',
                        border: '1px solid',
                        borderColor: 'divider',
                        height: { xs: '180px', sm: '200px' },
                        overflow: 'auto',
                        display: 'flex',
                        flexDirection: 'column'
                      }}>
                        <pre style={{
                          margin: 0,
                          fontSize: window.innerWidth < 600 ? '0.7rem' : '0.8rem',
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-word',
                          color: '#333',
                          overflowWrap: 'break-word',
                          fontFamily: 'monospace',
                          flex: 1
                        }}>
                          {result.expected || result.expectedOutput}
                        </pre>
                      </Paper>
                    </Box>

                    {/* Actual Output */}
                    <Box sx={{ flex: { xs: '1 1 100%', md: '1 1 33.33%' }, minWidth: 0 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                        <Typography variant="caption" sx={{
                          fontWeight: 600,
                          color: 'text.secondary',
                          textTransform: 'uppercase',
                          fontSize: { xs: '0.65rem', sm: '0.7rem' }
                        }}>
                          Actual
                        </Typography>
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            downloadText(result.output || result.actualOutput || '(No output)', `test_case_${index + 1}_actual.txt`);
                          }}
                          sx={{ color: 'text.secondary', p: { xs: 0.5, sm: 1 } }}
                          title="Download Actual Output"
                        >
                          <DownloadIcon sx={{ fontSize: { xs: '1rem', sm: '1.125rem' } }} />
                        </IconButton>
                      </Box>
                      <Paper elevation={0} sx={{
                        p: { xs: 1, sm: 1.5 },
                        backgroundColor: 'white',
                        border: '1px solid',
                        borderColor: result.passed ? 'divider' : '#ef9a9a',
                        height: { xs: '180px', sm: '200px' },
                        overflow: 'auto',
                        display: 'flex',
                        flexDirection: 'column'
                      }}>
                        <pre style={{
                          margin: 0,
                          fontSize: window.innerWidth < 600 ? '0.7rem' : '0.8rem',
                          whiteSpace: 'pre-wrap',
                          wordBreak: 'break-word',
                          color: result.passed ? '#333' : '#c62828',
                          overflowWrap: 'break-word',
                          fontFamily: 'monospace',
                          flex: 1
                        }}>
                          {result.output || result.actualOutput || '(No output)'}
                        </pre>
                      </Paper>
                    </Box>
                  </Box>

                  {result.error && (
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="caption" gutterBottom sx={{ fontWeight: 600, color: '#c62828', textTransform: 'uppercase', fontSize: '0.7rem', display: 'block', mb: 1 }}>
                        Error Message
                      </Typography>
                      <Paper elevation={0} sx={{ p: 1.5, backgroundColor: 'white', border: '1px solid', borderColor: '#ef9a9a' }}>
                        {result.error.includes('Segmentation fault') || result.error.includes('SIGSEGV') || result.status === 'segfault' ? (
                          <Box>
                            <Typography variant="body2" sx={{ fontWeight: 700, color: '#c62828', mb: 1 }}>
                              ⚠️ Segmentation Fault (메모리 접근 오류)
                            </Typography>
                            <Typography variant="body2" sx={{ color: '#c62828', fontSize: '0.875rem', mb: 1 }}>
                              프로그램이 잘못된 메모리 영역에 접근하려고 했습니다. 일반적인 원인:
                            </Typography>
                            <ul style={{ margin: 0, paddingLeft: '1.5rem', color: '#c62828', fontSize: '0.813rem' }}>
                              <li>배열 범위를 벗어난 접근</li>
                              <li>NULL 포인터 역참조</li>
                              <li>스택 오버플로우 (재귀 깊이 초과)</li>
                              <li>해제된 메모리 접근</li>
                            </ul>
                            <pre style={{ margin: '8px 0 0 0', fontSize: '0.75rem', whiteSpace: 'pre-wrap', color: '#999', fontFamily: 'monospace' }}>
                              {result.error}
                            </pre>
                          </Box>
                        ) : (
                          <pre style={{ margin: 0, fontSize: '0.8rem', whiteSpace: 'pre-wrap', color: '#c62828', fontFamily: 'monospace' }}>
                            {result.error}
                          </pre>
                        )}
                      </Paper>
                    </Box>
                  )}
                </AccordionDetails>
              </Accordion>
            );
          })}
        </>
      ) : (
        <Alert
          severity="info"
          sx={{
            backgroundColor: '#e3f2fd',
            color: '#1976d2',
            '& .MuiAlert-icon': {
              color: '#1976d2'
            }
          }}
        >
          No test results available
        </Alert>
      )}

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
    </Paper>
  );
}

export default TestResults;
