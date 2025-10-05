import { Box, Typography, Container, Paper, Divider } from '@mui/material';

function About() {
  return (
    <Container maxWidth="md" sx={{ py: 6 }}>
      <Paper elevation={0} sx={{ p: 4, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
        <Typography variant="h3" sx={{ fontWeight: 700, mb: 4, color: 'text.primary' }}>
          About TestCase.Run
        </Typography>

        <Box sx={{ mb: 4 }}>
          <Typography variant="h5" sx={{ fontWeight: 600, mb: 2 }}>
            What is this platform?
          </Typography>
          <Typography variant="body1" sx={{ color: 'text.secondary', lineHeight: 1.8 }}>
            This is a powerful algorithm problem test case generator and management platform designed to help developers
            and competitive programmers streamline their problem-solving workflow.
          </Typography>
        </Box>

        <Divider sx={{ my: 4 }} />

        <Box sx={{ mb: 4 }}>
          <Typography variant="h5" sx={{ fontWeight: 600, mb: 2 }}>
            Purpose
          </Typography>
          <Typography variant="body1" sx={{ color: 'text.secondary', mb: 2, lineHeight: 1.8 }}>
            Our platform serves multiple key purposes:
          </Typography>
          <Box component="ul" sx={{ pl: 3, '& li': { mb: 1.5, color: 'text.secondary', lineHeight: 1.8 } }}>
            <li>
              <strong>Automated Test Case Generation:</strong> Automatically generate diverse and comprehensive test cases
              for algorithm problems from popular platforms like Baekjoon and Codeforces.
            </li>
            <li>
              <strong>Code Testing:</strong> Test your solution code against generated test cases in real-time to validate
              correctness and identify edge cases.
            </li>
            <li>
              <strong>Problem Management:</strong> Register, organize, and manage algorithm problems with their test cases
              in one centralized location.
            </li>
            <li>
              <strong>Learning Enhancement:</strong> Improve your problem-solving skills by understanding various test case
              scenarios and edge cases that might not be obvious from problem descriptions alone.
            </li>
          </Box>
        </Box>

        <Divider sx={{ my: 4 }} />

        <Box sx={{ mb: 4 }}>
          <Typography variant="h5" sx={{ fontWeight: 600, mb: 3 }}>
            How to Use
          </Typography>

          <Box sx={{ mb: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
              1. Sign In
            </Typography>
            <Typography variant="body1" sx={{ color: 'text.secondary', lineHeight: 1.8 }}>
              Click the "Sign In" button in the header and authenticate using your Google account. Authentication is required
              to access problem details and use the platform's features.
            </Typography>
          </Box>

          <Box sx={{ mb: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
              2. Search for Problems
            </Typography>
            <Typography variant="body1" sx={{ color: 'text.secondary', mb: 1, lineHeight: 1.8 }}>
              Use the search functionality on the main page to find algorithm problems. You can search by:
            </Typography>
            <Box component="ul" sx={{ pl: 3, '& li': { mb: 0.5, color: 'text.secondary' } }}>
              <li>Problem title or ID</li>
              <li>Platform (Baekjoon or Codeforces)</li>
              <li>Tags and categories</li>
            </Box>
          </Box>

          <Box sx={{ mb: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
              3. Generate Test Cases
            </Typography>
            <Typography variant="body1" sx={{ color: 'text.secondary', mb: 1, lineHeight: 1.8 }}>
              Once you select a problem, the system will automatically generate test cases based on the problem's constraints
              and requirements. These test cases include:
            </Typography>
            <Box component="ul" sx={{ pl: 3, '& li': { mb: 0.5, color: 'text.secondary' } }}>
              <li>Basic cases covering standard inputs</li>
              <li>Edge cases for boundary conditions</li>
              <li>Corner cases for special scenarios</li>
              <li>Large cases for performance testing</li>
            </Box>
          </Box>

          <Box sx={{ mb: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
              4. Test Your Code
            </Typography>
            <Typography variant="body1" sx={{ color: 'text.secondary', lineHeight: 1.8 }}>
              Write or paste your solution code in the code editor. The platform supports multiple programming languages.
              Click "Run Tests" to execute your code against all generated test cases and see the results instantly.
            </Typography>
          </Box>

          <Box sx={{ mb: 3 }}>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>
              5. Register New Problems
            </Typography>
            <Typography variant="body1" sx={{ color: 'text.secondary', lineHeight: 1.8 }}>
              Can't find a problem in our database? Use the "Register Problem" feature to add new problems to the platform.
              Simply provide the problem URL from Baekjoon or Codeforces, and our system will fetch the problem details
              and generate test cases automatically.
            </Typography>
          </Box>
        </Box>

        <Divider sx={{ my: 4 }} />

        <Box sx={{ mb: 4 }}>
          <Typography variant="h5" sx={{ fontWeight: 600, mb: 2 }}>
            Key Features
          </Typography>
          <Box component="ul" sx={{ pl: 3, '& li': { mb: 1, color: 'text.secondary', lineHeight: 1.8 } }}>
            <li>Support for multiple competitive programming platforms</li>
            <li>Intelligent test case generation using AI</li>
            <li>Real-time code execution and validation</li>
            <li>Comprehensive test result analysis</li>
            <li>Problem search and filtering capabilities</li>
            <li>User-friendly code editor with syntax highlighting</li>
            <li>Background job processing for heavy operations</li>
            <li>Secure authentication via Google OAuth</li>
          </Box>
        </Box>

        <Divider sx={{ my: 4 }} />

        <Box>
          <Typography variant="h5" sx={{ fontWeight: 600, mb: 2 }}>
            Technology Stack
          </Typography>
          <Typography variant="body1" sx={{ color: 'text.secondary', mb: 2, lineHeight: 1.8 }}>
            TestCase.Run is built with modern web technologies:
          </Typography>
          <Box component="ul" sx={{ pl: 3, '& li': { mb: 1, color: 'text.secondary', lineHeight: 1.8 } }}>
            <li>Frontend: React.js with Vite for fast development</li>
            <li>Backend: Django (Python) for high-performance API</li>
            <li>Database: PostgreSQL for reliable data storage</li>
            <li>AI: Google Gemini for intelligent test case generation</li>
            <li>Authentication: Google OAuth for secure login</li>
          </Box>
        </Box>
      </Paper>
    </Container>
  );
}

export default About;
