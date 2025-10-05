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
  Dialog,
  DialogContent,
  DialogTitle,
  Snackbar,
  Alert
} from '@mui/material';
import {
  History as HistoryIcon,
  Add as AddIcon,
  Settings as SettingsIcon,
  Logout as LogoutIcon,
  Close as CloseIcon
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
import { getUser, logout, isAuthenticated } from './utils/auth';

function App() {
  const [currentView, setCurrentView] = useState('search');
  const [selectedProblem, setSelectedProblem] = useState(null);
  const [selectedJobId, setSelectedJobId] = useState(null);
  const [selectedProblemDetail, setSelectedProblemDetail] = useState(null);
  const [testResults, setTestResults] = useState(null);
  const [user, setUser] = useState(null);
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [anchorEl, setAnchorEl] = useState(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });

  useEffect(() => {
    if (isAuthenticated()) {
      setUser(getUser());
    }

    // Check URL for routes
    const urlParams = new URLSearchParams(window.location.search);
    const path = window.location.pathname;

    if (path === '/register' && urlParams.has('draft_id')) {
      setCurrentView('register');
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
      if (pathParts.length === 3) {
        setSelectedProblemDetail({ platform: pathParts[1], problem_id: pathParts[2] });
        setCurrentView('problem-detail');
      }
    }
  }, []);

  const handleSelectProblem = (problem) => {
    if (!isAuthenticated()) {
      showSnackbar('Please log in to view problem details', 'warning');
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
    window.history.pushState({}, '', '/');
  };

  const handleProblemsClick = () => {
    setCurrentView('problems');
    window.history.pushState({}, '', '/problems');
  };

  const handleRegisterClick = () => {
    if (!isAuthenticated()) {
      showSnackbar('Please log in to register new problems', 'warning');
      setShowLoginModal(true);
      return;
    }
    setCurrentView('register');
    window.history.pushState({}, '', '/register');
  };

  const handleLoginSuccess = (userData) => {
    setUser(userData);
    setShowLoginModal(false);
    showSnackbar('Successfully logged in!', 'success');
  };

  const handleLogout = () => {
    logout();
    setUser(null);
    setAnchorEl(null);
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
      <AppBar position="static" elevation={1} sx={{ backgroundColor: 'primary.main' }}>
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
            <Typography variant="h6" component="div" sx={{ fontWeight: 600 }}>
              TestCase.Run
            </Typography>
          </Box>

          <Box sx={{ display: 'flex', gap: 1, flexGrow: 1 }}>
            <Button
              color="inherit"
              startIcon={<HistoryIcon />}
              onClick={handleProblemsClick}
              sx={{ textTransform: 'none' }}
            >
              Problems
            </Button>
            <Button
              color="inherit"
              startIcon={<HistoryIcon />}
              onClick={() => setCurrentView('history')}
              sx={{ textTransform: 'none' }}
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
                  <MenuItem onClick={() => setAnchorEl(null)}>
                    <SettingsIcon sx={{ mr: 1 }} fontSize="small" />
                    Account Settings
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
                color="inherit"
                onClick={() => setShowLoginModal(true)}
                sx={{ borderColor: 'rgba(255, 255, 255, 0.5)' }}
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
                  <Box sx={{ mb: 3 }}>
                    <Typography variant="h4" gutterBottom sx={{ color: 'text.primary', fontWeight: 600 }}>
                      {selectedProblem.title}
                    </Typography>
                    <Typography variant="body1" sx={{ color: 'text.secondary', mb: 2 }}>
                      {selectedProblem.platform === 'baekjoon' ? 'Baekjoon' : 'Codeforces'} - {selectedProblem.problem_id}
                    </Typography>
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
            {currentView === 'search' && (
              <ProblemSearch onSelectProblem={handleSelectProblem} />
            )}

            {currentView === 'register' && (
              <ProblemRegister />
            )}

            {currentView === 'history' && (
              <SearchHistory />
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

      {/* Login Modal */}
      <Dialog
        open={showLoginModal}
        onClose={() => setShowLoginModal(false)}
        PaperProps={{
          sx: {
            minWidth: 400
          }
        }}
      >
        <DialogTitle>
          Sign In
          <IconButton
            onClick={() => setShowLoginModal(false)}
            sx={{ position: 'absolute', right: 8, top: 8 }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          <GoogleLogin onLoginSuccess={handleLoginSuccess} />
        </DialogContent>
      </Dialog>

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
