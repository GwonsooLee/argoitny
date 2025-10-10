import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Chip,
  CircularProgress,
  FormControlLabel,
  Switch,
  IconButton,
  Snackbar,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tooltip
} from '@mui/material';
import {
  Visibility as VisibilityIcon,
  NavigateBefore,
  NavigateNext,
  Download as DownloadIcon,
  Lightbulb as LightbulbIcon,
  LightbulbOutlined as LightbulbOutlinedIcon
} from '@mui/icons-material';
import { apiGet } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';
import { getUser } from '../utils/auth';
import CodeModal from './CodeModal';
import HintsDisplay from './HintsDisplay';

const ITEMS_PER_PAGE = 20;

function SearchHistory({ onRequestLogin }) {
  const [history, setHistory] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [nextCursor, setNextCursor] = useState(null);
  const [prevCursors, setPrevCursors] = useState([]); // Stack of previous page cursors
  const [loading, setLoading] = useState(false);
  const [selectedCode, setSelectedCode] = useState(null);
  const [selectedExecution, setSelectedExecution] = useState(null);
  const [hasMore, setHasMore] = useState(false);
  const [myOnly, setMyOnly] = useState(true); // Default to my history only
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });

  useEffect(() => {
    // Check if user is authenticated
    const user = getUser();
    if (!user) {
      if (onRequestLogin) {
        onRequestLogin();
      }
      return;
    }
    // Reset pagination when myOnly changes
    setCurrentPage(1);
    setPrevCursors([]);
    setNextCursor(null);
    fetchHistory(null);
  }, [myOnly]);

  const showSnackbar = (message, severity = 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  const fetchHistory = async (cursor) => {
    setLoading(true);
    try {
      const user = getUser();
      const params = new URLSearchParams({
        limit: ITEMS_PER_PAGE,
        my_only: myOnly.toString()
      });

      // Add cursor if provided
      if (cursor) {
        params.append('cursor', cursor);
      }

      const response = await apiGet(`${API_ENDPOINTS.history}?${params.toString()}`, { requireAuth: true });

      if (!response.ok) {
        throw new Error('Failed to fetch history');
      }

      const data = await response.json();
      setHistory(data.results);
      setNextCursor(data.next_cursor);
      setHasMore(data.has_more);
    } catch (error) {
      console.error('Error fetching history:', error);
      showSnackbar('Failed to fetch history', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handlePrevPage = () => {
    if (currentPage > 1) {
      // Remove the last cursor from the stack
      const newPrevCursors = [...prevCursors];
      newPrevCursors.pop();
      setPrevCursors(newPrevCursors);

      // Get the cursor for the previous page (or null for page 1)
      const prevCursor = newPrevCursors.length > 0 ? newPrevCursors[newPrevCursors.length - 1] : null;

      // Update page and fetch
      setCurrentPage(currentPage - 1);
      fetchHistory(prevCursor);
    }
  };

  const handleNextPage = () => {
    if (hasMore && nextCursor) {
      // Add current next cursor to the stack for navigation back
      setPrevCursors([...prevCursors, nextCursor]);

      // Update page and fetch next
      setCurrentPage(currentPage + 1);
      fetchHistory(nextCursor);
    }
  };

  const handleCodeClick = (item) => {
    if (item.is_code_public || isMyExecution(item)) {
      if (!item.code) {
        showSnackbar('Code not available', 'warning');
        return;
      }
      setSelectedCode({
        code: item.code,
        language: item.language,
        problemTitle: item.problem_title,
        platform: item.platform,
        problemNumber: item.problem_number
      });
    } else {
      showSnackbar('Code is private', 'warning');
    }
  };

  const handleExecutionClick = async (item) => {
    // Only allow viewing own execution details
    if (!isMyExecution(item)) {
      showSnackbar('You can only view your own execution details', 'warning');
      return;
    }

    // Fetch full execution details
    try {
      const response = await apiGet(`/history/${item.id}/`, { requireAuth: true });
      if (!response.ok) {
        throw new Error('You can only view details of your own executions');
      }
      const data = await response.json();
      setSelectedExecution(data);
    } catch (error) {
      console.error('Error fetching execution details:', error);
      showSnackbar('You can only view details of your own executions', 'error');
    }
  };

  const isMyExecution = (item) => {
    const user = getUser();
    return user && item.user_email === user.email;
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getResultColor = (item) => {
    if (item.passed_count === item.total_count) {
      return 'success';
    } else if (item.passed_count === 0) {
      return 'error';
    } else {
      return 'warning';
    }
  };

  return (
    <Box sx={{ p: { xs: 2, sm: 3 } }}>
      <Paper sx={{ p: { xs: 2, sm: 3 } }}>
        <Box sx={{
          display: 'flex',
          flexDirection: { xs: 'column', sm: 'row' },
          justifyContent: 'space-between',
          alignItems: { xs: 'flex-start', sm: 'center' },
          mb: 3,
          gap: 2
        }}>
          <Typography variant="h5" sx={{
            color: 'text.primary',
            fontWeight: 600,
            fontSize: { xs: '1.25rem', sm: '1.5rem', md: '1.75rem' }
          }}>
            Test Case Validation History
          </Typography>
          <FormControlLabel
            control={
              <Switch
                checked={myOnly}
                onChange={(e) => {
                  setMyOnly(e.target.checked);
                }}
              />
            }
            label="My History Only"
            sx={{
              '& .MuiFormControlLabel-label': {
                fontSize: { xs: '0.875rem', sm: '1rem' }
              }
            }}
            disabled={loading}
          />
        </Box>

        {loading && history.length === 0 ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', py: 8 }}>
            <CircularProgress />
          </Box>
        ) : (
          <>
            {/* Mobile View - Card Based */}
            <Box sx={{ display: { xs: 'block', md: 'none' } }}>
              {history.length === 0 ? (
                <Box sx={{ textAlign: 'center', py: 8 }}>
                  <Typography variant="body1" color="text.secondary">
                    No search history available
                  </Typography>
                </Box>
              ) : (
                history.map((item) => (
                  <Paper
                    key={item.id}
                    sx={{
                      p: 2,
                      mb: 2
                    }}
                  >
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1.5 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, flex: 1 }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 600, fontSize: '0.875rem' }}>
                          {item.problem_title}
                        </Typography>
                        {item.has_hints && (
                          <Tooltip title="Hints available">
                            <LightbulbIcon sx={{ fontSize: '1rem', color: '#f57c00' }} />
                          </Tooltip>
                        )}
                      </Box>
                      <Chip
                        label={`${item.passed_count}/${item.total_count}`}
                        size="small"
                        color={getResultColor(item)}
                      />
                    </Box>

                    <Box sx={{ display: 'flex', gap: 1, mb: 1, flexWrap: 'wrap' }}>
                      <Chip
                        label={item.platform === 'baekjoon' ? 'Baekjoon' : 'Codeforces'}
                        size="small"
                        color="primary"
                        variant="outlined"
                        sx={{ fontSize: '0.75rem' }}
                      />
                      <Chip
                        label={item.language}
                        size="small"
                        sx={{ fontSize: '0.75rem' }}
                      />
                      <Chip
                        label={`#${item.problem_number}`}
                        size="small"
                        variant="outlined"
                        sx={{ fontSize: '0.75rem' }}
                      />
                    </Box>

                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1, fontSize: '0.75rem' }}>
                      {formatDate(item.created_at)}
                    </Typography>

                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1.5, fontSize: '0.75rem' }}>
                      User: {item.user_email || item.user_identifier || 'Anonymous'}
                    </Typography>

                    <Box sx={{ display: 'flex', gap: 1 }} onClick={(e) => e.stopPropagation()}>
                      {item.is_code_public || isMyExecution(item) ? (
                        <Button
                          size="small"
                          variant="outlined"
                          startIcon={<VisibilityIcon sx={{ fontSize: '1rem' }} />}
                          onClick={() => handleCodeClick(item)}
                          sx={{ fontSize: '0.75rem' }}
                        >
                          Code
                        </Button>
                      ) : (
                        <Button
                          size="small"
                          variant="outlined"
                          disabled
                          sx={{ fontSize: '0.75rem' }}
                        >
                          Private Code
                        </Button>
                      )}
                      {isMyExecution(item) && (
                        <Button
                          size="small"
                          variant="contained"
                          onClick={() => handleExecutionClick(item)}
                          sx={{ fontSize: '0.75rem' }}
                        >
                          Details
                        </Button>
                      )}
                    </Box>
                  </Paper>
                ))
              )}
            </Box>

            {/* Desktop View - Table */}
            <TableContainer sx={{ display: { xs: 'none', md: 'block' } }}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Time</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Platform</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Problem #</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Problem Title</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Language</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>User</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Result</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Code</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Details</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {history.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={9} align="center" sx={{ py: 8 }}>
                        <Typography variant="body1" color="text.secondary">
                          No search history available
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    history.map((item) => (
                      <TableRow
                        key={item.id}
                        sx={{
                          '&:hover': { backgroundColor: 'action.hover' }
                        }}
                      >
                        <TableCell>
                          <Typography variant="body2" sx={{ fontSize: '0.875rem' }}>
                            {formatDate(item.created_at)}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={item.platform === 'baekjoon' ? 'Baekjoon' : 'Codeforces'}
                            size="small"
                            color="primary"
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell>{item.problem_number}</TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            {item.problem_title}
                            {item.has_hints && (
                              <Tooltip title="Hints available">
                                <LightbulbIcon sx={{ fontSize: '1.125rem', color: '#f57c00' }} />
                              </Tooltip>
                            )}
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Chip label={item.language} size="small" />
                        </TableCell>
                        <TableCell>
                          {item.user_email || item.user_identifier || 'Anonymous'}
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={`${item.passed_count}/${item.total_count}`}
                            size="small"
                            color={getResultColor(item)}
                          />
                        </TableCell>
                        <TableCell onClick={(e) => e.stopPropagation()}>
                          {item.is_code_public || isMyExecution(item) ? (
                            <IconButton
                              size="small"
                              onClick={() => handleCodeClick(item)}
                              color="primary"
                            >
                              <VisibilityIcon fontSize="small" />
                            </IconButton>
                          ) : (
                            <Typography variant="caption" color="text.secondary">
                              Private
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell onClick={(e) => e.stopPropagation()}>
                          {isMyExecution(item) && (
                            <Button
                              size="small"
                              variant="outlined"
                              onClick={() => handleExecutionClick(item)}
                            >
                              View
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>

            {history.length > 0 && (
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 3 }}>
                <Button
                  onClick={handlePrevPage}
                  disabled={currentPage === 1 || loading}
                  startIcon={<NavigateBefore />}
                  variant="outlined"
                >
                  Previous
                </Button>

                <Typography variant="body2" color="text.secondary">
                  Page {currentPage} - Showing {history.length} items{hasMore ? ' (more available)' : ''}
                </Typography>

                <Button
                  onClick={handleNextPage}
                  disabled={!hasMore || loading}
                  endIcon={<NavigateNext />}
                  variant="outlined"
                >
                  Next
                </Button>
              </Box>
            )}
          </>
        )}
      </Paper>

      {selectedCode && (
        <CodeModal
          code={selectedCode}
          onClose={() => setSelectedCode(null)}
        />
      )}

      {selectedExecution && (
        <ExecutionDetailModal
          execution={selectedExecution}
          onClose={() => setSelectedExecution(null)}
        />
      )}

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
    </Box>
  );
}

