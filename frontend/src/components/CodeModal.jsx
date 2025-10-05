import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Paper,
  IconButton,
  Chip
} from '@mui/material';
import { Close as CloseIcon } from '@mui/icons-material';

function CodeModal({ code, onClose }) {
  if (!code) return null;

  return (
    <Dialog
      open={true}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          maxHeight: '90vh'
        }
      }}
    >
      <DialogTitle>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            View Code
          </Typography>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent dividers>
        <Box sx={{ mb: 3 }}>
          <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap', alignItems: 'center' }}>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              Problem:
            </Typography>
            <Chip
              label={code.platform === 'baekjoon' ? 'Baekjoon' : 'Codeforces'}
              size="small"
              color="primary"
            />
            <Typography variant="body2">
              #{code.problemNumber} - {code.problemTitle}
            </Typography>
          </Box>

          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              Language:
            </Typography>
            <Chip label={code.language} size="small" />
          </Box>
        </Box>

        <Paper
          elevation={0}
          sx={{
            p: 2,
            backgroundColor: '#f5f5f5',
            border: '1px solid',
            borderColor: 'divider',
            maxHeight: '60vh',
            overflow: 'auto'
          }}
        >
          <pre style={{
            margin: 0,
            fontFamily: 'monospace',
            fontSize: '0.875rem',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            color: '#333'
          }}>
            {code.code}
          </pre>
        </Paper>
      </DialogContent>

      <DialogActions>
        <Button onClick={onClose} variant="outlined">
          Close
        </Button>
      </DialogActions>
    </Dialog>
  );
}

export default CodeModal;
