import { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Radio,
  RadioGroup,
  FormControlLabel,
  FormControl,
  FormLabel,
  Select,
  MenuItem,
  Chip,
  Alert,
  CircularProgress,
  Snackbar,
} from '@mui/material';
import { apiPost, apiGet } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';

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
  if (maxScore === 0) return 'python';

  return Object.keys(scores).find(key => scores[key] === maxScore);
}

// URL extraction function
function extractProblemInfo(url) {
  // Baekjoon: https://www.acmicpc.net/problem/1000
  const baekjoonMatch = url.match(/acmicpc\.net\/problem\/(\d+)/);
  if (baekjoonMatch) {
    return {
      platform: 'baekjoon',
      problemId: baekjoonMatch[1]
    };
  }

  // Codeforces: https://codeforces.com/problemset/problem/1234/A
  const codeforcesMatch = url.match(/codeforces\.com\/problemset\/problem\/(\d+)\/([A-Z])/i);
  if (codeforcesMatch) {
    return {
      platform: 'codeforces',
      problemId: `${codeforcesMatch[1]}${codeforcesMatch[2]}`
    };
  }

  return null;
}

function ProblemRegister({ onBack }) {
  const [problemUrl, setProblemUrl] = useState('');
  const [urlError, setUrlError] = useState('');
  const [platform, setPlatform] = useState('baekjoon');
  const [problemId, setProblemId] = useState('');
  const [title, setTitle] = useState('');
  const [solutionCode, setSolutionCode] = useState('');
  const [language, setLanguage] = useState('python');
  const [constraints, setConstraints] = useState('');
  const [tags, setTags] = useState([]);
  const [tagInput, setTagInput] = useState('');
  const [generatorCode, setGeneratorCode] = useState('');
  const [numTestCases, setNumTestCases] = useState(10);
  const [testCases, setTestCases] = useState(null);
  const [loading, setLoading] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [registering, setRegistering] = useState(false);
  const [saving, setSaving] = useState(false);
  const [progress, setProgress] = useState('');
  const [drafts, setDrafts] = useState([]);
  const [showDrafts, setShowDrafts] = useState(false);
  const [loadedDraftId, setLoadedDraftId] = useState(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });

  const showSnackbar = (message, severity = 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  // Fetch drafts on component mount
  useEffect(() => {
    fetchDrafts();
  }, []);

  // Load draft from URL params
  useEffect(() => {
    const loadDraftFromUrl = async () => {
      const urlParams = new URLSearchParams(window.location.search);
      const draftId = urlParams.get('draft_id');

      if (draftId) {
        // Fetch draft data from server
        try {
          const response = await apiGet(API_ENDPOINTS.drafts);
          if (response.ok) {
            const data = await response.json();
            const draft = data.drafts.find(d => d.id === parseInt(draftId));

            if (draft) {
              // Load data from draft
              setPlatform(draft.platform);
              setProblemId(draft.problem_id);
              setTitle(draft.title);
              setProblemUrl(draft.problem_url || '');
              setTags(draft.tags || []);
              setSolutionCode(draft.solution_code || '');
              setLanguage(draft.language || 'python');
              setConstraints(draft.constraints || '');
              setLoadedDraftId(draftId);
            } else {
              console.error('Draft not found:', draftId);
              alert('Draft not found');
            }
          }
        } catch (error) {
          console.error('Error loading draft:', error);
          alert('Failed to load draft: ' + error.message);
        }
      }
    };

    loadDraftFromUrl();
  }, []);

  const fetchDrafts = async () => {
    try {
      const response = await apiGet(API_ENDPOINTS.drafts);
      if (response.ok) {
        const data = await response.json();
        setDrafts(data.drafts || []);
      }
    } catch (error) {
      console.error('Error fetching drafts:', error);
    }
  };

  // Handle URL change and auto-extract problem info
  const handleUrlChange = (url) => {
    setProblemUrl(url);
    setUrlError('');

    if (!url.trim()) {
      return;
    }

    const extracted = extractProblemInfo(url);
    if (extracted) {
      setPlatform(extracted.platform);
      setProblemId(extracted.problemId);
      setUrlError('');
    } else {
      setUrlError('Invalid URL format. Please use Baekjoon or Codeforces URL.');
    }
  };

  const handleCodeChange = (code) => {
    setSolutionCode(code);
    if (code.trim()) {
      const detected = detectLanguage(code);
      setLanguage(detected);
    }
  };

  // Handle tag input
  const handleAddTag = () => {
    const trimmedTag = tagInput.trim().toLowerCase();
    if (trimmedTag && !tags.includes(trimmedTag)) {
      setTags([...tags, trimmedTag]);
      setTagInput('');
    }
  };

  const handleTagKeyPress = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddTag();
    }
  };

  const handleRemoveTag = (tagToRemove) => {
    setTags(tags.filter(tag => tag !== tagToRemove));
  };

  const handleLoadDraft = (draft) => {
    setProblemUrl(draft.problem_url || '');
    setPlatform(draft.platform);
    setProblemId(draft.problem_id);
    setTitle(draft.title);
    setTags(draft.tags || []);
    setSolutionCode(draft.solution_code || '');
    setLanguage(draft.language || 'python');
    setConstraints(draft.constraints || '');
    setLoadedDraftId(draft.id); // Track the loaded draft ID
    setShowDrafts(false);

    // Refresh drafts list after loading
    fetchDrafts();
  };

  const handleNewDraft = () => {
    // Clear all form fields for a new draft
    setProblemUrl('');
    setPlatform('baekjoon');
    setProblemId('');
    setTitle('');
    setSolutionCode('');
    setConstraints('');
    setTags([]);
    setLanguage('python');
    setUrlError('');
    setGeneratorCode('');
    setTestCases(null);
    setLoadedDraftId(null);
    setShowDrafts(false);
  };

  const handleGenerateScript = async () => {
    if (!platform || !problemId || !title || !constraints) {
      alert('Please fill in Platform, Problem ID, Title, and Constraints');
      return;
    }

    setLoading(true);
    setProgress('Creating script generation job...');

    try {
      const response = await apiPost(
        API_ENDPOINTS.generateTestCases,
        {
          platform,
          problem_id: problemId,
          title,
          problem_url: problemUrl,
          tags,
          solution_code: solutionCode,
          language,
          constraints,
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to create job');
      }

      const data = await response.json();
      setProgress('Job created! Redirecting to job detail page...');

      // Redirect to job detail page after a short delay
      setTimeout(() => {
        window.location.href = `/jobs?job_id=${data.job_id}`;
      }, 1500);
    } catch (error) {
      console.error('Error creating job:', error);
      alert('An error occurred while creating job: ' + error.message);
      setProgress('');
      setLoading(false);
    }
  };

  const handleExecuteScript = async () => {
    if (!generatorCode) {
      alert('Please generate script first');
      return;
    }

    if (numTestCases < 1 || numTestCases > 1000) {
      alert('Number of test cases must be between 1 and 1000');
      return;
    }

    setExecuting(true);
    setProgress(`Executing script to generate ${numTestCases} test cases...`);

    try {
      const response = await apiPost(API_ENDPOINTS.executeTestCases, {
        generator_code: generatorCode,
        num_cases: numTestCases,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to execute script');
      }

      const data = await response.json();
      setTestCases(data.test_cases.map(input => ({ input })));
      setProgress(`Successfully generated ${data.count} test cases!`);
      setTimeout(() => setProgress(''), 3000);
    } catch (error) {
      console.error('Error executing script:', error);
      alert('An error occurred while executing script: ' + error.message);
      setProgress('');
    } finally {
      setExecuting(false);
    }
  };

  const handleSaveDraft = async () => {
    if (!platform || !problemId || !title) {
      alert('Please fill in at least Platform, Problem ID, and Title');
      return;
    }

    setSaving(true);
    setProgress('Saving draft...');

    try {
      const response = await apiPost(API_ENDPOINTS.saveDraft, {
        id: loadedDraftId, // Include loaded draft ID if exists
        platform,
        problem_id: problemId,
        title,
        solution_code: solutionCode,
        language,
        constraints,
        tags,
        problem_url: problemUrl,
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error('Save draft error:', errorData);
        const errorMessage = typeof errorData.error === 'string'
          ? errorData.error
          : JSON.stringify(errorData.error || errorData);
        throw new Error(errorMessage);
      }

      setProgress('Draft saved successfully!');
      setTimeout(() => setProgress(''), 3000);

      // Refresh drafts list
      fetchDrafts();
    } catch (error) {
      console.error('Error saving draft:', error);
      alert('An error occurred while saving draft: ' + error.message);
      setProgress('');
    } finally {
      setSaving(false);
    }
  };

  const handleRegister = async () => {
    if (!testCases || testCases.length === 0) {
      alert('Please generate test cases first');
      return;
    }

    setRegistering(true);
    setProgress('Executing solution code and registering problem...');

    try {
      const response = await apiPost(API_ENDPOINTS.registerProblem, {
        platform,
        problem_id: problemId,
        title,
        solution_code: solutionCode,
        language,
        constraints,
        tags,
        problem_url: problemUrl,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to register problem');
      }

      const data = await response.json();
      setProgress('');
      alert(`Problem registered successfully!\nTest cases: ${data.problem.test_cases.length}`);

      // Reset form
      setProblemUrl('');
      setPlatform('baekjoon');
      setProblemId('');
      setTitle('');
      setSolutionCode('');
      setConstraints('');
      setTags([]);
      setTestCases(null);
      setLanguage('python');
      setUrlError('');
      setLoadedDraftId(null);
    } catch (error) {
      console.error('Error registering problem:', error);
      alert('An error occurred while registering the problem: ' + error.message);
      setProgress('');
    } finally {
      setRegistering(false);
    }
  };

  return (
    <Box sx={{ maxWidth: 1100, margin: '0 auto' }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, color: 'primary.main' }}>
          Register New Problem
        </Typography>
      </Box>

      {/* Main Form */}
      <Paper sx={{ p: 4, border: 1, borderColor: 'divider' }}>
        {/* Problem Information Section */}
        <Box sx={{ mb: 4, pb: 4, borderBottom: 2, borderColor: 'divider' }}>
          <Typography variant="h6" sx={{ mb: 3, fontWeight: 700, color: 'primary.main' }}>
            Problem Information
          </Typography>

          {/* Problem URL */}
          <Box sx={{ mb: 3 }}>
            <TextField
              fullWidth
              label="Problem URL"
              placeholder="e.g., https://www.acmicpc.net/problem/1000"
              value={problemUrl}
              onChange={(e) => handleUrlChange(e.target.value)}
              error={!!urlError}
              color={problemUrl && !urlError && problemId ? 'success' : 'primary'}
            />
            {urlError && (
              <Alert severity="error" sx={{ mt: 1 }}>
                {urlError}
              </Alert>
            )}
            {problemUrl && !urlError && problemId && (
              <Alert severity="success" sx={{ mt: 1 }}>
                Extracted: {platform.charAt(0).toUpperCase() + platform.slice(1)} - Problem {problemId}
              </Alert>
            )}
          </Box>

          {/* Platform */}
          <Box sx={{ mb: 3 }}>
            <FormControl component="fieldset">
              <FormLabel component="legend" sx={{ mb: 1, fontWeight: 600 }}>
                Platform
              </FormLabel>
              <RadioGroup
                row
                value={platform}
                onChange={(e) => setPlatform(e.target.value)}
              >
                <FormControlLabel
                  value="baekjoon"
                  control={<Radio />}
                  label="Baekjoon"
                  sx={{
                    border: 1,
                    borderColor: platform === 'baekjoon' ? 'primary.main' : 'divider',
                    borderRadius: 1,
                    px: 2,
                    py: 0.5,
                    mr: 2,
                  }}
                />
                <FormControlLabel
                  value="codeforces"
                  control={<Radio />}
                  label="Codeforces"
                  sx={{
                    border: 1,
                    borderColor: platform === 'codeforces' ? 'primary.main' : 'divider',
                    borderRadius: 1,
                    px: 2,
                    py: 0.5,
                  }}
                />
              </RadioGroup>
            </FormControl>
          </Box>

          {/* Problem Number */}
          <Box sx={{ mb: 3 }}>
            <TextField
              fullWidth
              label="Problem Number"
              placeholder="e.g., 1000 or 1A"
              value={problemId}
              onChange={(e) => setProblemId(e.target.value)}
            />
          </Box>

          {/* Problem Title */}
          <Box sx={{ mb: 3 }}>
            <TextField
              fullWidth
              label="Problem Title"
              placeholder="e.g., A+B"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </Box>

          {/* Tags */}
          <Box sx={{ mb: 3 }}>
            <Typography variant="body2" sx={{ mb: 1, fontWeight: 600, color: 'text.secondary' }}>
              Tags
            </Typography>
            <Paper
              variant="outlined"
              sx={{
                p: 2,
                mb: 2,
                minHeight: 60,
                display: 'flex',
                flexWrap: 'wrap',
                gap: 1,
                alignItems: 'center',
              }}
            >
              {tags.length === 0 ? (
                <Typography variant="body2" sx={{ color: 'text.secondary', fontStyle: 'italic' }}>
                  No tags added yet
                </Typography>
              ) : (
                tags.map((tag, index) => (
                  <Chip
                    key={index}
                    label={tag}
                    onDelete={() => handleRemoveTag(tag)}
                    color="primary"
                    sx={{ fontWeight: 600 }}
                  />
                ))
              )}
            </Paper>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <TextField
                fullWidth
                placeholder="Add tags (e.g., graph, dp, greedy)..."
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyPress={handleTagKeyPress}
                size="small"
              />
              <Button
                variant="outlined"
                onClick={handleAddTag}
                disabled={!tagInput.trim()}
                sx={{ minWidth: 80 }}
              >
                Add
              </Button>
            </Box>
          </Box>
        </Box>

        {/* Solution Code Section */}
        <Box sx={{ mb: 4, pb: 4, borderBottom: 2, borderColor: 'divider' }}>
          <Typography variant="h6" sx={{ mb: 3, fontWeight: 700, color: 'primary.main' }}>
            Solution Code
          </Typography>

          <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              Language:
            </Typography>
            <Select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              size="small"
              sx={{ minWidth: 120 }}
            >
              <MenuItem value="python">Python</MenuItem>
              <MenuItem value="javascript">JavaScript</MenuItem>
              <MenuItem value="cpp">C++</MenuItem>
              <MenuItem value="java">Java</MenuItem>
            </Select>
            <Typography variant="caption" sx={{ color: 'text.secondary', fontStyle: 'italic' }}>
              (Auto-detected)
            </Typography>
          </Box>

          <TextField
            fullWidth
            multiline
            rows={15}
            placeholder="Enter your solution code..."
            value={solutionCode}
            onChange={(e) => handleCodeChange(e.target.value)}
            InputProps={{
              sx: {
                fontFamily: "'JetBrains Mono', 'Fira Code', 'Courier New', monospace",
                fontSize: '0.9rem',
              },
            }}
            inputProps={{
              spellCheck: false,
            }}
          />
        </Box>

        {/* Input Constraints Section */}
        <Box sx={{ mb: 4, pb: 4, borderBottom: 2, borderColor: 'divider' }}>
          <Typography variant="h6" sx={{ mb: 3, fontWeight: 700, color: 'primary.main' }}>
            Input Constraints
          </Typography>

          <TextField
            fullWidth
            multiline
            rows={8}
            label="Constraint Description"
            placeholder="e.g.,&#10;- Two integers A and B are given in the first line (0 ≤ A, B ≤ 10,000)&#10;- A and B are separated by a space&#10;- Multiple test cases may exist"
            value={constraints}
            onChange={(e) => setConstraints(e.target.value)}
          />
        </Box>

        {/* Action Buttons */}
        <Box sx={{ display: 'flex', gap: 2, mt: 4 }}>
          <Button
            variant="contained"
            onClick={handleSaveDraft}
            disabled={loading || executing || registering || saving}
            sx={{
              flex: 1,
              py: 1.5,
              fontWeight: 700,
              textTransform: 'uppercase',
              bgcolor: 'grey.700',
              '&:hover': {
                bgcolor: 'grey.800',
              },
            }}
          >
            {saving ? 'Saving...' : 'Save'}
          </Button>
        </Box>

        {/* Progress Message */}
        {progress && (
          <Alert severity="info" sx={{ mt: 2 }}>
            {progress}
          </Alert>
        )}

        {/* Generator Code Section */}
        {generatorCode && (
          <Box sx={{ mt: 4, pt: 4, borderTop: 1, borderColor: 'divider' }}>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 700, color: 'primary.main' }}>
              Generated Test Case Generator Script
            </Typography>
            <Paper
              variant="outlined"
              sx={{
                p: 2,
                maxHeight: 400,
                overflow: 'auto',
                bgcolor: 'grey.50',
              }}
            >
              <Box
                component="pre"
                sx={{
                  fontFamily: "'JetBrains Mono', 'Fira Code', 'Courier New', monospace",
                  fontSize: '0.85rem',
                  margin: 0,
                  whiteSpace: 'pre-wrap',
                  wordWrap: 'break-word',
                }}
              >
                {generatorCode}
              </Box>
            </Paper>

            <Box sx={{ mt: 3, pt: 2, borderTop: 1, borderColor: 'divider' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                <Typography variant="body2" sx={{ fontWeight: 600, whiteSpace: 'nowrap' }}>
                  Number of test cases to generate:
                </Typography>
                <TextField
                  type="number"
                  value={numTestCases}
                  onChange={(e) => setNumTestCases(parseInt(e.target.value) || 1)}
                  inputProps={{ min: 1, max: 1000 }}
                  size="small"
                  sx={{ width: 120 }}
                />
                <Button
                  variant="contained"
                  color="success"
                  onClick={handleExecuteScript}
                  disabled={loading || executing || registering || saving}
                  sx={{ fontWeight: 700, textTransform: 'uppercase' }}
                >
                  {executing ? 'Executing...' : 'Execute Script'}
                </Button>
              </Box>
              <Alert severity="info" icon={false}>
                Distribution: 50% small ({Math.floor(numTestCases * 0.5)}),
                30% medium ({Math.floor(numTestCases * 0.3)}),
                20% large ({numTestCases - Math.floor(numTestCases * 0.5) - Math.floor(numTestCases * 0.3)})
              </Alert>
            </Box>
          </Box>
        )}

        {/* Test Cases Preview */}
        {testCases && (
          <Box sx={{ mt: 4, pt: 4, borderTop: 1, borderColor: 'divider' }}>
            <Typography variant="h6" sx={{ mb: 2, fontWeight: 700 }}>
              Test Cases Preview ({testCases.length} cases)
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mb: 3 }}>
              {testCases.slice(0, 10).map((tc, index) => (
                <Paper
                  key={index}
                  variant="outlined"
                  sx={{
                    p: 2,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 2,
                    '&:hover': {
                      bgcolor: 'action.hover',
                      borderColor: 'primary.main',
                    },
                  }}
                >
                  <Chip
                    label={`#${index + 1}`}
                    color="primary"
                    variant="outlined"
                    sx={{ minWidth: 60, fontWeight: 700 }}
                  />
                  <Box
                    component="pre"
                    sx={{
                      flex: 1,
                      margin: 0,
                      p: 1,
                      bgcolor: 'grey.50',
                      border: 1,
                      borderColor: 'divider',
                      borderRadius: 1,
                      fontFamily: "'JetBrains Mono', 'Fira Code', 'Courier New', monospace",
                      fontSize: '0.8rem',
                      whiteSpace: 'pre-wrap',
                      wordWrap: 'break-word',
                    }}
                  >
                    {tc.input}
                  </Box>
                </Paper>
              ))}
              {testCases.length > 10 && (
                <Typography variant="body2" sx={{ textAlign: 'center', color: 'text.secondary', fontStyle: 'italic', py: 1 }}>
                  ... and {testCases.length - 10} more
                </Typography>
              )}
            </Box>

            <Button
              fullWidth
              variant="contained"
              color="success"
              onClick={handleRegister}
              disabled={loading || executing || registering || saving}
              sx={{ py: 1.5, fontWeight: 700, textTransform: 'uppercase' }}
            >
              {registering ? 'Registering...' : 'Register Problem'}
            </Button>
          </Box>
        )}
      </Paper>
    </Box>
  );
}

export default ProblemRegister;
