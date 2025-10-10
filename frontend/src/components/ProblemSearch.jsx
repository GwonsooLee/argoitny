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
      // Search Codeforces only
      const codeforcesResponse = await apiGet(`${API_ENDPOINTS.problems}?platform=codeforces&search=${encodeURIComponent(query)}`);

      const results = [];

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
      pt: { xs: 4, sm: 8, md: 12 }
    }}>
      {/* Search Box */}
      <Box sx={{ width: '100%', maxWidth: 700, px: { xs: 0, sm: 2 } }}>
        <Box sx={{ display: 'flex', flexDirection: { xs: 'column', sm: 'row' }, gap: 1 }}>
          <TextField
            fullWidth
            placeholder="Search by problem number or title"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            sx={{
              '& .MuiOutlinedInput-root': {
                backgroundColor: 'white',
                borderRadius: { xs: 1, sm: 3 },
                fontSize: { xs: '0.875rem', sm: '1rem' },
                '&:hover': {
                  boxShadow: '0 1px 6px rgba(32, 33, 36, 0.28)'
                },
                '&.Mui-focused': {
                  boxShadow: '0 1px 6px rgba(32, 33, 36, 0.28)'
                }
              }
            }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon color="action" sx={{ fontSize: { xs: '1.25rem', sm: '1.5rem' } }} />
                </InputAdornment>
              ),
            }}
          />
          <Button
            variant="contained"
            onClick={handleSearch}
            disabled={loading || !query.trim()}
            sx={{
              minWidth: { xs: '100%', sm: 120 },
              borderRadius: { xs: 1, sm: 3 },
              textTransform: 'none',
              fontSize: { xs: '0.875rem', sm: '1rem' },
              py: { xs: 1.5, sm: 1 }
            }}
          >
            {loading ? <CircularProgress size={20} color="inherit" /> : 'Search'}
          </Button>
        </Box>
      </Box>

      {/* Search Results */}
      {hasSearched && (
        <Box sx={{ width: '100%', maxWidth: 700, mt: 3, px: { xs: 0, sm: 2 } }}>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : problems.length > 0 ? (
            <Box>
              {problems.map((problem, index) => (
                <Box
                  key={`${problem.platform}-${problem.problem_id}-${index}`}
                  onClick={() => onSelectProblem(problem)}
                  sx={{
                    p: { xs: 2, sm: 2.5 },
                    mb: 2,
                    backgroundColor: 'white',
                    borderRadius: { xs: 0, sm: 1 },
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    '&:hover': {
                      backgroundColor: '#f8f9fa'
                    }
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, mb: 0.5 }}>
                    <Typography
                      variant="h6"
                      sx={{
                        color: '#1a0dab',
                        fontSize: { xs: '1rem', sm: '1.125rem', md: '1.25rem' },
                        fontWeight: 400,
                        lineHeight: 1.3,
                        '&:hover': {
                          textDecoration: 'underline'
                        }
                      }}
                    >
                      {problem.title}
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 1, mb: 0.5 }}>
                    <Typography variant="body2" sx={{ color: '#202124', fontSize: { xs: '0.813rem', sm: '0.875rem' } }}>
                      Codeforces
                    </Typography>
                    <Typography variant="body2" sx={{ color: '#70757a' }}>
                      •
                    </Typography>
                    <Typography variant="body2" sx={{ color: '#70757a', fontSize: { xs: '0.813rem', sm: '0.875rem' } }}>
                      Problem ID: {problem.problem_id}
                    </Typography>
                  </Box>
                  {problem.problem_url && (
                    <Typography
                      variant="body2"
                      sx={{
                        color: '#006621',
                        fontSize: { xs: '0.75rem', sm: '0.813rem', md: '0.875rem' },
                        wordBreak: 'break-all',
                        lineHeight: 1.4
                      }}
                    >
                      {problem.problem_url}
                    </Typography>
                  )}
                </Box>
              ))}
            </Box>
          ) : (
            <Box sx={{ textAlign: 'center', py: 4, px: 2 }}>
              <Typography variant="body1" color="text.secondary" sx={{ fontSize: { xs: '0.875rem', sm: '1rem' } }}>
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
