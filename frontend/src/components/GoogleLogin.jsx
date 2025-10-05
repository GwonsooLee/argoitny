import { useState, useEffect } from 'react';
import { saveTokens, saveUser } from '../utils/auth';
import { apiPost } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';

const GoogleLogin = ({ onLoginSuccess }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

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
      document.body.removeChild(script);
    };
  }, []);

  const handleCredentialResponse = async (response) => {
    setIsLoading(true);
    setError(null);

    try {
      // Send Google token to backend
      const res = await apiPost(API_ENDPOINTS.googleLogin, {
        token: response.credential,
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || 'Login failed');
      }

      const data = await res.json();

      // Save tokens and user info
      saveTokens(data.access, data.refresh);
      saveUser(data.user);

      // Notify parent component
      if (onLoginSuccess) {
        onLoginSuccess(data.user);
      }
    } catch (err) {
      console.error('Login error:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="google-login-container">
      <div id="google-signin-button"></div>
      {isLoading && <p className="loading-text">Signing in...</p>}
      {error && <p className="error-text">{error}</p>}
    </div>
  );
};

export default GoogleLogin;
