import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ssh_connection import SSHConnection


@dataclass
class RemoteFolderInfo:
    relative_path: str
    absolute_path: str
    modified_at_epoch: int


def get_latest_modified_folder(
    conn: SSHConnection,
    remote_dir: str,
    newer_than_marker: Optional[str] = None,
) -> Optional[RemoteFolderInfo]:
    """
    Find the latest modified folder in remote_dir.
    
    Args:
        conn: SSHConnection instance
        remote_dir: Remote directory to search in
        newer_than_marker: Optional marker file to find folders modified after this file
    
    Returns:
        RemoteFolderInfo with folder path and modification time, or None if no folder found
    """
    newer_clause = ""
    if newer_than_marker:
        newer_clause = f"-newer {shlex.quote(newer_than_marker)} -a "

    # Find the latest modified folder (type d)
    find_command = (
        f"cd /&& "
        f"cd {shlex.quote(remote_dir)} && "
        f"find . -type d {newer_clause}! -name '.marker_*' -print0 | "
        "xargs -0 -I {} sh -c '\n"
        "f=\"{}\"; "
        "(stat -c \"%Y %n\" \"$f\" 2>/dev/null || stat -f \"%m %N\" \"$f\" 2>/dev/null)\n"
        "' | sort -nr | head -1"
    )

    code, out, err = conn.run(find_command)
    if code != 0 and not out.strip():
        raise RuntimeError(f"Unable to list latest folder: {err.strip()}")

    line = out.strip()
    if not line:
        return None

    first_space = line.find(" ")
    if first_space == -1:
        return None

    mtime = int(line[:first_space])
    path = line[first_space + 1:].strip()

    if path.startswith("./"):
        path = path[2:]

    # Skip root directory
    if not path or path == ".":
        return None

    absolute = f"{remote_dir.rstrip('/')}/{path}"
    return RemoteFolderInfo(relative_path=path, absolute_path=absolute, modified_at_epoch=mtime)


def download_remote_folder(
    conn: SSHConnection,
    remote_absolute_path: str,
    remote_relative_path: str,
    local_output_dir: Path,
) -> Path:
    """
    Download a complete remote folder and its contents to local directory.
    
    Args:
        conn: SSHConnection instance
        remote_absolute_path: Absolute path of the remote folder
        remote_relative_path: Relative path of the remote folder
        local_output_dir: Local output directory where folder will be downloaded
    
    Returns:
        Path to the downloaded local folder
    """
    local_output_dir.mkdir(parents=True, exist_ok=True)
    local_folder_path = local_output_dir / remote_relative_path
    local_folder_path.mkdir(parents=True, exist_ok=True)

    with conn.open_sftp() as sftp:
        _download_folder_recursive(sftp, remote_absolute_path, local_folder_path)

    return local_folder_path


def _download_folder_recursive(sftp, remote_path: str, local_path: Path) -> None:
    """
    Recursively download a folder and its contents via SFTP.
    
    Args:
        sftp: SFTP client
        remote_path: Remote folder path
        local_path: Local folder path
    """
    try:
        # List contents of remote folder
        items = sftp.listdir_attr(remote_path)
    except IOError as e:
        raise RuntimeError(f"Unable to read remote folder {remote_path}: {e}")

    for item in items:
        remote_item_path = f"{remote_path.rstrip('/')}/{item.filename}"
        local_item_path = local_path / item.filename

        # Check if it's a directory (bit 14 in mode is set for directories)
        is_dir = (item.st_mode >> 14) & 1

        if is_dir:
            # Create local directory and recurse
            local_item_path.mkdir(parents=True, exist_ok=True)
            _download_folder_recursive(sftp, remote_item_path, local_item_path)
        else:
            # Download file
            try:
                sftp.get(remote_item_path, str(local_item_path))
            except IOError as e:
                raise RuntimeError(f"Unable to download file {remote_item_path}: {e}")


def get_latest_modified_folder_by_pattern(
    conn: SSHConnection,
    remote_dir: str,
    patterns: Optional[list[str]] = None,
    newer_than_marker: Optional[str] = None,
) -> Optional[RemoteFolderInfo]:
    """
    Find the latest modified folder containing files matching specified patterns.
    
    Args:
        conn: SSHConnection instance
        remote_dir: Remote directory to search in
        patterns: List of file patterns (e.g., ['*.log', '*.txt'])
        newer_than_marker: Optional marker file to find folders modified after this file
    
    Returns:
        RemoteFolderInfo of the folder containing matching files, or None if no folder found
    """
    patterns = patterns or []
    
    # Build the pattern expression for find
    if patterns:
        pattern_chunks = []
        for pattern in patterns:
            pattern_chunks.append(f"-name {shlex.quote(pattern)}")
        pattern_expr = f"\\( {' -o '.join(pattern_chunks)} \\)"
    else:
        pattern_expr = ""

    newer_clause = ""
    if newer_than_marker:
        newer_clause = f"-newer {shlex.quote(newer_than_marker)} -a "

    # Find folders containing matching files
    find_command = (
        f"cd {shlex.quote(remote_dir)} && "
        f"find . -type f {pattern_expr} {newer_clause}! -name '.marker_*' -print0 | "
        "xargs -0 -I {} dirname {} | sort -u | while read dir; do\n"
        "  (stat -c \"%Y %n\" \"$dir\" 2>/dev/null || stat -f \"%m %N\" \"$dir\" 2>/dev/null)\n"
        "done | sort -nr | head -1"
    )

    code, out, err = conn.run(find_command)
    if code != 0 and not out.strip():
        raise RuntimeError(f"Unable to list latest folder by pattern: {err.strip()}")

    line = out.strip()
    if not line:
        return None

    first_space = line.find(" ")
    if first_space == -1:
        return None

    mtime = int(line[:first_space])
    path = line[first_space + 1:].strip()

    if path.startswith("./"):
        path = path[2:]

    if not path:
        return None

    absolute = f"{remote_dir.rstrip('/')}/{path}"
    return RemoteFolderInfo(relative_path=path, absolute_path=absolute, modified_at_epoch=mtime)
