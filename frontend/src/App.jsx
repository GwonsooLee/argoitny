import { useState, useEffect } from 'react';
import ProblemSearch from './components/ProblemSearch';
import CodeEditor from './components/CodeEditor';
import TestResults from './components/TestResults';
import ProblemRegister from './components/ProblemRegister';
import SearchHistory from './components/SearchHistory';
import GoogleLogin from './components/GoogleLogin';
import { getUser, logout, isAuthenticated } from './utils/auth';
import './App.css';

function App() {
  const [currentView, setCurrentView] = useState('search'); // 'search' | 'test' | 'register' | 'history'
  const [selectedProblem, setSelectedProblem] = useState(null);
  const [testResults, setTestResults] = useState(null);
  const [user, setUser] = useState(null);
  const [showLoginModal, setShowLoginModal] = useState(false);

  useEffect(() => {
    // Check if user is already logged in
    if (isAuthenticated()) {
      setUser(getUser());
    }
  }, []);

  const handleSelectProblem = (problem) => {
    setSelectedProblem(problem);
    setCurrentView('test');
  };

  const handleBackToSearch = () => {
    setSelectedProblem(null);
    setTestResults(null);
    setCurrentView('search');
  };

  const handleBackFromRegister = () => {
    setCurrentView('search');
  };

  const handleBackFromHistory = () => {
    setCurrentView('search');
  };

  const handleLoginSuccess = (userData) => {
    setUser(userData);
    setShowLoginModal(false);
  };

  const handleLogout = () => {
    logout();
    setUser(null);
  };

  return (
    <div className="App">
      <header>
        <h1>AlgoItny - 반례 검증 플랫폼</h1>
        <div className="header-buttons">
          {user ? (
            <div className="user-info">
              <img src={user.picture} alt={user.name} className="user-avatar" />
              <span className="user-name">{user.name}</span>
              <button onClick={handleLogout} className="logout-button">
                로그아웃
              </button>
            </div>
          ) : (
            <button onClick={() => setShowLoginModal(true)} className="login-button">
              로그인
            </button>
          )}
          {currentView === 'search' && (
            <>
              <button onClick={() => setCurrentView('history')} className="history-nav-button">
                검색 이력
              </button>
              <button onClick={() => setCurrentView('register')} className="register-nav-button">
                + 문제 등록
              </button>
            </>
          )}
        </div>
      </header>

      <main>
        {currentView === 'search' && (
          <ProblemSearch onSelectProblem={handleSelectProblem} />
        )}

        {currentView === 'test' && selectedProblem && (
          <>
            <div className="problem-info">
              <h2>{selectedProblem.title}</h2>
              <p>
                {selectedProblem.platform === 'baekjoon' ? '백준' : 'Codeforces'} - {selectedProblem.problem_id}
              </p>
              <button onClick={handleBackToSearch}>
                ← 다른 문제 선택
              </button>
            </div>

            <CodeEditor
              problemId={selectedProblem.id}
              onTestResults={setTestResults}
            />

            {testResults && <TestResults results={testResults} />}
          </>
        )}

        {currentView === 'register' && (
          <ProblemRegister onBack={handleBackFromRegister} />
        )}

        {currentView === 'history' && (
          <div>
            <button onClick={handleBackFromHistory} className="back-to-search-btn">
              ← 검색 페이지로
            </button>
            <SearchHistory />
          </div>
        )}
      </main>

      {showLoginModal && (
        <div className="modal-overlay" onClick={() => setShowLoginModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setShowLoginModal(false)}>
              ×
            </button>
            <h2>로그인</h2>
            <GoogleLogin onLoginSuccess={handleLoginSuccess} />
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
