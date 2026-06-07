import json
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Tab:
    title: str
    url: str
    id: str | None = None


@dataclass
class Window:
    id: int
    tabs: list[Tab]
    os_id: int | None = None


# Known Bundle IDs to avoid name ambiguity (e.g. extension vs app)
BUNDLE_IDS = {
    "Safari": "com.apple.Safari",
    "Google Chrome": "com.google.Chrome",
    "Chrome": "com.google.Chrome",
    "Chromium": "org.chromium.Chromium",
    "Opera": "com.operasoftware.Opera",
    "Vivaldi": "com.vivaldi.Vivaldi",
    "Brave Browser": "com.brave.Browser",
    "Microsoft Edge": "com.microsoft.edgemac",
    "Arc": "company.thebrowser.Browser",
    "Orion": "com.kagi.kagimacOS",
}


class Browser(ABC):
    def __init__(self, name: str):
        self.name = name
        self.bundle_id = BUNDLE_IDS.get(name)

    def activate(self):
        """Activates the browser application."""
        # Use 'open -a' for reliable activation/launching
        subprocess.run(["open", "-a", self.name], check=True)

    @property
    def app_ref(self) -> str:
        """Returns the AppleScript reference string (name or id)."""
        if self.bundle_id:
            return f'application id "{self.bundle_id}"'
        return f'application "{self.name}"'

    @property
    def jxa_app_ref(self) -> str:
        """Returns the JXA Application constructor string."""
        if self.bundle_id:
            return f'Application("{self.bundle_id}")'
        return f'Application("{self.name}")'

    @abstractmethod
    def get_windows(self) -> list[Window]:
        pass

    @abstractmethod
    def reload_tab(self, window_id: int, tab_index: int):
        pass

    @abstractmethod
    def get_tab_details(self, window_id: int, tab_index: int) -> Tab | None:
        """
        Gets details (title, url) for a specific tab.
        Returns None if tab/window not found.
        """
        pass

    @abstractmethod
    def is_tab_loading(self, window_id: int, tab_index: int) -> bool:
        """
        Returns True if the tab is still loading according to the browser's
        native loading state.

        Returns False when the tab is done loading, or if the query fails
        (so callers can safely fall through to title/URL checks).

        Args:
            window_id: The OS persistent window ID
            tab_index: The 1-based tab index
        """
        pass

    @abstractmethod
    def is_cloudflare_challenge(self, window_id: int, tab_index: int) -> bool:
        """
        Returns True if the tab is showing a Cloudflare challenge page.

        Checks the page body for the Cloudflare attribution URL
        (``cloudflare.com/?utm_source=challenge``) by executing JavaScript
        inside the tab. Returns False on error or if the browser does not
        support JavaScript execution.

        Args:
            window_id: The OS persistent window ID
            tab_index: The 1-based tab index
        """
        pass

    def get_frontmost_window_id(self) -> int | None:
        """
        Gets the OS ID of the frontmost window.
        Returns None if no windows exist.
        """
        script = f"""
        tell {self.app_ref}
            if (count of windows) > 0 then
                return id of front window
            else
                return 0
            end if
        end tell
        """
        try:
            result = self._run_osascript(script)
            window_id = int(result)
            return window_id if window_id > 0 else None
        except (RuntimeError, ValueError):
            return None

    def restore_frontmost_window(self, window_id: int):
        """
        Brings a specific window to the front by its OS ID.

        Args:
            window_id: The OS persistent window ID
        """
        script = f"""
        tell {self.app_ref}
            set index of window id {window_id} to 1
        end tell
        """
        try:
            self._run_osascript(script)
        except RuntimeError:
            # Window might have been closed, ignore error
            pass

    def _run_osascript(self, script: str) -> str:
        result = subprocess.run(
            [
                "osascript",
                "-e",
                script,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"AppleScript error: {result.stderr}")
        return result.stdout.strip()

    def _run_jxa(self, script: str) -> str:
        cmd = ["osascript", "-l", "JavaScript", "-e", script]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"JXA Error: {result.stderr}")
            return "[]"
        return result.stdout.strip()


