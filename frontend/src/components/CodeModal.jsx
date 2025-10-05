import './CodeModal.css';

function CodeModal({ code, onClose }) {
  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div className="modal-backdrop" onClick={handleBackdropClick}>
      <div className="modal-content">
        <div className="modal-header">
          <h3>View Code</h3>
          <button className="modal-close" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="modal-body">
          <div className="code-info">
            <span className="info-label">Problem:</span>
            <span className="info-value">
              {code.platform === 'baekjoon' ? 'Baekjoon' : 'Codeforces'} - {code.problemNumber} ({code.problemTitle})
            </span>
          </div>

          <div className="code-info">
            <span className="info-label">Language:</span>
            <span className="info-value">{code.language}</span>
          </div>

          <div className="code-container">
            <pre className="code-display">
              <code>{code.code}</code>
            </pre>
          </div>
        </div>

        <div className="modal-footer">
          <button className="modal-close-btn" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export default CodeModal;
