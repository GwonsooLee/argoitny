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
  IconButton
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Download as DownloadIcon
} from '@mui/icons-material';

function TestResults({ results }) {
  // Handle both old format (array) and new format (object with results and summary)
  const testResults = Array.isArray(results) ? results : (results?.results || []);
  const summary = results?.summary || {
    passed: testResults.filter(r => r.passed).length,
    failed: testResults.filter(r => !r.passed).length,
    total: testResults.length,
  };

  const truncateText = (text, maxLines = 30) => {
    if (!text) return { text: '', isTruncated: false };
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
    <Paper sx={{ p: 3, backgroundColor: 'white' }}>
      <Typography variant="h6" gutterBottom sx={{ color: 'text.primary', fontWeight: 600 }}>
        Test Case Validation Results
      </Typography>

      <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
        <Chip
          label={`Passed: ${summary.passed}`}
          sx={{
            fontWeight: 500,
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
            backgroundColor: '#f5f5f5',
            color: 'text.primary',
            border: '1px solid',
            borderColor: 'divider'
          }}
        />
      </Box>

      {testResults.length > 0 ? (
        <>
          <Typography variant="subtitle1" gutterBottom sx={{ color: 'text.primary', fontWeight: 600, mt: 2, mb: 2 }}>
            Test Cases
          </Typography>
          {testResults.map((result, index) => {
            const truncatedInput = truncateText(result.input);
            const truncatedExpected = truncateText(result.expected || result.expectedOutput);
            const truncatedActual = truncateText(result.output || result.actualOutput);

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
                <AccordionDetails sx={{ backgroundColor: '#fafafa', borderTop: '1px solid', borderColor: 'divider' }}>
                  <Box sx={{ display: 'flex', gap: 2 }}>
                    {/* Input - 1/3 width */}
                    <Box sx={{ flex: '1 1 33.33%', minWidth: 0 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                        <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary', textTransform: 'uppercase', fontSize: '0.7rem' }}>
                          Input
                        </Typography>
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            downloadText(result.input, `test_case_${index + 1}_input.txt`);
                          }}
                          sx={{ color: 'text.secondary' }}
                          title="Download Input"
                        >
                          <DownloadIcon fontSize="small" />
                        </IconButton>
                      </Box>
                      <Paper elevation={0} sx={{ p: 1.5, backgroundColor: 'white', border: '1px solid', borderColor: 'divider' }}>
                        <pre style={{ margin: 0, fontSize: '0.8rem', whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: '#333', overflowWrap: 'break-word', fontFamily: 'monospace' }}>
                          {truncatedInput.text}
                        </pre>
                        {truncatedInput.isTruncated && (
                          <Typography variant="caption" sx={{ color: 'text.secondary', mt: 1, display: 'block', fontSize: '0.7rem' }}>
                            (Truncated - download to see full content)
                          </Typography>
                        )}
                      </Paper>
                    </Box>

                    {/* Expected Output - 1/3 width */}
                    <Box sx={{ flex: '1 1 33.33%', minWidth: 0 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                        <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary', textTransform: 'uppercase', fontSize: '0.7rem' }}>
                          Expected
                        </Typography>
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            downloadText(result.expected || result.expectedOutput, `test_case_${index + 1}_expected.txt`);
                          }}
                          sx={{ color: 'text.secondary' }}
                          title="Download Expected Output"
                        >
                          <DownloadIcon fontSize="small" />
                        </IconButton>
                      </Box>
                      <Paper elevation={0} sx={{ p: 1.5, backgroundColor: 'white', border: '1px solid', borderColor: 'divider' }}>
                        <pre style={{ margin: 0, fontSize: '0.8rem', whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: '#333', overflowWrap: 'break-word', fontFamily: 'monospace' }}>
                          {truncatedExpected.text}
                        </pre>
                        {truncatedExpected.isTruncated && (
                          <Typography variant="caption" sx={{ color: 'text.secondary', mt: 1, display: 'block', fontSize: '0.7rem' }}>
                            (Truncated - download to see full content)
                          </Typography>
                        )}
                      </Paper>
                    </Box>

                    {/* Actual Output - 1/3 width */}
                    <Box sx={{ flex: '1 1 33.33%', minWidth: 0 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                        <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary', textTransform: 'uppercase', fontSize: '0.7rem' }}>
                          Actual
                        </Typography>
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            downloadText(result.output || result.actualOutput || '(No output)', `test_case_${index + 1}_actual.txt`);
                          }}
                          sx={{ color: 'text.secondary' }}
                          title="Download Actual Output"
                        >
                          <DownloadIcon fontSize="small" />
                        </IconButton>
                      </Box>
                      <Paper elevation={0} sx={{
                        p: 1.5,
                        backgroundColor: 'white',
                        border: '1px solid',
                        borderColor: result.passed ? 'divider' : '#ef9a9a'
                      }}>
                        <pre style={{ margin: 0, fontSize: '0.8rem', whiteSpace: 'pre-wrap', wordBreak: 'break-word', color: result.passed ? '#333' : '#c62828', overflowWrap: 'break-word', fontFamily: 'monospace' }}>
                          {truncatedActual.text || '(No output)'}
                        </pre>
                        {truncatedActual.isTruncated && (
                          <Typography variant="caption" sx={{ color: 'text.secondary', mt: 1, display: 'block', fontSize: '0.7rem' }}>
                            (Truncated - download to see full content)
                          </Typography>
                        )}
                      </Paper>
                    </Box>
                  </Box>

                  {result.error && (
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="caption" gutterBottom sx={{ fontWeight: 600, color: '#c62828', textTransform: 'uppercase', fontSize: '0.7rem', display: 'block', mb: 1 }}>
                        Error Message
                      </Typography>
                      <Paper elevation={0} sx={{ p: 1.5, backgroundColor: 'white', border: '1px solid', borderColor: '#ef9a9a' }}>
                        <pre style={{ margin: 0, fontSize: '0.8rem', whiteSpace: 'pre-wrap', color: '#c62828', fontFamily: 'monospace' }}>
                          {result.error}
                        </pre>
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
    </Paper>
  );
}

export default TestResults;