// Execution Detail Modal Component
function ExecutionDetailModal({ execution, onClose }) {
  const [selectedTestCase, setSelectedTestCase] = useState(null);
  const [hints, setHints] = useState(null);
  const [hintsLoading, setHintsLoading] = useState(false);

  // Check if execution has hints on mount
  useEffect(() => {
    const fetchHints = async () => {
      if (!execution.id) return;

      try {
        setHintsLoading(true);
        const response = await apiGet(
          API_ENDPOINTS.getHints(execution.id),
          { requireAuth: true }
        );

        if (response.ok) {
          const data = await response.json();
          if (data.hints && data.hints.length > 0) {
            setHints(data.hints);
          }
        }
      } catch (error) {
        console.error('Error fetching hints:', error);
      } finally {
        setHintsLoading(false);
      }
    };

    fetchHints();
  }, [execution.id]);

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
    <>
      <Box
        sx={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1300,
          p: 2
        }}
        onClick={onClose}
      >
        <Paper
          sx={{
            maxWidth: '90vw',
            maxHeight: '90vh',
            overflow: 'auto',
            p: 4,
            width: '100%'
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
            <Typography variant="h5" sx={{ fontWeight: 600 }}>
              Execution Details
            </Typography>
            <Button onClick={onClose} variant="outlined">
              Close
            </Button>
          </Box>

          <Box sx={{ mb: 3 }}>
            <Typography variant="body1" sx={{ mb: 1 }}>
              <strong>Problem:</strong> {execution.platform} #{execution.problem_number} - {execution.problem_title}
            </Typography>
            <Typography variant="body1" sx={{ mb: 1 }}>
              <strong>Language:</strong> {execution.language}
            </Typography>
            <Typography variant="body1" sx={{ mb: 1 }}>
              <strong>User:</strong> {execution.user_email || execution.user_identifier}
            </Typography>
            <Typography variant="body1" sx={{ mb: 1 }}>
              <strong>Time:</strong> {new Date(execution.created_at).toLocaleString('ko-KR')}
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
              <Chip
                label={`Passed: ${execution.passed_count}`}
                color="success"
                size="small"
              />
              <Chip
                label={`Failed: ${execution.failed_count}`}
                color="error"
                size="small"
              />
              <Chip
                label={`Total: ${execution.total_count}`}
                size="small"
              />
            </Box>
          </Box>

          {/* Hints Section */}
          {(hintsLoading || (hints && hints.length > 0)) && (
            <Box sx={{ mb: 3 }}>
              <HintsDisplay
                hints={hints || []}
                loading={hintsLoading}
                error={null}
                displayMode="accordion"
              />
            </Box>
          )}

          <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
            Test Case Results
          </Typography>

          {execution.test_results && execution.test_results.length > 0 ? (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 600 }}>Test #</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Error</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {execution.test_results.map((result, index) => (
                    <TableRow
                      key={index}
                      sx={{
                        backgroundColor: result.passed
                          ? 'rgba(76, 175, 80, 0.08)'
                          : 'rgba(244, 67, 54, 0.08)'
                      }}
                    >
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 500 }}>
                          #{index + 1}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={result.passed ? 'PASS' : 'FAIL'}
                          color={result.passed ? 'success' : 'error'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        <Typography
                          variant="body2"
                          sx={{
                            fontFamily: 'monospace',
                            color: 'error.main',
                            fontSize: '0.8rem'
                          }}
                        >
                          {result.error ? (result.error.length > 50 ? result.error.substring(0, 50) + '...' : result.error) : '-'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => setSelectedTestCase({ ...result, index })}
                        >
                          View I/O
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            <Typography variant="body2" color="text.secondary">
              No test case results available
            </Typography>
          )}
        </Paper>
      </Box>

      {/* Test Case I/O Dialog */}
      {selectedTestCase && (
        <Dialog
          open={true}
          onClose={() => setSelectedTestCase(null)}
          maxWidth="lg"
          fullWidth
        >
          <DialogTitle>
            Test Case #{selectedTestCase.index + 1} - {selectedTestCase.passed ? 'PASSED' : 'FAILED'}
          </DialogTitle>
          <DialogContent>
            <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
              {/* Input */}
              <Box sx={{ flex: '1 1 33.33%', minWidth: 0 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                    Input
                  </Typography>
                  <IconButton
                    size="small"
                    onClick={() => downloadText(selectedTestCase.input, `test_${selectedTestCase.index + 1}_input.txt`)}
                    title="Download Input"
                  >
                    <DownloadIcon fontSize="small" />
                  </IconButton>
                </Box>
                <Paper elevation={0} sx={{ p: 1.5, backgroundColor: '#f5f5f5', border: '1px solid', borderColor: 'divider' }}>
                  <pre style={{ margin: 0, fontSize: '0.8rem', whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontFamily: 'monospace', maxHeight: 400, overflow: 'auto' }}>
                    {truncateText(selectedTestCase.input).text}
                  </pre>
                  {truncateText(selectedTestCase.input).isTruncated && (
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                      (Truncated - download to see full content)
                    </Typography>
                  )}
                </Paper>
              </Box>

              {/* Expected Output */}
              <Box sx={{ flex: '1 1 33.33%', minWidth: 0 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                    Expected Output
                  </Typography>
                  <IconButton
                    size="small"
                    onClick={() => downloadText(selectedTestCase.expected, `test_${selectedTestCase.index + 1}_expected.txt`)}
                    title="Download Expected Output"
                  >
                    <DownloadIcon fontSize="small" />
                  </IconButton>
                </Box>
                <Paper elevation={0} sx={{ p: 1.5, backgroundColor: '#f5f5f5', border: '1px solid', borderColor: 'divider' }}>
                  <pre style={{ margin: 0, fontSize: '0.8rem', whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontFamily: 'monospace', maxHeight: 400, overflow: 'auto' }}>
                    {truncateText(selectedTestCase.expected).text}
                  </pre>
                  {truncateText(selectedTestCase.expected).isTruncated && (
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                      (Truncated - download to see full content)
                    </Typography>
                  )}
                </Paper>
              </Box>

              {/* Actual Output */}
              <Box sx={{ flex: '1 1 33.33%', minWidth: 0 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                    Actual Output
                  </Typography>
                  <IconButton
                    size="small"
                    onClick={() => downloadText(selectedTestCase.output || '(No output)', `test_${selectedTestCase.index + 1}_actual.txt`)}
                    title="Download Actual Output"
                  >
                    <DownloadIcon fontSize="small" />
                  </IconButton>
                </Box>
                <Paper elevation={0} sx={{
                  p: 1.5,
                  backgroundColor: '#f5f5f5',
                  border: '1px solid',
                  borderColor: selectedTestCase.passed ? 'divider' : '#ef9a9a'
                }}>
                  <pre style={{ margin: 0, fontSize: '0.8rem', whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontFamily: 'monospace', maxHeight: 400, overflow: 'auto', color: selectedTestCase.passed ? '#333' : '#c62828' }}>
                    {truncateText(selectedTestCase.output || '(No output)').text}
                  </pre>
                  {truncateText(selectedTestCase.output).isTruncated && (
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                      (Truncated - download to see full content)
                    </Typography>
                  )}
                </Paper>
              </Box>
            </Box>

            {selectedTestCase.error && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                  Error Message
                </Typography>
                <Paper elevation={0} sx={{ p: 1.5, backgroundColor: '#ffebee', border: '1px solid', borderColor: '#ef9a9a' }}>
                  <pre style={{ margin: 0, fontSize: '0.8rem', whiteSpace: 'pre-wrap', fontFamily: 'monospace', color: '#c62828' }}>
                    {selectedTestCase.error}
                  </pre>
                </Paper>
              </Box>
            )}
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setSelectedTestCase(null)} variant="outlined">
              Close
            </Button>
          </DialogActions>
        </Dialog>
      )}
    </>
  );
}

export default SearchHistory;
