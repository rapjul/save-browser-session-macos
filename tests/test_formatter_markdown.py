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


def test_markdown_with_tab_groups() -> None:
    """Test that Markdown organizes tabs into group subheadings while preserving exact order."""
    browser = MagicMock(spec=Browser)
    browser.name = "Microsoft Edge"

    tabs = [
        Tab("Top Tab 1", "https://example.com/top1", group=None),
        Tab("Top Tab 2", "https://example.com/top2", group=None),
        Tab("Group Tab 1", "https://example.com/g1", group="Local Services"),
        Tab("Group Tab 2", "https://example.com/g2", group="Local Services"),
        Tab("Middle Tab 1", "https://example.com/mid1", group=None),
        Tab("Group B Tab 1", "https://example.com/b1", group="Web Novels"),
    ]
    windows = [Window(1, tabs)]

    result = generate_formatted_content(
        browser=browser,
        windows=windows,
        session_name="Autosaved",
        include_empty=True,
        save_all=False,
        timestamp=datetime.now(),
        format_type="markdown",
    )
    content = result.content

    # Subheadings exist in the correct sequential order
    assert "### Ungrouped Tabs (2 Tabs)" in content
    assert "### Local Services (2 Tabs)" in content
    assert "### Ungrouped Tabs (1 Tabs)" in content
    assert "### Web Novels (1 Tabs)" in content

    # Check that sequential global numbering is preserved
    assert "1. [Top Tab 1]" in content
    assert "2. [Top Tab 2]" in content
    assert "3. [Group Tab 1]" in content
    assert "4. [Group Tab 2]" in content
    assert "5. [Middle Tab 1]" in content
    assert "6. [Group B Tab 1]" in content


def test_json_and_csv_with_tab_groups() -> None:
    """Test that JSON and CSV formats include tab group information."""
    import csv
    import json
    from io import StringIO

    browser = MagicMock(spec=Browser)
    browser.name = "Google Chrome"

    tabs = [
        Tab("Grouped Tab", "https://example.com/1", group="Work"),
        Tab("Ungrouped Tab", "https://example.com/2", group=None),
    ]
    windows = [Window(1, tabs)]

    # Test JSON
    json_result = generate_formatted_content(
        browser=browser,
        windows=windows,
        session_name="Test",
        include_empty=True,
        save_all=False,
        timestamp=datetime.now(),
        format_type="json",
    )
    data = json.loads(json_result.content)
    assert data["windows"][0]["tabs"][0]["group"] == "Work"
    assert data["windows"][0]["tabs"][1]["group"] is None

    # Test CSV
    csv_result = generate_formatted_content(
        browser=browser,
        windows=windows,
        session_name="Test",
        include_empty=True,
        save_all=False,
        timestamp=datetime.now(),
        format_type="csv",
    )
    reader = list(csv.reader(StringIO(csv_result.content)))
    header = reader[0]
    assert "Group" in header
    group_col = header.index("Group")
    assert reader[1][group_col] == "Work"
    assert reader[2][group_col] == ""
