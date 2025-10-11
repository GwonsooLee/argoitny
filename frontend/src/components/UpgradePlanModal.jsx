import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  CircularProgress,
  Alert,
  IconButton
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import PlanSelector from './PlanSelector';
import { apiPatch } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';
import { saveUser } from '../utils/auth';

const UpgradePlanModal = ({ open, user, onComplete, onCancel }) => {
  const [selectedPlan, setSelectedPlan] = useState(user?.subscription_plan_name || 'Free');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleConfirm = async () => {
    if (isLoading) return;

    setIsLoading(true);
    setError(null);

    try {
      // Call the update plan endpoint
      const res = await apiPatch(API_ENDPOINTS.updatePlan, {
        plan: selectedPlan,
      }, { requireAuth: true });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || 'Failed to update plan');
      }

      const updatedUser = await res.json();

      // Update user info in localStorage
      saveUser(updatedUser);

      // Call the onComplete callback with updated user
      if (onComplete) {
        onComplete(updatedUser);
      }
    } catch (err) {
      console.error('Plan update error:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClose = () => {
    if (isLoading) return;

    if (onCancel) {
      onCancel();
    }
  };

  return (
    <Dialog
      open={open}
      maxWidth="md"
      fullWidth
      onClose={handleClose}
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h5" component="div" sx={{ fontWeight: 600 }}>
            Upgrade Your Plan
          </Typography>
          <IconButton
            aria-label="close"
            onClick={handleClose}
            disabled={isLoading}
            sx={{
              color: 'grey.500',
              '&:hover': {
                color: 'grey.700',
              }
            }}
          >
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>
      <DialogContent>
        <Box sx={{ py: 2 }}>
          {error && (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          )}

          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Choose a new plan to upgrade or downgrade your subscription
          </Typography>

          <PlanSelector
            onSelectPlan={setSelectedPlan}
            selectedPlan={selectedPlan}
            showConfirmButton={false}
          />
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 3 }}>
        <Button
          onClick={handleClose}
          disabled={isLoading}
          sx={{ textTransform: 'none' }}
        >
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleConfirm}
          disabled={isLoading || selectedPlan === user?.subscription_plan_name}
          sx={{ textTransform: 'none' }}
        >
          {isLoading ? (
            <>
              <CircularProgress size={20} sx={{ mr: 1 }} />
              Updating...
            </>
          ) : (
            'Confirm'
          )}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default UpgradePlanModal;
