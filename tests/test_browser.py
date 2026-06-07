"""Tests for browser.py — focusing on is_tab_loading() for both browser types."""

from unittest.mock import patch

from save_browser_session.browser import ChromiumBrowser, WebKitBrowser


# ---------------------------------------------------------------------------
# WebKitBrowser.is_tab_loading
# ---------------------------------------------------------------------------


class TestWebKitBrowserIsTabLoading:
    """Tests for WebKitBrowser.is_tab_loading() using the AppleScript backend."""

    def _make_browser(self) -> WebKitBrowser:
        """Creates a WebKitBrowser instance for Safari (has a bundle ID)."""
        return WebKitBrowser("Safari")

    def test_returns_true_when_applescript_returns_true(self) -> None:
        """Browser reports loading → is_tab_loading returns True."""
        browser = self._make_browser()
        with patch.object(browser, "_run_osascript", return_value="true"):
            assert browser.is_tab_loading(12345, 3) is True

    def test_returns_false_when_applescript_returns_false(self) -> None:
        """Browser reports not loading → is_tab_loading returns False."""
        browser = self._make_browser()
        with patch.object(browser, "_run_osascript", return_value="false"):
            assert browser.is_tab_loading(12345, 3) is False

    def test_case_insensitive_true(self) -> None:
        """'True' with any casing is treated as loading."""
        browser = self._make_browser()
        with patch.object(browser, "_run_osascript", return_value="True"):
            assert browser.is_tab_loading(12345, 3) is True

    def test_returns_false_on_runtime_error(self) -> None:
        """If osascript raises RuntimeError, is_tab_loading returns False (safe fallback)."""
        browser = self._make_browser()
        with patch.object(
            browser, "_run_osascript", side_effect=RuntimeError("osascript error")
        ):
            assert browser.is_tab_loading(12345, 3) is False

    def test_script_references_window_id_and_tab_index(self) -> None:
        """The generated AppleScript contains the correct window ID and tab index."""
        browser = self._make_browser()
        captured: list[str] = []

        def capture_script(script: str) -> str:
            """Captures the script passed to _run_osascript."""
            captured.append(script)
            return "false"

        with patch.object(browser, "_run_osascript", side_effect=capture_script):
            browser.is_tab_loading(99999, 7)

        assert len(captured) == 1
        script = captured[0]
        assert "window id 99999" in script
        assert "tab 7" in script
        assert "loading" in script


# ---------------------------------------------------------------------------
# ChromiumBrowser.is_tab_loading
# ---------------------------------------------------------------------------


class TestChromiumBrowserIsTabLoading:
    """Tests for ChromiumBrowser.is_tab_loading() using the JXA backend."""

    def _make_browser(self) -> ChromiumBrowser:
        """Creates a ChromiumBrowser for Google Chrome."""
        return ChromiumBrowser("Google Chrome")

    def test_returns_true_when_jxa_returns_true(self) -> None:
        """JXA reports loading → is_tab_loading returns True."""
        browser = self._make_browser()
        with patch.object(browser, "_run_jxa", return_value="true"):
            assert browser.is_tab_loading(12345, 3) is True

    def test_returns_false_when_jxa_returns_false(self) -> None:
        """JXA reports not loading → is_tab_loading returns False."""
        browser = self._make_browser()
        with patch.object(browser, "_run_jxa", return_value="false"):
            assert browser.is_tab_loading(12345, 3) is False

    def test_returns_false_on_exception(self) -> None:
        """Any exception from _run_jxa causes is_tab_loading to return False."""
        browser = self._make_browser()
        with patch.object(browser, "_run_jxa", side_effect=Exception("jxa failure")):
            assert browser.is_tab_loading(12345, 3) is False

    def test_script_uses_zero_based_tab_index(self) -> None:
        """The JXA script accesses tabs with a 0-based index (tab_index - 1)."""
        browser = self._make_browser()
        captured: list[str] = []

        def capture_script(script: str) -> str:
            """Captures the script passed to _run_jxa."""
            captured.append(script)
            return "false"

        with patch.object(browser, "_run_jxa", side_effect=capture_script):
            browser.is_tab_loading(99999, 5)

        assert len(captured) == 1
        script = captured[0]
        # 1-based tab 5 → 0-based index 4
        assert "tabs[4]" in script

    def test_script_references_correct_window_id(self) -> None:
        """The JXA script queries the correct persistent window ID."""
        browser = self._make_browser()
        captured: list[str] = []

        def capture_script(script: str) -> str:
            """Captures the script passed to _run_jxa."""
            captured.append(script)
            return "false"

        with patch.object(browser, "_run_jxa", side_effect=capture_script):
            browser.is_tab_loading(77777, 1)

        script = captured[0]
        assert "77777" in script
        assert "loading" in script


