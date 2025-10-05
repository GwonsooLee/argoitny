import { Box, Typography, Button, Container, Link, Stack } from '@mui/material';
import { GitHub, Email, Info } from '@mui/icons-material';

function Footer({ onAboutClick }) {
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
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap', justifyContent: 'center' }}>
            <Button
              onClick={onAboutClick}
              startIcon={<Info />}
              sx={{
                color: 'text.primary',
                textTransform: 'none',
                fontWeight: 500,
                '&:hover': {
                  backgroundColor: 'rgba(0, 0, 0, 0.04)',
                  transform: 'translateY(-1px)'
                },
                transition: 'all 0.2s'
              }}
            >
              About
            </Button>
            <Link
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              sx={{
                color: 'text.primary',
                display: 'flex',
                alignItems: 'center',
                gap: 0.75,
                textDecoration: 'none',
                fontWeight: 500,
                px: 1.5,
                py: 0.75,
                borderRadius: 1,
                '&:hover': {
                  backgroundColor: 'rgba(0, 0, 0, 0.04)',
                  transform: 'translateY(-1px)'
                },
                transition: 'all 0.2s'
              }}
            >
              <GitHub fontSize="small" />
              <Typography variant="body2" sx={{ fontWeight: 500 }}>GitHub</Typography>
            </Link>
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
