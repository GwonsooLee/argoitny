import { Box, Typography, Button, Container, Stack, Link } from '@mui/material';
import { Info, Description, Policy } from '@mui/icons-material';

function Footer({ onAboutClick, onTermsClick, onPrivacyClick }) {
  return (
    <Box
      component="footer"
      sx={{
        backgroundColor: '#f5f5f5',
        color: 'text.primary',
        py: 3,
        px: 2,
        mt: 'auto',
        borderTop: '1px solid',
        borderColor: 'divider'
      }}
    >
      <Container maxWidth="lg">
        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          justifyContent="space-between"
          alignItems="center"
          spacing={2}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: { xs: 1, sm: 2 }, flexWrap: 'wrap', justifyContent: 'center' }}>
            <Button
              onClick={onAboutClick}
              startIcon={<Info />}
              sx={{
                color: 'text.primary',
                textTransform: 'none',
                fontWeight: 500,
                fontSize: { xs: '0.813rem', sm: '0.875rem' },
                px: { xs: 1, sm: 1.5 },
                '&:hover': {
                  backgroundColor: 'rgba(0, 0, 0, 0.04)',
                  transform: 'translateY(-1px)'
                },
                transition: 'all 0.2s'
              }}
            >
              About
            </Button>
            <Button
              onClick={onTermsClick}
              startIcon={<Description />}
              sx={{
                color: 'text.primary',
                textTransform: 'none',
                fontWeight: 500,
                fontSize: { xs: '0.813rem', sm: '0.875rem' },
                px: { xs: 1, sm: 1.5 },
                '&:hover': {
                  backgroundColor: 'rgba(0, 0, 0, 0.04)',
                  transform: 'translateY(-1px)'
                },
                transition: 'all 0.2s'
              }}
            >
              Terms
            </Button>
            <Button
              onClick={onPrivacyClick}
              startIcon={<Policy />}
              sx={{
                color: 'text.primary',
                textTransform: 'none',
                fontWeight: 500,
                fontSize: { xs: '0.813rem', sm: '0.875rem' },
                px: { xs: 1, sm: 1.5 },
                '&:hover': {
                  backgroundColor: 'rgba(0, 0, 0, 0.04)',
                  transform: 'translateY(-1px)'
                },
                transition: 'all 0.2s'
              }}
            >
              Privacy
            </Button>
          </Box>

          <Typography
            variant="body2"
            sx={{
              color: 'text.secondary',
              textAlign: { xs: 'center', sm: 'right' },
              fontWeight: 400,
              fontSize: '0.875rem'
            }}
          >
            © 2025 TestCase.Run. All rights reserved.
          </Typography>
        </Stack>
      </Container>
    </Box>
  );
}

export default Footer;
