import { useState, useEffect, useRef } from 'react';
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
  const [showUserMenu, setShowUserMenu] = useState(false);
  const userMenuRef = useRef(null);

  useEffect(() => {
    // Check if user is already logged in
    if (isAuthenticated()) {
      setUser(getUser());
    }
  }, []);

  // Close user menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target)) {
        setShowUserMenu(false);
      }
    };

    if (showUserMenu) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showUserMenu]);

  const handleSelectProblem = (problem) => {
    // Check if user is authenticated when accessing problem details
    if (!isAuthenticated()) {
      alert('Please log in to view problem details');
      setShowLoginModal(true);
      return;
    }
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

  const handleRegisterClick = () => {
    // Check if user is authenticated when accessing problem registration
    if (!isAuthenticated()) {
      alert('Please log in to register new problems');
      setShowLoginModal(true);
      return;
    }
    setCurrentView('register');
  };

  const handleLoginSuccess = (userData) => {
    setUser(userData);
    setShowLoginModal(false);
  };

  const handleLogout = () => {
    logout();
    setUser(null);
    setShowUserMenu(false);
  };

  const toggleUserMenu = () => {
    setShowUserMenu(!showUserMenu);
  };

  return (
    <div className="App">
      <header>
        <div className="header-logo">
          <h1 onClick={handleBackToSearch} style={{ cursor: 'pointer' }}>TestRun</h1>
        </div>

        <nav className="header-nav">
          {currentView === 'search' && (
            <>
              <button onClick={() => setCurrentView('history')} className="nav-button">
                Search History
              </button>
              <button onClick={handleRegisterClick} className="nav-button nav-button-primary">
                + Register Problem
              </button>
            </>
          )}
        </nav>

        <div className="header-user">
          {user ? (
            <div className="user-menu-container" ref={userMenuRef}>
              <button onClick={toggleUserMenu} className="user-button">
                <img src={user.picture} alt={user.name} className="user-avatar" />
              </button>

              {showUserMenu && (
                <div className="user-dropdown">
                  <div className="user-dropdown-header">
                    <img src={user.picture} alt={user.name} className="user-dropdown-avatar" />
                    <div className="user-dropdown-info">
                      <div className="user-dropdown-name">{user.name}</div>
                      <div className="user-dropdown-email">{user.email}</div>
                    </div>
                  </div>
                  <div className="user-dropdown-divider"></div>
                  <button className="user-dropdown-item">
                    <svg className="dropdown-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                    Account Settings
                  </button>
                  <button onClick={handleLogout} className="user-dropdown-item user-dropdown-logout">
                    <svg className="dropdown-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                    </svg>
                    Logout
                  </button>
                </div>
              )}
            </div>
          ) : (
            <button onClick={() => setShowLoginModal(true)} className="login-button">
              Sign In
            </button>
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
                {selectedProblem.platform === 'baekjoon' ? 'Baekjoon' : 'Codeforces'} - {selectedProblem.problem_id}
              </p>
              <button onClick={handleBackToSearch}>
                ← Select Another Problem
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
              ← Back to Search
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
            <h2>Sign In</h2>
            <GoogleLogin onLoginSuccess={handleLoginSuccess} />
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
