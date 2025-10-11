import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Checkbox,
  FormControlLabel,
  CircularProgress,
  Alert,
  Link,
  Divider,
  IconButton
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';

const ConsentModal = ({ open, onComplete, onCancel }) => {
  const [privacyAgreed, setPrivacyAgreed] = useState(false);
  const [termsAgreed, setTermsAgreed] = useState(false);
  const [codeOwnershipAgreed, setCodeOwnershipAgreed] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const allAgreed = privacyAgreed && termsAgreed && codeOwnershipAgreed;

  const handleSubmit = async () => {
    if (!allAgreed) {
      setError('You must agree to all terms to continue');
      return;
    }

    setIsLoading(true);
    setError(null);

    // Call the onComplete callback
    if (onComplete) {
      try {
        await onComplete({
          privacy_agreed: privacyAgreed,
          terms_agreed: termsAgreed,
          code_ownership_agreed: codeOwnershipAgreed
        });
      } catch (err) {
        setError(err.message || 'Failed to save consents');
        setIsLoading(false);
      }
    }
  };

  const handleClose = () => {
    if (isLoading) return; // Prevent closing while loading

    if (onCancel) {
      onCancel();
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
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <Box>
            <Typography variant="h5" component="div" sx={{ fontWeight: 600 }}>
              Welcome to TestCase.Run
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Please review and accept the following terms to continue
            </Typography>
          </Box>
          <IconButton
            aria-label="close"
            onClick={handleClose}
            disabled={isLoading}
            sx={{
              color: 'grey.500',
              '&:hover': {
                color: 'error.main',
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

          <Box sx={{ mb: 3 }}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={privacyAgreed}
                  onChange={(e) => setPrivacyAgreed(e.target.checked)}
                  disabled={isLoading}
                />
              }
              label={
                <Typography variant="body1">
                  I have read and agree to the{' '}
                  <Link
                    href="/privacy"
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                  >
                    Privacy Policy
                  </Link>
                </Typography>
              }
            />
          </Box>

          <Box sx={{ mb: 3 }}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={termsAgreed}
                  onChange={(e) => setTermsAgreed(e.target.checked)}
                  disabled={isLoading}
                />
              }
              label={
                <Typography variant="body1">
                  I have read and agree to the{' '}
                  <Link
                    href="/terms"
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                  >
                    Terms of Service
                  </Link>
                </Typography>
              }
            />
          </Box>

          <Divider sx={{ my: 2 }} />

          <Box sx={{ mb: 2, p: 2, bgcolor: 'info.light', borderRadius: 1 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
              Code Ownership Agreement
            </Typography>
            <Typography variant="body2" color="text.secondary">
              By submitting your code to TestCase.Run for testing and validation, you acknowledge that:
            </Typography>
            <Box component="ul" sx={{ mt: 1, pl: 3 }}>
              <Typography component="li" variant="body2" color="text.secondary">
                You retain all ownership rights to your submitted code
              </Typography>
              <Typography component="li" variant="body2" color="text.secondary">
                You grant TestCase.Run a license to execute and test your code for the purpose of providing the Service
              </Typography>
              <Typography component="li" variant="body2" color="text.secondary">
                TestCase.Run does not claim ownership of your submitted code
              </Typography>
              <Typography component="li" variant="body2" color="text.secondary">
                Your code submissions are stored temporarily for execution and may be cached for performance
              </Typography>
            </Box>
          </Box>

          <Box sx={{ mb: 3 }}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={codeOwnershipAgreed}
                  onChange={(e) => setCodeOwnershipAgreed(e.target.checked)}
                  disabled={isLoading}
                />
              }
              label={
                <Typography variant="body1">
                  I understand and agree to the Code Ownership terms described above
                </Typography>
              }
            />
          </Box>
        </Box>
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 3 }}>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={!allAgreed || isLoading}
          fullWidth
          size="large"
        >
          {isLoading ? (
            <>
              <CircularProgress size={20} sx={{ mr: 1 }} />
              Processing...
            </>
          ) : (
            'Accept and Continue'
          )}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ConsentModal;
