from datetime import datetime
from unittest.mock import MagicMock

from save_browser_session.browser import Browser
from save_browser_session.formatter import Tab, Window, generate_html


def test_html_generation() -> None:
    browser = MagicMock(spec=Browser)
    browser.name = "TestBrowser"
    windows = [
        Window(
            1,
            [
                Tab("Tab 1", "http://example.com/1"),
                Tab("Tab 2", "http://example.com/2"),
            ],
        ),
        Window(2, [Tab("Tab 3", "http://example.com/3")]),
    ]
    html = generate_html(browser, windows, "Test Session", datetime.now())

    assert "TestBrowser Session" in html
    assert "http://example.com/1" in html
    assert 'id="copyAll"' in html
    assert 'id="copyFiltered"' in html
    # Check simple JS presence
    assert "navigator.clipboard.writeText" in html


def test_html_generation_with_tab_groups() -> None:
    """Test that HTML export formats tab groups with distinct group headings."""
    browser = MagicMock(spec=Browser)
    browser.name = "Microsoft Edge"
    windows = [
        Window(
            1,
            [
                Tab("Local Tab", "http://example.com/1", group="Local Services"),
                Tab("Ungrouped Tab", "http://example.com/2", group=None),
            ],
        ),
    ]
    html = generate_html(browser, windows, "Test Session", datetime.now())

    assert "<h3>Local Services (1 tabs)</h3>" in html
    assert "<h3>Ungrouped Tabs (1 tabs)</h3>" in html
    assert "http://example.com/1" in html
    assert "http://example.com/2" in html
