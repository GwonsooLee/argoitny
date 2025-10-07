import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Checkbox,
  FormControlLabel,
  Paper,
  CircularProgress,
  Snackbar,
  Alert
} from '@mui/material';
import { PlayArrow as PlayArrowIcon } from '@mui/icons-material';
import { apiPost, apiGet } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';
import { getUser, isAuthenticated } from '../utils/auth';

// Language detection patterns
const languagePatterns = {
  python: [/^import\s/, /^from\s.*import/, /def\s+\w+\(/, /print\(/],
  javascript: [/^const\s/, /^let\s/, /^var\s/, /console\.log/, /=>\s*{/, /function\s+\w+\(/],
  cpp: [/#include\s*</, /using namespace/, /int main\(/, /std::/, /cout\s*<</, /cin\s*>>/],
  java: [/public\s+class/, /public\s+static\s+void\s+main/, /System\.out\.println/]
};

function detectLanguage(code) {
  const scores = {
    python: 0,
    javascript: 0,
    cpp: 0,
    java: 0
  };

  for (const [lang, patterns] of Object.entries(languagePatterns)) {
    for (const pattern of patterns) {
      if (pattern.test(code)) {
        scores[lang]++;
      }
    }
  }

  const maxScore = Math.max(...Object.values(scores));
  if (maxScore === 0) return 'python'; // Default

  return Object.keys(scores).find(key => scores[key] === maxScore);
}

function CodeEditor({ problemId, onTestResults }) {
  const [code, setCode] = useState('');
  const [language, setLanguage] = useState('python');
  const [loading, setLoading] = useState(false);
  const [isCodePublic, setIsCodePublic] = useState(false);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });
  const [progress, setProgress] = useState({ current: 0, total: 0 });

  useEffect(() => {
    if (code.trim()) {
      const detected = detectLanguage(code);
      setLanguage(detected);
    }
  }, [code]);

  const showSnackbar = (message, severity = 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  const handleExecute = async () => {
    if (!code.trim()) {
      showSnackbar('Please enter your code', 'warning');
      return;
    }

    setLoading(true);
    try {
      const user = getUser();
      const userIdentifier = user ? user.email : 'anonymous';

      // Start async execution
      const response = await apiPost(
        API_ENDPOINTS.execute,
        {
          code,
          language,
          problem_id: problemId,
          user_identifier: userIdentifier,
          is_code_public: isCodePublic,
        },
        { requireAuth: true }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to execute code');
      }

      const data = await response.json();
      const taskId = data.task_id;

      showSnackbar('Code execution started...', 'info');

      // Poll for task completion
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await apiGet(API_ENDPOINTS.taskStatus(taskId), { requireAuth: true });
          if (!statusResponse.ok) {
            clearInterval(pollInterval);
            setLoading(false);
            return;
          }

          const statusData = await statusResponse.json();

          if (statusData.status === 'COMPLETED') {
            clearInterval(pollInterval);
            setLoading(false);
            setProgress({ current: 0, total: 0 });
            console.log('[CodeEditor] Task completed, result:', statusData.result);
            onTestResults(statusData.result);
            showSnackbar('Code executed successfully', 'success');
          } else if (statusData.status === 'FAILED') {
            clearInterval(pollInterval);
            setLoading(false);
            setProgress({ current: 0, total: 0 });
            showSnackbar(`Execution failed: ${statusData.result?.error || 'Unknown error'}`, 'error');
          } else if (statusData.status === 'PROGRESS' && statusData.result) {
            // Update progress
            setProgress({
              current: statusData.result.current || 0,
              total: statusData.result.total || 0
            });
          }
        } catch (pollError) {
          clearInterval(pollInterval);
          setLoading(false);
          showSnackbar('Error checking execution status', 'error');
        }
      }, 3000); // Poll every 3 seconds

    } catch (error) {
      console.error('Error executing code:', error);
      showSnackbar(error.message || 'An error occurred while executing your code', 'error');
      setLoading(false);
    }
  };

  return (
    <Paper sx={{ p: { xs: 2, sm: 3 }, mb: 3 }}>
      <Box sx={{
        display: 'flex',
        flexDirection: { xs: 'column', sm: 'row' },
        justifyContent: 'space-between',
        alignItems: { xs: 'flex-start', sm: 'center' },
        mb: 2,
        gap: 2
      }}>
        <Typography variant="h6" sx={{
          color: 'text.primary',
          fontWeight: 600,
          fontSize: { xs: '1.125rem', sm: '1.25rem' }
        }}>
          Code Editor
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: { xs: '100%', sm: 'auto' } }}>
          <FormControl size="small" sx={{ minWidth: { xs: '100%', sm: 150 } }}>
            <InputLabel sx={{ fontSize: { xs: '0.875rem', sm: '1rem' } }}>Language</InputLabel>
            <Select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              label="Language"
              sx={{ fontSize: { xs: '0.875rem', sm: '1rem' } }}
            >
              <MenuItem value="python">Python</MenuItem>
              <MenuItem value="javascript">JavaScript</MenuItem>
              <MenuItem value="cpp">C++</MenuItem>
              <MenuItem value="java">Java</MenuItem>
            </Select>
          </FormControl>
          <Typography
            variant="caption"
            sx={{
              color: 'text.secondary',
              display: { xs: 'none', sm: 'block' },
              fontSize: '0.75rem'
            }}
          >
            (Auto-detected)
          </Typography>
        </Box>
      </Box>

      <TextField
        fullWidth
        multiline
        rows={15}
        value={code}
        onChange={(e) => setCode(e.target.value)}
        placeholder="Enter your code here..."
        sx={{
          mb: 2,
          '& .MuiOutlinedInput-root': {
            fontFamily: 'monospace',
            fontSize: { xs: '0.813rem', sm: '0.875rem', md: '0.9rem' },
            backgroundColor: '#f5f5f5',
          }
        }}
        inputProps={{
          spellCheck: false,
          style: { fontFamily: 'monospace' }
        }}
      />

      <Box sx={{
        display: 'flex',
        flexDirection: { xs: 'column', sm: 'row' },
        gap: 2,
        mb: 2,
        alignItems: { xs: 'stretch', sm: 'center' },
        justifyContent: { xs: 'flex-start', sm: 'flex-end' }
      }}>
        <FormControlLabel
          control={
            <Checkbox
              checked={isCodePublic}
              onChange={(e) => setIsCodePublic(e.target.checked)}
            />
          }
          label="Make code public"
          sx={{
            '& .MuiFormControlLabel-label': {
              fontSize: { xs: '0.875rem', sm: '1rem' }
            }
          }}
        />
      </Box>

      <Button
        fullWidth
        variant="contained"
        size="large"
        onClick={handleExecute}
        disabled={loading}
        startIcon={loading ? <CircularProgress size={20} /> : <PlayArrowIcon />}
        sx={{
          backgroundColor: 'primary.main',
          fontSize: { xs: '0.875rem', sm: '1rem' },
          py: { xs: 1.5, sm: 1.75 },
          '&:hover': { backgroundColor: 'primary.dark' }
        }}
      >
        {loading ? (progress.total > 0 ? `Testing ${progress.current}/${progress.total}...` : 'Executing...') : 'Run Code'}
      </Button>

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

export default CodeEditor;