class WebKitBrowser(Browser):
    """Safari, Webkit, Orion, etc."""

    def get_windows(self) -> list[Window]:
        jxa = f"""
        const app = {self.jxa_app_ref};
        const output = [];

        // Handle Safari vs others if property names differ?
        // WebKit usually: windows[].tabs[].name() .url()

        for (let i = 0; i < app.windows.length; i++) {{
            const win = app.windows[i];
            const winTabs = [];
            const tabs = win.tabs;

            // Optimization: Get arrays
            const titles = tabs.name();
            const urls = tabs.url();

            // Try to get persistent ID
            let winId = 0;
            try {{ winId = win.id(); }} catch(e) {{}}

            for (let t = 0; t < titles.length; t++) {{
                winTabs.push({{
                    title: titles[t],
                    url: urls[t]
                }});
            }}
            output.push({{
                os_id: winId,
                tabs: winTabs
            }});
        }}
        JSON.stringify(output);
        """

        output_json = self._run_jxa(jxa)
        try:
            data = json.loads(output_json)
        except json.JSONDecodeError:
            return []

        windows: list[Window] = []
        for i, win_data in enumerate(data):
            tabs = [Tab(t["title"], t["url"]) for t in win_data["tabs"]]
            windows.append(Window(id=i + 1, tabs=tabs, os_id=win_data.get("os_id")))

        return windows

    def reload_tab(self, window_id: int, tab_index: int):
        """
        Reloads a specific tab in a Safari window.

        Uses ``do JavaScript "location.reload()"`` via Safari's native
        AppleScript dictionary — no Accessibility/System Events permissions
        required. The tab is made current first so the reload is visible.

        Args:
            window_id: The OS persistent window ID
            tab_index: The 1-based tab index
        """
        script = f"""
        tell {self.app_ref}
            tell window id {window_id}
                set current tab to tab {tab_index}
                do JavaScript "location.reload()" in tab {tab_index}
            end tell
        end tell
        """
        self._run_osascript(script)

    def get_tab_details(self, window_id: int, tab_index: int) -> Tab | None:
        """
        Fetches the current title and URL for a specific tab.

        Uses ``|||`` as the field separator between title and URL to avoid
        ambiguity with real newline characters that ``.strip()`` may discard.

        Args:
            window_id: The OS persistent window ID
            tab_index: The 1-based tab index

        Returns:
            A :class:`Tab` with the current title and URL, or ``None`` if the
            window/tab could not be found.
        """
        script = f"""
        tell {self.app_ref}
            try
                tell window id {window_id}
                    set tTitle to name of tab {tab_index}
                    set tUrl to URL of tab {tab_index}
                    return tTitle & "|||" & tUrl
                end tell
            on error
                return ""
            end try
        end tell
        """
        result = self._run_osascript(script)
        if not result or "|||" not in result:
            return None

        title, _, url = result.partition("|||")
        return Tab(title=title, url=url)

    def is_tab_loading(self, window_id: int, tab_index: int) -> bool:
        """
        Checks the WebKit/Safari native ``loading`` property of the tab.

        Uses AppleScript ``loading of tab N`` which returns ``true`` while the
        page is still being fetched and ``false`` once it is complete.

        Args:
            window_id: The OS persistent window ID
            tab_index: The 1-based tab index

        Returns:
            True if the tab is still loading, False if done (or on error).
        """
        script = f"""
        tell {self.app_ref}
            try
                tell window id {window_id}
                    return loading of tab {tab_index}
                end tell
            on error
                return false
            end try
        end tell
        """
        try:
            result = self._run_osascript(script)
            return result.strip().lower() == "true"
        except RuntimeError:
            return False

    def is_cloudflare_challenge(self, window_id: int, tab_index: int) -> bool:
        """
        Detects whether a tab is showing a Cloudflare challenge page.

        Runs JavaScript inside the tab via AppleScript ``do JavaScript`` to
        search the page body for the Cloudflare attribution URL
        (``cloudflare.com/?utm_source=challenge``). The tab's title is
        typically ``"Just a moment..."`` in this state.

        Args:
            window_id: The OS persistent window ID
            tab_index: The 1-based tab index

        Returns:
            True if the tab contains a Cloudflare challenge, False otherwise
            (including on error).
        """
        script = f"""
        tell {self.app_ref}
            try
                tell window id {window_id}
                    set jsResult to do JavaScript \
                        "!!document.body && document.body.innerHTML.includes('cloudflare.com/?utm_source=challenge')" \
                        in tab {tab_index}
                    return jsResult
                end tell
            on error
                return false
            end try
        end tell
        """
        try:
            result = self._run_osascript(script)
            return result.strip().lower() == "true"
        except RuntimeError:
            return False


