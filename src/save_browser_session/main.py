import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Annotated, List, Optional, Tuple

import pyperclip
import typer

from .browser import get_browser_instance
from .formatter import generate_formatted_content
from .processing import is_broken_tab
from .ui import UserAction, UserScope, get_ui
from .utils import (
    check_connection,
    focus_app,
    get_current_app_name,
    is_app_running,
    open_with_application,
    set_file_dates,
)

app = typer.Typer(
    help="Save tabs from your web browser to a Markdown file.",
    context_settings={"help_option_names": ["-h", "--help"]},
)


class BrowserName(str, Enum):
    """Supported browser names and their command-line aliases."""

    SAFARI = "Safari"
    """Safari browser."""

    WEBKIT = "Webkit"
    """Webkit engine/browser."""

    CHROME = "Google Chrome"
    """Google Chrome browser."""

    CHROME_ALIAS = "Chrome"
    """Short alias for Google Chrome browser."""

    CHROMIUM = "Chromium"
    """Chromium browser."""

    OPERA = "Opera"
    """Opera browser."""

    VIVALDI = "Vivaldi"
    """Vivaldi browser."""

    BRAVE = "Brave Browser"
    """Brave browser."""

    EDGE = "Microsoft Edge"
    """Microsoft Edge browser."""

    EDGE_ALIAS = "Edge"
    """Short alias for Microsoft Edge browser."""

    ARC = "Arc"
    """Arc browser."""

    ORION = "Orion"
    """Orion browser."""


class MarkdownEditor(str, Enum):
    TEXTEDIT = "TextEdit"
    VSCODE = "Visual Studio Code"
    VSCODE_SHORT_ALIAS = "VS Code"
    ANTIGRAVITY = "Antigravity"
    CURSOR = "Cursor"
    CODEX = "Codex"
    CLAUDE = "Claude Code"


