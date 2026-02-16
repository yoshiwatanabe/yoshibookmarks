"""Content analyzer for webpage fetching and basic parsing (Phase 1 MVP - no OpenAI)."""

import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from ..utils.url_utils import (
    URLValidationError,
    extract_domain_name,
    is_valid_keyword,
    validate_url_scheme,
)

logger = logging.getLogger(__name__)


class ContentAnalysisError(Exception):
    """Content analysis error."""

    pass


class TimeoutError(ContentAnalysisError):
    """Request timeout error."""

    pass


class NetworkError(ContentAnalysisError):
    """Network connection error."""

    pass


class ContentAnalyzer:
    """Analyzes webpage content for title, keywords, and favicon (without OpenAI)."""

    def __init__(self, timeout: int = 10):
        """Initialize content analyzer.

        Args:
            timeout: HTTP request timeout in seconds (default: 10)
        """
        self.timeout = timeout
        self.max_response_size = 10 * 1024 * 1024  # 10MB
        self.max_favicon_size = 1024 * 1024  # 1MB

    async def analyze_url(self, url: str) -> Dict[str, any]:
        """Fetch URL and analyze content for title and keywords.

        Args:
            url: URL to analyze

        Returns:
            Dictionary with title, keywords, and optional error

        Example:
            {
                "title": "Example Site",
                "keywords": ["example", "demo", "site"],
                "error": None
            }
        """
        # Validate URL scheme
        try:
            validate_url_scheme(url)
        except URLValidationError as e:
            logger.error(f"Invalid URL scheme for {url}: {e}")
            return {
                "title": extract_domain_name(url),
                "keywords": self.extract_keywords_from_url(url),
                "error": str(e),
            }

        # Fetch webpage content
        try:
            html_content = await self.fetch_url(url)
        except (TimeoutError, NetworkError, ContentAnalysisError) as e:
            logger.warning(f"Failed to fetch {url}: {e}")
            return {
                "title": extract_domain_name(url),
                "keywords": self.extract_keywords_from_url(url),
                "error": str(e),
            }

        # Parse HTML
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
        except Exception as e:
            logger.warning(f"Failed to parse HTML from {url}: {e}")
            return {
                "title": extract_domain_name(url),
                "keywords": self.extract_keywords_from_url(url),
                "error": f"HTML parsing failed: {e}",
            }

        # Extract title
        title = self._extract_title(soup, url)

        # Extract keywords from URL
        url_keywords = self.extract_keywords_from_url(url)

        return {
            "title": title,
            "keywords": url_keywords,
            "error": None,
        }

    async def fetch_url(self, url: str) -> str:
        """Fetch URL content with timeout and validation.

        Args:
            url: URL to fetch

        Returns:
            HTML content as string

        Raises:
            TimeoutError: If request times out
            NetworkError: If connection fails
            ContentAnalysisError: If response is invalid
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(url)

                # Check HTTP status
                if response.status_code == 404:
                    raise ContentAnalysisError(f"Page not found (404): {url}")
                elif response.status_code >= 500:
                    raise ContentAnalysisError(f"Server error ({response.status_code}): {url}")
                elif response.status_code >= 400:
                    raise ContentAnalysisError(f"Client error ({response.status_code}): {url}")

                response.raise_for_status()

                # Check content type
                content_type = response.headers.get("content-type", "").lower()
                if "text/html" not in content_type and "text/plain" not in content_type:
                    logger.warning(f"Non-HTML content-type for {url}: {content_type}")

                # Check response size
                content_length = len(response.content)
                if content_length > self.max_response_size:
                    raise ContentAnalysisError(
                        f"Response too large: {content_length} bytes (max {self.max_response_size})"
                    )

                return response.text

        except httpx.TimeoutException as e:
            raise TimeoutError(f"Request timed out after {self.timeout}s: {url}") from e
        except httpx.NetworkError as e:
            raise NetworkError(f"Network error: {e}") from e
        except httpx.HTTPStatusError as e:
            raise ContentAnalysisError(f"HTTP error {e.response.status_code}: {url}") from e
        except Exception as e:
            raise ContentAnalysisError(f"Failed to fetch URL: {e}") from e

    def _extract_title(self, soup: BeautifulSoup, url: str) -> str:
        """Extract title from HTML or use domain name as fallback.

        Args:
            soup: BeautifulSoup parsed HTML
            url: Original URL (for fallback)

        Returns:
            Page title or domain name
        """
        # Try <title> tag
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
            if title:
                return title

        # Try og:title meta tag
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = og_title["content"].strip()
            if title:
                return title

        # Try first <h1> tag
        h1 = soup.find("h1")
        if h1 and h1.string:
            title = h1.string.strip()
            if title:
                return title

        # Fallback to domain name
        return extract_domain_name(url)

    def extract_keywords_from_url(self, url: str) -> List[str]:
        """Extract keywords from URL path segments.

        Args:
            url: URL to extract keywords from

        Returns:
            List of keywords (max 4)

        Example:
            "https://github.com/python/cpython" -> ["github", "python", "cpython"]
        """
        parsed = urlparse(url)

        # Get domain keyword
        domain_parts = parsed.netloc.split(".")
        if domain_parts[0] == "www" and len(domain_parts) > 1:
            domain_keyword = domain_parts[1]
        else:
            domain_keyword = domain_parts[0]

        # Get path segments
        path_segments = [
            seg for seg in parsed.path.split("/")
            if seg and seg not in ["index.html", "index.htm", "default.html"]
        ]

        # Combine and clean
        keywords = [domain_keyword] + path_segments[:3]

        # Clean and validate
        cleaned_keywords = []
        for keyword in keywords:
            # Remove file extensions
            keyword = keyword.rsplit(".", 1)[0]

            # Convert to lowercase
            keyword = keyword.lower()

            # Replace special chars with nothing
            keyword = keyword.replace("_", "").replace("-", "")

            # Validate
            if is_valid_keyword(keyword):
                cleaned_keywords.append(keyword)

        # Limit to 4 keywords
        return cleaned_keywords[:4]

    async def download_favicon(self, url: str, storage_path: Path) -> Optional[str]:
        """Download favicon for URL.

        Args:
            url: URL to download favicon from
            storage_path: Storage location path

        Returns:
            Relative path to saved favicon, or None if failed

        Example:
            "favicons/example.com.ico"
        """
        parsed = urlparse(url)
        domain = parsed.netloc

        # Common favicon URLs to try
        favicon_urls = [
            f"{parsed.scheme}://{domain}/favicon.ico",
            f"{parsed.scheme}://{domain}/favicon.png",
            f"{parsed.scheme}://{domain}/apple-touch-icon.png",
        ]

        for favicon_url in favicon_urls:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(favicon_url)

                    if response.status_code != 200:
                        continue

                    # Check size
                    if len(response.content) > self.max_favicon_size:
                        logger.warning(
                            f"Favicon too large: {len(response.content)} bytes (max {self.max_favicon_size})"
                        )
                        continue

                    # Save favicon
                    favicon_filename = f"{domain}.ico"
                    favicon_path = storage_path / "favicons" / favicon_filename
                    favicon_path.parent.mkdir(parents=True, exist_ok=True)

                    await asyncio.to_thread(favicon_path.write_bytes, response.content)

                    logger.info(f"Downloaded favicon for {domain}")

                    return f"favicons/{favicon_filename}"

            except Exception as e:
                logger.debug(f"Failed to download favicon from {favicon_url}: {e}")
                continue

        logger.info(f"No favicon found for {domain}")
        return None
