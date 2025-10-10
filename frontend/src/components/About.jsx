import { Box, Typography, Container, Paper, Divider } from '@mui/material';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import TipsAndUpdatesIcon from '@mui/icons-material/TipsAndUpdates';
import SpeedIcon from '@mui/icons-material/Speed';
import SecurityIcon from '@mui/icons-material/Security';

function About() {
  return (
    <Container maxWidth="md" sx={{ py: 6 }}>
      <Paper elevation={0} sx={{ p: 4, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
        <Typography variant="h3" sx={{ fontWeight: 700, mb: 2, color: 'text.primary' }}>
          About TestCase.Run
        </Typography>
        <Typography variant="subtitle1" sx={{ color: 'text.secondary', mb: 4, fontSize: '1.1rem' }}>
          Your AI-powered companion for mastering algorithm problems
        </Typography>

        <Divider sx={{ my: 4 }} />

        {/* Why AlgoItny Exists */}
        <Box sx={{ mb: 5 }}>
          <Typography variant="h5" sx={{ fontWeight: 600, mb: 2 }}>
            Why TestCase.Run?
          </Typography>
          <Typography variant="body1" sx={{ color: 'text.secondary', lineHeight: 1.8, mb: 2 }}>
            Every algorithm problem solver has faced this frustration: <strong>your solution passes the sample test cases,
            but fails mysteriously when submitted</strong>. You spend hours debugging, only to discover it was an edge case
            you never thought to test.
          </Typography>
          <Typography variant="body1" sx={{ color: 'text.secondary', lineHeight: 1.8, mb: 2 }}>
            <strong>TestCase.Run solves this problem.</strong> We help you discover hidden edge cases, validate your solutions
            thoroughly, and learn from comprehensive test scenarios—all before you submit your code.
          </Typography>
          <Typography variant="body1" sx={{ color: 'text.secondary', lineHeight: 1.8 }}>
            Whether you're preparing for coding interviews, competing in programming contests, or simply improving your
            problem-solving skills, TestCase.Run gives you the confidence that your solution works—not just for the examples,
            but for <strong>all possible inputs</strong>.
          </Typography>
        </Box>

        <Divider sx={{ my: 4 }} />

        {/* What AlgoItny Does */}
        <Box sx={{ mb: 5 }}>
          <Typography variant="h5" sx={{ fontWeight: 600, mb: 3 }}>
            What is TestCase.Run?
          </Typography>
          <Typography variant="body1" sx={{ color: 'text.secondary', lineHeight: 1.8, mb: 3 }}>
            TestCase.Run is an <strong>AI-powered testing platform</strong> for algorithm problems from Codeforces and Baekjoon.
            We don't just run your code—we help you <strong>find bugs before they fail</strong>.
          </Typography>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
              <TipsAndUpdatesIcon sx={{ color: 'primary.main', mt: 0.5 }} />
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
                  AI-Generated Test Cases
                </Typography>
                <Typography variant="body2" sx={{ color: 'text.secondary', lineHeight: 1.7 }}>
                  Our AI analyzes problem constraints and generates comprehensive test cases including edge cases,
                  boundary conditions, and corner cases you might miss.
                </Typography>
              </Box>
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
              <SpeedIcon sx={{ color: 'primary.main', mt: 0.5 }} />
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
                  Instant Code Execution
                </Typography>
                <Typography variant="body2" sx={{ color: 'text.secondary', lineHeight: 1.7 }}>
                  Test your Python, JavaScript, C++, or Java code immediately in a secure sandbox environment.
                  See results in seconds, not minutes.
                </Typography>
              </Box>
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
              <CheckCircleOutlineIcon sx={{ color: 'primary.main', mt: 0.5 }} />
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
                  Comprehensive Validation
                </Typography>
                <Typography variant="body2" sx={{ color: 'text.secondary', lineHeight: 1.7 }}>
                  Every test shows you the input, expected output, your output, and execution time.
                  Identify exactly where and why your solution fails.
                </Typography>
              </Box>
            </Box>

            <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
              <SecurityIcon sx={{ color: 'primary.main', mt: 0.5 }} />
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 600, mb: 0.5 }}>
                  AI Hints When You're Stuck
                </Typography>
                <Typography variant="body2" sx={{ color: 'text.secondary', lineHeight: 1.7 }}>
                  Get AI-powered hints that guide you toward the solution without spoiling the problem.
                  Learn problem-solving patterns, not just answers.
                </Typography>
              </Box>
            </Box>
          </Box>
        </Box>

        <Divider sx={{ my: 4 }} />

        {/* How to Use */}
        <Box sx={{ mb: 5 }}>
          <Typography variant="h5" sx={{ fontWeight: 600, mb: 3 }}>
            How to Use TestCase.Run
          </Typography>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            <Box>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 1, color: 'primary.main' }}>
                1. Sign in with Google
              </Typography>
              <Typography variant="body1" sx={{ color: 'text.secondary', lineHeight: 1.7 }}>
                Quick and secure authentication. No password to remember.
              </Typography>
            </Box>

            <Box>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 1, color: 'primary.main' }}>
                2. Search for your problem
              </Typography>
              <Typography variant="body1" sx={{ color: 'text.secondary', lineHeight: 1.7 }}>
                Find any problem from Codeforces or Baekjoon by name, ID, or tag.
                If it's not in our database, register it with one click.
              </Typography>
            </Box>

            <Box>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 1, color: 'primary.main' }}>
                3. Write your solution
              </Typography>
              <Typography variant="body1" sx={{ color: 'text.secondary', lineHeight: 1.7 }}>
                Use our code editor or paste your existing solution. Supports Python, JavaScript, C++, and Java.
              </Typography>
            </Box>

            <Box>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 1, color: 'primary.main' }}>
                4. Run comprehensive tests
              </Typography>
              <Typography variant="body1" sx={{ color: 'text.secondary', lineHeight: 1.7 }}>
                Click "Execute" to test your code against sample cases and AI-generated edge cases.
                See exactly which tests pass and which fail.
              </Typography>
            </Box>

            <Box>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 1, color: 'primary.main' }}>
                5. Get AI hints if needed
              </Typography>
              <Typography variant="body1" sx={{ color: 'text.secondary', lineHeight: 1.7 }}>
                Stuck on a test case? Request an AI hint that points you in the right direction without giving away the answer.
              </Typography>
            </Box>

            <Box>
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 1, color: 'primary.main' }}>
                6. Submit with confidence
              </Typography>
              <Typography variant="body1" sx={{ color: 'text.secondary', lineHeight: 1.7 }}>
                Once all tests pass, submit your solution to Codeforces or Baekjoon knowing it's been thoroughly validated.
              </Typography>
            </Box>
          </Box>
        </Box>

        <Divider sx={{ my: 4 }} />

        {/* Why You Should Use AlgoItny */}
        <Box sx={{ mb: 5 }}>
          <Typography variant="h5" sx={{ fontWeight: 600, mb: 3 }}>
            Why Use TestCase.Run?
          </Typography>

          <Box component="ul" sx={{ pl: 3, '& li': { mb: 2, color: 'text.secondary', lineHeight: 1.8 } }}>
            <li>
              <strong>Stop wasting time on hidden edge cases.</strong> Our AI generates the tricky test cases you wouldn't think of,
              helping you catch bugs before submission.
            </li>
            <li>
              <strong>Learn by doing.</strong> See exactly what inputs break your solution and why.
              Understand the patterns behind edge cases and boundary conditions.
            </li>
            <li>
              <strong>Practice like a pro.</strong> Top competitive programmers always test thoroughly.
              TestCase.Run makes professional-level testing accessible to everyone.
            </li>
            <li>
              <strong>Save your submission attempts.</strong> Each wrong submission can affect your rating or ranking.
              Test exhaustively with TestCase.Run first, submit once, and get it right.
            </li>
            <li>
              <strong>Speed up your learning.</strong> Get instant feedback, AI hints, and detailed test results.
              Learn faster than trial-and-error on the judge.
            </li>
            <li>
              <strong>Multiple languages supported.</strong> Test in Python for quick prototyping, then optimize in C++ or Java.
              All in one place.
            </li>
          </Box>
        </Box>

        <Divider sx={{ my: 4 }} />

        {/* Subscription Plans */}
        <Box sx={{ mb: 5 }}>
          <Typography variant="h5" sx={{ fontWeight: 600, mb: 2 }}>
            Flexible Plans for Every User
          </Typography>
          <Typography variant="body1" sx={{ color: 'text.secondary', lineHeight: 1.8, mb: 2 }}>
            Start with our <strong>Free plan</strong> (5 AI hints and 50 code executions per day) to explore the platform.
            Upgrade to <strong>Pro</strong> (30 hints, 200 executions per day) when you're serious about leveling up your skills.
          </Typography>
          <Typography variant="body1" sx={{ color: 'text.secondary', lineHeight: 1.8 }}>
            All plans include unlimited problem viewing, search history, and access to our comprehensive problem database.
          </Typography>
        </Box>

        <Divider sx={{ my: 4 }} />

        {/* Call to Action */}
        <Box sx={{ textAlign: 'center', py: 3, bgcolor: 'primary.50', borderRadius: 2, px: 3 }}>
          <Typography variant="h5" sx={{ fontWeight: 600, mb: 2, color: 'primary.main' }}>
            Ready to solve problems with confidence?
          </Typography>
          <Typography variant="body1" sx={{ color: 'text.secondary', lineHeight: 1.8 }}>
            Join TestCase.Run today and never submit a wrong answer due to a missed edge case again.
            Sign in with Google and start testing smarter.
          </Typography>
        </Box>
      </Paper>
    </Container>
  );
}

export default About;
