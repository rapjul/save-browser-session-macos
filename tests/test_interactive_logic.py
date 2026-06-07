from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from save_browser_session.main import app

runner = CliRunner()


@patch("save_browser_session.main.set_file_dates")
@patch("save_browser_session.main.focus_app")
@patch("save_browser_session.main.get_current_app_name")
@patch("save_browser_session.main.get_ui")
@patch("save_browser_session.main.get_browser_instance")
@patch("save_browser_session.main.is_app_running")
@patch("save_browser_session.main.generate_formatted_content")
@patch("save_browser_session.main.pyperclip")
@patch("builtins.open", new_callable=MagicMock)
def test_interactive_session_name_prompt(
    mock_open: MagicMock,
    mock_pyperclip: MagicMock,
    mock_generate: MagicMock,
    mock_is_running: MagicMock,
    mock_get_browser: MagicMock,
    mock_get_ui: MagicMock,
    mock_get_current_app: MagicMock,
    mock_focus_app: MagicMock,
    mock_set_dates: MagicMock,
) -> None:
    # Setup Mocks
    mock_ui = MagicMock()
    mock_get_ui.return_value = mock_ui
    mock_browser = MagicMock()
    mock_get_browser.return_value = mock_browser
    mock_browser.get_windows.return_value = [MagicMock()]
    mock_browser.name = "Safari"  # type: ignore[misc]
    mock_browser.id = 1  # type: ignore[misc]
    mock_browser.get_frontmost_window_id.return_value = None  # type: ignore[misc]
    mock_is_running.return_value = True

    # When no --current or --all flag is provided, ask_scope is called
    # Return False (current window) so that ask_session_name gets called
    mock_ui.ask_scope.return_value = False  # type: ignore[misc]
    mock_ui.ask_session_name_with_suggestions.return_value = "Prompted Name"  # type: ignore[misc]

    mock_result = MagicMock()
    mock_result.content = "Content"  # type: ignore[misc]
    mock_result.total_tabs = 1  # type: ignore[misc]
    mock_result.extension = ".md"  # type: ignore[misc]
    mock_generate.return_value = mock_result

    # 1. Test when NO --session-name flag is provided -> Should prompt for scope AND session name
    result = runner.invoke(app, ["--browser", "Safari"])
    assert result.exit_code == 0

    # Should ask for both scope and session name
    mock_ui.ask_scope.assert_called_once()  # type: ignore[misc]
    mock_ui.ask_session_name_with_suggestions.assert_called_once()  # type: ignore[misc]

    # Verify generate called with prompted name (3rd arg)
    args, _ = mock_generate.call_args
    assert args[2] == "Prompted Name"


@patch("save_browser_session.main.set_file_dates")
@patch("save_browser_session.main.focus_app")
@patch("save_browser_session.main.get_current_app_name")
@patch("save_browser_session.main.get_ui")
@patch("save_browser_session.main.get_browser_instance")
@patch("save_browser_session.main.is_app_running")
@patch("save_browser_session.main.generate_formatted_content")
@patch("save_browser_session.main.pyperclip")
@patch("builtins.open", new_callable=MagicMock)
def test_flag_session_name_bypass_prompt(
    mock_open: MagicMock,
    mock_pyperclip: MagicMock,
    mock_generate: MagicMock,
    mock_is_running: MagicMock,
    mock_get_browser: MagicMock,
    mock_get_ui: MagicMock,
    mock_get_current_app: MagicMock,
    mock_focus_app: MagicMock,
    mock_set_dates: MagicMock,
) -> None:
    # Setup Mocks
    mock_ui = MagicMock()
    mock_get_ui.return_value = mock_ui
    mock_browser = MagicMock()
    mock_get_browser.return_value = mock_browser
    mock_browser.get_windows.return_value = [MagicMock()]
    mock_browser.name = "Safari"  # type: ignore[misc]
    mock_browser.get_frontmost_window_id.return_value = None  # type: ignore[misc]
    mock_is_running.return_value = True

    # When --session-name is provided, scope will be asked but session name won't
    mock_ui.ask_scope.return_value = False  # type: ignore[misc]  # Choose current window

    mock_result = MagicMock()
    mock_result.content = "Content"  # type: ignore[misc]
    mock_result.total_tabs = 1  # type: ignore[misc]
    mock_result.extension = ".md"  # type: ignore[misc]
    mock_generate.return_value = mock_result

    # 2. Test when --session-name FLAG IS provided -> Should ask scope but NOT session name
    result = runner.invoke(app, ["--browser", "Safari", "--session-name", "Flag Name"])
    assert result.exit_code == 0

    # Should ask for scope (no window flag provided) but not session name (provided via flag)
    mock_ui.ask_scope.assert_called_once()  # type: ignore[misc]
    mock_ui.ask_session_name.assert_not_called()  # type: ignore[misc]

    # Verify generate called with flag name
    args, _ = mock_generate.call_args
    assert args[2] == "Flag Name"


@patch("save_browser_session.main.set_file_dates")
@patch("save_browser_session.main.focus_app")
@patch("save_browser_session.main.get_current_app_name")
@patch("save_browser_session.main.get_ui")
@patch("save_browser_session.main.get_browser_instance")
@patch("save_browser_session.main.is_app_running")
@patch("save_browser_session.main.generate_formatted_content")
@patch("save_browser_session.main.pyperclip")
@patch("builtins.open", new_callable=MagicMock)
def test_autosave_bypass_prompt(
    mock_open: MagicMock,
    mock_pyperclip: MagicMock,
    mock_generate: MagicMock,
    mock_is_running: MagicMock,
    mock_get_browser: MagicMock,
    mock_get_ui: MagicMock,
    mock_get_current_app: MagicMock,
    mock_focus_app: MagicMock,
    mock_set_dates: MagicMock,
) -> None:
    # Setup Mocks
    mock_ui = MagicMock()
    mock_get_ui.return_value = mock_ui
    mock_browser = MagicMock()
    mock_get_browser.return_value = mock_browser
    mock_browser.get_windows.return_value = [MagicMock()]
    mock_browser.name = "Safari"  # type: ignore[misc]
    mock_browser.get_frontmost_window_id.return_value = None  # type: ignore[misc]
    mock_is_running.return_value = True

    mock_result = MagicMock()
    mock_result.content = "Content"  # type: ignore[misc]
    mock_result.total_tabs = 1  # type: ignore[misc]
    mock_result.extension = ".md"  # type: ignore[misc]
    mock_generate.return_value = mock_result

    # 3. Autosave -> Should NOT prompt for scope or session name, Name="Autosaved"
    result = runner.invoke(app, ["--browser", "Safari", "--autosave"])
    assert result.exit_code == 0

    # In autosave mode, no prompts should occur
    mock_ui.ask_scope.assert_not_called()  # type: ignore[misc]
    mock_ui.ask_session_name.assert_not_called()  # type: ignore[misc]

    # Verify generate called with "Autosaved" name
    args, _ = mock_generate.call_args
    assert args[2] == "Autosaved"
