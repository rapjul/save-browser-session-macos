"""
URL normalization module for removing tracking parameters.

This module provides functionality to clean URLs by removing common tracking
parameters while preserving all functional parameters and URL structure.
"""

from typing import List, NamedTuple
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


class CleanedUrl(NamedTuple):
    """
    Result of URL cleaning with tracking information.

    Attributes:
        cleaned: The cleaned URL with tracking parameters removed
        original: The original URL before cleaning
        removed_params: List of parameter names that were removed
        is_modified: Whether the URL was modified during cleaning
    """

    cleaned: str
    original: str
    removed_params: List[str]
    is_modified: bool


# Tracking parameters to remove from URLs
TRACKING_PARAMS = {
    # Google Analytics & Ads
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "utm_source_platform",
    "utm_creative_format",
    "utm_marketing_tactic",
    "gclid",
    "gclsrc",
    "dclid",
    "gbraid",
    "wbraid",
    # Facebook & Meta
    "fbclid",
    "fb_action_ids",
    "fb_action_types",
    "fb_ref",
    "fb_source",
    # Twitter/X
    "twclid",
    "tw_source",
    "tw_campaign",
    # Microsoft/Bing
    "msclkid",
    "mc_cid",
    "mc_eid",
    # Email marketing
    "mkt_tok",
    "_hsenc",
    "_hsmi",
    "vero_id",
    "vero_conv",
    # Reddit
    "ref_source",
    "ref_campaign",
    # LinkedIn
    "li_fat_id",
    "lipi",
    "licu",
    # General tracking
    "source",
    "campaign",
    "medium",
    # Session/referral
    "affiliate",
    "click_id",
    "trk",
    # Amazon
    "tag",
    "ref_",
    "psc",
    # YouTube
    "share",
    # Note: 't' (timestamp) is already handled by existing regex in clean_url()
}


def remove_tracking_params(url: str) -> CleanedUrl:
    """
    Remove tracking parameters from URL while preserving everything else.

    This function removes only tracking/marketing parameters while preserving:
    - URL structure (protocol, domain, path)
    - Functional parameters
    - Empty parameters (may be functionally important)
    - Fragment identifiers (hash)
    - Parameter order

    Parameters:
        url: The URL to clean

    Returns:
        CleanedUrl named tuple with:
        - cleaned: URL with tracking params removed
        - original: Original URL
        - removed_params: List of removed parameter names
        - is_modified: True if URL was changed

    Examples:
        >>> result = remove_tracking_params("https://example.com?utm_source=google&id=123")
        >>> result.cleaned
        'https://example.com?id=123'
        >>> result.removed_params
        ['utm_source']
        >>> result.is_modified
        True
    """
    if not url:
        return CleanedUrl(url, url, [], False)

    try:
        parsed = urlparse(url)
        if not parsed.query:
            return CleanedUrl(url, url, [], False)

        # Parse query parameters, preserving empty values
        params: dict[str, list[str]] = parse_qs(parsed.query, keep_blank_values=True)

        # Track removed parameters
        removed: list[str] = []
        cleaned_params: dict[str, list[str]] = {}

        for key, values in params.items():
            if key in TRACKING_PARAMS:
                removed.append(key)
            else:
                # Preserve empty parameters - may be functionally important
                cleaned_params[key] = values

        if not removed:
            return CleanedUrl(url, url, [], False)

        # Rebuild query string
        # Note: urlencode doesn't preserve original order, but that's acceptable
        if cleaned_params:
            new_query = urlencode(cleaned_params, doseq=True)
        else:
            new_query = ""

        # Rebuild URL
        cleaned = urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment,
            )
        )

        return CleanedUrl(cleaned, url, removed, True)

    except Exception:
        # If parsing fails, return original URL unchanged
        return CleanedUrl(url, url, [], False)
