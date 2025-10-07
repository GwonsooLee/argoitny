import React, { useState } from 'react';
import { Dialog, DialogTitle, DialogContent, Button, Box, CircularProgress, Typography } from '@mui/material';
import PlanSelector from './PlanSelector';
import { apiPatch } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';
import { saveUser } from '../utils/auth';

const PlanSelectionModal = ({ open, user, onComplete }) => {
  const [selectedPlan, setSelectedPlan] = useState('Free');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handlePlanSelect = async (plan) => {
    if (isLoading) return;

    setSelectedPlan(plan);
    setIsLoading(true);
    setError(null);

    try {
      const res = await apiPatch(API_ENDPOINTS.updatePlan, {
        plan: plan,
      }, { requireAuth: true });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || 'Failed to update subscription plan');
      }

      const data = await res.json();

      // Update user info in local storage
      saveUser(data);

      // Notify parent
      if (onComplete) {
        onComplete(data);
      }
    } catch (err) {
      console.error('Failed to update plan:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog
      open={open}
      maxWidth="md"
      fullWidth
      disableEscapeKeyDown
      onClose={(event, reason) => {
        // Prevent closing by clicking outside or pressing ESC
        if (reason === 'backdropClick' || reason === 'escapeKeyDown') {
          return;
        }
      }}
    >
      <DialogTitle>
        <Typography variant="h5" component="div" sx={{ fontWeight: 600 }}>
          Select Your Subscription Plan
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Please choose a plan to continue using the service
        </Typography>
      </DialogTitle>
      <DialogContent>
        <PlanSelector
          onSelectPlan={handlePlanSelect}
          selectedPlan={selectedPlan}
          showComingSoon={true}
          showConfirmButton={true}
        />
        {isLoading && (
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', mt: 3, gap: 1 }}>
            <CircularProgress size={20} />
            <Typography sx={{ color: 'text.secondary' }}>Updating plan...</Typography>
          </Box>
        )}
        {error && (
          <Typography sx={{ color: 'error.main', mt: 2, textAlign: 'center' }}>
            {error}
          </Typography>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default PlanSelectionModal;
