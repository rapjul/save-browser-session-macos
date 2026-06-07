from unittest.mock import MagicMock, patch
from typer.testing import CliRunner

from save_browser_session.main import app

runner = CliRunner()


def test_help_argument() -> None:
    """Test that the help argument works and displays options correctly."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    # Rich formatting can be complex, just check basic keywords exist
    out = result.stdout.lower()
    assert "save tabs" in out or "usage" in out

    # Verify main options are present (lenient check)
    assert "current" in out
    assert "all" in out
    assert "browser" in out
    assert "open-with" in out
    assert "format" in out
    assert "fix-broken" in out
    assert "list-broken" in out


def test_annotated_defaults_shown_in_help() -> None:
    """Verify that defaults (or absence of defaults) are correctly displayed."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    out = result.stdout.lower()

    # Check for some known defaults or help text
    assert "markdown" in out  # Default format
    assert "json" in out


@patch("save_browser_session.main.set_file_dates")
@patch("save_browser_session.main.focus_app")
@patch("save_browser_session.main.get_current_app_name")
@patch("save_browser_session.main.pyperclip")
@patch("save_browser_session.main.get_browser_instance")
@patch("save_browser_session.main.is_app_running")
@patch("save_browser_session.main.generate_formatted_content")
@patch("save_browser_session.main.get_ui")
@patch("builtins.open", new_callable=MagicMock)
def test_browser_aliases(
    mock_open: MagicMock,
    mock_get_ui: MagicMock,
    mock_generate: MagicMock,
    mock_is_running: MagicMock,
    mock_get_browser: MagicMock,
    mock_pyperclip: MagicMock,
    mock_get_current_app: MagicMock,
    mock_focus_app: MagicMock,
    mock_set_dates: MagicMock,
) -> None:
    """Test that browser aliases like 'Edge' and 'Chrome' map to the correct names.

    Parameters:
        mock_open (MagicMock): Mocked builtins.open file writer function.
        mock_get_ui (MagicMock): Mocked UI helper function.
        mock_generate (MagicMock): Mocked session formatting function.
        mock_is_running (MagicMock): Mocked application running checker.
        mock_get_browser (MagicMock): Mocked browser instance retriever.
        mock_pyperclip (MagicMock): Mocked pyperclip clipboard module.
        mock_get_current_app (MagicMock): Mocked get_current_app_name utility.
        mock_focus_app (MagicMock): Mocked focus_app utility.
        mock_set_dates (MagicMock): Mocked set_file_dates utility.
    """
    # Setup standard mocks to allow CLI execution without side-effects
    mock_ui = MagicMock()
    mock_get_ui.return_value = mock_ui
    mock_browser = MagicMock()
    mock_get_browser.return_value = mock_browser
    mock_browser.get_windows.return_value = [MagicMock()]
    mock_browser.name = "Test Browser"
    mock_browser.get_frontmost_window_id.return_value = None
    mock_is_running.return_value = True

    mock_result = MagicMock()
    mock_result.content = "Mocked Session Content"
    mock_result.total_tabs = 1
    mock_result.extension = ".md"
    mock_generate.return_value = mock_result

    # 1. Test "Edge" alias resolves to "Microsoft Edge"
    result_edge = runner.invoke(app, ["--browser", "Edge", "--autosave"])
    assert result_edge.exit_code == 0
    mock_get_browser.assert_any_call("Microsoft Edge")

    # 2. Test "Chrome" alias resolves to "Google Chrome"
    result_chrome = runner.invoke(app, ["--browser", "Chrome", "--autosave"])
    assert result_chrome.exit_code == 0
    mock_get_browser.assert_any_call("Google Chrome")
