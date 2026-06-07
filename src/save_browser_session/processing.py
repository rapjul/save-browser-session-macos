import re


def clean_url(url: str, remove_tracking: bool = True) -> str:
    """
    Cleans a URL by encoding parentheses, removing specific trailing query
    parameters, and optionally removing tracking parameters.

    Parameters:
        url: The URL to clean
        remove_tracking: Whether to remove tracking parameters (default: True)

    Returns:
        Cleaned URL string
    """
    if not url:
        return ""

    # Remove specific zero-width characters
    url = re.sub(r"[\u202A\u202C]", "", url)

    # Existing logic: encode parentheses
    url = url.replace("(", "%28").replace(")", "%29")

    # Remove &t=XmYs or &t=Xs at the end
    url = re.sub(r"&t=(\d+m)?(\d+s)$", "", url)

    # Remove ?tab=readme-ov-file at the end
    url = re.sub(r"\?tab=readme-ov-file$", "", url)

    # NEW: Remove tracking parameters if enabled
    if remove_tracking:
        from .url_normalizer import remove_tracking_params

        result = remove_tracking_params(url)
        return result.cleaned

    return url


def clean_title(title: str) -> str:
    """
    Cleans and formats a title string by applying various text transformations.
    """
    if not title:
        return ""

    # Remove trailing newlines and replace internal newlines
    title = re.sub(r"\n$", "", title)
    title = title.replace("\n", " ")

    # Remove numbered prefixes like "(123) " or "(123+) " or "(12 34+) "
    title = re.sub(r"^\([\d]{1,6}\+?\) ", "", title)
    title = re.sub(r"^\([\d\s]{1,8}\+?\) ", "", title)

    # Escape brackets for Markdown - DISABLED matching JXA v2
    # title = re.sub(r"(\[|\])", r"\\\1", title)

    # Format Twitter/X
    title = re.sub(r"(on (?:Twitter|X))\:", r"\1 –", title)
    title = title.replace(" / X", "")

    # Normalize whitespace
    title = re.sub(r"\s{2,8}\"", '"', title)
    title = re.sub(r"^([\s]+)", "", title)
    title = re.sub(r"([\s]{2,6})", " ", title)
    title = re.sub(r"([\s]+)$", "", title)

    # Remove trailing period if preceded by optional space?
    # Original: .replace(/(\s?)\.$/, "") -> removes " ." or "." at end
    title = re.sub(r"(\s?)\.$", "", title)

    # Remove invisible/zero-width characters
    title = title.replace("\u200e", "")  # Left-to-right mark
    title = title.replace("\u200f", "")  # Right-to-left mark
    title = title.replace("\u202a", "")  # Left-to-right embedding
    title = title.replace("\u202c", "")  # Right-to-left embedding
    title = title.replace("\u202b", "")  # Pop directional formatting
    title = title.replace("\u202d", "")  # Left-to-right override
    title = title.replace("\u202e", "")  # Right-to-left override
    title = title.replace("\u202f", "")  # Narrow no-break space
    title = title.replace("\u200b", "")  # Zero-width space
    title = title.replace("\u2060", "")  # Word joiner
    title = title.replace("\u2061", "")  # Function application
    title = title.replace("\u2062", "")  # Invisible times
    title = title.replace("\u2063", "")  # Invisible separator
    title = title.replace("\u2064", "")  # Invisible plus
    title = title.replace("\u2065", "")  # Left-to-right isolate
    title = title.replace("\u2066", "")  # Right-to-left isolate
    title = title.replace("\u2067", "")  # First strong isolate
    title = title.replace("\u2068", "")  # Last strong isolate
    title = title.replace("\u2069", "")  # Pop directional formatting
    title = title.replace("\u200c", "")  # Zero-width non-joiner

    # Remove specific query param from title if present (original updated this too?)
    title = title.replace("?tab=readme-ov-file", "")

    # Previously commented out rules in JXA preserved here as comments
    # title = re.sub(r"^\#", "\\#", title)
    # title = re.sub(r"\s?https:\/\/(?:[^\"]*)(\")?", r"\1", title)
    # title = title.replace(" / Twitter", "")
    # title = re.sub(r"<", "\\<", title)
    # title = re.sub(r">", "\\>", title)
    # title = re.sub(r"\(", "\\(", title)
    # title = re.sub(r"\)", "\\)", title)

    # Re-apply explicit HTML entity encoding for brackets if the slash escape isn't desired
    # The original JXA had .replace(/\[/g, "&#91;").replace(/\]/g, "&#93;") at the very end
    # AFTER the slash escape? No, let's check the order in JXA.
    # JXA v2:
    # .replace(/\[/g, "&#91;")
    # .replace(/\]/g, "&#93;")
    # It does NOT use slash escape in the final active block of v2.

    # Let's revert the slash escape and use HTML entities to match v2 exactly
    # Undo the separateslash escape above if we want exact v2 behavior.

    # Re-implementing correctly based on v2 JXA:
    # Remove the slash escape I added above: title = re.sub(r"(\[|\])", r"\\\1", title)

    return title.strip()


