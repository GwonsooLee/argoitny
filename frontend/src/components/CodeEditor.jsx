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
      alert('코드를 입력하세요');
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
      alert('코드 실행 중 오류가 발생했습니다');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="code-editor">
      <div className="editor-header">
        <h3>코드 입력</h3>
        <div className="language-selector">
          <label>언어: </label>
          <select value={language} onChange={(e) => setLanguage(e.target.value)}>
            <option value="python">Python</option>
            <option value="javascript">JavaScript</option>
            <option value="cpp">C++</option>
            <option value="java">Java</option>
          </select>
          <span className="detected-language">
            (자동 감지됨)
          </span>
        </div>
      </div>

      <textarea
        className="code-input"
        value={code}
        onChange={(e) => setCode(e.target.value)}
        placeholder="여기에 코드를 입력하세요..."
        spellCheck="false"
      />

      <div className="user-settings">
        <div className="user-id-input">
          <label>사용자 ID (선택):</label>
          <input
            type="text"
            placeholder="익명"
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
            코드 공개
          </label>
        </div>
      </div>

      <button
        className="execute-button"
        onClick={handleExecute}
        disabled={loading}
      >
        {loading ? '실행 중...' : '반례 검증하기'}
      </button>
    </div>
  );
}

export default CodeEditor;
