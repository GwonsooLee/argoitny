import { useState, useEffect } from 'react';
import { apiGet } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';
import CodeModal from './CodeModal';
import './SearchHistory.css';

const ITEMS_PER_PAGE = 20;

function SearchHistory() {
  const [history, setHistory] = useState([]);
  const [offset, setOffset] = useState(0);
  const [totalItems, setTotalItems] = useState(0);
  const [loading, setLoading] = useState(false);
  const [selectedCode, setSelectedCode] = useState(null);
  const [hasMore, setHasMore] = useState(true);

  useEffect(() => {
    fetchHistory(0);
  }, []);

  const fetchHistory = async (currentOffset) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        offset: currentOffset,
        limit: ITEMS_PER_PAGE,
      });

      const response = await apiGet(`${API_ENDPOINTS.history}?${params.toString()}`);

      if (!response.ok) {
        throw new Error('Failed to fetch history');
      }

      const data = await response.json();
      setHistory(data.results);
      setTotalItems(data.count);
      setHasMore(data.has_more);
      setOffset(currentOffset);
    } catch (error) {
      console.error('Error fetching history:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePrevPage = () => {
    if (offset >= ITEMS_PER_PAGE) {
      fetchHistory(offset - ITEMS_PER_PAGE);
    }
  };

  const handleNextPage = () => {
    if (hasMore) {
      fetchHistory(offset + ITEMS_PER_PAGE);
    }
  };

  const handleCodeClick = (item) => {
    if (item.is_code_public) {
      setSelectedCode({
        code: item.code,
        language: item.language,
        problemTitle: item.problem_title,
        platform: item.platform,
        problemNumber: item.problem_number
      });
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleString('ko-KR', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getResultStatus = (item) => {
    if (item.passed_count === item.total_count) {
      return 'success';
    } else if (item.passed_count === 0) {
      return 'fail';
    } else {
      return 'partial';
    }
  };

  return (
    <div className="search-history">
      <h2>Recent Test Case Validation History</h2>

      {loading && history.length === 0 ? (
        <div className="loading">Loading...</div>
      ) : (
        <>
          <div className="history-table-container">
            <table className="history-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Platform</th>
                  <th>Problem #</th>
                  <th>Problem Title</th>
                  <th>Language</th>
                  <th>User</th>
                  <th>Result</th>
                  <th>Code</th>
                </tr>
              </thead>
              <tbody>
                {history.length === 0 ? (
                  <tr>
                    <td colSpan="8" className="no-data">
                      No search history available
                    </td>
                  </tr>
                ) : (
                  history.map((item) => (
                    <tr key={item.id}>
                      <td className="date-cell">{formatDate(item.created_at)}</td>
                      <td className="platform-cell">
                        <span className={`platform-badge ${item.platform}`}>
                          {item.platform === 'baekjoon' ? 'Baekjoon' : 'Codeforces'}
                        </span>
                      </td>
                      <td className="problem-number-cell">{item.problem_number}</td>
                      <td className="problem-title-cell">{item.problem_title}</td>
                      <td className="language-cell">
                        <span className="language-badge">{item.language}</span>
                      </td>
                      <td className="user-cell">{item.user_identifier || item.user_email || 'Anonymous'}</td>
                      <td className={`result-cell ${getResultStatus(item)}`}>
                        <div className="result-info">
                          <span className="passed">{item.passed_count}</span>
                          <span className="separator">/</span>
                          <span className="total">{item.total_count}</span>
                        </div>
                      </td>
                      <td className="code-cell">
                        {item.is_code_public ? (
                          <button
                            className="view-code-btn"
                            onClick={() => handleCodeClick(item)}
                          >
                            View
                          </button>
                        ) : (
                          <span className="private-code">Private</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {history.length > 0 && (
            <div className="pagination">
              <button
                onClick={handlePrevPage}
                disabled={offset === 0 || loading}
                className="pagination-btn"
              >
                ← Previous
              </button>

              <div className="page-info">
                <span className="current-range">
                  {offset + 1} - {Math.min(offset + ITEMS_PER_PAGE, totalItems)}
                </span>
                <span className="page-separator">/</span>
                <span className="total-items">{totalItems}</span>
              </div>

              <button
                onClick={handleNextPage}
                disabled={!hasMore || loading}
                className="pagination-btn"
              >
                Next →
              </button>
            </div>
          )}
        </>
      )}

      {selectedCode && (
        <CodeModal
          code={selectedCode}
          onClose={() => setSelectedCode(null)}
        />
      )}
    </div>
  );
}

export default SearchHistory;