def is_broken_tab(title: str, url: str) -> bool:
    """
    Checks if a tab is considered 'broken' or loading/empty.

    Uses different matching strategies for different patterns:
    - Exact match: For generic words that are broken when standalone
    - Prefix match: For loading/error states that may have additional text
    - Substring match: For checking if certain patterns appear anywhere in title
    """
    # Tabs that should_skip considers valid (e.g. Start Page at favorites://) are
    # intentional empty/default tabs, not broken ones — exclude them early.
    if should_skip(title, url):
        return False

    # If no URL...
    if not url:
        # ... but has title -> BROKEN given it has no URL
        if title and title.strip():
            return True
        # ... and no title -> VALID (Empty Tab / Start Page)
        return False

    # If URL is present, proceed with existing checks

    # Exclude known-valid URL patterns that should never be flagged as broken
    excluded_url_patterns = [
        "raw.githubusercontent.com",
    ]
    if any(pattern in url for pattern in excluded_url_patterns):
        return False

    # If no title or title equals URL, check if it's a file before marking broken
    if not title or not title.strip() or title == url:
        # Check if it looks like a file (common to have title=url)
        # We check the path part of the URL to avoid query params messing it up
        from urllib.parse import urlparse

        try:
            path = urlparse(url).path.lower()
            file_extensions = (
                ".pdf",
                ".png",
                ".jpg",
                ".jpeg",
                ".gif",
                ".webp",
                ".svg",
                ".txt",
                ".md",
                ".markdown",
                ".json",
                ".xml",
                ".yaml",
                ".yml",
                ".py",
                ".sh",
                ".csv",
                ".vtt",
                ".srt",
                ".mp3",
                ".opus",
                ".aac",
                ".m4a",
                ".m4b",
                ".m4v",
                ".mp4",
                ".webm",
                ".ts",
                ".m3u8",
                ".m3u",
            )
            if path.endswith(file_extensions):
                return False
        except Exception:
            pass

        # If no title but has a URL (and not a file), it's likely a broken/loading tab
        if url:
            return True
        return False  # If no title AND no URL, it's just an empty tab/new tab page

    # Exact match - these are only broken if they match exactly
    exact_match_patterns = [
        "Untitled",
        "Start Page",
        "Loading",
        "Loading...",
        "Can't Open Page",
        "Just a moment..",
        "Failed to open page",
        "YouTube",
        "Reddit - Dive into anything",
        "reddit.com",
        "Mastodon",
        "Printables",
        "printables.com",
        "Docker",
        "Twitter",
        "Tweet / Twitter",
        "twitter.com",
        "X",
        "x.com",
        "arducam.com",
        "Account - My Archives – Thread Reader App",
        "Mastodon",
        "TikTok - Make Your Day",
        "amazon.com",
        "github.com",
        "http://",
        "https://",
        "Client Challenge",
    ]

    # Check exact matches
    if title in exact_match_patterns:
        return True

    # Prefix match - these indicate broken/loading states when at the start
    prefix_match_patterns = [
        "Thingiverse - ",
        "Ow!",
        "nytimes",
    ]

    # Check prefix matches
    if any(title.startswith(pattern) for pattern in prefix_match_patterns):
        return True

    # Substring match - these indicate issues if they appear anywhere
    substring_match_patterns = [
        "mobile.twitter.com",
        "fora.snahp.eu",
        "ui.com",
        "doc.rust-lang.org",
    ]

    # Check substring matches
    if any(pattern in title for pattern in substring_match_patterns):
        return True

    return False


def should_skip(title: str, url: str) -> bool:
    """
    Determines if a tab should be skipped (empty/default) based on config.
    """
    if not url or url == "favorites://" or url == "":
        return True
    if title == "Untitled" or title == "Start Page":
        return True
    return False
