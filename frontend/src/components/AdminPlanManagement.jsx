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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
  Snackbar,
  Alert,
  IconButton,
  Chip,
  FormControlLabel,
  Switch,
  Grid
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Close as CloseIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon
} from '@mui/icons-material';
import { apiGet, apiPost, apiPatch, apiDelete } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';

function AdminPlanManagement() {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });

  // Create/Edit dialog state
  const [formDialog, setFormDialog] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [currentPlan, setCurrentPlan] = useState(null);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    max_hints_per_day: '',
    max_executions_per_day: '',
    max_problems: '',
    can_view_all_problems: true,
    can_register_problems: false,
    is_active: true
  });
  const [saving, setSaving] = useState(false);

  // Delete confirmation dialog
  const [deleteDialog, setDeleteDialog] = useState(false);
  const [planToDelete, setPlanToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    fetchPlans();
  }, []);

  const fetchPlans = async () => {
    setLoading(true);
    try {
      const response = await apiGet('/admin/plans/', { requireAuth: true });

      if (!response.ok) {
        if (response.status === 403) {
          showSnackbar('Access denied. Admin privileges required.', 'error');
        } else {
          throw new Error('Failed to fetch plans');
        }
      } else {
        const data = await response.json();
        setPlans(data.plans || []);
      }
    } catch (error) {
      console.error('Error fetching plans:', error);
      showSnackbar('Failed to load plans: ' + error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const showSnackbar = (message, severity = 'info') => {
    setSnackbar({ open: true, message, severity });
  };

  const handleCreateClick = () => {
    setEditMode(false);
    setCurrentPlan(null);
    setFormData({
      name: '',
      description: '',
      max_hints_per_day: '',
      max_executions_per_day: '',
      max_problems: '',
      can_view_all_problems: true,
      can_register_problems: false,
      is_active: true
    });
    setFormDialog(true);
  };

  const handleEditClick = (plan) => {
    setEditMode(true);
    setCurrentPlan(plan);
    setFormData({
      name: plan.name,
      description: plan.description,
      max_hints_per_day: plan.max_hints_per_day === -1 ? '-1' : plan.max_hints_per_day.toString(),
      max_executions_per_day: plan.max_executions_per_day === -1 ? '-1' : plan.max_executions_per_day.toString(),
      max_problems: plan.max_problems === -1 ? '-1' : plan.max_problems.toString(),
      can_view_all_problems: plan.can_view_all_problems,
      can_register_problems: plan.can_register_problems,
      is_active: plan.is_active
    });
    setFormDialog(true);
  };

  const handleFormSubmit = async () => {
    // Validation
    if (!formData.name.trim()) {
      showSnackbar('Plan name is required', 'warning');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        name: formData.name.trim(),
        description: formData.description.trim(),
        max_hints_per_day: formData.max_hints_per_day === '' ? -1 : parseInt(formData.max_hints_per_day),
        max_executions_per_day: formData.max_executions_per_day === '' ? -1 : parseInt(formData.max_executions_per_day),
        max_problems: formData.max_problems === '' ? -1 : parseInt(formData.max_problems),
        can_view_all_problems: formData.can_view_all_problems,
        can_register_problems: formData.can_register_problems,
        is_active: formData.is_active
      };

      const endpoint = editMode
        ? `/admin/plans/${currentPlan.id}/`
        : `/admin/plans/`;

      const response = editMode
        ? await apiPatch(endpoint, payload, { requireAuth: true })
        : await apiPost(endpoint, payload, { requireAuth: true });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `Failed to ${editMode ? 'update' : 'create'} plan`);
      }

      showSnackbar(`Plan ${editMode ? 'updated' : 'created'} successfully!`, 'success');
      setFormDialog(false);
      fetchPlans();
    } catch (error) {
      console.error(`Error ${editMode ? 'updating' : 'creating'} plan:`, error);
      showSnackbar(`Failed to ${editMode ? 'update' : 'create'} plan: ` + error.message, 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteClick = (plan) => {
    setPlanToDelete(plan);
    setDeleteDialog(true);
  };

  const handleDeleteConfirm = async () => {
    if (!planToDelete) return;

    setDeleting(true);
    try {
      const response = await apiDelete(`/admin/plans/${planToDelete.id}/`, { requireAuth: true });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to delete plan');
      }

      showSnackbar('Plan deleted successfully!', 'success');
      setDeleteDialog(false);
      setPlanToDelete(null);
      fetchPlans();
    } catch (error) {
      console.error('Error deleting plan:', error);
      showSnackbar('Failed to delete plan: ' + error.message, 'error');
    } finally {
      setDeleting(false);
    }
  };

  const handleFormChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" sx={{
          color: 'text.primary',
          fontWeight: 600
        }}>
          Subscription Plan Management
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleCreateClick}
        >
          Create Plan
        </Button>
      </Box>

      {/* Plans Table */}
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow sx={{ backgroundColor: '#f5f5f5' }}>
              <TableCell sx={{ fontWeight: 600 }}>Name</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Description</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Hints/Day</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Executions/Day</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Max Problems</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Features</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>User Count</TableCell>
              <TableCell sx={{ fontWeight: 600 }}>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {plans.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} align="center" sx={{ py: 4 }}>
                  <Typography color="text.secondary">
                    No subscription plans yet
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              plans.map((plan) => (
                <TableRow key={plan.id} hover>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {plan.name}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary" sx={{
                      maxWidth: 200,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap'
                    }}>
                      {plan.description || '-'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    {plan.max_hints_per_day === -1 ? (
                      <Chip label="Unlimited" size="small" color="success" variant="outlined" />
                    ) : (
                      plan.max_hints_per_day
                    )}
                  </TableCell>
                  <TableCell>
                    {plan.max_executions_per_day === -1 ? (
                      <Chip label="Unlimited" size="small" color="success" variant="outlined" />
                    ) : (
                      plan.max_executions_per_day
                    )}
                  </TableCell>
                  <TableCell>
                    {plan.max_problems === -1 ? (
                      <Chip label="Unlimited" size="small" color="success" variant="outlined" />
                    ) : (
                      plan.max_problems
                    )}
                  </TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        {plan.can_view_all_problems ? (
                          <CheckCircleIcon sx={{ fontSize: 16, color: 'success.main' }} />
                        ) : (
                          <CancelIcon sx={{ fontSize: 16, color: 'error.main' }} />
                        )}
                        <Typography variant="caption">View All</Typography>
                      </Box>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                        {plan.can_register_problems ? (
                          <CheckCircleIcon sx={{ fontSize: 16, color: 'success.main' }} />
                        ) : (
                          <CancelIcon sx={{ fontSize: 16, color: 'error.main' }} />
                        )}
                        <Typography variant="caption">Register</Typography>
                      </Box>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={plan.is_active ? 'Active' : 'Inactive'}
                      color={plan.is_active ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>{plan.user_count || 0}</TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <IconButton
                        size="small"
                        color="primary"
                        onClick={() => handleEditClick(plan)}
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => handleDeleteClick(plan)}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Box>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Create/Edit Plan Dialog */}
      <Dialog
        open={formDialog}
        onClose={() => !saving && setFormDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          {editMode ? 'Edit Plan' : 'Create New Plan'}
          <IconButton
            onClick={() => setFormDialog(false)}
            disabled={saving}
            sx={{ position: 'absolute', right: 8, top: 8 }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          <Box sx={{ mt: 2 }}>
            <Grid container spacing={2}>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Plan Name"
                  value={formData.name}
                  onChange={(e) => handleFormChange('name', e.target.value)}
                  disabled={saving}
                  required
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Description"
                  value={formData.description}
                  onChange={(e) => handleFormChange('description', e.target.value)}
                  disabled={saving}
                  multiline
                  rows={2}
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  fullWidth
                  label="Max Hints Per Day"
                  type="number"
                  value={formData.max_hints_per_day}
                  onChange={(e) => handleFormChange('max_hints_per_day', e.target.value)}
                  disabled={saving}
                  helperText="Use -1 for unlimited"
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  fullWidth
                  label="Max Executions Per Day"
                  type="number"
                  value={formData.max_executions_per_day}
                  onChange={(e) => handleFormChange('max_executions_per_day', e.target.value)}
                  disabled={saving}
                  helperText="Use -1 for unlimited"
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <TextField
                  fullWidth
                  label="Max Problems"
                  type="number"
                  value={formData.max_problems}
                  onChange={(e) => handleFormChange('max_problems', e.target.value)}
                  disabled={saving}
                  helperText="Use -1 for unlimited"
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.can_view_all_problems}
                      onChange={(e) => handleFormChange('can_view_all_problems', e.target.checked)}
                      disabled={saving}
                    />
                  }
                  label="Can View All Problems"
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.can_register_problems}
                      onChange={(e) => handleFormChange('can_register_problems', e.target.checked)}
                      disabled={saving}
                    />
                  }
                  label="Can Register Problems"
                />
              </Grid>
              <Grid item xs={12} sm={4}>
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.is_active}
                      onChange={(e) => handleFormChange('is_active', e.target.checked)}
                      disabled={saving}
                    />
                  }
                  label="Active"
                />
              </Grid>
            </Grid>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setFormDialog(false);
            }}
            disabled={saving}
          >
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleFormSubmit}
            disabled={saving || !formData.name.trim()}
          >
            {saving ? 'Saving...' : (editMode ? 'Update Plan' : 'Create Plan')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialog}
        onClose={() => !deleting && setDeleteDialog(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          Confirm Delete
          <IconButton
            onClick={() => setDeleteDialog(false)}
            disabled={deleting}
            sx={{ position: 'absolute', right: 8, top: 8 }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          <Typography variant="body1" sx={{ mb: 2 }}>
            Are you sure you want to delete this subscription plan?
          </Typography>
          {planToDelete && (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Plan: <strong>{planToDelete.name}</strong>
              <br />
              Current users: <strong>{planToDelete.user_count || 0}</strong>
            </Typography>
          )}
          <Typography variant="body2" color="error">
            This action cannot be undone. Users with this plan will need to be assigned a different plan.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setDeleteDialog(false);
              setPlanToDelete(null);
            }}
            disabled={deleting}
          >
            Cancel
          </Button>
          <Button
            variant="contained"
            color="error"
            startIcon={<DeleteIcon />}
            onClick={handleDeleteConfirm}
            disabled={deleting}
          >
            {deleting ? 'Deleting...' : 'Delete Plan'}
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

export default AdminPlanManagement;
