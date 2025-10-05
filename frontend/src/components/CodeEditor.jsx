import { useState, useEffect } from 'react';
import { apiPost } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';
import { getUser } from '../utils/auth';
import './CodeEditor.css';

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
    <div className="code-editor">
      <div className="editor-header">
        <h3>Code Editor</h3>
        <div className="language-selector">
          <label>Language: </label>
          <select value={language} onChange={(e) => setLanguage(e.target.value)}>
            <option value="python">Python</option>
            <option value="javascript">JavaScript</option>
            <option value="cpp">C++</option>
            <option value="java">Java</option>
          </select>
          <span className="detected-language">
            (Auto-detected)
          </span>
        </div>
      </div>

      <textarea
        className="code-input"
        value={code}
        onChange={(e) => setCode(e.target.value)}
        placeholder="Enter your code here..."
        spellCheck="false"
      />

      <div className="user-settings">
        <div className="user-id-input">
          <label>User ID (Optional):</label>
          <input
            type="text"
            placeholder="Anonymous"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
          />
        </div>

        <div className="code-public-toggle">
          <label>
            <input
              type="checkbox"
              checked={isCodePublic}
              onChange={(e) => setIsCodePublic(e.target.checked)}
            />
            Make code public
          </label>
        </div>
      </div>

      <button
        className="execute-button"
        onClick={handleExecute}
        disabled={loading}
      >
        {loading ? 'Executing...' : 'Validate Test Cases'}
      </button>
    </div>
  );
}

export default CodeEditor;
