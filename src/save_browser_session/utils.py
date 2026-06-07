import os
import subprocess
from datetime import datetime
from pathlib import Path


def set_file_dates(file_path: Path, dt: datetime):
    """
    Sets the creation and modification timestamps of a file.
    Uses 'SetFile' (macOS) for creation time and os.utime for modification time.
    """
    # format for SetFile: "mm/dd/yyyy hh:mm:ss"
    # Note: SetFile expects month/day/year
    date_str = dt.strftime("%Y-%m-%d H:%M:%S")

    # 1. Set Creation Date (macOS specific)
    try:
        subprocess.run(
            ["SetFile", "-d", date_str, str(file_path)],
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        # SetFile might not be installed or not on macOS
        pass

    # 2. Set Modification (and Access) Date
    timestamp = dt.timestamp()
    os.utime(file_path, (timestamp, timestamp))


def get_current_app_name() -> str:
    """
    Returns the name of the frontmost application using AppleScript.
    """
    try:
        result = subprocess.run(
            [
                "osascript",
                "-e",
                'tell application "System Events" to name of first application process whose frontmost is true',
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return ""


def focus_app(app_name: str):
    """
    Activates the specified application.
    """
    if not app_name:
        return
    try:
        subprocess.run(
            [
                "osascript",
                "-e",
                f'tell application "{app_name}" to activate',
            ],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        pass


def open_with_application(file_path: Path, app_name: str):
    """
    Opens the specified file with the given application.
    """
    subprocess.run(["open", "-a", app_name, str(file_path)], check=True)


def is_app_running(app_name: str) -> bool:
    """
    Checks if an application is running using pgrep.
    Uses exact match (-x) to avoid false positives (e.g. extensions).
    """
    try:
        subprocess.run(
            ["pgrep", "-x", app_name],
            capture_output=True,
            check=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def check_connection(
    host: str = "8.8.8.8",
    port: int = 53,
    timeout: int = 3,
) -> bool:
    """
    Checks for network connectivity by attempting to connect to a reliable host.
    Defaults to Google DNS (8.8.8.8) on port 53 (DNS).
    """
    import socket

    try:
        # socket.setdefaulttimeout(timeout) # Global, maybe unsafe?
        # Better to use timeout in create_connection
        socket.create_connection((host, port), timeout=timeout)
        return True
    except OSError:
        return False
