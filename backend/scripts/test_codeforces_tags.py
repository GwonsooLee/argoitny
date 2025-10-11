"""
Test script to verify Codeforces tag extraction
"""
import cloudscraper
from bs4 import BeautifulSoup
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_tag_extraction(url):
    """Test tag extraction from Codeforces URL"""

    logger.info(f"Testing URL: {url}")

    # Fetch the page with headers to avoid 403
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    }

    # Use cloudscraper to bypass Cloudflare
    scraper = cloudscraper.create_scraper()
    scraper.headers.update(headers)

    try:
        response = scraper.get(url, timeout=30)
        response.raise_for_status()
        logger.info(f"Successfully fetched page, status: {response.status_code}")
        logger.info(f"Response encoding: {response.encoding}")
        logger.info(f"Content-Type header: {response.headers.get('content-type')}")
        logger.info(f"Content-Encoding header: {response.headers.get('content-encoding')}")

        # Check if response needs decompression
        content_encoding = response.headers.get('content-encoding', '').lower()
        if content_encoding == 'br' or response.text.startswith('\x1f\x8b'):
            logger.warning(f"Response is compressed ({content_encoding})! Attempting manual decompression...")
            try:
                if content_encoding == 'br':
                    import brotli
                    html_content = brotli.decompress(response.content).decode('utf-8')
                else:
                    import gzip
                    html_content = gzip.decompress(response.content).decode('utf-8')
            except Exception as decomp_error:
                logger.error(f"Decompression failed: {decomp_error}")
                html_content = response.text
        else:
            html_content = response.text

        logger.info(f"HTML content length: {len(html_content)}")
        logger.info(f"First 200 chars: {html_content[:200]}")
    except Exception as e:
        logger.error(f"Failed to fetch page: {e}")
        return

    # Parse HTML
    soup = BeautifulSoup(html_content, 'html.parser')

    # Method 1: Look for tag-box class (current implementation)
    logger.info("\n=== Method 1: Looking for span.tag-box ===")
    tag_elements = soup.find_all('span', class_='tag-box')
    if tag_elements:
        logger.info(f"Found {len(tag_elements)} tag-box elements:")
        for idx, tag_elem in enumerate(tag_elements, 1):
            tag_text = tag_elem.get_text(strip=True)
            logger.info(f"  {idx}. {tag_text}")
    else:
        logger.warning("No tag-box elements found!")

    # Method 2: Look for any tags-related elements
    logger.info("\n=== Method 2: Looking for any tag-related elements ===")

    # Check for problem-tags section
    problem_tags = soup.find_all(class_=lambda x: x and 'tag' in x.lower())
    if problem_tags:
        logger.info(f"Found {len(problem_tags)} elements with 'tag' in class:")
        for elem in problem_tags[:10]:  # Limit to first 10
            logger.info(f"  - Class: {elem.get('class')}, Text: {elem.get_text(strip=True)[:50]}")

    # Check for specific tag patterns
    all_spans = soup.find_all('span')
    tag_spans = [s for s in all_spans if 'tag' in str(s.get('class', '')).lower()]
    if tag_spans:
        logger.info(f"\nFound {len(tag_spans)} span elements with 'tag' in class:")
        for span in tag_spans[:10]:
            logger.info(f"  - {span.get('class')}: {span.get_text(strip=True)[:50]}")

    # Method 3: Look for sidebar or tags section
    logger.info("\n=== Method 3: Looking for sidebar/tags section ===")
    sidebar = soup.find('div', class_='roundbox')
    if sidebar:
        logger.info("Found roundbox div, checking for tags...")
        tags_in_sidebar = sidebar.find_all('a', href=lambda x: x and '/problemset/problem' in x)
        if tags_in_sidebar:
            logger.info(f"Found {len(tags_in_sidebar)} tag links in sidebar")

    # Save HTML snippet for analysis
    with open('/tmp/codeforces_page.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    logger.info("Saved full HTML to /tmp/codeforces_page.html")

    # Look for any element containing the word "tags"
    logger.info("\n=== Method 4: Searching for 'tags' text ===")
    tags_text = soup.find_all(string=lambda text: text and 'tag' in text.lower())
    if tags_text:
        logger.info(f"Found {len(tags_text)} elements containing 'tag' text:")
        for idx, text in enumerate(tags_text[:5], 1):
            parent = text.parent
            logger.info(f"  {idx}. Parent: {parent.name}, Class: {parent.get('class')}, Text: {text.strip()[:100]}")

if __name__ == "__main__":
    test_url = "https://codeforces.com/contest/1037/problem/D"
    test_tag_extraction(test_url)
