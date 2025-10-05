import { useState, useEffect } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  Container,
  IconButton,
  Avatar,
  Menu,
  MenuItem,
  Divider,
  Snackbar,
  Alert,
  Paper
} from '@mui/material';
import {
  History as HistoryIcon,
  Add as AddIcon,
  Settings as SettingsIcon,
  Logout as LogoutIcon
} from '@mui/icons-material';

import ProblemSearch from './components/ProblemSearch';
import CodeEditor from './components/CodeEditor';
import TestResults from './components/TestResults';
import ProblemRegister from './components/ProblemRegister';
import SearchHistory from './components/SearchHistory';
import Problems from './components/Problems';
import ProblemDetail from './components/ProblemDetail';
import JobDetail from './components/JobDetail';
import GoogleLogin from './components/GoogleLogin';
import Footer from './components/Footer';
import About from './components/About';
import AccountDetail from './components/AccountDetail';
import { getUser, logout, isAuthenticated, refreshToken } from './utils/auth';
import { apiGet } from './utils/api-client';
import { API_ENDPOINTS } from './config/api';

function App() {
  const [currentView, setCurrentView] = useState('search');
  const [selectedProblem, setSelectedProblem] = useState(null);
  const [selectedJobId, setSelectedJobId] = useState(null);
  const [selectedProblemDetail, setSelectedProblemDetail] = useState(null);
  const [testResults, setTestResults] = useState(null);
  const [user, setUser] = useState(null);
  const [anchorEl, setAnchorEl] = useState(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });
  const [returnToView, setReturnToView] = useState(null);

  useEffect(() => {
    if (isAuthenticated()) {
      setUser(getUser());
    }

    // Check URL for routes
    const urlParams = new URLSearchParams(window.location.search);
    const path = window.location.pathname;

    if (path === '/login') {
      setCurrentView('login');
    } else if (path === '/register' && urlParams.has('draft_id')) {
      setCurrentView('register');
    } else if (path === '/register') {
      setCurrentView('register');
    } else if (path === '/problems') {
      setCurrentView('problems');
    } else if (path === '/history') {
      setCurrentView('history');
    } else if (path === '/account') {
      setCurrentView('account');
    } else if (path === '/jobs') {
      const jobId = urlParams.get('job_id');
      if (jobId) {
        setSelectedJobId(jobId);
        setCurrentView('job-detail');
      } else {
        setCurrentView('jobs');
      }
    } else if (path.startsWith('/problems/')) {
      const pathParts = path.split('/').filter(p => p);
      if (pathParts.length >= 2) {
        setSelectedProblemDetail({ platform: pathParts[1], problem_id: pathParts[2] });
        setCurrentView('problem-detail');
      }
    } else if (path.startsWith('/test/')) {
      const pathParts = path.split('/').filter(p => p);
      if (pathParts.length >= 3) {
        // Fetch problem and set for test view
        const platform = pathParts[1];
        const problemId = pathParts[2];

        // Check authentication first
        if (!isAuthenticated()) {
          setCurrentView('login');
          window.history.pushState({}, '', '/login');
          showSnackbar('Please log in to test problems', 'warning');
        } else {
          // Fetch the problem
          apiGet(`${API_ENDPOINTS.problems}${platform}/${problemId}/`).then(async (response) => {
            if (response.ok) {
              const problem = await response.json();
              setSelectedProblem(problem);
              setCurrentView('test');
            } else {
              showSnackbar('Problem not found', 'error');
              setCurrentView('search');
              window.history.pushState({}, '', '/');
            }
          }).catch(() => {
            showSnackbar('Failed to load problem', 'error');
            setCurrentView('search');
            window.history.pushState({}, '', '/');
          });
        }
      }
    }

    // Listen for force logout event
    const handleForceLogout = () => {
      setUser(null);
      setCurrentView('login');
      window.history.pushState({}, '', '/login');
      showSnackbar('Session expired. Please log in again.', 'warning');
    };

    window.addEventListener('forceLogout', handleForceLogout);

    // Periodic token refresh (every 50 minutes)
    const tokenRefreshInterval = setInterval(async () => {
      if (isAuthenticated()) {
        try {
          await refreshToken();
          console.log('Token refreshed successfully');
        } catch (error) {
          console.error('Failed to refresh token:', error);
          handleForceLogout();
        }
      }
    }, 50 * 60 * 1000); // 50 minutes

    return () => {
      window.removeEventListener('forceLogout', handleForceLogout);
      clearInterval(tokenRefreshInterval);
    };
  }, []);

  const handleSelectProblem = (problem) => {
    if (!isAuthenticated()) {
      handleRequestLogin('test');
      return;
    }
    setSelectedProblem(problem);
    setCurrentView('test');
    window.history.pushState({}, '', `/test/${problem.platform}/${problem.problem_id}`);
  };

  const handleBackToSearch = () => {
    setSelectedProblem(null);
    setTestResults(null);
    setCurrentView('search');
    window.history.pushState({}, '', '/');
  };

  const handleProblemsClick = () => {
    setCurrentView('problems');
    window.history.pushState({}, '', '/problems');
  };

  const handleRegisterClick = () => {
    if (!isAuthenticated()) {
      handleRequestLogin('register');
      return;
    }
    setCurrentView('register');
    window.history.pushState({}, '', '/register');
  };

  const handleLoginSuccess = (userData) => {
    setUser(userData);
    showSnackbar('Successfully logged in!', 'success');

    // Return to the view user was trying to access
    if (returnToView) {
      setCurrentView(returnToView);
      const viewUrlMap = {
        'history': '/history',
        'account': '/account',
        'problems': '/problems',
        'register': '/register'
      };
      window.history.pushState({}, '', viewUrlMap[returnToView] || '/');
      setReturnToView(null);
    } else {
      setCurrentView('search');
      window.history.pushState({}, '', '/');
    }
  };

  const handleRequestLogin = (targetView) => {
    setReturnToView(targetView || currentView);
    setCurrentView('login');
    window.history.pushState({}, '', '/login');
    showSnackbar('Please log in to continue', 'warning');
  };

  const handleLogout = () => {
    logout();
    setUser(null);
    setAnchorEl(null);
    setCurrentView('search');
    window.history.pushState({}, '', '/');
    showSnackbar('Successfully logged out', 'info');
  };

  const showSnackbar = (message, severity = 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  const showAds = currentView === 'test';

  return (
    <Box sx={{
      minHeight: '100vh',
      backgroundColor: 'background.default',
      display: 'flex',
      flexDirection: 'column'
    }}>
      {/* AppBar */}
      <AppBar position="static" elevation={0} sx={{
        backgroundColor: 'white',
        borderBottom: '1px solid',
        borderColor: 'divider'
      }}>
        <Toolbar>
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              cursor: 'pointer',
              flexGrow: 0,
              mr: 4
            }}
            onClick={handleBackToSearch}
          >
            <img
              src="/logo2.png"
              alt="Logo"
              style={{ height: 40, marginRight: 12 }}
            />
            <Typography variant="h6" component="div" sx={{ fontWeight: 600, color: 'text.primary' }}>
              TestCase.Run
            </Typography>
          </Box>

          <Box sx={{ display: 'flex', gap: 1, flexGrow: 1 }}>
            <Button
              startIcon={<HistoryIcon />}
              onClick={handleProblemsClick}
              sx={{
                textTransform: 'none',
                color: 'text.primary',
                '&:hover': { backgroundColor: 'action.hover' }
              }}
            >
              Problems
            </Button>
            <Button
              startIcon={<HistoryIcon />}
              onClick={() => {
                setCurrentView('history');
                window.history.pushState({}, '', '/history');
              }}
              sx={{
                textTransform: 'none',
                color: 'text.primary',
                '&:hover': { backgroundColor: 'action.hover' }
              }}
            >
              History
            </Button>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={handleRegisterClick}
              sx={{
                ml: 'auto',
                mr: 2,
                backgroundColor: 'primary.main',
                '&:hover': { backgroundColor: 'primary.dark' }
              }}
            >
              Register Problem
            </Button>
          </Box>

          <Box sx={{ ml: 'auto' }}>
            {user ? (
              <>
                <IconButton onClick={(e) => setAnchorEl(e.currentTarget)} sx={{ p: 0 }}>
                  <Avatar src={user.picture} alt={user.name} />
                </IconButton>
                <Menu
                  anchorEl={anchorEl}
                  open={Boolean(anchorEl)}
                  onClose={() => setAnchorEl(null)}
                  PaperProps={{
                    sx: {
                      mt: 1.5,
                      minWidth: 200
                    }
                  }}
                >
                  <Box sx={{ px: 2, py: 1.5 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                      {user.name}
                    </Typography>
                    <Typography variant="caption" sx={{ color: 'text.secondary' }}>
                      {user.email}
                    </Typography>
                  </Box>
                  <Divider />
                  <MenuItem onClick={() => {
                    setAnchorEl(null);
                    setCurrentView('account');
                  }}>
                    <SettingsIcon sx={{ mr: 1 }} fontSize="small" />
                    Account Statistics
                  </MenuItem>
                  <MenuItem onClick={handleLogout}>
                    <LogoutIcon sx={{ mr: 1 }} fontSize="small" />
                    Logout
                  </MenuItem>
                </Menu>
              </>
            ) : (
              <Button
                variant="outlined"
                onClick={() => {
                  setCurrentView('login');
                  window.history.pushState({}, '', '/login');
                }}
                sx={{
                  borderColor: 'primary.main',
                  color: 'primary.main',
                  '&:hover': {
                    borderColor: 'primary.dark',
                    backgroundColor: 'rgba(25, 118, 210, 0.04)'
                  }
                }}
              >
                Sign In
              </Button>
            )}
          </Box>
        </Toolbar>
      </AppBar>

      {/* Main Content */}
      <Box sx={{ flexGrow: 1, py: 4 }}>
        {showAds ? (
          <Box sx={{ display: 'flex', gap: 3, px: 3 }}>
            <Box sx={{ width: 160, flexShrink: 0 }}>
              {/* Ad slot left */}
            </Box>
            <Container maxWidth="lg" sx={{ flexGrow: 1 }}>
              {selectedProblem && (
                <>
                  <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <Box>
                      <Typography variant="h4" gutterBottom sx={{ color: 'text.primary', fontWeight: 600 }}>
                        {selectedProblem.title}
                      </Typography>
                      <Typography variant="body1" sx={{ color: 'text.secondary', mb: 2 }}>
                        {selectedProblem.platform === 'baekjoon' ? 'Baekjoon' : 'Codeforces'} - {selectedProblem.problem_id}
                      </Typography>
                    </Box>
                    {selectedProblem.problem_url && (
                      <Button
                        variant="outlined"
                        onClick={() => window.open(selectedProblem.problem_url, '_blank')}
                      >
                        Open Problem
                      </Button>
                    )}
                  </Box>
                  <CodeEditor
                    problemId={selectedProblem.id}
                    onTestResults={setTestResults}
                  />
                  {testResults && <TestResults results={testResults} />}
                </>
              )}
            </Container>
            <Box sx={{ width: 160, flexShrink: 0 }}>
              {/* Ad slot right */}
            </Box>
          </Box>
        ) : (
          <Container maxWidth="lg">
            {currentView === 'login' && (
              <Box sx={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                minHeight: '70vh',
                py: 6
              }}>
                <Paper
                  elevation={0}
                  sx={{
                    p: { xs: 4, md: 6 },
                    maxWidth: 460,
                    width: '100%',
                    textAlign: 'center',
                    borderRadius: 3,
                    border: '1px solid',
                    borderColor: 'divider',
                    backgroundColor: 'white'
                  }}
                >
                  <Box sx={{ mb: 5 }}>
                    <Typography variant="h4" sx={{ fontWeight: 700, mb: 1.5, color: 'text.primary' }}>
                      Welcome to TestCase.Run
                    </Typography>
                    <Typography variant="body1" sx={{ color: 'text.secondary', fontWeight: 400 }}>
                      Sign in to test your algorithms
                    </Typography>
                  </Box>

                  <Box sx={{ mb: 4 }}>
                    <GoogleLogin onLoginSuccess={handleLoginSuccess} />
                  </Box>

                  <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block' }}>
                    By signing in, you agree to our Terms of Service and Privacy Policy
                  </Typography>
                </Paper>
              </Box>
            )}

            {currentView === 'search' && (
              <ProblemSearch onSelectProblem={handleSelectProblem} />
            )}

            {currentView === 'register' && (
              <ProblemRegister />
            )}

            {currentView === 'history' && (
              <SearchHistory onRequestLogin={() => handleRequestLogin('history')} />
            )}

            {currentView === 'account' && (
              <AccountDetail onRequestLogin={() => handleRequestLogin('account')} />
            )}

            {currentView === 'problems' && (
              <Problems
                onViewProblem={(platform, problemId) => {
                  setSelectedProblemDetail({ platform, problem_id: problemId });
                  setCurrentView('problem-detail');
                  window.history.pushState({}, '', `/problems/${platform}/${problemId}`);
                }}
              />
            )}

            {currentView === 'problem-detail' && selectedProblemDetail && (
              <ProblemDetail
                platform={selectedProblemDetail.platform}
                problemId={selectedProblemDetail.problem_id}
              />
            )}

            {currentView === 'job-detail' && selectedJobId && (
              <JobDetail
                jobId={selectedJobId}
              />
            )}

            {currentView === 'about' && (
              <About />
            )}
          </Container>
        )}
      </Box>

      <Footer onAboutClick={() => setCurrentView('about')} />

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={handleCloseSnackbar} severity={snackbar.severity} sx={{ width: '100%' }}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}

export default App;
