import { Box, Typography, Button } from '@mui/material';

function Footer({ onAboutClick }) {
  return (
    <Box
      component="footer"
      sx={{
        backgroundColor: 'rgba(0, 0, 0, 0.2)',
        py: 3,
        px: 2,
        mt: 'auto',
        borderTop: '1px solid rgba(255, 255, 255, 0.1)'
      }}
    >
      <Box sx={{ maxWidth: 'lg', mx: 'auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Button
          onClick={onAboutClick}
          sx={{ color: 'rgba(255, 255, 255, 0.7)', '&:hover': { color: 'white' } }}
        >
          About
        </Button>
        <Typography variant="body2" sx={{ color: 'rgba(255, 255, 255, 0.5)' }}>
          Copyright 2025. All rights reserved.
        </Typography>
      </Box>
    </Box>
  );
}

export default Footer;
