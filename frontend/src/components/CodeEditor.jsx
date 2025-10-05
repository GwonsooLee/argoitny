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
  CircularProgress
} from '@mui/material';
import { PlayArrow as PlayArrowIcon } from '@mui/icons-material';
import { apiPost } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';
import { getUser } from '../utils/auth';

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
  const [userId, setUserId] = useState('');
  const [isCodePublic, setIsCodePublic] = useState(false);

  useEffect(() => {
    if (code.trim()) {
      const detected = detectLanguage(code);
      setLanguage(detected);
    }
  }, [code]);

  const handleExecute = async () => {
    if (!code.trim()) {
      alert('Please enter your code');
      return;
    }

    setLoading(true);
    try {
      const user = getUser();
      const userIdentifier = userId.trim() || (user ? user.email : 'anonymous');

      const response = await apiPost(
        API_ENDPOINTS.execute,
        {
          code,
          language,
          problem_id: problemId,
          user_identifier: userIdentifier,
          is_code_public: isCodePublic,
        },
        { requireAuth: !!user }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to execute code');
      }

      const data = await response.json();
      onTestResults(data);
    } catch (error) {
      console.error('Error executing code:', error);
      alert('An error occurred while executing your code');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Paper sx={{ p: 3, mb: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" sx={{ color: 'white', fontWeight: 600 }}>
          Code Editor
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel sx={{ color: 'rgba(255, 255, 255, 0.7)' }}>Language</InputLabel>
            <Select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              label="Language"
              sx={{
                color: 'white',
                '.MuiOutlinedInput-notchedOutline': {
                  borderColor: 'rgba(255, 255, 255, 0.2)',
                },
                '&:hover .MuiOutlinedInput-notchedOutline': {
                  borderColor: 'rgba(255, 255, 255, 0.3)',
                },
                '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                  borderColor: 'primary.main',
                },
              }}
            >
              <MenuItem value="python">Python</MenuItem>
              <MenuItem value="javascript">JavaScript</MenuItem>
              <MenuItem value="cpp">C++</MenuItem>
              <MenuItem value="java">Java</MenuItem>
            </Select>
          </FormControl>
          <Typography variant="caption" sx={{ color: 'rgba(255, 255, 255, 0.5)' }}>
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
            color: 'white',
            backgroundColor: 'rgba(0, 0, 0, 0.3)',
            '& fieldset': {
              borderColor: 'rgba(255, 255, 255, 0.2)',
            },
            '&:hover fieldset': {
              borderColor: 'rgba(255, 255, 255, 0.3)',
            },
            '&.Mui-focused fieldset': {
              borderColor: 'primary.main',
            }
          }
        }}
        inputProps={{
          spellCheck: false,
          style: { fontFamily: 'monospace' }
        }}
      />

      <Box sx={{ display: 'flex', gap: 2, mb: 2, alignItems: 'center' }}>
        <TextField
          label="User ID (Optional)"
          placeholder="Anonymous"
          value={userId}
          onChange={(e) => setUserId(e.target.value)}
          size="small"
          sx={{
            flexGrow: 1,
            '& .MuiOutlinedInput-root': {
              color: 'white',
              '& fieldset': {
                borderColor: 'rgba(255, 255, 255, 0.2)',
              },
              '&:hover fieldset': {
                borderColor: 'rgba(255, 255, 255, 0.3)',
              },
              '&.Mui-focused fieldset': {
                borderColor: 'primary.main',
              }
            },
            '& .MuiInputLabel-root': {
              color: 'rgba(255, 255, 255, 0.7)',
            }
          }}
        />
        <FormControlLabel
          control={
            <Checkbox
              checked={isCodePublic}
              onChange={(e) => setIsCodePublic(e.target.checked)}
              sx={{
                color: 'white',
                '&.Mui-checked': {
                  color: 'primary.main',
                }
              }}
            />
          }
          label="Make code public"
          sx={{ color: 'white' }}
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
    </Paper>
  );
}

export default CodeEditor;
