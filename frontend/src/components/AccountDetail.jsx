import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  CircularProgress,
  Chip,
  Divider
} from '@mui/material';
import {
  Code as CodeIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  Assignment as AssignmentIcon
} from '@mui/icons-material';
import { apiGet } from '../utils/api-client';
import { getUser } from '../utils/auth';

function AccountDetail({ onRequestLogin }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);

  useEffect(() => {
    const currentUser = getUser();
    if (!currentUser) {
      if (onRequestLogin) {
        onRequestLogin();
      }
      return;
    }
    setUser(currentUser);
    fetchStats();
  }, []);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const response = await apiGet('/account/stats/', { requireAuth: true });
      if (!response.ok) {
        throw new Error('Failed to fetch statistics');
      }
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!stats) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography variant="h6" color="text.secondary">
          Failed to load statistics
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ maxWidth: 1000, mx: 'auto', p: { xs: 2, md: 4 } }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ fontWeight: 700, mb: 1, color: 'text.primary' }}>
          Account Statistics
        </Typography>
        <Typography variant="body1" sx={{ color: 'text.secondary' }}>
          {user?.name || user?.email}
        </Typography>
      </Box>

      {/* Statistics Card */}
      <Paper elevation={0} sx={{ p: 4, border: '1px solid', borderColor: 'divider', borderRadius: 2, mb: 3 }}>
        <Grid container spacing={4}>
          {/* Total Executions */}
          <Grid item xs={6} sm={3}>
            <Box>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5 }}>
                <Box sx={{
                  p: 1,
                  borderRadius: 1.5,
                  backgroundColor: 'rgba(25, 118, 210, 0.1)',
                  color: 'primary.main',
                  display: 'flex',
                  mr: 1.5
                }}>
                  <CodeIcon fontSize="small" />
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Executions
                </Typography>
              </Box>
              <Typography variant="h4" sx={{ fontWeight: 700, color: 'text.primary' }}>
                {stats.total_executions}
              </Typography>
            </Box>
          </Grid>

          {/* Total Problems */}
          <Grid item xs={6} sm={3}>
            <Box>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5 }}>
                <Box sx={{
                  p: 1,
                  borderRadius: 1.5,
                  backgroundColor: 'rgba(25, 118, 210, 0.1)',
                  color: 'primary.main',
                  display: 'flex',
                  mr: 1.5
                }}>
                  <AssignmentIcon fontSize="small" />
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Problems
                </Typography>
              </Box>
              <Typography variant="h4" sx={{ fontWeight: 700, color: 'text.primary' }}>
                {stats.total_problems}
              </Typography>
            </Box>
          </Grid>

          {/* Passed */}
          <Grid item xs={6} sm={3}>
            <Box>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5 }}>
                <Box sx={{
                  p: 1,
                  borderRadius: 1.5,
                  backgroundColor: 'rgba(76, 175, 80, 0.1)',
                  color: '#4caf50',
                  display: 'flex',
                  mr: 1.5
                }}>
                  <CheckCircleIcon fontSize="small" />
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Passed
                </Typography>
              </Box>
              <Typography variant="h4" sx={{ fontWeight: 700, color: '#4caf50' }}>
                {stats.passed_executions}
              </Typography>
            </Box>
          </Grid>

          {/* Failed */}
          <Grid item xs={6} sm={3}>
            <Box>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5 }}>
                <Box sx={{
                  p: 1,
                  borderRadius: 1.5,
                  backgroundColor: 'rgba(244, 67, 54, 0.1)',
                  color: '#f44336',
                  display: 'flex',
                  mr: 1.5
                }}>
                  <CancelIcon fontSize="small" />
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Failed
                </Typography>
              </Box>
              <Typography variant="h4" sx={{ fontWeight: 700, color: '#f44336' }}>
                {stats.failed_executions}
              </Typography>
            </Box>
          </Grid>
        </Grid>

        <Divider sx={{ my: 3 }} />

        {/* Platform and Language Statistics */}
        <Grid container spacing={4}>
          <Grid item xs={12} sm={6}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2, color: 'text.primary' }}>
              By Platform
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {Object.entries(stats.by_platform).map(([platform, count]) => (
                <Chip
                  key={platform}
                  label={`${platform}: ${count}`}
                  size="small"
                  sx={{
                    fontSize: '0.875rem',
                    fontWeight: 500,
                    backgroundColor: 'primary.main',
                    color: 'white'
                  }}
                />
              ))}
            </Box>
          </Grid>

          <Grid item xs={12} sm={6}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2, color: 'text.primary' }}>
              By Language
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
              {Object.entries(stats.by_language).map(([language, count]) => (
                <Chip
                  key={language}
                  label={`${language}: ${count}`}
                  size="small"
                  sx={{
                    fontSize: '0.875rem',
                    fontWeight: 500,
                    backgroundColor: 'secondary.main',
                    color: 'white'
                  }}
                />
              ))}
            </Box>
          </Grid>
        </Grid>
      </Paper>
    </Box>
  );
}

export default AccountDetail;
