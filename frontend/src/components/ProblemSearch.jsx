import { useState } from 'react';
import { apiGet } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';
import './ProblemSearch.css';

function ProblemSearch({ onSelectProblem }) {
  const [platform, setPlatform] = useState('baekjoon');
  const [query, setQuery] = useState('');
  const [problems, setProblems] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) {
      alert('검색어를 입력하세요');
      return;
    }

    setLoading(true);
    try {
      const params = new URLSearchParams({
        platform,
        search: query,
      });

      const response = await apiGet(`${API_ENDPOINTS.problems}?${params.toString()}`);

      if (!response.ok) {
        throw new Error('Failed to search problems');
      }

      const data = await response.json();
      setProblems(data);
    } catch (error) {
      console.error('Error searching problems:', error);
      alert('문제 검색 중 오류가 발생했습니다');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <div className="problem-search">
      <h2>문제 검색</h2>

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

      <div className="search-box">
        <input
          type="text"
          placeholder="문제 번호 또는 제목으로 검색"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyPress={handleKeyPress}
        />
        <button onClick={handleSearch} disabled={loading}>
          {loading ? '검색 중...' : '검색'}
        </button>
      </div>

      {problems.length > 0 && (
        <div className="problem-list">
          <h3>검색 결과</h3>
          {problems.map((problem) => (
            <div
              key={problem.id}
              className="problem-item"
              onClick={() => onSelectProblem(problem)}
            >
              <div className="problem-id">{problem.problem_id}</div>
              <div className="problem-title">{problem.title}</div>
            </div>
          ))}
        </div>
      )}

      {!loading && problems.length === 0 && query && (
        <p className="no-results">검색 결과가 없습니다</p>
      )}
    </div>
  );
}

export default ProblemSearch;
