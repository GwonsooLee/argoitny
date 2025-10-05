import {
  Box,
  Typography,
  Paper,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Grid,
  Alert
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon
} from '@mui/icons-material';

function TestResults({ results }) {
  // Handle both old format (array) and new format (object with results and summary)
  const testResults = results.results || results;
  const summary = results.summary || {
    passed: testResults.filter(r => r.passed).length,
    failed: testResults.filter(r => !r.passed).length,
    total: testResults.length,
  };

  const failedTests = testResults.filter(r => !r.passed);

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom sx={{ color: 'white', fontWeight: 600 }}>
        Test Case Validation Results
      </Typography>

      <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
        <Chip
          icon={<CheckCircleIcon />}
          label={`Passed: ${summary.passed}`}
          color="success"
          sx={{ fontWeight: 600 }}
        />
        <Chip
          icon={<ErrorIcon />}
          label={`Failed: ${summary.failed}`}
          color="error"
          sx={{ fontWeight: 600 }}
        />
        <Chip
          label={`Total: ${summary.total}`}
          sx={{
            backgroundColor: 'rgba(255, 255, 255, 0.1)',
            color: 'white',
            fontWeight: 600
          }}
        />
      </Box>

      {failedTests.length > 0 ? (
        <>
          <Typography variant="subtitle1" gutterBottom sx={{ color: 'white', fontWeight: 600, mt: 2 }}>
            Failed Test Cases
          </Typography>
          {failedTests.map((result, index) => (
            <Accordion
              key={result.testCaseId || index}
              sx={{
                mb: 1,
                backgroundColor: 'rgba(211, 47, 47, 0.1)',
                '&:before': { display: 'none' }
              }}
            >
              <AccordionSummary
                expandIcon={<ExpandMoreIcon sx={{ color: 'white' }} />}
                sx={{
                  backgroundColor: 'rgba(0, 0, 0, 0.2)',
                  '&:hover': {
                    backgroundColor: 'rgba(0, 0, 0, 0.3)',
                  }
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <ErrorIcon color="error" />
                  <Typography sx={{ color: 'white', fontWeight: 600 }}>
                    Test Case #{index + 1}
                  </Typography>
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <Grid container spacing={2}>
                  <Grid item xs={12}>
                    <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
                      Input:
                    </Typography>
                    <Paper sx={{ p: 1.5, backgroundColor: 'rgba(0, 0, 0, 0.3)' }}>
                      <pre style={{ margin: 0, fontSize: '0.875rem', whiteSpace: 'pre-wrap', color: 'white' }}>
                        {result.input}
                      </pre>
                    </Paper>
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
                      Expected Output:
                    </Typography>
                    <Paper sx={{ p: 1.5, backgroundColor: 'rgba(0, 0, 0, 0.3)' }}>
                      <pre style={{ margin: 0, fontSize: '0.875rem', whiteSpace: 'pre-wrap', color: 'white' }}>
                        {result.expected || result.expectedOutput}
                      </pre>
                    </Paper>
                  </Grid>

                  <Grid item xs={12} md={6}>
                    <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
                      Actual Output:
                    </Typography>
                    <Paper sx={{ p: 1.5, backgroundColor: 'rgba(211, 47, 47, 0.2)' }}>
                      <pre style={{ margin: 0, fontSize: '0.875rem', whiteSpace: 'pre-wrap', color: 'white' }}>
                        {result.output || result.actualOutput || '(No output)'}
                      </pre>
                    </Paper>
                  </Grid>

                  {result.error && (
                    <Grid item xs={12}>
                      <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600, color: 'error.light' }}>
                        Error:
                      </Typography>
                      <Paper sx={{ p: 1.5, backgroundColor: 'rgba(211, 47, 47, 0.2)' }}>
                        <pre style={{ margin: 0, fontSize: '0.875rem', whiteSpace: 'pre-wrap', color: 'error.light' }}>
                          {result.error}
                        </pre>
                      </Paper>
                    </Grid>
                  )}
                </Grid>
              </AccordionDetails>
            </Accordion>
          ))}
        </>
      ) : (
        <Alert
          icon={<CheckCircleIcon fontSize="large" />}
          severity="success"
          sx={{
            backgroundColor: 'rgba(46, 125, 50, 0.2)',
            color: 'white',
            fontSize: '1.1rem',
            fontWeight: 600,
            '& .MuiAlert-icon': {
              color: 'success.light'
            }
          }}
        >
          All test cases passed!
        </Alert>
      )}
    </Paper>
  );
}

export default TestResults;
