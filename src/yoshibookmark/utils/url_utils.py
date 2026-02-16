"""URL validation and parsing utilities."""

import re
from urllib.parse import urlparse
from typing import Optional


class URLValidationError(Exception):
    """URL validation error."""

    pass


def validate_url_scheme(url: str) -> None:
    """Validate URL has allowed scheme (http/https only).

    Args:
        url: URL to validate

    Raises:
        URLValidationError: If URL scheme is not allowed
    """
    parsed = urlparse(url)

    if not parsed.scheme:
        raise URLValidationError("URL missing scheme (http:// or https://)")

    if parsed.scheme not in ["http", "https"]:
        raise URLValidationError(
            f"URL scheme '{parsed.scheme}' not allowed. Only http:// and https:// are permitted."
        )


def extract_domain_name(url: str) -> str:
    """Extract domain name from URL for use as fallback title.

    Args:
        url: URL to extract domain from

    Returns:
        Domain name without TLD

    Example:
        "https://github.com/user/repo" -> "GitHub"
    """
    parsed = urlparse(url)
    domain = parsed.netloc

    # Remove www. prefix
    if domain.startswith("www."):
        domain = domain[4:]

    # Remove TLD
    parts = domain.split(".")
    if len(parts) > 1:
        domain_name = parts[0]
    else:
        domain_name = domain

    # Capitalize
    return domain_name.capitalize()


def is_valid_keyword(keyword: str) -> bool:
    """Check if a keyword is valid.

    Args:
        keyword: Keyword to validate

    Returns:
        True if valid, False otherwise

    Valid keywords:
    - At least 2 characters
    - Alphanumeric (letters, numbers, hyphens, underscores)
    """
    if len(keyword) < 2:
        return False

    # Allow alphanumeric, hyphens, underscores
    return bool(re.match(r'^[a-zA-Z0-9_-]+$', keyword))