# ---------------------------------------------------------------------------
# WebKitBrowser.is_cloudflare_challenge
# ---------------------------------------------------------------------------


class TestWebKitBrowserIsCloudflareChallenge:
    """Tests for WebKitBrowser.is_cloudflare_challenge() using AppleScript do JavaScript."""

    def _make_browser(self) -> WebKitBrowser:
        """Creates a WebKitBrowser instance for Safari."""
        return WebKitBrowser("Safari")

    def test_returns_true_when_cloudflare_url_found(self) -> None:
        """JS returns true → is_cloudflare_challenge returns True."""
        browser = self._make_browser()
        with patch.object(browser, "_run_osascript", return_value="true"):
            assert browser.is_cloudflare_challenge(12345, 3) is True

    def test_returns_false_when_cloudflare_url_not_found(self) -> None:
        """JS returns false → is_cloudflare_challenge returns False."""
        browser = self._make_browser()
        with patch.object(browser, "_run_osascript", return_value="false"):
            assert browser.is_cloudflare_challenge(12345, 3) is False

    def test_returns_false_on_runtime_error(self) -> None:
        """RuntimeError (e.g. JS not allowed) → returns False (safe fallback)."""
        browser = self._make_browser()
        with patch.object(
            browser, "_run_osascript", side_effect=RuntimeError("not allowed")
        ):
            assert browser.is_cloudflare_challenge(12345, 3) is False

    def test_script_contains_cloudflare_url(self) -> None:
        """The generated AppleScript checks for the Cloudflare attribution URL."""
        browser = self._make_browser()
        captured: list[str] = []

        def capture_script(script: str) -> str:
            """Captures the script passed to _run_osascript."""
            captured.append(script)
            return "false"

        with patch.object(browser, "_run_osascript", side_effect=capture_script):
            browser.is_cloudflare_challenge(99999, 4)

        script = captured[0]
        assert "cloudflare.com/?utm_source=challenge" in script
        assert "window id 99999" in script
        assert "tab 4" in script


# ---------------------------------------------------------------------------
# ChromiumBrowser.is_cloudflare_challenge
# ---------------------------------------------------------------------------


class TestChromiumBrowserIsCloudflareChallenge:
    """Tests for ChromiumBrowser.is_cloudflare_challenge() using JXA tab.execute()."""

    def _make_browser(self) -> ChromiumBrowser:
        """Creates a ChromiumBrowser for Google Chrome."""
        return ChromiumBrowser("Google Chrome")

    def test_returns_true_when_cloudflare_url_found(self) -> None:
        """JXA returns true → is_cloudflare_challenge returns True."""
        browser = self._make_browser()
        with patch.object(browser, "_run_jxa", return_value="true"):
            assert browser.is_cloudflare_challenge(12345, 3) is True

    def test_returns_false_when_cloudflare_url_not_found(self) -> None:
        """JXA returns false → is_cloudflare_challenge returns False."""
        browser = self._make_browser()
        with patch.object(browser, "_run_jxa", return_value="false"):
            assert browser.is_cloudflare_challenge(12345, 3) is False

    def test_returns_false_on_exception(self) -> None:
        """Any exception from _run_jxa → returns False (safe fallback)."""
        browser = self._make_browser()
        with patch.object(browser, "_run_jxa", side_effect=Exception("jxa error")):
            assert browser.is_cloudflare_challenge(12345, 3) is False

    def test_script_contains_cloudflare_url(self) -> None:
        """The JXA script checks for the Cloudflare attribution URL."""
        browser = self._make_browser()
        captured: list[str] = []

        def capture_script(script: str) -> str:
            """Captures the script passed to _run_jxa."""
            captured.append(script)
            return "false"

        with patch.object(browser, "_run_jxa", side_effect=capture_script):
            browser.is_cloudflare_challenge(88888, 2)

        script = captured[0]
        assert "cloudflare.com/?utm_source=challenge" in script
        assert "88888" in script

    def test_script_uses_zero_based_tab_index(self) -> None:
        """JXA script accesses tabs with 0-based index (tab_index - 1)."""
        browser = self._make_browser()
        captured: list[str] = []

        def capture_script(script: str) -> str:
            """Captures the script passed to _run_jxa."""
            captured.append(script)
            return "false"

        with patch.object(browser, "_run_jxa", side_effect=capture_script):
            browser.is_cloudflare_challenge(11111, 6)

        # 1-based tab 6 → 0-based index 5
        assert "tabs[5]" in captured[0]
