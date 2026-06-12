"""Tests for URL tracking parameter removal."""

from save_browser_session.url_normalizer import CleanedUrl, remove_tracking_params


def test_tracking_param_removal() -> None:
    """Test that common tracking parameters are removed."""
    result = remove_tracking_params("https://example.com/page?utm_source=google&id=123")

    assert result.cleaned == "https://example.com/page?id=123"
    assert "utm_source" in result.removed_params
    assert result.is_modified
    assert result.original == "https://example.com/page?utm_source=google&id=123"


def test_youtube_share_param() -> None:
    """Test YouTube share parameter, si, and t are removed."""
    result = remove_tracking_params(
        "https://youtube.com/watch?v=abc123&share=xyz&si=tracking_id&t=1m20s"
    )

    assert "share=" not in result.cleaned
    assert "si=" not in result.cleaned
    assert "t=" not in result.cleaned
    assert "v=abc123" in result.cleaned
    assert "share" in result.removed_params
    assert "si" in result.removed_params
    assert "t" in result.removed_params
    assert result.is_modified


def test_empty_params_preserved() -> None:
    """Test empty parameters are preserved (may be functionally important)."""
    result = remove_tracking_params("https://example.com/search?q=&category=books")

    assert "q=" in result.cleaned
    assert "category=books" in result.cleaned
    assert result.is_modified is False  # No tracking params removed


def test_no_tracking_params() -> None:
    """Test URL without tracking params is unchanged."""
    url = "https://example.com/page?id=123&sort=date"
    result = remove_tracking_params(url)

    assert result.cleaned == url
    assert result.original == url
    assert result.removed_params == []
    assert result.is_modified is False


def test_multiple_tracking_params() -> None:
    """Test removal of multiple tracking parameters."""
    url = "https://example.com?utm_source=email&utm_campaign=spring&fbclid=xyz&id=123"
    result = remove_tracking_params(url)

    assert result.cleaned == "https://example.com?id=123"
    assert "utm_source" in result.removed_params
    assert "utm_campaign" in result.removed_params
    assert "fbclid" in result.removed_params
    assert len(result.removed_params) == 3
    assert result.is_modified


def test_no_query_string() -> None:
    """Test URL without query string is unchanged."""
    url = "https://example.com/page"
    result = remove_tracking_params(url)

    assert result.cleaned == url
    assert result.is_modified is False


def test_only_tracking_params() -> None:
    """Test URL with only tracking params results in no query string."""
    url = "https://example.com/page?utm_source=google&fbclid=123"
    result = remove_tracking_params(url)

    assert result.cleaned == "https://example.com/page"
    assert result.is_modified


def test_fragment_preserved() -> None:
    """Test URL fragment (hash) is preserved."""
    url = "https://example.com/page?utm_source=google&id=123#section"
    result = remove_tracking_params(url)

    assert result.cleaned == "https://example.com/page?id=123#section"
    assert "#section" in result.cleaned
    assert result.is_modified


def test_empty_url() -> None:
    """Test empty URL is handled gracefully."""
    result = remove_tracking_params("")

    assert result.cleaned == ""
    assert result.is_modified is False


def test_malformed_url() -> None:
    """Test malformed URL returns original."""
    url = "not a valid url"
    result = remove_tracking_params(url)

    # Should return original if parsing fails
    assert result.cleaned == url
    assert result.is_modified is False


def test_named_tuple_access() -> None:
    """Test CleanedUrl NamedTuple provides easy attribute access."""
    result = remove_tracking_params("https://example.com?utm_source=test&id=1")

    # Test attribute access
    assert hasattr(result, "cleaned")
    assert hasattr(result, "original")
    assert hasattr(result, "removed_params")
    assert hasattr(result, "is_modified")

    # Test it's a NamedTuple
    assert isinstance(result, CleanedUrl)
    assert isinstance(result, tuple)
