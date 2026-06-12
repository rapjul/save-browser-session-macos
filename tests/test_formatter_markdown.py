from datetime import datetime
from unittest.mock import MagicMock

from save_browser_session.browser import Browser
from save_browser_session.formatter import Tab, Window, generate_formatted_content


def test_markdown_padding() -> None:
    browser = MagicMock(spec=Browser)
    browser.name = "TestBrowser"

    # Window with 12 tabs (2 digits)
    tabs = [Tab(f"Tab {i}", f"http://example.com/{i}") for i in range(1, 13)]
    windows = [Window(1, tabs)]

    result = generate_formatted_content(
        browser=browser,
        windows=windows,
        session_name="Test Session",
        include_empty=True,
        save_all=True,
        timestamp=datetime.now(),
        format_type="markdown",
    )

    content = result.content

    # Print content for manual inspection
    print("\n--- Content Start ---")
    print(content)
    print("--- Content End ---")

    # New behavior: Space (right) padded on the number string
    # "1." (len 2) -> padded to (digits+1)=3 -> "1. " + " " (suffix) = "1.  "
    # "12." (len 3) -> padded to 3 -> "12." + " " (suffix) = "12. "
    assert "1.  [Tab 1]" in content
    assert "12. [Tab 12]" in content


def test_markdown_padding_small() -> None:
    browser = MagicMock(spec=Browser)
    browser.name = "TestBrowser"

    # Window with 5 tabs (1 digit)
    tabs = [Tab(f"Tab {i}", f"http://example.com/{i}") for i in range(1, 6)]
    windows = [Window(1, tabs)]

    result = generate_formatted_content(
        browser=browser,
        windows=windows,
        session_name="Test Session",
        include_empty=True,
        save_all=True,
        timestamp=datetime.now(),
        format_type="markdown",
    )

    content = result.content
    print("\n--- Content Small Start ---")
    print(content)
    print("--- Content Small End ---")

    # Current behavior:
    # count=1 digit. max_width=2.
    # "1." -> "1." + 1 space (fmt) = "1. "
    assert "1. [Tab 1]" in content


def test_markdown_url_as_title() -> None:
    """
    Tests that a tab whose title is identical to its URL (e.g. an unloaded tab)
    is formatted as a plain URL link: <url>.
    """
    browser = MagicMock(spec=Browser)
    browser.name = "TestBrowser"

    # Tab where title is identical to url (simulating an unloaded tab)
    tabs = [
        Tab(
            title="https://www.nyctrackbook.com/collections/current-edition.pdf",
            url="https://www.nyctrackbook.com/collections/current-edition.pdf",
        )
    ]
    windows = [Window(1, tabs)]

    result = generate_formatted_content(
        browser=browser,
        windows=windows,
        session_name="Test Session",
        include_empty=True,
        save_all=True,
        timestamp=datetime.now(),
        format_type="markdown",
    )

    content = result.content
    # It should format as a plain URL link: <url>
    assert (
        "1. <https://www.nyctrackbook.com/collections/current-edition.pdf>" in content
    )
