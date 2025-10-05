import { useState } from 'react';
import {
  Box,
  Typography,
  TextField,
  Button,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  CircularProgress,
  InputAdornment,
  Chip
} from '@mui/material';
import { Search as SearchIcon } from '@mui/icons-material';
import { apiGet } from '../utils/api-client';
import { API_ENDPOINTS } from '../config/api';

function ProblemSearch({ onSelectProblem }) {
  const [query, setQuery] = useState('');
  const [problems, setProblems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) {
      return;
    }

    setLoading(true);
    setHasSearched(true);
    try {
      // Search both platforms
      const [baekjoonResponse, codeforcesResponse] = await Promise.all([
        apiGet(`${API_ENDPOINTS.problems}?platform=baekjoon&search=${encodeURIComponent(query)}`),
        apiGet(`${API_ENDPOINTS.problems}?platform=codeforces&search=${encodeURIComponent(query)}`)
      ]);

      const results = [];

      if (baekjoonResponse.ok) {
        const data = await baekjoonResponse.json();
        results.push(...(data.problems || data || []));
      }

      if (codeforcesResponse.ok) {
        const data = await codeforcesResponse.json();
        results.push(...(data.problems || data || []));
      }

      setProblems(results);
    } catch (error) {
      console.error('Error searching problems:', error);
      setProblems([]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <Box sx={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      minHeight: '70vh',
      pt: hasSearched ? 8 : 20,
      transition: 'padding-top 0.3s ease'
    }}>
      {/* Search Box */}
      <Box sx={{ width: '100%', maxWidth: 700, px: 2 }}>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <TextField
            fullWidth
            placeholder="Search by problem number or title"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: 3,
                '&:hover': {
                  boxShadow: 1
                },
                '&.Mui-focused': {
                  boxShadow: 2
                }
              }
            }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon color="action" />
                </InputAdornment>
              ),
            }}
          />
          <Button
            variant="contained"
            onClick={handleSearch}
            disabled={loading || !query.trim()}
            sx={{
              minWidth: 120,
              borderRadius: 3,
              textTransform: 'none',
              fontSize: '1rem'
            }}
          >
            {loading ? <CircularProgress size={20} color="inherit" /> : 'Search'}
          </Button>
        </Box>
      </Box>

      {/* Search Results */}
      {hasSearched && (
        <Box sx={{ width: '100%', maxWidth: 600, mt: 4, px: 2 }}>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : problems.length > 0 ? (
            <List sx={{ bgcolor: 'background.paper', borderRadius: 1, boxShadow: 1 }}>
              {problems.map((problem, index) => (
                <ListItem
                  key={`${problem.platform}-${problem.problem_id}-${index}`}
                  disablePadding
                  divider={index < problems.length - 1}
                >
                  <ListItemButton
                    onClick={() => onSelectProblem(problem)}
                    sx={{ py: 2 }}
                  >
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography variant="body1" sx={{ fontWeight: 500 }}>
                            {problem.title}
                          </Typography>
                          <Chip
                            label={problem.platform === 'baekjoon' ? 'Baekjoon' : 'Codeforces'}
                            size="small"
                            color="primary"
                            variant="outlined"
                          />
                        </Box>
                      }
                      secondary={`Problem ID: ${problem.problem_id}`}
                    />
                  </ListItemButton>
                </ListItem>
              ))}
            </List>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="text.secondary">
                No problems found for "{query}"
              </Typography>
            </Box>
          )}
        </Box>
      )}
    </Box>
  );
}

export default ProblemSearch;
