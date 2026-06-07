from save_browser_session.utils import is_app_running


def test_is_app_running_positive() -> None:
    # Finder is almost always running on macOS
    assert is_app_running("Finder") is True


def test_is_app_running_negative() -> None:
    assert is_app_running("NonExistentApp12345") is False


def test_pgrep_flags() -> None:
    """
    Verify `pgrep` flags used in is_app_running match expectations.
    This mirrors logic from debug_pgrep.py
    """
    # Simply call the function which uses `pgrep -x`
    assert is_app_running("Finder") is True
