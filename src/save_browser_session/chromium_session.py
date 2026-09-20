import struct
from pathlib import Path

# Mapping of browser names to their macOS Application Support directories
CHROMIUM_APP_SUPPORT_DIRS: dict[str, str] = {
    "Microsoft Edge": "Microsoft Edge",
    "Edge": "Microsoft Edge",
    "Google Chrome": "Google/Chrome",
    "Chrome": "Google/Chrome",
    "Chromium": "Chromium",
    "Brave Browser": "BraveSoftware/Brave-Browser",
    "Vivaldi": "Vivaldi",
    "Opera": "com.operasoftware.Opera",
}


def get_chromium_session_dir(
    browser_name: str, profile_name: str = "Default"
) -> Path | None:
    """Locate the Sessions directory for a given Chromium browser and profile.

    Parameters
    ----------
    browser_name : str
        The user-facing or internal name of the browser (e.g. 'Microsoft Edge').
    profile_name : str
        The browser profile name (defaults to 'Default').

    Returns
    -------
    Path | None
        The path to the Sessions directory, or None if the browser is unsupported.
    """
    rel_path: str | None = CHROMIUM_APP_SUPPORT_DIRS.get(browser_name)
    if not rel_path:
        return None

    app_support: Path = Path.home() / "Library/Application Support"
    sessions_dir: Path = app_support / rel_path / profile_name / "Sessions"
    return sessions_dir


def find_latest_session_file(sessions_dir: Path) -> Path | None:
    """Find the most recently modified Session_* file in the given directory.

    Parameters
    ----------
    sessions_dir : Path
        The directory containing Chromium session state files.

    Returns
    -------
    Path | None
        The path to the latest session file, or None if no session files exist.
    """
    try:
        if not sessions_dir.is_dir():
            return None
        session_files: list[Path] = sorted(
            sessions_dir.glob("Session_*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return session_files[0] if session_files else None
    except (OSError, PermissionError):
        return None


def parse_snss_tab_groups(session_file: Path) -> dict[int, str]:
    """Parse an SNSS binary session file and return a mapping of tab ID to group name.

    Parameters
    ----------
    session_file : Path
        The binary Session_* file to parse.

    Returns
    -------
    dict[int, str]
        A mapping from integer tab IDs to their string group titles.
    """
    tab_to_group: dict[int, str] = {}
    tab_to_token: dict[int, bytes] = {}
    token_to_title: dict[bytes, str] = {}

    try:
        if not session_file.is_file():
            return {}

        with open(session_file, "rb") as f:
            magic: bytes = f.read(4)
            if magic != b"SNSS":
                return {}

            # Read 4-byte version integer (typically 1, 2, or 3)
            version_bytes: bytes = f.read(4)
            if len(version_bytes) < 4:
                return {}

            while True:
                size_bytes: bytes = f.read(2)
                if len(size_bytes) < 2:
                    break

                size: int = struct.unpack("<H", size_bytes)[0]
                if size == 0:
                    continue

                cmd_bytes: bytes = f.read(1)
                if len(cmd_bytes) < 1:
                    break
                cmd_id: int = cmd_bytes[0]

                payload_len: int = size - 1
                payload: bytes = f.read(payload_len)
                if len(payload) < payload_len:
                    break

                # Command 16: kCommandTabClosed
                # Payload: int32 tab_id (or int64 in newer builds)
                if cmd_id == 16 and len(payload) >= 4:
                    tab_id: int = struct.unpack("<i", payload[:4])[0]
                    tab_to_token.pop(tab_id, None)

                # Command 25: kCommandSetTabGroup
                # Payload: int64 tab_id (or int32), 16-byte group token, bool has_group
                elif cmd_id == 25 and len(payload) >= 25:
                    tab_id = struct.unpack("<i", payload[:4])[0]
                    token: bytes = payload[8:24]
                    has_group: bool = bool(payload[24])
                    if has_group:
                        tab_to_token[tab_id] = token
                    else:
                        tab_to_token.pop(tab_id, None)

                # Command 27: kCommandSetTabGroupMetadata2 (base::Pickle)
                # Pickle header: uint32 payload size
                # 16-byte group token
                # uint32 string16 length (characters)
                # UTF-16LE characters (length * 2 bytes)
                elif cmd_id == 27 and len(payload) >= 24:
                    token = payload[4:20]
                    title_char_len: int = struct.unpack("<I", payload[20:24])[0]
                    title_bytes_len: int = title_char_len * 2
                    title_start: int = 24
                    title_end: int = title_start + title_bytes_len
                    if len(payload) >= title_end:
                        title_bytes: bytes = payload[title_start:title_end]
                        title: str = title_bytes.decode("utf-16-le", errors="ignore")
                        token_to_title[token] = title

        for tid, tok in tab_to_token.items():
            group_name: str | None = token_to_title.get(tok)
            if group_name:
                tab_to_group[tid] = group_name

        return tab_to_group

    except (OSError, PermissionError, struct.error, ValueError, UnicodeDecodeError):
        return {}


def get_chromium_tab_groups(
    browser_name: str, profile_name: str = "Default"
) -> dict[int, str]:
    """Retrieve tab group names for open tabs in a Chromium-based browser.

    Parameters
    ----------
    browser_name : str
        The name of the browser (e.g. 'Microsoft Edge', 'Google Chrome').
    profile_name : str
        The browser profile name (defaults to 'Default').

    Returns
    -------
    dict[int, str]
        A mapping from integer tab IDs to their group title, or an empty dict if unavailable.
    """
    sessions_dir: Path | None = get_chromium_session_dir(browser_name, profile_name)
    if not sessions_dir:
        return {}

    session_file: Path | None = find_latest_session_file(sessions_dir)
    if not session_file:
        return {}

    return parse_snss_tab_groups(session_file)
