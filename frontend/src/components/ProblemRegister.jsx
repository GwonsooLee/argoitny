import { useState } from 'react';
import { apiPost } from '../utils/api-client';
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

function ProblemRegister({ onBack }) {
  const [platform, setPlatform] = useState('baekjoon');
  const [problemId, setProblemId] = useState('');
  const [title, setTitle] = useState('');
  const [solutionCode, setSolutionCode] = useState('');
  const [language, setLanguage] = useState('python');
  const [constraints, setConstraints] = useState('');
  const [testCases, setTestCases] = useState(null);
  const [loading, setLoading] = useState(false);
  const [registering, setRegistering] = useState(false);
  const [progress, setProgress] = useState('');

  const handleCodeChange = (code) => {
    setSolutionCode(code);
    if (code.trim()) {
      const detected = detectLanguage(code);
      setLanguage(detected);
    }
  };

  const handleGenerateTestCases = async () => {
    if (!platform || !problemId || !title || !solutionCode || !constraints) {
      alert('모든 필드를 입력하세요');
      return;
    }

    setLoading(true);
    setProgress('Gemini API를 통해 반례 생성 중...');

    try {
      const response = await apiPost(API_ENDPOINTS.generateTestCases, {
        platform,
        problem_id: problemId,
        title,
        solution_code: solutionCode,
        language,
        constraints,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || '반례 생성 실패');
      }

      const data = await response.json();
      setTestCases(data.test_cases);
      setProgress(`${data.test_cases.length}개의 반례가 생성되었습니다!`);
    } catch (error) {
      console.error('Error generating test cases:', error);
      alert('반례 생성 중 오류가 발생했습니다: ' + error.message);
      setProgress('');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async () => {
    if (!testCases || testCases.length === 0) {
      alert('먼저 반례를 생성하세요');
      return;
    }

    setRegistering(true);
    setProgress('정답 코드 실행 중...');

    try {
      const response = await apiPost(API_ENDPOINTS.registerProblem, {
        platform,
        problem_id: problemId,
        title,
        solution_code: solutionCode,
        language,
        constraints,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || '문제 등록 실패');
      }

      const data = await response.json();
      setProgress('');
      alert(`문제가 성공적으로 등록되었습니다!\n테스트 케이스: ${data.problem.test_cases.length}개`);

      // Reset form
      setPlatform('baekjoon');
      setProblemId('');
      setTitle('');
      setSolutionCode('');
      setConstraints('');
      setTestCases(null);
      setLanguage('python');
    } catch (error) {
      console.error('Error registering problem:', error);
      alert('문제 등록 중 오류가 발생했습니다: ' + error.message);
      setProgress('');
    } finally {
      setRegistering(false);
    }
  };

  return (
    <div className="problem-register">
      <div className="register-header">
        <h2>새 문제 등록</h2>
        <button onClick={onBack} className="back-button">← 뒤로 가기</button>
      </div>

      <div className="register-form">
        <div className="form-section">
          <h3>문제 정보</h3>

          <div className="form-group">
            <label>플랫폼</label>
            <div className="platform-selector">
              <label>
                <input
                  type="radio"
                  value="baekjoon"
                  checked={platform === 'baekjoon'}
                  onChange={(e) => setPlatform(e.target.value)}
                />
                백준 (Baekjoon)
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
            <label>문제 번호</label>
            <input
              type="text"
              placeholder="예: 1000 또는 1A"
              value={problemId}
              onChange={(e) => setProblemId(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label>문제 제목</label>
            <input
              type="text"
              placeholder="예: A+B"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>
        </div>

        <div className="form-section">
          <h3>정답 코드</h3>

          <div className="form-group">
            <div className="code-header">
              <label>언어: </label>
              <select value={language} onChange={(e) => setLanguage(e.target.value)}>
                <option value="python">Python</option>
                <option value="javascript">JavaScript</option>
                <option value="cpp">C++</option>
                <option value="java">Java</option>
              </select>
              <span className="detected-info">(자동 감지됨)</span>
            </div>

            <textarea
              className="code-textarea"
              placeholder="정답 코드를 입력하세요..."
              value={solutionCode}
              onChange={(e) => handleCodeChange(e.target.value)}
              spellCheck="false"
            />
          </div>
        </div>

        <div className="form-section">
          <h3>입력 변수 조건</h3>

          <div className="form-group">
            <label>조건 설명</label>
            <textarea
              className="constraints-textarea"
              placeholder="예:&#10;- 첫 번째 줄에 두 정수 A, B가 주어진다 (0 ≤ A, B ≤ 10,000)&#10;- A와 B는 공백으로 구분된다&#10;- 여러 테스트 케이스가 있을 수 있다"
              value={constraints}
              onChange={(e) => setConstraints(e.target.value)}
            />
          </div>
        </div>

        <div className="action-buttons">
          <button
            onClick={handleGenerateTestCases}
            disabled={loading || registering}
            className="generate-button"
          >
            {loading ? '생성 중...' : '반례 생성 (100개)'}
          </button>

          {testCases && (
            <button
              onClick={handleRegister}
              disabled={loading || registering}
              className="register-button"
            >
              {registering ? '등록 중...' : '문제 등록'}
            </button>
          )}
        </div>

        {progress && (
          <div className="progress-message">
            {progress}
          </div>
        )}

        {testCases && (
          <div className="test-cases-preview">
            <h3>생성된 반례 미리보기 ({testCases.length}개)</h3>
            <div className="preview-list">
              {testCases.slice(0, 10).map((tc, index) => (
                <div key={index} className="preview-item">
                  <span className="preview-index">#{index + 1}</span>
                  <pre className="preview-input">{tc.input}</pre>
                </div>
              ))}
              {testCases.length > 10 && (
                <div className="preview-more">
                  ... 외 {testCases.length - 10}개
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default ProblemRegister;
