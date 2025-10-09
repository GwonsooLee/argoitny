import { useState, useEffect } from 'react';
import { Container, Typography, Box, Paper, Button, CircularProgress, Alert } from '@mui/material';
import { ArrowBack } from '@mui/icons-material';
import ReactMarkdown from 'react-markdown';
import { apiGet } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';

function PrivacyPolicy({ onBack }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [document, setDocument] = useState(null);

  useEffect(() => {
    const fetchDocument = async () => {
      try {
        const response = await apiGet(`${API_ENDPOINTS.legal}/privacy/`);
        if (response.ok) {
          const data = await response.json();
          setDocument(data);
        } else {
          setError('Failed to load Privacy Policy');
        }
      } catch (err) {
        console.error('Error fetching privacy policy:', err);
        setError('Failed to load Privacy Policy');
      } finally {
        setLoading(false);
      }
    };

    fetchDocument();
  }, []);

  if (loading) {
    return (
      <Container maxWidth="md" sx={{ py: 4, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="md" sx={{ py: 4 }}>
        <Button startIcon={<ArrowBack />} onClick={onBack} sx={{ mb: 3 }}>
          Back
        </Button>
        <Alert severity="error">{error}</Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Button
        startIcon={<ArrowBack />}
        onClick={onBack}
        sx={{ mb: 3 }}
      >
        Back
      </Button>

      <Paper elevation={0} sx={{ p: { xs: 3, sm: 4, md: 5 }, border: '1px solid', borderColor: 'divider' }}>
        {document && (
          <Box sx={{ mb: 3 }}>
            <Typography variant="caption" color="text.secondary">
              Version: {document.version} | Effective Date: {document.effective_date}
            </Typography>
          </Box>
        )}

        <Box sx={{
          '& h1': { fontSize: '2rem', fontWeight: 700, mt: 4, mb: 3 },
          '& h2': { fontSize: '1.5rem', fontWeight: 600, mt: 4, mb: 2 },
          '& h3': { fontSize: '1.125rem', fontWeight: 600, mt: 3, mb: 1.5 },
          '& h4': { fontSize: '1rem', fontWeight: 600, mt: 2, mb: 1 },
          '& p': { mb: 2, lineHeight: 1.7 },
          '& ul': { mb: 2, pl: 3 },
          '& ol': { mb: 2, pl: 3 },
          '& li': { mb: 1 },
          '& strong': { fontWeight: 600 },
          '& hr': { my: 4, border: 'none', borderTop: '1px solid', borderColor: 'divider' }
        }}>
          {document && <ReactMarkdown>{document.content}</ReactMarkdown>}
        </Box>
      </Paper>
    </Container>
  );
}

export default PrivacyPolicy;
