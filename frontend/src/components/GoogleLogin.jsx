import { useState, useEffect } from 'react';
import { Box, Typography, CircularProgress, Button } from '@mui/material';
import { saveTokens, saveUser, clearAuth } from '../utils/auth';
import { apiPost, apiGet } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';
import ConsentModal from './ConsentModal';

const GoogleLogin = ({ onLoginSuccess }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showConsentModal, setShowConsentModal] = useState(false);
  const [pendingUser, setPendingUser] = useState(null);

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
      // Login with Google - Free plan will be auto-assigned
      const res = await apiPost(API_ENDPOINTS.googleLogin, {
        token: response.credential,
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || 'Login failed');
      }

      const data = await res.json();

      // Save tokens and user
      saveTokens(data.access, data.refresh);
      saveUser(data.user);
      setPendingUser(data.user);

      // Wait a bit to ensure tokens are saved to localStorage
      await new Promise(resolve => setTimeout(resolve, 100));

      // Check if user has given all consents
      const consentsRes = await apiGet(API_ENDPOINTS.getConsents, { requireAuth: true });

      if (!consentsRes.ok) {
        throw new Error('Failed to check consent status');
      }

      const consentsData = await consentsRes.json();

      // If not all consents are given, show consent modal
      if (!consentsData.all_consents_given) {
        setShowConsentModal(true);
      } else {
        // All consents given - complete login
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


  const handleConsentsComplete = async (consents) => {
    setIsLoading(true);
    setError(null);

    try {
      // Submit consents to backend
      const res = await apiPost(API_ENDPOINTS.submitConsents, consents, { requireAuth: true });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || 'Failed to save consents');
      }

      // Hide consent modal
      setShowConsentModal(false);

      // Complete login with Free plan (auto-assigned)
      if (onLoginSuccess && pendingUser) {
        onLoginSuccess(pendingUser);
      }
    } catch (err) {
      console.error('Consent submission error:', err);
      throw err; // Re-throw to let ConsentModal handle the error
    } finally {
      setIsLoading(false);
    }
  };

  const handleConsentsCancel = () => {
    // Clear authentication tokens
    clearAuth();

    // Reset states
    setShowConsentModal(false);
    setPendingUser(null);
    setError('Login cancelled. You must accept all terms to use the service.');

    // Re-render Google button after a short delay
    setTimeout(() => {
      if (window.google && document.getElementById('google-signin-button')) {
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
    }, 100);
  };

  if (showConsentModal) {
    return (
      <ConsentModal
        open={showConsentModal}
        onComplete={handleConsentsComplete}
        onCancel={handleConsentsCancel}
      />
    );
  }

  const handleTryAgain = () => {
    setError(null);

    // Re-render Google button after clearing error
    setTimeout(() => {
      if (window.google && document.getElementById('google-signin-button')) {
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
    }, 100);
  };

  return (
    <Box sx={{ textAlign: 'center', py: 2 }}>
      {error && (
        <Box sx={{ mb: 3 }}>
          <Typography sx={{ color: 'error.main', mb: 2 }}>
            {error}
          </Typography>
          <Button
            variant="outlined"
            onClick={handleTryAgain}
            sx={{ textTransform: 'none' }}
          >
            Try Again
          </Button>
        </Box>
      )}
      {!error && (
        <>
          <div id="google-signin-button"></div>
          {isLoading && (
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', mt: 2, gap: 1 }}>
              <CircularProgress size={20} />
              <Typography sx={{ color: 'text.secondary' }}>Signing in...</Typography>
            </Box>
          )}
        </>
      )}
    </Box>
  );
};

export default GoogleLogin;
