import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Alert,
  IconButton,
  Button,
  Snackbar,
  CircularProgress
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Download as DownloadIcon,
  Lightbulb as LightbulbIcon,
  Psychology as PsychologyIcon
} from '@mui/icons-material';
import { apiPost, apiGet } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';
import HintsDisplay from './HintsDisplay';

function TestResults({ results, executionId, platform, problemId, onHintsLoadingChange }) {
  // Handle both old format (array) and new format (object with results and summary)
  const testResults = Array.isArray(results) ? results : (results?.results || []);
  const summary = results?.summary || {
    passed: testResults.filter(r => r.passed).length,
    failed: testResults.filter(r => !r.passed).length,
    total: testResults.length,
  };

  // Two-tier hints system
  const [problemHints, setProblemHints] = useState(null); // Tier 1: Problem's general hints
  const [codeHints, setCodeHints] = useState(null); // Tier 2: Code analysis hints
  const [problemHintsLoading, setProblemHintsLoading] = useState(false);
  const [codeHintsLoading, setCodeHintsLoading] = useState(false);
  const [hintsError, setHintsError] = useState(null);
  const [problemHintsVisible, setProblemHintsVisible] = useState(false);
  const [codeHintsRequested, setCodeHintsRequested] = useState(false);
  const [pollingInterval, setPollingInterval] = useState(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });

  // Check if test cases have failed
  const hasFailedTests = summary.failed > 0;

  // Load existing code analysis hints
  useEffect(() => {
    const loadCodeHints = async () => {
      if (!executionId || !hasFailedTests) {
        return;
      }

      try {
        const response = await apiGet(
          API_ENDPOINTS.getHints(executionId),
          { requireAuth: true }
        );

        if (response.ok) {
          const data = await response.json();
          if (data.status === 'available' && data.hints && Array.isArray(data.hints) && data.hints.length > 0) {
            setCodeHints(data.hints);
            setCodeHintsRequested(true);
          }
        }
      } catch (error) {
        console.error('[Code Hints] Error loading:', error);
      }
    };

    loadCodeHints();
  }, [executionId, hasFailedTests]);

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
      onHintsLoadingChange(codeHintsLoading);
    }
  }, [codeHintsLoading, onHintsLoadingChange]);

  const showSnackbar = (message, severity = 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  const handleShowProblemHints = async () => {
    if (!platform || !problemId) {
      showSnackbar('Cannot load hints: Missing problem information', 'error');
      return;
    }

    // Check if hints are already loaded
    if (problemHints && problemHints.length > 0) {
      // Just show existing hints
      setProblemHintsVisible(true);
      showSnackbar('Problem hints loaded', 'info');
      return;
    }

    // Fetch hints from API (rate limit is checked in backend)
    setProblemHintsLoading(true);
    try {
      const response = await apiGet(
        API_ENDPOINTS.getProblemHints(platform, problemId),
        { requireAuth: true }
      );

      if (response.ok) {
        const data = await response.json();
        if (data.hints && Array.isArray(data.hints) && data.hints.length > 0) {
          setProblemHints(data.hints);
          setProblemHintsVisible(true);
          showSnackbar('Problem hints loaded', 'success');
        } else {
          showSnackbar('No hints available for this problem', 'info');
        }
      } else if (response.status === 429) {
        // Plan limit exceeded
        const errorData = await response.json();
        showSnackbar(
          errorData.message || 'Daily hint limit exceeded. Please upgrade your plan.',
          'warning'
        );
      } else {
        showSnackbar('Failed to load hints', 'error');
      }
    } catch (error) {
      console.error('Error loading hints:', error);
      showSnackbar('Failed to load hints', 'error');
    } finally {
      setProblemHintsLoading(false);
    }
  };

  const requestCodeAnalysis = async () => {
    if (!executionId) {
      showSnackbar('Cannot request hints: No execution ID available', 'error');
      return;
    }

    setCodeHintsLoading(true);
    setHintsError(null);
    setCodeHintsRequested(true);

    try {
      const response = await apiPost(
        API_ENDPOINTS.requestHints(executionId),
        {},
        { requireAuth: true }
      );

      if (!response.ok) {
        if (response.status === 429) {
          throw new Error('RATE_LIMIT_EXCEEDED');
        }
        if (response.status === 501) {
          throw new Error('FEATURE_NOT_IMPLEMENTED');
        }
        throw new Error('Failed to request hints');
      }

      const data = await response.json();

      if (data.hints && data.hints.length > 0) {
        setCodeHints(data.hints);
        setCodeHintsLoading(false);
        showSnackbar('Code analysis complete!', 'success');
      } else {
        showSnackbar('Analyzing code... Please wait', 'info');
        startPollingForCodeHints();
      }
    } catch (error) {
      console.error('Error requesting code analysis:', error);

      if (error.message === 'RATE_LIMIT_EXCEEDED') {
        setHintsError('Plan limit reached. Upgrade required.');
        showSnackbar('Plan limit reached', 'warning');
      } else if (error.message === 'FEATURE_NOT_IMPLEMENTED') {
        setHintsError('Hint feature is temporarily disabled.');
        showSnackbar('Feature temporarily disabled', 'info');
      } else {
        setHintsError(error.message || 'Failed to request hints');
        showSnackbar('Failed to request hints', 'error');
      }

      setCodeHintsLoading(false);
      setCodeHintsRequested(false);
    }
  };

  const startPollingForCodeHints = () => {
    let pollCount = 0;
    const maxPolls = 36;

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

        if (data.status === 'available' && data.hints && data.hints.length > 0) {
          setCodeHints(data.hints);
          setCodeHintsLoading(false);
          clearInterval(interval);
          setPollingInterval(null);
          showSnackbar('Code analysis complete!', 'success');
        } else if (pollCount >= maxPolls) {
          clearInterval(interval);
          setPollingInterval(null);
          setCodeHintsLoading(false);
          setCodeHintsRequested(false);
          setHintsError('Hint generation timed out');
          showSnackbar('Timeout - please try again', 'warning');
        }
      } catch (error) {
        console.error('Error polling for hints:', error);
        clearInterval(interval);
        setPollingInterval(null);
        setCodeHintsLoading(false);
        setCodeHintsRequested(false);
        setHintsError(error.message || 'Failed to fetch hints');
        showSnackbar('Failed to fetch hints', 'error');
      }
    }, 5000);

    setPollingInterval(interval);
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

      {/* Two-Tier Hints System */}
      {hasFailedTests && (
        <Box sx={{ mb: 3 }}>
          {/* Tier 1: Problem Hints Button */}
          {!problemHintsVisible && !codeHintsRequested && (
            <Box sx={{ mb: 2 }}>
              <Button
                variant="outlined"
                startIcon={<LightbulbIcon />}
                onClick={handleShowProblemHints}
                disabled={problemHintsLoading}
                sx={{
                  borderColor: '#2196f3',
                  color: '#2196f3',
                  fontSize: { xs: '0.875rem', sm: '1rem' },
                  px: { xs: 2, sm: 3 },
                  py: { xs: 1, sm: 1.25 },
                  fontWeight: 600,
                  '&:hover': {
                    borderColor: '#1976d2',
                    backgroundColor: '#e3f2fd'
                  }
                }}
                fullWidth
              >
                {problemHintsLoading ? 'Loading hints...' : '💡 Show Step-by-Step Hints'}
              </Button>
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1, fontSize: { xs: '0.75rem', sm: '0.813rem' } }}>
                View general problem-solving approaches and hints
              </Typography>
            </Box>
          )}

          {/* Tier 2: Code Analysis Button */}
          {!codeHintsRequested && problemHintsVisible && (
            <Box>
              <Button
                variant="contained"
                startIcon={<PsychologyIcon />}
                onClick={requestCodeAnalysis}
                disabled={codeHintsLoading}
                sx={{
                  backgroundColor: '#f57c00',
                  fontSize: { xs: '0.875rem', sm: '1rem' },
                  px: { xs: 2, sm: 3 },
                  py: { xs: 1, sm: 1.25 },
                  fontWeight: 600,
                  boxShadow: 2,
                  '&:hover': {
                    backgroundColor: '#e65100',
                    boxShadow: 4
                  }
                }}
                fullWidth
              >
                🔍 Request Code Analysis
              </Button>
              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1, fontSize: { xs: '0.75rem', sm: '0.813rem' } }}>
                AI will analyze your code and provide specific bug fixes and solutions
              </Typography>
            </Box>
          )}
        </Box>
      )}

      {/* Display Problem Hints (Tier 1) */}
      {problemHintsVisible && problemHints && (
        <Box sx={{ mb: 3 }}>
          <HintsDisplay
            hints={problemHints}
            loading={false}
            error={null}
            displayMode="stepper"
          />
        </Box>
      )}

      {/* Display Code Analysis Hints (Tier 2) */}
      {(codeHintsLoading || codeHints) && (
        <Box sx={{ mb: 3 }}>
          <HintsDisplay
            hints={codeHints}
            loading={codeHintsLoading}
            error={hintsError}
            displayMode="accordion"
          />
        </Box>
      )}

      {/* Test Cases */}
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
