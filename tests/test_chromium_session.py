import struct
from pathlib import Path

import pytest

from save_browser_session.chromium_session import (
    find_latest_session_file,
    get_chromium_session_dir,
    get_chromium_tab_groups,
    parse_snss_tab_groups,
)


def create_snss_test_data(
    groups: list[tuple[bytes, str]],
    tabs: list[tuple[int, bytes]],
    closed_tabs: list[int] | None = None,
) -> bytes:
    """Helper to synthesize valid binary SNSS session records for testing.

    Parameters
    ----------
    groups : list[tuple[bytes, str]]
        List of (16-byte token, title) tuples.
    tabs : list[tuple[int, bytes]]
        List of (tab_id, 16-byte token) tuples.
    closed_tabs : list[int] | None
        List of tab IDs that should be marked closed.

    Returns
    -------
    bytes
        The binary content representing an SNSS session stream.
    """
    buffer: bytearray = bytearray()
    # 4-byte magic signature + 4-byte version
    buffer.extend(b"SNSS")
    buffer.extend(struct.pack("<I", 3))

    # Command 27: kCommandSetTabGroupMetadata2
    for token, title in groups:
        title_utf16: bytes = title.encode("utf-16-le")
        title_chars: int = len(title)
        # Pickle payload:
        # uint32 payload_len (16 + 4 + len(title_utf16))
        # 16-byte token
        # uint32 title char count
        # UTF-16LE title bytes
        pickle_payload: bytearray = bytearray()
        pickle_payload.extend(token)
        pickle_payload.extend(struct.pack("<I", title_chars))
        pickle_payload.extend(title_utf16)

        payload: bytearray = bytearray()
        payload.extend(struct.pack("<I", len(pickle_payload)))
        payload.extend(pickle_payload)

        # Record: uint16 size (1 + len(payload)), uint8 cmd_id (27), payload
        rec_size: int = 1 + len(payload)
        buffer.extend(struct.pack("<H", rec_size))
        buffer.append(27)
        buffer.extend(payload)

    # Command 25: kCommandSetTabGroup
    for tab_id, token in tabs:
        # payload: int32 tab_id (4), 4 bytes padding, 16 bytes token, uint8 has_group (1)
        payload = bytearray()
        payload.extend(struct.pack("<i", tab_id))
        payload.extend(b"\x00\x00\x00\x00")
        payload.extend(token)
        payload.append(1)  # has_group = True
        payload.extend(b"\x00" * 7)  # padding

        rec_size = 1 + len(payload)
        buffer.extend(struct.pack("<H", rec_size))
        buffer.append(25)
        buffer.extend(payload)

    # Command 16: kCommandTabClosed
    if closed_tabs:
        for tab_id in closed_tabs:
            payload = bytearray(struct.pack("<i", tab_id))
            rec_size = 1 + len(payload)
            buffer.extend(struct.pack("<H", rec_size))
            buffer.append(16)
            buffer.extend(payload)

    return bytes(buffer)


def test_get_chromium_session_dir() -> None:
    """Test session directory resolution across supported and unsupported browser names."""
    edge_dir: Path | None = get_chromium_session_dir("Microsoft Edge")
    assert edge_dir is not None
    assert edge_dir.name == "Sessions"
    assert "Microsoft Edge" in str(edge_dir)

    chrome_dir: Path | None = get_chromium_session_dir("Google Chrome")
    assert chrome_dir is not None
    assert "Google/Chrome" in str(chrome_dir)

    brave_dir: Path | None = get_chromium_session_dir("Brave Browser")
    assert brave_dir is not None
    assert "BraveSoftware" in str(brave_dir)

    unknown_dir: Path | None = get_chromium_session_dir("Safari")
    assert unknown_dir is None


def test_find_latest_session_file(tmp_path: Path) -> None:
    """Test finding the newest session file in a profile directory."""
    # Non-existent directory returns None
    assert find_latest_session_file(tmp_path / "non_existent") is None

    # Empty directory returns None
    empty_dir: Path = tmp_path / "empty"
    empty_dir.mkdir()
    assert find_latest_session_file(empty_dir) is None

    # Multiple session files: return the newest one
    sessions_dir: Path = tmp_path / "Sessions"
    sessions_dir.mkdir()
    old_file: Path = sessions_dir / "Session_1000"
    new_file: Path = sessions_dir / "Session_2000"
    old_file.write_text("old")
    new_file.write_text("new")

    # Set distinct modification times
    import os

    os.utime(old_file, (1000, 1000))
    os.utime(new_file, (2000, 2000))

    latest: Path | None = find_latest_session_file(sessions_dir)
    assert latest is not None
    assert latest.name == "Session_2000"


def test_parse_snss_tab_groups_valid(tmp_path: Path) -> None:
    """Test parsing a valid synthetic SNSS file with groups and assigned tabs."""
    token_a: bytes = b"A" * 16
    token_b: bytes = b"B" * 16

    data: bytes = create_snss_test_data(
        groups=[(token_a, "Work Projects"), (token_b, "Reference Reading")],
        tabs=[(101, token_a), (102, token_a), (201, token_b), (301, b"C" * 16)],
        closed_tabs=[102],
    )

    session_file: Path = tmp_path / "Session_valid"
    session_file.write_bytes(data)

    results: dict[int, str] = parse_snss_tab_groups(session_file)

    # 101 belongs to Work Projects
    assert results.get(101) == "Work Projects"
    # 102 was closed, so it should not appear
    assert 102 not in results
    # 201 belongs to Reference Reading
    assert results.get(201) == "Reference Reading"
    # 301 belongs to an unknown token without metadata, so it should not be in results
    assert 301 not in results


def test_parse_snss_tab_groups_invalid_and_corrupt(tmp_path: Path) -> None:
    """Test defensive handling of non-existent, empty, and corrupt files."""
    # Non-existent file
    assert parse_snss_tab_groups(tmp_path / "does_not_exist") == {}

    # Empty file
    empty_file: Path = tmp_path / "empty"
    empty_file.write_bytes(b"")
    assert parse_snss_tab_groups(empty_file) == {}

    # Bad magic header
    bad_magic: Path = tmp_path / "bad_magic"
    bad_magic.write_bytes(b"NOT_SNSS_FILE_HEADER")
    assert parse_snss_tab_groups(bad_magic) == {}

    # Truncated after header
    truncated: Path = tmp_path / "truncated"
    truncated.write_bytes(b"SNSS\x03\x00\x00\x00\xff\x00")
    assert parse_snss_tab_groups(truncated) == {}


def test_get_chromium_tab_groups_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that get_chromium_tab_groups returns empty dict on any failure."""
    assert get_chromium_tab_groups("Unsupported Browser Name") == {}
