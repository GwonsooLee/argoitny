import { useState, useEffect } from 'react';
import { Box, Typography, CircularProgress, Button } from '@mui/material';
import { saveTokens, saveUser } from '../utils/auth';
import { apiPost } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';
import PlanSelector from './PlanSelector';

const GoogleLogin = ({ onLoginSuccess }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showPlanSelector, setShowPlanSelector] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState('Free');
  const [pendingCredential, setPendingCredential] = useState(null);

  useEffect(() => {
    // Load Google Sign-In SDK
    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    document.body.appendChild(script);

    script.onload = () => {
      if (window.google) {
        window.google.accounts.id.initialize({
          client_id: import.meta.env.VITE_GOOGLE_CLIENT_ID,
          callback: handleCredentialResponse,
        });

        window.google.accounts.id.renderButton(
          document.getElementById('google-signin-button'),
          {
            theme: 'outline',
            size: 'large',
            text: 'signin_with',
            locale: 'ko',
          }
        );
      }
    };

    return () => {
      if (document.body.contains(script)) {
        document.body.removeChild(script);
      }
    };
  }, []);

  const handleCredentialResponse = async (response) => {
    setIsLoading(true);
    setError(null);

    try {
      // First, try to login to check if user already has a plan
      // We use 'Free' as placeholder - backend won't change existing user's plan
      const res = await apiPost(API_ENDPOINTS.googleLogin, {
        token: response.credential,
        plan: 'Free',
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || 'Login failed');
      }

      const data = await res.json();

      // Check if this is a new user or existing user without plan
      if (data.is_new_user || !data.user.subscription_plan_name) {
        // Show plan selector for new users or users without plan
        setPendingCredential(response.credential);
        setShowPlanSelector(true);
      } else {
        // Existing user with plan - login directly
        saveTokens(data.access, data.refresh);
        saveUser(data.user);

        // Wait a tick to ensure tokens are saved to localStorage
        await new Promise(resolve => setTimeout(resolve, 100));

        if (onLoginSuccess) {
          onLoginSuccess(data.user);
        }
      }
    } catch (err) {
      console.error('Login error:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePlanSelect = async (plan) => {
    if (!pendingCredential || isLoading) return;

    setSelectedPlan(plan);
    setIsLoading(true);
    setError(null);

    try {
      // Send Google token and selected plan to backend
      const res = await apiPost(API_ENDPOINTS.googleLogin, {
        token: pendingCredential,
        plan: plan,
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || 'Login failed');
      }

      const data = await res.json();

      // Save tokens and user info
      saveTokens(data.access, data.refresh);
      saveUser(data.user);

      // Wait a tick to ensure tokens are saved to localStorage
      await new Promise(resolve => setTimeout(resolve, 0));

      // Notify parent component
      if (onLoginSuccess) {
        onLoginSuccess(data.user);
      }
    } catch (err) {
      console.error('Login error:', err);
      setError(err.message);
      setShowPlanSelector(false);
      setPendingCredential(null);
    } finally {
      setIsLoading(false);
    }
  };

  if (showPlanSelector) {
    return (
      <Box sx={{ py: 2 }}>
        <Typography variant="h5" sx={{ textAlign: 'center', mb: 3, fontWeight: 600 }}>
          Choose Your Plan
        </Typography>
        <PlanSelector
          onSelectPlan={handlePlanSelect}
          selectedPlan={selectedPlan}
          showConfirmButton={true}
        />
        {isLoading && (
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', mt: 3, gap: 1 }}>
            <CircularProgress size={20} />
            <Typography sx={{ color: 'text.secondary' }}>Processing...</Typography>
          </Box>
        )}
        {error && (
          <Typography sx={{ color: 'error.main', mt: 2, textAlign: 'center' }}>
            {error}
          </Typography>
        )}
      </Box>
    );
  }

  return (
    <Box sx={{ textAlign: 'center', py: 2 }}>
      <div id="google-signin-button"></div>
      {isLoading && (
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', mt: 2, gap: 1 }}>
          <CircularProgress size={20} />
          <Typography sx={{ color: 'text.secondary' }}>Signing in...</Typography>
        </Box>
      )}
      {error && (
        <Typography sx={{ color: 'error.main', mt: 2 }}>
          {error}
        </Typography>
      )}
    </Box>
  );
};

export default GoogleLogin;
