import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Card,
  CardContent,
  CircularProgress,
  Snackbar,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  ButtonGroup,
  Divider
} from '@mui/material';
import {
  People as PeopleIcon,
  Assignment as AssignmentIcon,
  Lightbulb as LightbulbIcon,
  Code as CodeIcon,
  TrendingUp as TrendingUpIcon
} from '@mui/icons-material';
import { apiGet, apiPost, apiPut, apiDelete } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';

function AdminStats() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [periodDays, setPeriodDays] = useState(7);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });

  useEffect(() => {
    fetchStats();
  }, [periodDays]);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const response = await apiGet(`/admin/usage-stats/?days=${periodDays}`, { requireAuth: true });

      if (!response.ok) {
        if (response.status === 403) {
          showSnackbar('Access denied. Admin privileges required.', 'error');
        } else {
          throw new Error('Failed to fetch statistics');
        }
      } else {
        const data = await response.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Error fetching stats:', error);
      showSnackbar('Failed to load statistics: ' + error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const showSnackbar = (message, severity = 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
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

  // Calculate total for plan distribution percentages
  const totalUsersInDistribution = stats.plan_distribution?.reduce((sum, plan) => sum + plan.user_count, 0) || 1;

  return (
    <Box>
      {/* Header with Date Range Selector */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3, flexWrap: 'wrap', gap: 2 }}>
        <Typography variant="h4" sx={{
          color: 'text.primary',
          fontWeight: 600
        }}>
          Usage Statistics
        </Typography>
        <ButtonGroup variant="outlined">
          <Button
            variant={periodDays === 7 ? 'contained' : 'outlined'}
            onClick={() => setPeriodDays(7)}
          >
            7 Days
          </Button>
          <Button
            variant={periodDays === 30 ? 'contained' : 'outlined'}
            onClick={() => setPeriodDays(30)}
          >
            30 Days
          </Button>
          <Button
            variant={periodDays === 90 ? 'contained' : 'outlined'}
            onClick={() => setPeriodDays(90)}
          >
            90 Days
          </Button>
        </ButtonGroup>
      </Box>

      {/* Key Metrics Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Box sx={{
                  p: 1.5,
                  borderRadius: 2,
                  backgroundColor: 'rgba(25, 118, 210, 0.1)',
                  color: 'primary.main',
                  display: 'flex',
                  mr: 2
                }}>
                  <PeopleIcon />
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Total Users
                </Typography>
              </Box>
              <Typography variant="h3" sx={{ fontWeight: 700, color: 'text.primary' }}>
                {stats.total_users || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Box sx={{
                  p: 1.5,
                  borderRadius: 2,
                  backgroundColor: 'rgba(156, 39, 176, 0.1)',
                  color: 'secondary.main',
                  display: 'flex',
                  mr: 2
                }}>
                  <AssignmentIcon />
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Total Problems
                </Typography>
              </Box>
              <Typography variant="h3" sx={{ fontWeight: 700, color: 'text.primary' }}>
                {stats.total_problems || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Box sx={{
                  p: 1.5,
                  borderRadius: 2,
                  backgroundColor: 'rgba(255, 152, 0, 0.1)',
                  color: '#ff9800',
                  display: 'flex',
                  mr: 2
                }}>
                  <LightbulbIcon />
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Hints Generated
                </Typography>
              </Box>
              <Typography variant="h3" sx={{ fontWeight: 700, color: 'text.primary' }}>
                {stats.hints_count || 0}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Last {stats.period_days} days
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Box sx={{
                  p: 1.5,
                  borderRadius: 2,
                  backgroundColor: 'rgba(76, 175, 80, 0.1)',
                  color: '#4caf50',
                  display: 'flex',
                  mr: 2
                }}>
                  <CodeIcon />
                </Box>
                <Typography variant="body2" color="text.secondary">
                  Code Executions
                </Typography>
              </Box>
              <Typography variant="h3" sx={{ fontWeight: 700, color: 'text.primary' }}>
                {stats.executions_count || 0}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Last {stats.period_days} days
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* Top Users Table */}
        <Grid item xs={12} lg={7}>
          <Paper sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
              <TrendingUpIcon sx={{ mr: 1, color: 'primary.main' }} />
              <Typography variant="h6" sx={{ fontWeight: 600, color: 'text.primary' }}>
                Top Active Users (Last {stats.period_days} days)
              </Typography>
            </Box>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
                    <TableCell sx={{ fontWeight: 600 }}>Rank</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>User</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Plan</TableCell>
                    <TableCell sx={{ fontWeight: 600 }}>Activity Count</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {!stats.top_users || stats.top_users.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={4} align="center" sx={{ py: 4 }}>
                        <Typography color="text.secondary">
                          No activity data for this period
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    stats.top_users.map((user, index) => (
                      <TableRow key={index} hover>
                        <TableCell>
                          <Box sx={{
                            width: 32,
                            height: 32,
                            borderRadius: '50%',
                            backgroundColor: index < 3 ? 'primary.main' : 'grey.300',
                            color: index < 3 ? 'white' : 'text.primary',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontWeight: 600,
                            fontSize: '0.875rem'
                          }}>
                            {index + 1}
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Box>
                            <Typography variant="body2" sx={{ fontWeight: 600 }}>
                              {user.name || 'Unknown'}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {user.email}
                            </Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" color="text.secondary">
                            {user.subscription_plan}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {user.activity_count}
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        </Grid>

        {/* Plan Distribution */}
        <Grid item xs={12} lg={5}>
          <Paper sx={{ p: 3, height: '100%' }}>
            <Typography variant="h6" sx={{ fontWeight: 600, color: 'text.primary', mb: 3 }}>
              Plan Distribution
            </Typography>
            {!stats.plan_distribution || stats.plan_distribution.length === 0 ? (
              <Box sx={{ textAlign: 'center', py: 4 }}>
                <Typography color="text.secondary">
                  No plan distribution data available
                </Typography>
              </Box>
            ) : (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                {stats.plan_distribution.map((plan, index) => {
                  const percentage = ((plan.user_count / totalUsersInDistribution) * 100).toFixed(1);
                  return (
                    <Box key={index}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {plan.name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {plan.user_count} users ({percentage}%)
                        </Typography>
                      </Box>
                      <Box sx={{
                        width: '100%',
                        height: 32,
                        backgroundColor: '#e0e0e0',
                        borderRadius: 1,
                        overflow: 'hidden',
                        position: 'relative'
                      }}>
                        <Box sx={{
                          width: `${percentage}%`,
                          height: '100%',
                          backgroundColor: index % 4 === 0 ? 'primary.main' :
                                         index % 4 === 1 ? 'secondary.main' :
                                         index % 4 === 2 ? '#ff9800' :
                                         '#4caf50',
                          transition: 'width 0.3s ease',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center'
                        }}>
                          {percentage > 10 && (
                            <Typography variant="caption" sx={{ color: 'white', fontWeight: 600 }}>
                              {percentage}%
                            </Typography>
                          )}
                        </Box>
                      </Box>
                    </Box>
                  );
                })}
                <Divider sx={{ my: 2 }} />
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    Total Users
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 600, color: 'primary.main' }}>
                    {totalUsersInDistribution}
                  </Typography>
                </Box>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}

export default AdminStats;
