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
  Logout as LogoutIcon,
  AdminPanelSettings as AdminIcon,
  Upgrade as UpgradeIcon
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
import TermsOfService from './components/TermsOfService';
import PrivacyPolicy from './components/PrivacyPolicy';
import AdminUserManagement from './components/AdminUserManagement';
import AdminPlanManagement from './components/AdminPlanManagement';
import ConsentModal from './components/ConsentModal';
import UpgradePlanModal from './components/UpgradePlanModal';
import { getUser, saveUser, logout, isAuthenticated, refreshToken } from './utils/auth';
import { apiGet, apiPost } from './utils/api-client';
import { API_ENDPOINTS } from './config/api';

function App() {
  const [currentView, setCurrentView] = useState('search');
  const [selectedProblem, setSelectedProblem] = useState(null);
  const [selectedJobId, setSelectedJobId] = useState(null);
  const [selectedProblemDetail, setSelectedProblemDetail] = useState(null);
  const [testResults, setTestResults] = useState(null);
  const [hintsLoading, setHintsLoading] = useState(false);
  const [user, setUser] = useState(null);
  const [userLoading, setUserLoading] = useState(true);
  const [anchorEl, setAnchorEl] = useState(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });
  const [returnToView, setReturnToView] = useState(null);
  const [showConsentModal, setShowConsentModal] = useState(false);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [planUsage, setPlanUsage] = useState(null);

  const fetchPlanUsage = async () => {
    try {
      const response = await apiGet(API_ENDPOINTS.planUsage, { requireAuth: true });
      if (response.ok) {
        const data = await response.json();
        setPlanUsage(data);
      }
    } catch (error) {
      console.error('Failed to fetch plan usage:', error);
    }
  };

  // Refresh plan usage when test results are updated (after code execution)
  useEffect(() => {
    if (testResults && user) {
      fetchPlanUsage();
    }
  }, [testResults]);

  useEffect(() => {
    if (isAuthenticated()) {
      const currentUser = getUser();
      // Set user immediately from localStorage to avoid flash of logged-out state
      setUser(currentUser);
      setUserLoading(true);

      // Fetch latest user profile from server to get updated plan name
      apiGet('/account/me/', { requireAuth: true })
        .then(res => {
          if (!res.ok) {
            // If 401/403, token is invalid - don't use cached data
            if (res.status === 401 || res.status === 403) {
              throw new Error('Authentication failed');
            }
            throw new Error(`HTTP ${res.status}`);
          }
          return res.json();
        })
        .then(async data => {
          // Update user with latest data from server
          setUser(data);
          saveUser(data);
          setUserLoading(false);

          // Check consent status (all users should have Free plan auto-assigned now)
          try {
            const consentsRes = await apiGet(API_ENDPOINTS.getConsents, { requireAuth: true });
            if (consentsRes.ok) {
              const consentsData = await consentsRes.json();
              if (!consentsData.all_consents_given) {
                setShowConsentModal(true);
              }
            }
          } catch (err) {
            console.error('Failed to check consent status:', err);
          }
        })
        .catch(err => {
          console.error('Failed to fetch user profile:', err);

          // If authentication failed, wait for token refresh to complete
          // api-client will automatically retry, so we keep user state
          if (err.message === 'Session expired. Please login again.') {
            // Token refresh failed - user will be logged out by forceLogout event
            setUserLoading(false);
            return;
          }

          // For other errors, keep using cached user data
          setUserLoading(false);

          // Check consent status even with cached user data
          if (currentUser) {
            apiGet(API_ENDPOINTS.getConsents, { requireAuth: true })
              .then(res => res.json())
              .then(consentsData => {
                if (!consentsData.all_consents_given) {
                  setShowConsentModal(true);
                }
              })
              .catch(err => {
                console.error('Failed to check consent status:', err);
              });
          }
        });

      // Fetch plan usage
      fetchPlanUsage();
    } else {
      setUserLoading(false);
    }

    // Check URL for routes
    const urlParams = new URLSearchParams(window.location.search);
    const path = window.location.pathname;

    if (path === '/login') {
      // If user is already logged in, redirect to home
      if (isAuthenticated()) {
        setCurrentView('search');
        window.history.pushState({}, '', '/');
      } else {
        setCurrentView('login');
      }
    } else if (path === '/register' && urlParams.has('draft_id')) {
      setCurrentView('register');
    } else if (path === '/register') {
      setCurrentView('register');
    } else if (path === '/problems') {
      setCurrentView('problems');
    } else if (path === '/history') {
      setCurrentView('history');
    } else if (path === '/admin/users') {
      setCurrentView('admin-users');
    } else if (path === '/admin/plans') {
      setCurrentView('admin-plans');
    } else if (path === '/terms') {
      setCurrentView('terms');
    } else if (path === '/privacy') {
      setCurrentView('privacy');
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
          apiGet(`${API_ENDPOINTS.problems}${platform}/${problemId}/`, { requireAuth: true }).then(async (response) => {
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

    // Fetch plan usage in background (non-blocking) after a delay
    setTimeout(() => {
      fetchPlanUsage().catch(err => {
        console.error('Failed to fetch plan usage on login:', err);
        // Don't block login flow if plan usage fetch fails
      });
    }, 500); // Wait 500ms to ensure tokens are ready

    // Note: Consent check is already handled in GoogleLogin component
    // Return to the view user was trying to access
    if (returnToView) {
      setCurrentView(returnToView);
      const viewUrlMap = {
        'history': '/history',
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

  const handleConsentsComplete = async (consents) => {
    try {
      // Submit consents to backend
      const res = await apiPost(API_ENDPOINTS.submitConsents, consents, { requireAuth: true });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || 'Failed to save consents');
      }

      // Hide consent modal
      setShowConsentModal(false);
      showSnackbar('Consents saved successfully', 'success');
    } catch (err) {
      console.error('Consent submission error:', err);
      throw err; // Re-throw to let ConsentModal handle the error
    }
  };

  const handleConsentsCancel = () => {
    // User declined consents - logout
    logout();
    setUser(null);
    setShowConsentModal(false);
    setCurrentView('login');
    window.history.pushState({}, '', '/login');
    showSnackbar('You must accept all terms to use the service', 'warning');
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
        <Toolbar sx={{
          flexWrap: { xs: 'wrap', md: 'nowrap' },
          gap: { xs: 1, sm: 2 },
          py: { xs: 1, sm: 1.5 }
        }}>
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              cursor: 'pointer',
              flexShrink: 0,
              mr: { xs: 1, sm: 2, md: 4 }
            }}
            onClick={handleBackToSearch}
          >
            <img
              src="/logo2.png"
              alt="Logo"
              style={{ height: 32, marginRight: 8 }}
            />
            <Typography
              variant="h6"
              component="div"
              sx={{
                fontWeight: 600,
                color: 'text.primary',
                fontSize: { xs: '1rem', sm: '1.25rem' },
                display: { xs: 'none', sm: 'block' }
              }}
            >
              TestCase.Run
            </Typography>
          </Box>

          <Box sx={{
            display: 'flex',
            gap: { xs: 0.5, sm: 1 },
            flexGrow: 1,
            flexWrap: 'wrap',
            alignItems: 'center'
          }}>
            {user?.is_admin && (
              <Button
                startIcon={<HistoryIcon sx={{ display: { xs: 'none', sm: 'block' } }} />}
                onClick={handleProblemsClick}
                sx={{
                  textTransform: 'none',
                  color: 'text.primary',
                  fontSize: { xs: '0.813rem', sm: '0.875rem' },
                  px: { xs: 1, sm: 2 },
                  minWidth: { xs: 'auto', sm: 'auto' },
                  '&:hover': { backgroundColor: 'action.hover' }
                }}
              >
                Problems
              </Button>
            )}
            <Button
              startIcon={<HistoryIcon sx={{ display: { xs: 'none', sm: 'block' } }} />}
              onClick={() => {
                setCurrentView('history');
                window.history.pushState({}, '', '/history');
              }}
              sx={{
                textTransform: 'none',
                color: 'text.primary',
                fontSize: { xs: '0.813rem', sm: '0.875rem' },
                px: { xs: 1, sm: 2 },
                minWidth: { xs: 'auto', sm: 'auto' },
                '&:hover': { backgroundColor: 'action.hover' }
              }}
            >
              History
            </Button>
            {user?.is_admin && (
              <Button
                startIcon={<AddIcon sx={{ display: { xs: 'none', sm: 'block' } }} />}
                onClick={handleRegisterClick}
                sx={{
                  textTransform: 'none',
                  color: 'text.primary',
                  fontSize: { xs: '0.813rem', sm: '0.875rem' },
                  px: { xs: 1, sm: 2 },
                  minWidth: { xs: 'auto', sm: 'auto' },
                  '&:hover': { backgroundColor: 'action.hover' }
                }}
              >
                <Box component="span" sx={{ display: { xs: 'none', sm: 'inline' } }}>
                  Register Problem
                </Box>
                <Box component="span" sx={{ display: { xs: 'inline', sm: 'none' } }}>
                  Register
                </Box>
              </Button>
            )}
          </Box>

          <Box sx={{ ml: { xs: 'auto', sm: 0 } }}>
            {user ? (
              <>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  {user.subscription_plan_name && (
                    <Box
                      sx={{
                        px: 1.5,
                        py: 0.5,
                        borderRadius: 1,
                        bgcolor: user.subscription_plan_name === 'Admin' ? '#9c27b0' :
                                user.subscription_plan_name === 'Pro+' ? '#ff9800' :
                                user.subscription_plan_name === 'Pro' ? '#2196f3' :
                                '#4caf50',
                        display: { xs: 'none', sm: 'block' }
                      }}
                    >
                      <Typography
                        variant="caption"
                        sx={{
                          color: 'white',
                          fontWeight: 600,
                          fontSize: '0.75rem'
                        }}
                      >
                        {user.subscription_plan_name}
                      </Typography>
                    </Box>
                  )}
                  {planUsage && (
                    <Box
                      sx={{
                        display: { xs: 'none', md: 'flex' },
                        gap: 1.5,
                        px: 1.5,
                        py: 0.5,
                        borderRadius: 1,
                        bgcolor: 'rgba(0, 0, 0, 0.04)',
                      }}
                    >
                      <Typography
                        variant="caption"
                        sx={{
                          color: 'text.secondary',
                          fontSize: '0.75rem'
                        }}
                      >
                        Problems: {planUsage.usage.total_problems}
                        {planUsage.limits.max_problems !== -1 && `/${planUsage.limits.max_problems}`}
                      </Typography>
                      <Typography
                        variant="caption"
                        sx={{
                          color: 'text.secondary',
                          fontSize: '0.75rem'
                        }}
                      >
                        Hints: {planUsage.usage.hints_today}
                        {planUsage.limits.max_hints_per_day !== -1 && `/${planUsage.limits.max_hints_per_day}`}
                      </Typography>
                      <Typography
                        variant="caption"
                        sx={{
                          color: 'text.secondary',
                          fontSize: '0.75rem'
                        }}
                      >
                        Executions: {planUsage.usage.executions_today}
                        {planUsage.limits.max_executions_per_day !== -1 && `/${planUsage.limits.max_executions_per_day}`}
                      </Typography>
                    </Box>
                  )}
                  <IconButton onClick={(e) => setAnchorEl(e.currentTarget)} sx={{ p: 0.5 }}>
                    <Avatar
                      src={user.picture}
                      alt={user.name}
                      sx={{
                        width: { xs: 32, sm: 40 },
                        height: { xs: 32, sm: 40 }
                      }}
                    />
                  </IconButton>
                </Box>
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
                    <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block' }}>
                      {user.email}
                    </Typography>
                    {user.subscription_plan_name && (
                      <Box
                        sx={{
                          display: 'inline-block',
                          mt: 0.5,
                          px: 1,
                          py: 0.25,
                          borderRadius: 0.5,
                          bgcolor: user.subscription_plan_name === 'Admin' ? '#9c27b0' :
                                  user.subscription_plan_name === 'Pro+' ? '#ff9800' :
                                  user.subscription_plan_name === 'Pro' ? '#2196f3' :
                                  '#4caf50',
                        }}
                      >
                        <Typography
                          variant="caption"
                          sx={{
                            color: 'white',
                            fontWeight: 600,
                            fontSize: '0.7rem'
                          }}
                        >
                          {user.subscription_plan_name} Plan
                        </Typography>
                      </Box>
                    )}
                  </Box>
                  {user.is_admin && [
                    <Divider key="admin-divider-1" />,
                    <MenuItem key="admin-users" onClick={() => {
                      setAnchorEl(null);
                      setCurrentView('admin-users');
                      window.history.pushState({}, '', '/admin/users');
                    }}>
                      <AdminIcon sx={{ mr: 1 }} fontSize="small" />
                      User Management
                    </MenuItem>,
                    <MenuItem key="admin-plans" onClick={() => {
                      setAnchorEl(null);
                      setCurrentView('admin-plans');
                      window.history.pushState({}, '', '/admin/plans');
                    }}>
                      <AdminIcon sx={{ mr: 1 }} fontSize="small" />
                      Plan Management
                    </MenuItem>
                  ]}
                  {!user.is_admin && (
                    <>
                      <Divider />
                      <MenuItem
                        onClick={() => {
                          setAnchorEl(null);
                          setShowUpgradeModal(true);
                        }}
                        sx={{
                          bgcolor: 'primary.main',
                          color: 'white',
                          fontWeight: 600,
                          '&:hover': {
                            bgcolor: 'primary.dark',
                          }
                        }}
                      >
                        <UpgradeIcon sx={{ mr: 1 }} fontSize="small" />
                        Upgrade Plan
                      </MenuItem>
                    </>
                  )}
                  <Divider />
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
                  fontSize: { xs: '0.813rem', sm: '0.875rem' },
                  px: { xs: 1.5, sm: 2 },
                  py: { xs: 0.5, sm: 0.75 },
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
      <Box sx={{ flexGrow: 1, py: { xs: 2, sm: 3, md: 4 } }}>
        {showAds ? (
          <Box sx={{ display: 'flex', gap: { xs: 0, md: 3 }, px: { xs: 2, sm: 3 } }}>
            <Box sx={{ width: 160, flexShrink: 0, display: { xs: 'none', lg: 'block' } }}>
              {/* Ad slot left */}
            </Box>
            <Container maxWidth="lg" sx={{ flexGrow: 1, px: { xs: 0, sm: 2 } }}>
              {selectedProblem && (
                <>
                  <Box sx={{
                    mb: 3,
                    display: 'flex',
                    flexDirection: { xs: 'column', sm: 'row' },
                    justifyContent: 'space-between',
                    alignItems: { xs: 'flex-start', sm: 'center' },
                    gap: 2
                  }}>
                    <Box>
                      <Typography
                        variant="h4"
                        gutterBottom
                        sx={{
                          color: 'text.primary',
                          fontWeight: 600,
                          fontSize: { xs: '1.5rem', sm: '2rem', md: '2.125rem' }
                        }}
                      >
                        {selectedProblem.title}
                      </Typography>
                      <Typography variant="body1" sx={{ color: 'text.secondary', mb: 2, fontSize: { xs: '0.875rem', sm: '1rem' } }}>
                        {selectedProblem.platform === 'baekjoon' ? 'Baekjoon' : 'Codeforces'} - {selectedProblem.problem_id}
                      </Typography>
                    </Box>
                    {selectedProblem.problem_url && (
                      <Button
                        variant="outlined"
                        onClick={() => window.open(selectedProblem.problem_url, '_blank')}
                        sx={{
                          fontSize: { xs: '0.813rem', sm: '0.875rem' },
                          px: { xs: 2, sm: 3 },
                          flexShrink: 0
                        }}
                      >
                        Open Problem
                      </Button>
                    )}
                  </Box>
                  <CodeEditor
                    platform={selectedProblem.platform}
                    problemId={selectedProblem.problem_id}
                    onTestResults={setTestResults}
                    hintsLoading={hintsLoading}
                  />
                  {testResults && <TestResults results={testResults} executionId={testResults.execution_id} onHintsLoadingChange={setHintsLoading} />}
                </>
              )}
            </Container>
            <Box sx={{ width: 160, flexShrink: 0, display: { xs: 'none', lg: 'block' } }}>
              {/* Ad slot right */}
            </Box>
          </Box>
        ) : (
          <Container maxWidth="lg" sx={{ px: { xs: 2, sm: 3 } }}>
            {currentView === 'login' && (
              <Box sx={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                minHeight: '70vh',
                py: { xs: 3, sm: 6 }
              }}>
                <Paper
                  elevation={0}
                  sx={{
                    p: { xs: 3, sm: 4, md: 6 },
                    maxWidth: 460,
                    width: '100%',
                    textAlign: 'center',
                    borderRadius: 3,
                    border: '1px solid',
                    borderColor: 'divider',
                    backgroundColor: 'white'
                  }}
                >
                  <Box sx={{ mb: { xs: 3, sm: 5 } }}>
                    <Typography
                      variant="h4"
                      sx={{
                        fontWeight: 700,
                        mb: 1.5,
                        color: 'text.primary',
                        fontSize: { xs: '1.5rem', sm: '2rem', md: '2.125rem' }
                      }}
                    >
                      Welcome to TestCase.Run
                    </Typography>
                    <Typography variant="body1" sx={{ color: 'text.secondary', fontWeight: 400, fontSize: { xs: '0.875rem', sm: '1rem' } }}>
                      Sign in to test your algorithms
                    </Typography>
                  </Box>

                  <Box sx={{ mb: { xs: 3, sm: 4 } }}>
                    <GoogleLogin onLoginSuccess={handleLoginSuccess} />
                  </Box>

                  <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', fontSize: { xs: '0.75rem', sm: '0.813rem' } }}>
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
                onBack={() => {
                  setCurrentView('search');
                  setSelectedProblemDetail(null);
                  window.history.pushState({}, '', '/');
                }}
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

            {currentView === 'admin-users' && (
              <AdminUserManagement />
            )}

            {currentView === 'admin-plans' && (
              <AdminPlanManagement />
            )}

            {currentView === 'terms' && (
              <TermsOfService onBack={() => {
                setCurrentView('search');
                window.history.pushState({}, '', '/');
              }} />
            )}

            {currentView === 'privacy' && (
              <PrivacyPolicy onBack={() => {
                setCurrentView('search');
                window.history.pushState({}, '', '/');
              }} />
            )}
          </Container>
        )}
      </Box>

      <Footer
        onAboutClick={() => {
          setCurrentView('about');
          window.history.pushState({}, '', '/about');
        }}
        onTermsClick={() => {
          setCurrentView('terms');
          window.history.pushState({}, '', '/terms');
        }}
        onPrivacyClick={() => {
          setCurrentView('privacy');
          window.history.pushState({}, '', '/privacy');
        }}
      />

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


      {/* Consent Modal - required for all users */}
      {showConsentModal && user && (
        <ConsentModal
          open={showConsentModal}
          onComplete={handleConsentsComplete}
          onCancel={handleConsentsCancel}
        />
      )}

      {/* Upgrade Plan Modal */}
      {showUpgradeModal && user && (
        <UpgradePlanModal
          open={showUpgradeModal}
          user={user}
          onComplete={(updatedUser) => {
            setUser(updatedUser);
            setShowUpgradeModal(false);
            showSnackbar('Plan updated successfully', 'success');
            // Fetch updated plan usage
            fetchPlanUsage();
          }}
          onCancel={() => setShowUpgradeModal(false)}
        />
      )}
    </Box>
  );
}

export default App;
