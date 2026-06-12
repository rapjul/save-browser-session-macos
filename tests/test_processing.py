from save_browser_session.processing import clean_title, clean_url, is_broken_tab


def test_clean_url() -> None:
    assert clean_url("https://example.com") == "https://example.com"
    assert (
        clean_url("https://example.com/foo(bar)") == "https://example.com/foo%28bar%29"
    )
    assert (
        clean_url("https://youtube.com/watch?v=123&t=1m20s")
        == "https://youtube.com/watch?v=123"
    )
    # Test additional YouTube formats for t parameter removal
    assert (
        clean_url("https://youtube.com/watch?v=123&t=80s&feature=shared")
        == "https://youtube.com/watch?v=123&feature=shared"
    )
    assert clean_url("https://youtu.be/123?t=80") == "https://youtu.be/123"
    assert (
        clean_url("https://youtube.com/watch?v=123&t=2m")
        == "https://youtube.com/watch?v=123"
    )
    assert (
        clean_url("https://youtube.com/watch?v=123&t=16m39s")
        == "https://youtube.com/watch?v=123"
    )
    assert (
        clean_url("https://youtube.com/watch?v=123&t=2h58m59s")
        == "https://youtube.com/watch?v=123"
    )
    # Test YouTube share tracking parameter (si) removal
    assert (
        clean_url("https://youtube.com/watch?v=123&si=tracking_id")
        == "https://youtube.com/watch?v=123"
    )
    assert (
        clean_url("https://github.com/repo?tab=readme-ov-file")
        == "https://github.com/repo"
    )
    assert clean_url("https://example.com/\u202afoo\u202c") == "https://example.com/foo"
    assert clean_url("") == ""


def test_clean_title() -> None:
    # Basic cleaning
    assert clean_title("  My Title  ") == "My Title"
    assert clean_title("(12) My Title") == "My Title"
    assert clean_title("(123+) My Title") == "My Title"

    # Twitter/X
    assert clean_title("User on Twitter: Tweet") == "User on Twitter – Tweet"
    assert clean_title("User / X") == "User"

    # Brackets
    assert clean_title("[Tag] Title") == "[Tag] Title"

    # Newlines
    assert clean_title("Line1\nLine2") == "Line1 Line2"

    # Invisible chars
    assert clean_title("Title\u200e") == "Title"
    assert clean_title("Title\u202a\u202c") == "Title"


def test_is_broken_tab() -> None:
    assert is_broken_tab("https://google.com", "https://google.com") is True
    assert (
        is_broken_tab("https://example.com/file.md", "https://example.com/file.md")
        is False
    )
    assert (
        is_broken_tab("https://example.com/image.png", "https://example.com/image.png")
        is False
    )
    assert is_broken_tab("", "https://example.com/file.txt") is False
    assert is_broken_tab("   ", "https://google.com") is True
    assert is_broken_tab("", "https://google.com") is True
    assert is_broken_tab("", "") is False
    assert is_broken_tab("   ", "") is False
    assert is_broken_tab("Untitled", "") is False
    assert is_broken_tab("Loading...", "https://google.com") is True
    assert is_broken_tab("Google", "https://google.com") is False
    assert is_broken_tab("Can't Open Page", "err://") is True
