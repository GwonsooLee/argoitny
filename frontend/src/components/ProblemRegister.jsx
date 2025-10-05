import { useState, useEffect } from 'react';
import { apiPost, apiGet } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';
import './ProblemRegister.css';

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

  // Fetch drafts on component mount
  useEffect(() => {
    fetchDrafts();
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
    setProgress('Generating test case generator script via Gemini API...');

    try {
      const response = await apiPost(API_ENDPOINTS.generateTestCases, {
        platform,
        problem_id: problemId,
        title,
        solution_code: solutionCode,
        language,
        constraints,
        tags,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to generate script');
      }

      const data = await response.json();
      setGeneratorCode(data.generator_code);
      setProgress('Script generated successfully!');
      setTimeout(() => setProgress(''), 3000);
    } catch (error) {
      console.error('Error generating script:', error);
      alert('An error occurred while generating script: ' + error.message);
      setProgress('');
    } finally {
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
    <div className="problem-register">
      <div className="register-header">
        <h2>Register New Problem</h2>
        <div className="header-actions">
          {loadedDraftId && (
            <button
              onClick={handleNewDraft}
              className="new-draft-button"
            >
              New Draft
            </button>
          )}
          <button
            onClick={() => setShowDrafts(!showDrafts)}
            className="load-draft-button"
          >
            Load Draft {drafts.length > 0 && `(${drafts.length})`}
          </button>
          <button onClick={onBack} className="back-button">← Back</button>
        </div>
      </div>

      {showDrafts && drafts.length > 0 && (
        <div className="drafts-section">
          <h3>Saved Drafts</h3>
          <div className="drafts-list">
            {drafts.map((draft) => (
              <div key={draft.id} className="draft-item">
                <div className="draft-info">
                  <div className="draft-title">
                    {draft.title}
                  </div>
                  <div className="draft-meta">
                    {draft.platform.charAt(0).toUpperCase() + draft.platform.slice(1)} - {draft.problem_id}
                    {draft.tags && draft.tags.length > 0 && (
                      <span className="draft-tags">
                        {draft.tags.map((tag, idx) => (
                          <span key={idx} className="draft-tag">{tag}</span>
                        ))}
                      </span>
                    )}
                  </div>
                  <div className="draft-date">
                    {new Date(draft.created_at).toLocaleDateString()}
                  </div>
                </div>
                <button
                  onClick={() => handleLoadDraft(draft)}
                  className="load-button"
                >
                  Load
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="register-form">
        <div className="form-section">
          <h3>Problem Information</h3>

          <div className="form-group">
            <label>Problem URL</label>
            <input
              type="text"
              placeholder="e.g., https://www.acmicpc.net/problem/1000"
              value={problemUrl}
              onChange={(e) => handleUrlChange(e.target.value)}
              className={urlError ? 'input-error' : problemUrl && !urlError ? 'input-success' : ''}
            />
            {urlError && <div className="error-message">{urlError}</div>}
            {problemUrl && !urlError && problemId && (
              <div className="success-message">
                Extracted: {platform.charAt(0).toUpperCase() + platform.slice(1)} - Problem {problemId}
              </div>
            )}
          </div>

          <div className="form-group">
            <label>Platform</label>
            <div className="platform-selector">
              <label>
                <input
                  type="radio"
                  value="baekjoon"
                  checked={platform === 'baekjoon'}
                  onChange={(e) => setPlatform(e.target.value)}
                />
                Baekjoon
              </label>
              <label>
                <input
                  type="radio"
                  value="codeforces"
                  checked={platform === 'codeforces'}
                  onChange={(e) => setPlatform(e.target.value)}
                />
                Codeforces
              </label>
            </div>
          </div>

          <div className="form-group">
            <label>Problem Number</label>
            <input
              type="text"
              placeholder="e.g., 1000 or 1A"
              value={problemId}
              onChange={(e) => setProblemId(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label>Problem Title</label>
            <input
              type="text"
              placeholder="e.g., A+B"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label>Tags</label>
            <div className="tags-container">
              <div className="tags-list">
                {tags.map((tag, index) => (
                  <span key={index} className="tag-chip">
                    {tag}
                    <button
                      type="button"
                      className="tag-remove"
                      onClick={() => handleRemoveTag(tag)}
                      aria-label={`Remove ${tag} tag`}
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
              <div className="tag-input-group">
                <input
                  type="text"
                  placeholder="Add tags (e.g., graph, dp, greedy)..."
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyPress={handleTagKeyPress}
                  className="tag-input"
                />
                <button
                  type="button"
                  onClick={handleAddTag}
                  className="tag-add-button"
                  disabled={!tagInput.trim()}
                >
                  Add
                </button>
              </div>
            </div>
          </div>
        </div>

        <div className="form-section">
          <h3>Solution Code</h3>

          <div className="form-group">
            <div className="code-header">
              <label>Language: </label>
              <select value={language} onChange={(e) => setLanguage(e.target.value)}>
                <option value="python">Python</option>
                <option value="javascript">JavaScript</option>
                <option value="cpp">C++</option>
                <option value="java">Java</option>
              </select>
              <span className="detected-info">(Auto-detected)</span>
            </div>

            <textarea
              className="code-textarea"
              placeholder="Enter your solution code..."
              value={solutionCode}
              onChange={(e) => handleCodeChange(e.target.value)}
              spellCheck="false"
            />
          </div>
        </div>

        <div className="form-section">
          <h3>Input Constraints</h3>

          <div className="form-group">
            <label>Constraint Description</label>
            <textarea
              className="constraints-textarea"
              placeholder="e.g.,&#10;- Two integers A and B are given in the first line (0 ≤ A, B ≤ 10,000)&#10;- A and B are separated by a space&#10;- Multiple test cases may exist"
              value={constraints}
              onChange={(e) => setConstraints(e.target.value)}
            />
          </div>
        </div>

        <div className="action-buttons">
          <button
            onClick={handleSaveDraft}
            disabled={loading || executing || registering || saving}
            className="save-draft-button"
          >
            {saving ? 'Saving...' : 'Save Draft'}
          </button>

          <button
            onClick={handleGenerateScript}
            disabled={loading || executing || registering || saving}
            className="generate-button"
          >
            {loading ? 'Generating...' : 'Generate Script'}
          </button>
        </div>

        {progress && (
          <div className="progress-message">
            {progress}
          </div>
        )}

        {generatorCode && (
          <div className="generator-code-section">
            <h3>Generated Test Case Generator Script</h3>
            <pre className="generator-code">{generatorCode}</pre>

            <div className="execute-section">
              <div className="execute-controls">
                <label htmlFor="numTestCases">Number of test cases to generate:</label>
                <input
                  id="numTestCases"
                  type="number"
                  min="1"
                  max="1000"
                  value={numTestCases}
                  onChange={(e) => setNumTestCases(parseInt(e.target.value) || 1)}
                  className="num-cases-input"
                />
                <button
                  onClick={handleExecuteScript}
                  disabled={loading || executing || registering || saving}
                  className="execute-button"
                >
                  {executing ? 'Executing...' : 'Execute Script'}
                </button>
              </div>
              <div className="distribution-info">
                Distribution: 50% small ({Math.floor(numTestCases * 0.5)}),
                30% medium ({Math.floor(numTestCases * 0.3)}),
                20% large ({numTestCases - Math.floor(numTestCases * 0.5) - Math.floor(numTestCases * 0.3)})
              </div>
            </div>
          </div>
        )}

        {testCases && (
          <div className="test-cases-preview">
            <h3>Test Cases Preview ({testCases.length} cases)</h3>
            <div className="preview-list">
              {testCases.slice(0, 10).map((tc, index) => (
                <div key={index} className="preview-item">
                  <span className="preview-index">#{index + 1}</span>
                  <pre className="preview-input">{tc.input}</pre>
                </div>
              ))}
              {testCases.length > 10 && (
                <div className="preview-more">
                  ... and {testCases.length - 10} more
                </div>
              )}
            </div>

            <button
              onClick={handleRegister}
              disabled={loading || executing || registering || saving}
              className="register-button"
            >
              {registering ? 'Registering...' : 'Register Problem'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default ProblemRegister;
