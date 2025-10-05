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
          const statusResponse = await apiGet(`/tasks/${taskId}/`, { requireAuth: true });
          if (!statusResponse.ok) {
            clearInterval(pollInterval);
            setLoading(false);
            return;
          }

          const statusData = await statusResponse.json();

          if (statusData.status === 'COMPLETED') {
            clearInterval(pollInterval);
            setLoading(false);
            onTestResults(statusData.result);
            showSnackbar('Code executed successfully', 'success');
          } else if (statusData.status === 'FAILED') {
            clearInterval(pollInterval);
            setLoading(false);
            showSnackbar(`Execution failed: ${statusData.result?.error || 'Unknown error'}`, 'error');
          }
        } catch (pollError) {
          clearInterval(pollInterval);
          setLoading(false);
          showSnackbar('Error checking execution status', 'error');
        }
      }, 2000); // Poll every 2 seconds

    } catch (error) {
      console.error('Error executing code:', error);
      showSnackbar(error.message || 'An error occurred while executing your code', 'error');
      setLoading(false);
    }
  };

  return (
    <Paper sx={{ p: 3, mb: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" sx={{ color: 'text.primary', fontWeight: 600 }}>
          Code Editor
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Language</InputLabel>
            <Select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              label="Language"
            >
              <MenuItem value="python">Python</MenuItem>
              <MenuItem value="javascript">JavaScript</MenuItem>
              <MenuItem value="cpp">C++</MenuItem>
              <MenuItem value="java">Java</MenuItem>
            </Select>
          </FormControl>
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
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
            fontSize: '0.9rem',
            backgroundColor: '#f5f5f5',
          }
        }}
        inputProps={{
          spellCheck: false,
          style: { fontFamily: 'monospace' }
        }}
      />

      <Box sx={{ display: 'flex', gap: 2, mb: 2, alignItems: 'center', justifyContent: 'flex-end' }}>
        <FormControlLabel
          control={
            <Checkbox
              checked={isCodePublic}
              onChange={(e) => setIsCodePublic(e.target.checked)}
            />
          }
          label="Make code public"
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
          '&:hover': { backgroundColor: 'primary.dark' }
        }}
      >
        {loading ? 'Executing...' : 'Validate Test Cases'}
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
