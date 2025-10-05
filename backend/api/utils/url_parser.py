"""URL parsing utilities for extracting problem information"""
import re
from urllib.parse import urlparse
from typing import Optional, Tuple


class ProblemURLParser:
    """Parse problem URLs to extract platform and problem_id"""

    @staticmethod
    def parse_url(url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse problem URL and extract platform and problem_id

        Args:
            url: Full URL to the problem

        Returns:
            Tuple of (platform, problem_id) or (None, None) if parsing fails

        Supported formats:
            - Baekjoon: https://www.acmicpc.net/problem/{number}
            - Codeforces: https://codeforces.com/problemset/problem/{contest}/{letter}
        """
        if not url:
            return None, None

        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            path = parsed.path

            # Baekjoon (acmicpc.net)
            if 'acmicpc.net' in domain:
                match = re.search(r'/problem/(\d+)', path)
                if match:
                    return 'baekjoon', match.group(1)

            # Codeforces
            elif 'codeforces.com' in domain:
                # Format: /problemset/problem/{contest}/{letter}
                match = re.search(r'/problemset/problem/(\d+)/([A-Z]\d?)', path, re.IGNORECASE)
                if match:
                    contest = match.group(1)
                    letter = match.group(2).upper()
                    return 'codeforces', f"{contest}{letter}"

                # Alternative format: /contest/{contest}/problem/{letter}
                match = re.search(r'/contest/(\d+)/problem/([A-Z]\d?)', path, re.IGNORECASE)
                if match:
                    contest = match.group(1)
                    letter = match.group(2).upper()
                    return 'codeforces', f"{contest}{letter}"

            return None, None

        except Exception:
            return None, None

    @staticmethod
    def validate_url_format(url: str) -> bool:
        """
        Validate if URL is in a supported format

        Args:
            url: URL to validate

        Returns:
            True if URL is valid and supported, False otherwise
        """
        platform, problem_id = ProblemURLParser.parse_url(url)
        return platform is not None and problem_id is not None
