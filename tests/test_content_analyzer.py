"""Tests for ContentAnalyzer and URL utilities."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from yoshibookmark.core.content_analyzer import (
    ContentAnalysisError,
    ContentAnalyzer,
    NetworkError,
    TimeoutError,
)
from yoshibookmark.utils.url_utils import (
    URLValidationError,
    extract_domain_name,
    is_valid_keyword,
    validate_url_scheme,
)


class TestURLUtils:
    """Test URL utility functions."""

    def test_validate_url_scheme_http(self):
        """Test valid HTTP URL."""
        validate_url_scheme("http://example.com")  # Should not raise

    def test_validate_url_scheme_https(self):
        """Test valid HTTPS URL."""
        validate_url_scheme("https://example.com")  # Should not raise

    def test_validate_url_scheme_missing(self):
        """Test URL without scheme is rejected."""
        with pytest.raises(URLValidationError, match="missing scheme"):
            validate_url_scheme("example.com")

    def test_validate_url_scheme_invalid(self):
        """Test invalid URL schemes are rejected."""
        with pytest.raises(URLValidationError, match="not allowed"):
            validate_url_scheme("file:///etc/passwd")

        with pytest.raises(URLValidationError, match="not allowed"):
            validate_url_scheme("javascript:alert(1)")

        with pytest.raises(URLValidationError, match="not allowed"):
            validate_url_scheme("ftp://example.com")

    def test_extract_domain_name(self):
        """Test extracting domain name from URL."""
        assert extract_domain_name("https://github.com/user/repo") == "Github"
        assert extract_domain_name("https://www.example.com") == "Example"
        assert extract_domain_name("http://stackoverflow.com/questions") == "Stackoverflow"

    def test_is_valid_keyword(self):
        """Test keyword validation."""
        assert is_valid_keyword("python") is True
        assert is_valid_keyword("web-dev") is True
        assert is_valid_keyword("test_123") is True

        # Too short
        assert is_valid_keyword("a") is False

        # Invalid characters
        assert is_valid_keyword("hello world") is False
        assert is_valid_keyword("test@example") is False


class TestContentAnalyzer:
    """Test ContentAnalyzer functionality."""

    @pytest.mark.asyncio
    async def test_analyze_valid_html_page(self):
        """Test analyzing a valid HTML page."""
        html_content = """
        <html>
            <head><title>Test Page Title</title></head>
            <body><h1>Test Page</h1></body>
        </html>
        """

        analyzer = ContentAnalyzer()

        with patch.object(analyzer, 'fetch_url', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = html_content

            result = await analyzer.analyze_url("https://example.com/test/page")

            assert result["title"] == "Test Page Title"
            assert "example" in result["keywords"]
            assert result["error"] is None

    @pytest.mark.asyncio
    async def test_analyze_page_without_title(self):
        """Test analyzing page without title tag."""
        html_content = "<html><body>No title</body></html>"

        analyzer = ContentAnalyzer()

        with patch.object(analyzer, 'fetch_url', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = html_content

            result = await analyzer.analyze_url("https://github.com/user/repo")

            # Should use domain name as fallback
            assert result["title"] == "Github"

    @pytest.mark.asyncio
    async def test_analyze_page_with_og_title(self):
        """Test extracting title from og:title meta tag."""
        html_content = """
        <html>
            <head>
                <meta property="og:title" content="Open Graph Title" />
            </head>
            <body></body>
        </html>
        """

        analyzer = ContentAnalyzer()

        with patch.object(analyzer, 'fetch_url', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = html_content

            result = await analyzer.analyze_url("https://example.com")

            assert result["title"] == "Open Graph Title"

    @pytest.mark.asyncio
    async def test_extract_keywords_from_url(self):
        """Test keyword extraction from URL paths."""
        analyzer = ContentAnalyzer()

        keywords = analyzer.extract_keywords_from_url("https://github.com/python/cpython")
        assert "github" in keywords
        assert "python" in keywords
        assert "cpython" in keywords

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test handling of request timeout."""
        analyzer = ContentAnalyzer(timeout=1)

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.TimeoutException("Timeout")

            result = await analyzer.analyze_url("https://slow-site.com")

            assert "Timeout" in result["error"] or "timed out" in result["error"].lower()
            assert result["title"] == "Slow-site"  # Fallback to domain

    @pytest.mark.asyncio
    async def test_http_404_error(self):
        """Test handling of HTTP 404 error."""
        analyzer = ContentAnalyzer()

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404", request=MagicMock(), response=mock_response
        )

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await analyzer.analyze_url("https://example.com/notfound")

            assert result["error"] is not None
            assert "404" in result["error"]

    @pytest.mark.asyncio
    async def test_http_500_error(self):
        """Test handling of HTTP 500 error."""
        analyzer = ContentAnalyzer()

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=mock_response
        )

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await analyzer.analyze_url("https://example.com")

            assert result["error"] is not None
            assert "500" in result["error"]

    @pytest.mark.asyncio
    async def test_network_error_handling(self):
        """Test handling of network connection error."""
        analyzer = ContentAnalyzer()

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.NetworkError("Connection failed")

            result = await analyzer.analyze_url("https://unreachable.com")

            assert result["error"] is not None
            assert "Network" in result["error"] or "Connection" in result["error"]

    @pytest.mark.asyncio
    async def test_malformed_html_parsing(self):
        """Test handling of malformed HTML."""
        malformed_html = "<html><head><title>Test</title><body>Missing closing tags"

        analyzer = ContentAnalyzer()

        with patch.object(analyzer, 'fetch_url', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = malformed_html

            # Should parse what's possible
            result = await analyzer.analyze_url("https://example.com")

            assert result["title"] == "Test"
            assert result["error"] is None  # BeautifulSoup handles malformed HTML

    @pytest.mark.asyncio
    async def test_invalid_url_scheme(self):
        """Test rejection of invalid URL schemes."""
        analyzer = ContentAnalyzer()

        result = await analyzer.analyze_url("file:///etc/passwd")

        assert result["error"] is not None
        assert "not allowed" in result["error"]

    @pytest.mark.asyncio
    async def test_too_large_response(self):
        """Test handling of too large response."""
        analyzer = ContentAnalyzer()
        analyzer.max_response_size = 100  # Set low limit for testing

        large_content = "x" * 1000
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = large_content.encode()
        mock_response.headers = {"content-type": "text/html"}
        mock_response.text = large_content

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            result = await analyzer.analyze_url("https://example.com")

            assert result["error"] is not None
            assert "too large" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_non_html_content_type(self):
        """Test handling of non-HTML content type."""
        analyzer = ContentAnalyzer()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.content = b'{"test": "data"}'
        mock_response.text = '{"test": "data"}'

        with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response

            # Should still process but may warn
            result = await analyzer.analyze_url("https://api.example.com")

            # Should return domain as title since no HTML structure
            assert result["title"] is not None

    @pytest.mark.asyncio
    async def test_download_favicon_success(self):
        """Test successful favicon download."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir)

            analyzer = ContentAnalyzer()

            fake_favicon = b'\x00\x00\x01\x00'  # Fake ICO data
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = fake_favicon

            with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_response

                result = await analyzer.download_favicon("https://example.com", storage_path)

                assert result is not None
                assert "favicons/example.com.ico" == result

                # Check file was created
                favicon_path = storage_path / result
                assert favicon_path.exists()

    @pytest.mark.asyncio
    async def test_download_favicon_not_found(self):
        """Test favicon download when not found."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir)

            analyzer = ContentAnalyzer()

            mock_response = MagicMock()
            mock_response.status_code = 404

            with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_response

                result = await analyzer.download_favicon("https://example.com", storage_path)

                assert result is None

    @pytest.mark.asyncio
    async def test_download_favicon_too_large(self):
        """Test favicon download rejects files that are too large."""
        with tempfile.TemporaryDirectory() as temp_dir:
            storage_path = Path(temp_dir)

            analyzer = ContentAnalyzer()

            # Create favicon larger than 1MB
            large_favicon = b'x' * (2 * 1024 * 1024)
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = large_favicon

            with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = mock_response

                result = await analyzer.download_favicon("https://example.com", storage_path)

                # Should skip large favicon
                assert result is None
