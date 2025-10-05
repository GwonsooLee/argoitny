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
      <h3>Test Case Validation Results</h3>

      <div className="summary">
        <span className="passed">Passed: {summary.passed}</span>
        <span className="failed">Failed: {summary.failed}</span>
        <span className="total">Total: {summary.total}</span>
      </div>

      {failedTests.length > 0 ? (
        <>
          <h4>Failed Test Cases</h4>
          {failedTests.map((result, index) => (
            <div key={result.testCaseId} className="test-case failed">
              <div className="test-case-header">
                <strong>Test Case #{index + 1}</strong>
              </div>

              <div className="test-case-content">
                <div className="io-section">
                  <label>Input:</label>
                  <pre>{result.input}</pre>
                </div>

                <div className="io-section">
                  <label>Expected Output:</label>
                  <pre>{result.expected || result.expectedOutput}</pre>
                </div>

                <div className="io-section">
                  <label>Actual Output:</label>
                  <pre className="actual-output">
                    {result.output || result.actualOutput || '(No output)'}
                  </pre>
                </div>

                {result.error && (
                  <div className="io-section error">
                    <label>Error:</label>
                    <pre>{result.error}</pre>
                  </div>
                )}
              </div>
            </div>
          ))}
        </>
      ) : (
        <div className="all-passed">
          ✓ All test cases passed!
        </div>
      )}
    </div>
  );
}

export default TestResults;
