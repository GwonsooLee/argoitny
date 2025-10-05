function About({ onBack }) {
  return (
    <div className="about-page">
      <button onClick={onBack} className="back-to-search-btn">
        ← Back
      </button>

      <div className="about-content">
        <h1>About</h1>

        <section className="about-section">
          <h2>What is this platform?</h2>
          <p>
            This is a powerful algorithm problem test case generator and management platform designed to help developers
            and competitive programmers streamline their problem-solving workflow.
          </p>
        </section>

        <section className="about-section">
          <h2>Purpose</h2>
          <p>
            Our platform serves multiple key purposes:
          </p>
          <ul>
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
          </ul>
        </section>

        <section className="about-section">
          <h2>How to Use</h2>

          <div className="usage-step">
            <h3>1. Sign In</h3>
            <p>
              Click the "Sign In" button in the header and authenticate using your Google account. Authentication is required
              to access problem details and use the platform's features.
            </p>
          </div>

          <div className="usage-step">
            <h3>2. Search for Problems</h3>
            <p>
              Use the search functionality on the main page to find algorithm problems. You can search by:
            </p>
            <ul>
              <li>Problem title or ID</li>
              <li>Platform (Baekjoon or Codeforces)</li>
              <li>Tags and categories</li>
            </ul>
          </div>

          <div className="usage-step">
            <h3>3. Generate Test Cases</h3>
            <p>
              Once you select a problem, the system will automatically generate test cases based on the problem's constraints
              and requirements. These test cases include:
            </p>
            <ul>
              <li>Basic cases covering standard inputs</li>
              <li>Edge cases for boundary conditions</li>
              <li>Corner cases for special scenarios</li>
              <li>Large cases for performance testing</li>
            </ul>
          </div>

          <div className="usage-step">
            <h3>4. Test Your Code</h3>
            <p>
              Write or paste your solution code in the code editor. The platform supports multiple programming languages.
              Click "Run Tests" to execute your code against all generated test cases and see the results instantly.
            </p>
          </div>

          <div className="usage-step">
            <h3>5. Register New Problems</h3>
            <p>
              Can't find a problem in our database? Use the "Register Problem" feature to add new problems to the platform.
              Simply provide the problem URL from Baekjoon or Codeforces, and our system will fetch the problem details
              and generate test cases automatically.
            </p>
          </div>

          <div className="usage-step">
            <h3>6. Track Your Progress</h3>
            <p>
              Use the following features to manage your workflow:
            </p>
            <ul>
              <li><strong>History:</strong> View your recently searched problems for quick access</li>
              <li><strong>Jobs & Drafts:</strong> Monitor background jobs for problem registration and test case generation</li>
              <li><strong>Test Results:</strong> Review detailed test results including execution time and memory usage</li>
            </ul>
          </div>
        </section>

        <section className="about-section">
          <h2>Key Features</h2>
          <ul>
            <li>Support for multiple competitive programming platforms</li>
            <li>Intelligent test case generation using AI</li>
            <li>Real-time code execution and validation</li>
            <li>Comprehensive test result analysis</li>
            <li>Problem search and filtering capabilities</li>
            <li>User-friendly code editor with syntax highlighting</li>
            <li>Background job processing for heavy operations</li>
            <li>Secure authentication via Google OAuth</li>
          </ul>
        </section>

        <section className="about-section">
          <h2>Technology Stack</h2>
          <p>
            AlgoItny is built with modern web technologies:
          </p>
          <ul>
            <li>Frontend: React.js with Vite for fast development</li>
            <li>Backend: FastAPI (Python) for high-performance API</li>
            <li>Database: PostgreSQL for reliable data storage</li>
            <li>AI: OpenAI GPT for intelligent test case generation</li>
            <li>Authentication: Google OAuth for secure login</li>
          </ul>
        </section>

        <section className="about-section">
          <h2>Getting Started</h2>
          <p>
            Ready to enhance your algorithm problem-solving experience? Here's how to get started:
          </p>
          <ol>
            <li>Sign in with your Google account</li>
            <li>Search for a problem you're working on</li>
            <li>Review the generated test cases</li>
            <li>Write your solution and test it</li>
            <li>Iterate and improve based on test results</li>
          </ol>
          <p>
            If you encounter any issues or have suggestions for improvement, please feel free to reach out to our team.
          </p>
        </section>
      </div>
    </div>
  );
}

export default About;