class Format(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"
    CSV = "csv"
    HTML = "html"


DEFAULT_OUTPUT_DIR = (
    Path.home()
    / "Library/Mobile Documents/iCloud~is~workflow~my~workflows/Documents/Programs/Browser Sessions"
)
AUTOSAVE_DIR = DEFAULT_OUTPUT_DIR / "Autosaved"


@app.command()
def main(
    ctx: typer.Context,
    current_window: Annotated[
        bool,
        typer.Option(
            "--current",
            "--current-window",
            "-c",
            help="Save only the current window.",
        ),
    ] = False,
    all_windows: Annotated[
        bool,
        typer.Option(
            "--all",
            "--all-windows",
            "-a",
            "--windows",
            help="Save all windows.",
        ),
    ] = False,
    autosave: Annotated[
        bool,
        typer.Option(
            "--autosave",
            help="Run in silent autosave mode (saves to 'Autosaved' sub-directory).",
        ),
    ] = False,
    browser_name: Annotated[
        Optional[BrowserName],
        typer.Option(
            "--browser",
            "-b",
            help="Force a specific browser. If not set, detects frontmost.",
        ),
    ] = None,
    session_name_arg: Annotated[
        Optional[str],
        typer.Option(
            "--session-name",
            "--name",
            "-n",
            help="Name of the session (used in filename and header).",
        ),
    ] = None,
    include_empty: Annotated[
        bool,
        typer.Option(
            "--include-empty",
            help="Include empty/untitled tabs that are normally skipped.",
            show_default=False,
        ),
    ] = False,
    gui: Annotated[
        bool,
        typer.Option(
            "--gui",
            help="Force GUI dialogs even in terminal.",
            show_default=False,
        ),
    ] = False,
    open_with: Annotated[
        Optional[MarkdownEditor],
        typer.Option(
            "--open-with",
            help="Open the saved file with a specific application.",
            show_default=False,
        ),
    ] = None,
    custom_open_with: Annotated[
        Optional[str],
        typer.Option(
            "--custom-open-with",
            help="Open the saved file with a custom application name.",
            show_default=False,
        ),
    ] = None,
    session_date: Annotated[
        Optional[str],
        typer.Option(
            "--session-date",
            "--date",
            "-d",
            help="Manually set the session date (format: YYYY-MM-DD HH:MM or HH:MM).",
        ),
    ] = None,
    output_format: Annotated[
        Format,
        typer.Option(
            "--format",
            "-f",
            help="Output format (markdown, json, csv, html).",
        ),
    ] = Format.MARKDOWN,
    fix_broken_tabs: Annotated[
        bool,
        typer.Option(
            "--fix-broken",
            "--fix-broken-tabs",
            help="Automatically fix broken tabs (reload/activate) without prompting.",
            show_default=False,
        ),
    ] = False,
    list_broken_tabs: Annotated[
        bool,
        typer.Option(
            "--list-broken",
            "--list-broken-tabs",
            help="List broken tabs with their Window and Tab IDs, then exit.",
            show_default=False,
        ),
    ] = False,
    smart_naming: Annotated[
        bool,
        typer.Option(
            "--smart-naming/--no-smart-naming",
            help="Enable smart session name suggestions based on tab analysis.",
        ),
    ] = True,
    remove_tracking: Annotated[
        bool,
        typer.Option(
            "--remove-tracking/--keep-tracking",
            help="Remove tracking parameters from URLs.",
        ),
    ] = True,
):
    """
    Save Browser Session
    """
    ui = get_ui(force_gui=gui)

    # 0. Capture Current App (for restore focus)
    current_app = get_current_app_name()

    # 1. Detect Browser
    target_browser_name = None
    if browser_name:
        target_browser_name = browser_name.value

    # Handle Chrome/Edge browser aliases
    if target_browser_name == BrowserName.CHROME_ALIAS:
        target_browser_name = BrowserName.CHROME.value
    elif target_browser_name == BrowserName.EDGE_ALIAS:
        target_browser_name = BrowserName.EDGE.value

    try:
        if target_browser_name:
            # Force specific
            if not is_app_running(target_browser_name):
                if autosave:
                    ui.status(
                        f"Browser '{target_browser_name}' is not running. Autosave aborted."
                    )
                    raise typer.Exit(code=1)

                if not ui.confirm(
                    f"'{target_browser_name}' is not running. Do you want to open it?"
                ):
                    raise typer.Exit(code=0)

                # Open and wait
                ui.status(f"Opening {target_browser_name}...")
                browser = get_browser_instance(target_browser_name)
                browser.activate()

                # Wait for it to appear
                with ui.spinner(f"Waiting for {target_browser_name} to launch..."):
                    retries = 20
                    while not is_app_running(target_browser_name) and retries > 0:
                        time.sleep(0.5)
                        retries -= 1

                    # Wait a bit more for windows to initialize
                    time.sleep(2)
            else:
                browser = get_browser_instance(target_browser_name)
        else:
            # Detect frontmost
            # We need a generic way to find frontmost compatible browser
            # For now, let's try to get "Safari" or "Chrome" if active
            # Actually, the logic in JXA was "get frontmost app name", check if valid.
            import subprocess

            res = subprocess.run(
                [
                    "osascript",
                    "-e",
                    'tell application "System Events" to name of first application process whose frontmost is true',
                ],
                capture_output=True,
                text=True,
            )
            front_name = res.stdout.strip()

            # Simple mapping check
            valid_browsers = [b.value for b in BrowserName]

            # Allow prefix matching (e.g. "Google Chrome" matches "Google Chrome")
            # JXA logic: "startWith(n)"
            detected = None
            for vb in valid_browsers:
                if front_name.startswith(vb):
                    detected = vb
                    break

            if not detected:
                # If autosave, we might default to Safari or fail?
                # JXA threw error.
                if autosave:
                    ui.status("No browser detected in autosave mode. Exiting.")
                    raise typer.Exit(code=1)

                # Try to guess or ask?
                # For now fail gracefully
                ui.status(f"Frontmost app '{front_name}' is not a supported browser.")
                raise typer.Exit(code=1)

            browser = get_browser_instance(
                front_name
            )  # Use the actual front name (e.g. "Google Chrome")

    except typer.Exit:
        raise
    except Exception as e:
        ui.status(f"Error initializing browser detected: {e}")
        raise typer.Exit(code=1)

    # Capture the frontmost window to restore it later
    original_window_id = browser.get_frontmost_window_id()
    app_to_open = None

    try:
        # 2. Setup Config
        save_all = True
        view_only = False  # Default to False
        if current_window:
            save_all = False
        # If both or neither, default to all?
        # JXA default was: Interactive -> ask. CLI -> "all" or "current" explicit.
        # Here, if interactive (no autosave), we might ask?
        # Typer args are static. Let's stick to flags.
        # If no flags provided, maybe ask in UI if strictly interactive?
        # Implementation Plan says: "If interactive, show Rich UI."
        # Let's keep it simple: Default to ALL unless --current.

        session_name = session_name_arg or ""
        output_dir = DEFAULT_OUTPUT_DIR

        if autosave:
            session_name = "Autosaved"
            output_dir = AUTOSAVE_DIR
            save_all = True  # Autosave usually means backup everything

        elif not (list_broken_tabs or fix_broken_tabs):
            # Interactive or semi-interactive mode

            # 1. Determine Scope first
            # Logic: If user just ran `save-browser-session` without --current or --all
            # Note: We check if flags were defaulted (False).
            if not all_windows and not current_window:
                # Ask for Action first
                action = ui.ask_action()
                if action == UserAction.VIEW:
                    # If viewing, ask for scope too
                    scope = ui.ask_scope()
                    save_all = scope == UserScope.ALL
                    # Set a flag to View Only
                    view_only = True
                else:
                    view_only = False
                    # Saving...
                    scope = ui.ask_scope()
                    save_all = scope == UserScope.ALL
            else:
                # Flag logic
                save_all = True
                view_only = False
                if current_window:
                    save_all = False

            # 2. Prompt for Name only if saving current window (not all windows)
            # Session name is optional for all windows, but useful for current window
            # Note: Will ask again after fetching windows for smart suggestions
            # if no name is provided here

        # 3. Fetch Data
        # Activate browser only after prompts are done to prevent focus stealing
        browser.activate()
        with ui.spinner("Fetching tabs..."):
            windows = browser.get_windows()

        if not windows:
            ui.status("No windows found.")
            raise typer.Exit()

        if not save_all:
            # Filter to 1st window (usually frontmost in JXA array return?)
            windows = windows[:1]

        # 3b. Smart naming after fetching windows
        # Ask for session name if needed, using smart suggestions
        if (
            not save_all
            and not session_name
            and not autosave
            and not (list_broken_tabs or fix_broken_tabs)
        ):
            if smart_naming:
                from .session_analyzer import SessionAnalyzer

                analyzer = SessionAnalyzer(windows)
                suggestions = analyzer.suggest_names(
                    max_suggestions=5, include_history=True
                )
                session_name = ui.ask_session_name_with_suggestions(suggestions)
            else:
                session_name = ui.ask_session_name()

        # 4. Check Broken
        total_broken = 0
        broken_indices: List[
            Tuple[int, int | None, int]
        ] = []  # (win_display_id, win_os_id, tab_idx)

        if fix_broken_tabs or list_broken_tabs:
            for window in windows:
                for t_idx, tab in enumerate(window.tabs):
                    if is_broken_tab(tab.title, tab.url):
                        total_broken += 1
                        broken_indices.append(
                            (window.id, window.os_id, t_idx + 1)
                        )  # 1-based index for reload

        if list_broken_tabs:
            if total_broken > 0:
                print(f"\nFound {total_broken} broken tabs:\n")

                # Group by window for cleaner output
                from itertools import groupby

                # Sort first by window_id to ensure groupby works
                broken_indices.sort(key=lambda x: x[0])

                for w_display_id, group in groupby(broken_indices, key=lambda x: x[0]):
                    group_list = list(group)
                    # Get OS/System Window ID from first item
                    first_os_id = group_list[0][1]
                    os_id_str = (
                        f" (System Window ID: {first_os_id})" if first_os_id else ""
                    )

                    print(f"Window {w_display_id}{os_id_str}:")

                    target_win = next(
                        (w for w in windows if w.id == w_display_id), None
                    )

                    for _, _, t_id in group_list:
                        status_text = "[Unknown]"
                        url_text = ""
                        if target_win and 0 <= t_id - 1 < len(target_win.tabs):
                            t = target_win.tabs[t_id - 1]
                            status_text = f"[{t.title}]"
                            url_text = f" ({t.url})" if t.url else "()"

                        print(f"  • Tab {t_id}: {status_text}{url_text}")
                    print("")  # Space between windows

                print(
                    f"Found {total_broken} broken tabs. (Robustness: Using persistent System Window IDs)"
                )

            else:
                print("No broken tabs found.")
            raise typer.Exit()

        if total_broken > 0 and not autosave:
            # New Step: Check connection before fixing
            if not check_connection():
                ui.status(
                    "⚠️  No internet connection detected. Skipping fixes to avoid errors."
                )
                should_fix = False
            else:
                should_fix = fix_broken_tabs
                if not should_fix:
                    should_fix = ui.confirm_fix_broken(total_broken)

            if should_fix:
                ui.status(f"Fixing {total_broken} broken tabs...")
                # Fix them
                # We need to iterate and reload
                # This is tricky because we need the browser object to reload specific tabs
                # and then RE-FETCH data.

                fixed_count = 0
                TIMEOUT = 10  # Seconds to wait for load

                for idx, (_, w_os_id, t_id) in enumerate(broken_indices, 1):
                    # Add separator if not first
                    if idx > 1:
                        ui.print_line("")

                    if w_os_id:
                        ui.status(
                            f"[{idx}/{total_broken}] Reloading Window (System Window ID: {w_os_id}), Tab {t_id}..."
                        )
                        browser.reload_tab(w_os_id, t_id)

                        # Two-phase wait:
                        # Phase 1 — wait for the browser's native loading flag
                        # to clear (polls every 0.5 s, up to TIMEOUT seconds).
                        # This avoids waiting the full timeout for tabs that
                        # finish loading but briefly show a "broken" title.
                        start_time = time.time()
                        while time.time() - start_time < TIMEOUT:
                            time.sleep(0.5)
                            if not browser.is_tab_loading(w_os_id, t_id):
                                break  # Native loading complete

                        elapsed = time.time() - start_time

                        # Phase 2 — retrieve the final title/URL once loading is
                        # done. We trust the browser's native loading signal here:
                        # once it says the tab is finished, we count it as fixed
                        # regardless of is_broken_tab(), which would wrongly
                        # reject legitimately-loaded pages whose titles happen to
                        # match generic-looking patterns (GitHub, Twitter, etc.).
                        tab_details = browser.get_tab_details(w_os_id, t_id)

                        if elapsed >= TIMEOUT:
                            # Native loading never finished within the timeout
                            ui.status(f"  ⚠️  Timeout waiting for Tab {t_id} to load.")
                        elif tab_details and (tab_details.title or tab_details.url):
                            # Page finished loading and has a title/URL — success
                            fixed_count += 1
                            title_display = (tab_details.title or tab_details.url)[:50]
                            ui.status(f"  ✓ Fixed: [{title_display}]")
                        else:
                            # Loading finished but we couldn't read title/URL.
                            # Check explicitly for a Cloudflare challenge page —
                            # title is "Just a moment..." and the body contains
                            # the Cloudflare attribution link.
                            if browser.is_cloudflare_challenge(w_os_id, t_id):
                                ui.status(
                                    f"  ⚠️  Tab {t_id}: Cloudflare challenge"
                                    " detected — cannot auto-fix."
                                )
                            else:
                                ui.status(
                                    f"  ⚠️  Tab {t_id} finished loading but"
                                    " returned no content."
                                )

                    else:
                        # Fallback if no OS ID? (Shouldn't happen with new browser.py)
                        pass

                if fixed_count < total_broken:
                    ui.status(
                        f"Fixed {fixed_count}/{total_broken} tabs (others timed out or failed)."
                    )

                # Re-fetch
                # Optimization: Wait a bit more?
                time.sleep(1)
                ui.status("Re-fetching tabs after fixing...")
                windows = browser.get_windows()
                if not save_all:
                    windows = windows[:1]

                if fixed_count > 0:
                    ui.status(f"✓ Fixed {fixed_count} broken tabs successfully.")

                # Exit early - don't save session file when just fixing tabs
                raise typer.Exit()
        elif (
            (fix_broken_tabs or list_broken_tabs)
            and total_broken == 0
            and not list_broken_tabs
        ):
            # Notify user when no broken tabs found (only for --fix-broken, not --list-broken)
            ui.status("No broken tabs found.")
            # Exit early - don't save session file
            raise typer.Exit()

        # 4b. Handle View Only Mode
        if "view_only" in locals() and view_only:
            ui.display_tabs(windows)
            raise typer.Exit()

        # 5. Process & Generate Markdown
        if session_date:
            try:
                dt = datetime.strptime(session_date, "%Y-%m-%d %H:%M")
            except ValueError:
                # Try time only
                try:
                    t = datetime.strptime(session_date, "%H:%M").time()
                    dt = datetime.combine(datetime.now().date(), t)
                except ValueError:
                    ui.status("Invalid date format. Using current time.")
                    dt = datetime.now()
        else:
            dt = datetime.now()

        result = generate_formatted_content(
            browser,
            windows,
            session_name,
            include_empty,
            save_all,
            dt,
            output_format.value,
        )
        final_content = result.content
        total_tabs = result.total_tabs

        # 6. Save Actions

        # Always Copy to Clipboard unless autosave?
        # JXA had options.
        # Let's copy by default if interactive.
        if not autosave:
            pyperclip.copy(final_content)

        # Save to File
        # Ensure dir exists
        output_dir.mkdir(parents=True, exist_ok=True)

        # Determine filename based on output format and whether we're saving multiple windows
        if not save_all and output_format == Format.MARKDOWN:
            # Single window filename format: "Safari Tabs | SessionName [YYYY-MM-DD HHMM]"
            # This matches the header format but removes the leading "# " and the colon in the time.
            file_date_str = dt.strftime("%Y-%m-%d %H%M")
            if session_name and session_name != "Autosaved":
                filename_base = (
                    f"{browser.name} Tabs | {session_name} [{file_date_str}]"
                )
            else:
                filename_base = f"{browser.name} Window [{file_date_str}]"
            filename = f"{filename_base}{result.extension}"
        elif save_all and output_format == Format.MARKDOWN:
            # Filename format for multiple windows in Markdown format
            file_date_str = dt.strftime("%Y-%m-%d %H%M")
            filename = (
                f"Browser Session - {browser.name} [{file_date_str}]{result.extension}"
            )
        else:
            # Filename format for non-Markdown output
            file_date_str = dt.strftime("%Y-%m-%d %H%M")
            sanitized_session_str = (
                session_name.replace("/", "-") if session_name else ""
            )
            filename = f"Browser Session - {browser.name} - {sanitized_session_str} [{file_date_str}]{result.extension}"
        file_path = output_dir / filename

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(final_content)

        # Set file dates
        set_file_dates(file_path, dt)

        # Record session name to history (skip autosave and empty names)
        if session_name and not autosave:
            from .session_history import SessionHistory

            history = SessionHistory()
            history.add_session(session_name)

        # Restore focus to terminal (or previous app)
        if current_app and current_app != browser.name:
            focus_app(current_app)

        ui.notify_success(total_tabs, str(file_path))

        # 7. Open With
        app_to_open = None
        if custom_open_with:
            app_to_open = custom_open_with
        elif open_with:
            app_to_open = open_with.value

        # Handle VS Code editor/viewer alias
        if app_to_open == MarkdownEditor.VSCODE_SHORT_ALIAS.value:
            app_to_open = MarkdownEditor.VSCODE.value

        if app_to_open:
            try:
                ui.status(f"Opening with {app_to_open}...")
                open_with_application(file_path, app_to_open)
            except Exception as e:
                ui.status(f"Failed to open with {app_to_open}: {e}")
                pass

    except KeyboardInterrupt:
        pass

    finally:
        # Restore the original frontmost window
        # This runs even if the script is interrupted (Ctrl+C) or encounters errors
        if original_window_id:
            print(f"\nRestoring frontmost window: {original_window_id}")
            try:
                browser.restore_frontmost_window(original_window_id)
            except Exception as e:
                ui.status(f"Failed to restore frontmost window: {e}")

        # Restore focus to terminal (or previous app)
        # Only if we didn't open another app that should take focus
        if current_app and current_app != browser.name and not app_to_open:
            focus_app(current_app)


if __name__ == "__main__":
    app()
