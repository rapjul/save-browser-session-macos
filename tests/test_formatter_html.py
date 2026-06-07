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