class ChromiumBrowser(Browser):
    """Chrome, Edge, Brave, etc."""

    def get_windows(self) -> list[Window]:
        jxa = f"""
        const app = {self.jxa_app_ref};
        const output = [];

        for (let i = 0; i < app.windows.length; i++) {{
            const win = app.windows[i];
            const winTabs = [];
            const tabs = win.tabs;

            // Try to get persistent ID
            let winId = 0;
            try {{ winId = win.id(); }} catch(e) {{}}

            const titles = tabs.title(); // Chrome uses .title()
            const urls = tabs.url();

            for (let t = 0; t < titles.length; t++) {{
                winTabs.push({{
                    title: titles[t],
                    url: urls[t]
                }});
            }}
            output.push({{
                os_id: winId,
                tabs: winTabs
            }});
        }}
        JSON.stringify(output);
        """

        output_json = self._run_jxa(jxa)
        try:
            data = json.loads(output_json)
        except json.JSONDecodeError:
            return []

        windows: list[Window] = []
        for i, win_data in enumerate(data):
            tabs = [Tab(t["title"], t["url"]) for t in win_data["tabs"]]
            windows.append(Window(id=i + 1, tabs=tabs, os_id=win_data.get("os_id")))

        return windows

    def reload_tab(self, window_id: int, tab_index: int):
        # Chrome: `reload tab X of window Y`
        # Also `set active tab index of window Y to X`

        script = f"""
        tell {self.app_ref}
            tell window id {window_id}
                set active tab index to {tab_index}
                reload tab {tab_index}
            end tell
        end tell
        """
        self._run_osascript(script)

    def get_tab_details(self, window_id: int, tab_index: int) -> Tab | None:
        """
        Fetches the current title and URL for a specific tab.

        Uses ``|||`` as the field separator between title and URL to avoid
        ambiguity with real newline characters that ``.strip()`` may discard.
        Note: Chrome uses ``title`` instead of ``name``.

        Args:
            window_id: The OS persistent window ID
            tab_index: The 1-based tab index

        Returns:
            A :class:`Tab` with the current title and URL, or ``None`` if the
            window/tab could not be found.
        """
        script = f"""
        tell {self.app_ref}
            try
                tell window id {window_id}
                    set tTitle to title of tab {tab_index}
                    set tUrl to URL of tab {tab_index}
                    return tTitle & "|||" & tUrl
                end tell
            on error
                return ""
            end try
        end tell
        """
        result = self._run_osascript(script)
        if not result or "|||" not in result:
            return None

        title, _, url = result.partition("|||")
        return Tab(title=title, url=url)

    def is_tab_loading(self, window_id: int, tab_index: int) -> bool:
        """
        Checks the Chromium native ``loading`` property of the tab via JXA.

        Uses ``tab.loading()`` which returns ``true`` while the page is still
        fetching and ``false`` once it is done.

        The tab is addressed by the 0-based index derived from ``tab_index``
        within the window whose persistent ID is ``window_id``.

        Args:
            window_id: The OS persistent window ID
            tab_index: The 1-based tab index

        Returns:
            True if the tab is still loading, False if done (or on error).
        """
        zero_based = tab_index - 1
        jxa = f"""
        try {{
            const app = {self.jxa_app_ref};
            const wins = app.windows.whose({{id: {window_id}}});
            if (wins.length === 0) {{ false; }}
            else {{
                const tab = wins[0].tabs[{zero_based}];
                tab.loading();
            }}
        }} catch(e) {{
            false;
        }}
        """
        try:
            result = self._run_jxa(jxa)
            return result.strip().lower() == "true"
        except Exception:
            return False

    def is_cloudflare_challenge(self, window_id: int, tab_index: int) -> bool:
        """
        Detects whether a tab is showing a Cloudflare challenge page.

        Runs JavaScript inside the tab via JXA ``tab.execute()`` to search the
        page body for the Cloudflare attribution URL
        (``cloudflare.com/?utm_source=challenge``). The tab's title is
        typically ``"Just a moment..."`` in this state.

        Args:
            window_id: The OS persistent window ID
            tab_index: The 1-based tab index

        Returns:
            True if the tab contains a Cloudflare challenge, False otherwise
            (including on error).
        """
        zero_based = tab_index - 1
        jxa = f"""
        try {{
            const app = {self.jxa_app_ref};
            const wins = app.windows.whose({{id: {window_id}}});
            if (wins.length === 0) {{ false; }}
            else {{
                const result = wins[0].tabs[{zero_based}].execute({{
                    javascript: "!!document.body && document.body.innerHTML.includes('cloudflare.com/?utm_source=challenge')"
                }});
                result === true || String(result) === 'true';
            }}
        }} catch(e) {{
            false;
        }}
        """
        try:
            result = self._run_jxa(jxa)
            return result.strip().lower() == "true"
        except Exception:
            return False


def get_browser_instance(name: str) -> Browser:
    # Basic detection logic or factory
    if any(k in name for k in ["Safari", "Orion", "Webkit"]):
        return WebKitBrowser(name)
    else:
        return ChromiumBrowser(name)
