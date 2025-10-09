import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  TextField,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  Snackbar,
  Alert,
  IconButton,
  InputAdornment,
  Chip
} from '@mui/material';
import {
  Search as SearchIcon,
  Edit as EditIcon,
  Close as CloseIcon,
  AdminPanelSettings as AdminIcon,
  Person as PersonIcon
} from '@mui/icons-material';
import { apiGet, apiPut } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

function AdminUserManagement() {
  const [users, setUsers] = useState([]);
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterPlan, setFilterPlan] = useState('all');
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });

  // Change plan dialog state
  const [changePlanDialog, setChangePlanDialog] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [selectedPlanId, setSelectedPlanId] = useState('');
  const [changingPlan, setChangingPlan] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [usersResponse, plansResponse] = await Promise.all([
        apiGet('/admin/users/', { requireAuth: true }),
        apiGet('/admin/plans/', { requireAuth: true })
      ]);

      if (!usersResponse.ok) {
        if (usersResponse.status === 403) {
          showSnackbar('Access denied. Admin privileges required.', 'error');
        } else if (usersResponse.status === 401) {
          showSnackbar('Please login again.', 'error');
        } else {
          throw new Error('Failed to fetch users');
        }
      } else {
        const usersData = await usersResponse.json();
        setUsers(usersData.users || []);
      }

      if (plansResponse.ok) {
        const plansData = await plansResponse.json();
        setPlans(plansData.plans || []);
      }
    } catch (error) {
      console.error('Error fetching data:', error);
      showSnackbar('Failed to load data: ' + error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const showSnackbar = (message, severity = 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  const handleChangePlanClick = (user) => {
    setSelectedUser(user);
    // subscription_plan is an object with id, name, etc.
    setSelectedPlanId(user.subscription_plan?.id || '');
    setChangePlanDialog(true);
  };

  const handleChangePlanSubmit = async () => {
    if (!selectedUser || !selectedPlanId) return;

    setChangingPlan(true);
    try {
      const response = await apiPut(
        `/admin/users/${selectedUser.id}/`,
        { subscription_plan: selectedPlanId },
        { requireAuth: true }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to update subscription plan');
      }

      showSnackbar('Subscription plan updated successfully!', 'success');
      setChangePlanDialog(false);
      setSelectedUser(null);
      setSelectedPlanId('');
      fetchData();
    } catch (error) {
      console.error('Error updating plan:', error);
      showSnackbar('Failed to update plan: ' + error.message, 'error');
    } finally {
      setChangingPlan(false);
    }
  };

  const filterUsers = (users) => {
    let filtered = users;

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(user =>
        user.email?.toLowerCase().includes(query) ||
        user.name?.toLowerCase().includes(query)
      );
    }

    // Filter by subscription plan
    if (filterPlan !== 'all') {
      filtered = filtered.filter(user => user.subscription_plan === parseInt(filterPlan));
    }

    return filtered;
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  const filteredUsers = filterUsers(users);

  return (
    <Box>
      <Typography variant="h4" sx={{
        color: 'text.primary',
        fontWeight: 600,
        mb: 3
      }}>
        User Management
      </Typography>

      {/* Search and Filter Controls */}
      <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
        <TextField
          placeholder="Search by email or name..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          sx={{ flex: 1, minWidth: '250px' }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
        />
        <TextField
          select
          label="Filter by Plan"
          value={filterPlan}
          onChange={(e) => setFilterPlan(e.target.value)}
          sx={{ minWidth: '200px' }}
        >
          <MenuItem value="all">All Plans</MenuItem>
          {plans.map((plan) => (
            <MenuItem key={plan.id} value={plan.id}>
              {plan.name}
            </MenuItem>
          ))}
        </TextField>
      </Box>

      {/* Users Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
              <TableCell sx={{ fontWeight: 600 }}>Email</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Name</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Subscription Plan</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Admin</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Usage Today</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Created At</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredUsers.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                  <Typography color="text.secondary">
                    {searchQuery || filterPlan !== 'all' ? 'No users found matching your criteria' : 'No users yet'}
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              filteredUsers.map((user) => (
                <TableRow key={user.id} hover>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      {user.picture && (
                        <img
                          src={user.picture}
                          alt={user.name}
                          style={{
                            width: 32,
                            height: 32,
                            borderRadius: '50%',
                            objectFit: 'cover'
                          }}
                        />
                      )}
                      {user.email}
                    </Box>
                  </TableCell>
                  <TableCell>{user.name || '-'}</TableCell>
                  <TableCell>
                    <Chip
                      label={user.subscription_plan_name}
                      color="primary"
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    {user.is_admin ? (
                      <Chip
                        icon={<AdminIcon />}
                        label="Admin"
                        color="secondary"
                        size="small"
                      />
                    ) : (
                      <Chip
                        icon={<PersonIcon />}
                        label="User"
                        size="small"
                        variant="outlined"
                      />
                    )}
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                      <Typography variant="caption" color="text.secondary">
                        Hints: {user.usage_stats?.hints_today || 0}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Executions: {user.usage_stats?.executions_today || 0}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    {new Date(user.created_at).toLocaleDateString()}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={<EditIcon />}
                      onClick={() => handleChangePlanClick(user)}
                    >
                      Change Plan
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Change Plan Dialog */}
      <Dialog
        open={changePlanDialog}
        onClose={() => !changingPlan && setChangePlanDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          Change Subscription Plan
          <IconButton
            onClick={() => setChangePlanDialog(false)}
            disabled={changingPlan}
            sx={{ position: 'absolute', right: 8, top: 8 }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          {selectedUser && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                User: <strong>{selectedUser.email}</strong>
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Current Plan: <strong>{selectedUser.subscription_plan_name}</strong>
              </Typography>
              <TextField
                select
                fullWidth
                label="New Subscription Plan"
                value={selectedPlanId}
                onChange={(e) => setSelectedPlanId(e.target.value)}
                disabled={changingPlan}
                sx={{ mt: 2 }}
              >
                {plans.filter(p => p.is_active).map((plan) => {
                  const isCurrentPlan = plan.id === selectedUser?.subscription_plan?.id;
                  return (
                    <MenuItem
                      key={plan.id}
                      value={plan.id}
                      disabled={isCurrentPlan}
                    >
                      <Box>
                        <Typography
                          variant="body2"
                          sx={{
                            fontWeight: 600,
                            color: isCurrentPlan ? 'text.disabled' : 'text.primary'
                          }}
                        >
                          {plan.name} {isCurrentPlan && '(Current)'}
                        </Typography>
                        <Typography
                          variant="caption"
                          color={isCurrentPlan ? 'text.disabled' : 'text.secondary'}
                        >
                          {plan.description}
                        </Typography>
                      </Box>
                    </MenuItem>
                  );
                })}
              </TextField>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setChangePlanDialog(false);
              setSelectedUser(null);
              setSelectedPlanId('');
            }}
            disabled={changingPlan}
          >
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleChangePlanSubmit}
            disabled={changingPlan || !selectedPlanId || selectedPlanId === selectedUser?.subscription_plan?.id}
          >
            {changingPlan ? 'Updating...' : 'Update Plan'}
          </Button>
        </DialogActions>
      </Dialog>

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

export default AdminUserManagement;
