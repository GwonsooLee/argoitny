"""Gemini Flash Service for cost-effective simple extractions"""
import json
import requests
import random
import time
import re
import google.generativeai as genai
from django.conf import settings
from bs4 import BeautifulSoup
from .gemini_service import GeminiService
import logging

logger = logging.getLogger(__name__)


class GeminiFlashService(GeminiService):
    """
    Gemini Flash service for cost-effective tasks

    Use this for:
    - Title extraction
    - Constraints extraction
    - Tag classification
    - Test case generator code generation
    - Hint generation
    - Other simple to moderate complexity tasks

    Cost: $0.075/$0.30 per 1M tokens (94% cheaper than Gemini Pro)

    Inherits all methods from GeminiService but uses Flash model for lower cost.
    """

    def __init__(self):
        """Initialize with Gemini Flash model instead of Pro"""
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            # Use Gemini 2.5 Flash for best cost/performance ratio
            # Pricing: $0.075/$0.30 per 1M tokens (input/output)
            # Docs: https://ai.google.dev/gemini-api/docs/pricing#gemini-2.5-flash
            try:
                self.model = genai.GenerativeModel('gemini-2.5-flash')
                logger.info("Using Gemini 2.5 Flash model")
            except Exception as e:
                # Fallback to gemini-flash-latest if 2.5 not available
                logger.warning(f"Failed to load gemini-2.5-flash, falling back to gemini-flash-latest: {e}")
                self.model = genai.GenerativeModel('gemini-flash-latest')
        else:
            self.model = None

    def extract_problem_metadata_from_url(self, problem_url, difficulty_rating=None, progress_callback=None, user_samples=None):
        """
        Extract only problem metadata (title, constraints, samples) from URL using Gemini Flash

        This is optimized for cost savings - uses the cheapest Gemini model for simple extraction.

        Args:
            problem_url: URL to the problem page
            difficulty_rating: Optional difficulty rating (not used for Flash)
            progress_callback: Optional callback function to report progress
            user_samples: Optional user-provided sample test cases

        Returns:
            dict: {
                'title': str,
                'constraints': str,
                'samples': list of {'input': str, 'output': str},
                'platform': str,
                'problem_id': str,
                'tags': list (optional)
            }
        """
        if not self.model:
            raise ValueError('Gemini API key not configured')

        def update_progress(message):
            if progress_callback:
                progress_callback(message)

        try:
            # Fetch webpage content
            update_progress("Fetching webpage...")

            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            ]

            headers = {
                'User-Agent': random.choice(user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
            }

            time.sleep(random.uniform(3, 7))

            session = requests.Session()
            session.headers.update(headers)

            max_retries = 3
            response = None
            for attempt in range(max_retries):
                try:
                    response = session.get(problem_url, timeout=30, allow_redirects=True)
                    if response.status_code == 403:
                        if attempt < max_retries - 1:
                            time.sleep(random.uniform(5, 10) * (attempt + 1))
                            continue
                        else:
                            raise ValueError('Failed to fetch: 403 Forbidden')
                    response.raise_for_status()
                    break
                except requests.exceptions.RequestException as e:
                    if attempt < max_retries - 1:
                        time.sleep(random.uniform(3, 6) * (attempt + 1))
                        continue
                    else:
                        raise ValueError(f'Failed to fetch: {str(e)}')

            # Extract clean text from HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            update_progress("Extracting problem content...")
            problem_content = None
            extracted_tags = []

            # Codeforces: Extract problem statement div and tags
            if 'codeforces.com' in problem_url:
                problem_div = soup.find('div', class_='problem-statement')
                if problem_div:
                    problem_content = problem_div
                    logger.info("Found Codeforces problem-statement div")
                else:
                    logger.warning("Could not find problem-statement div, using full content")

                # Extract tags from tag-box class
                tag_elements = soup.find_all('span', class_='tag-box')
                if tag_elements:
                    for tag_elem in tag_elements:
                        tag_text = tag_elem.get_text(strip=True).lower()
                        # Remove special characters and asterisks
                        tag_text = tag_text.replace('*', '').strip()
                        if tag_text and tag_text not in extracted_tags:
                            extracted_tags.append(tag_text)
                    logger.info(f"Extracted {len(extracted_tags)} tags from Codeforces: {extracted_tags}")
                else:
                    logger.warning("Could not find tag-box elements on Codeforces page")

            # Baekjoon: Extract problem content and tags
            elif 'acmicpc.net' in problem_url:
                problem_div = soup.find('div', id='problem-body') or soup.find('div', id='problem_description')
                if problem_div:
                    problem_content = problem_div
                    logger.info("Found Baekjoon problem content div")
                else:
                    logger.warning("Could not find problem body div, using full content")

                # Extract tags from problem-tag or algorithm tags
                tag_section = soup.find('div', class_='problem-tag') or soup.find('section', id='problem_tags')
                if tag_section:
                    tag_links = tag_section.find_all('a')
                    for tag_link in tag_links:
                        tag_text = tag_link.get_text(strip=True).lower()
                        # Clean up Korean classification markers
                        tag_text = tag_text.replace('분류:', '').replace('알고리즘:', '').strip()
                        if tag_text and tag_text not in extracted_tags:
                            extracted_tags.append(tag_text)
                    logger.info(f"Extracted {len(extracted_tags)} tags from Baekjoon: {extracted_tags}")
                else:
                    logger.warning("Could not find tag section on Baekjoon page")

            if problem_content:
                soup = BeautifulSoup(str(problem_content), 'html.parser')

            for script in soup(["script", "style", "noscript"]):
                script.decompose()

            text = soup.get_text(separator=' ', strip=True)
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            webpage_content = '\n'.join(chunk for chunk in chunks if chunk)
            webpage_content = re.sub(r' +', ' ', webpage_content)

            # Remove LaTeX math delimiters
            webpage_content = re.sub(r'\$\$\$([^\$]+)\$\$\$', r'\1', webpage_content)

            if len(webpage_content) > 80000:
                webpage_content = webpage_content[:80000]

            logger.info(f"[Flash] Fetched webpage: {len(webpage_content)} chars")

            # System context optimized for Flash (simpler, more direct)
            system_context = """Extract problem metadata in JSON format. Be precise and concise.

Extract:
1. **Title**: Exact problem title
2. **Constraints**: Input format only (NOT output format)
   - First line format
   - Subsequent line formats
   - Variable ranges (e.g., 1 ≤ N ≤ 10^5)
3. **Sample Test Cases**: Extract ALL samples
   - Input/Output pairs
   - Preserve exact formatting (spaces, newlines)
   - Use \\n for newlines in JSON

Return ONLY valid JSON (no markdown):
{
    "title": "Problem Title",
    "constraints": "First line: integer N (1 ≤ N ≤ 10^5)...",
    "samples": [
        {"input": "3\\n1 2 3", "output": "6"}
    ]
}"""

            user_prompt = f"""Extract metadata from this problem page.

WEBPAGE CONTENT:
{webpage_content}

Return ONLY valid JSON."""

            update_progress("Extracting metadata with Gemini Flash...")

            # Use Flash model with low temperature for deterministic output
            response = self.model.generate_content(
                [system_context, user_prompt],
                generation_config=genai.GenerationConfig(
                    temperature=0.0,  # Deterministic
                    response_mime_type="application/json",
                    max_output_tokens=4096
                )
            )

            response_text = response.text.strip()
            logger.info(f"[Flash] Response: {len(response_text)} chars")

            # Parse JSON
            result = json.loads(response_text)

            # Validate required fields
            if not result.get('title') or result.get('title').strip() == '':
                raise ValueError('Missing title in extracted data')
            if not result.get('constraints'):
                result['constraints'] = 'No constraints provided'

            # Parse problem URL
            platform, problem_id = self._parse_problem_url(problem_url)
            result['platform'] = platform
            result['problem_id'] = problem_id

            # Add extracted tags
            if extracted_tags:
                result['tags'] = extracted_tags
            else:
                result['tags'] = []

            # If user provided samples, use them instead of extracted ones
            if user_samples:
                logger.info(f"[Flash] Using {len(user_samples)} user-provided samples instead of extracted samples")
                result['samples'] = user_samples

            logger.info(f"[Flash] Extracted: {result['title']}, {len(result.get('samples', []))} samples, {len(result.get('tags', []))} tags")
            return result

        except Exception as e:
            logger.error(f"[Flash] Error: {e}", exc_info=True)
            raise ValueError(f'Failed to extract metadata: {str(e)}')

    def _parse_problem_url(self, url):
        """Parse platform and problem_id from URL"""
        if 'codeforces.com' in url:
            match = re.search(r'/problem/(\d+)/([A-Z]\d*)', url)
            if match:
                return 'codeforces', f"{match.group(1)}{match.group(2)}"
        elif 'acmicpc.net' in url or 'baekjoon' in url:
            match = re.search(r'/problem/(\d+)', url)
            if match:
                return 'baekjoon', match.group(1)

        return 'unknown', 'unknown'
