import './TestResults.css';

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
    <div className="test-results">
      <h3>반례 검증 결과</h3>

      <div className="summary">
        <span className="passed">통과: {summary.passed}</span>
        <span className="failed">실패: {summary.failed}</span>
        <span className="total">전체: {summary.total}</span>
      </div>

      {failedTests.length > 0 ? (
        <>
          <h4>틀린 반례</h4>
          {failedTests.map((result, index) => (
            <div key={result.testCaseId} className="test-case failed">
              <div className="test-case-header">
                <strong>반례 #{index + 1}</strong>
              </div>

              <div className="test-case-content">
                <div className="io-section">
                  <label>입력:</label>
                  <pre>{result.input}</pre>
                </div>

                <div className="io-section">
                  <label>예상 출력:</label>
                  <pre>{result.expected || result.expectedOutput}</pre>
                </div>

                <div className="io-section">
                  <label>실제 출력:</label>
                  <pre className="actual-output">
                    {result.output || result.actualOutput || '(출력 없음)'}
                  </pre>
                </div>

                {result.error && (
                  <div className="io-section error">
                    <label>에러:</label>
                    <pre>{result.error}</pre>
                  </div>
                )}
              </div>
            </div>
          ))}
        </>
      ) : (
        <div className="all-passed">
          ✓ 모든 반례를 통과했습니다!
        </div>
      )}
    </div>
  );
}

export default TestResults;
