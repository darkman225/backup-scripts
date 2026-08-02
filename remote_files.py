import shlex
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ssh_connection import SSHConnection


@dataclass
class RemoteExecResult:
    exit_code: int
    stdout: str
    stderr: str


@dataclass
class RemoteFileInfo:
    relative_path: str
    absolute_path: str
    modified_at_epoch: int


def create_marker(conn: SSHConnection, remote_dir: str) -> str:
    marker_name = f".marker_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    cmd = f"cd {shlex.quote(remote_dir)} && : > {shlex.quote(marker_name)}"
    code, _, err = conn.run(cmd)
    if code != 0:
        raise RuntimeError(f"Unable to create marker file: {err.strip()}")
    return marker_name


def remove_marker(conn: SSHConnection, remote_dir: str, marker_name: str) -> None:
    cmd = f"cd {shlex.quote(remote_dir)} && rm -f {shlex.quote(marker_name)}"
    conn.run(cmd)


def execute_remote_command(conn: SSHConnection, remote_dir: str, command: str) -> RemoteExecResult:
    code, out, err = conn.run_in_dir(remote_dir, command)
    return RemoteExecResult(exit_code=code, stdout=out, stderr=err)


def _build_name_expression(patterns: list[str]) -> str:
    if not patterns:
        return "-type f"

    chunks = []
    for idx, pattern in enumerate(patterns):
        item = f"-name {shlex.quote(pattern)}"
        if idx == 0:
            chunks.append(item)
        else:
            chunks.append(f"-o {item}")
    return f"-type f \\( {' '.join(chunks)} \\)"


def get_latest_modified_file(
    conn: SSHConnection,
    remote_dir: str,
    patterns: Optional[list[str]] = None,
    newer_than_marker: Optional[str] = None,
) -> Optional[RemoteFileInfo]:
    patterns = patterns or []
    name_expr = _build_name_expression(patterns)

    newer_clause = ""
    if newer_than_marker:
        newer_clause = f"-newer {shlex.quote(newer_than_marker)} -a "

    # Works on GNU + BSD stat by trying GNU first.
    find_command = (
        f"cd {shlex.quote(remote_dir)} && "
        f"find . {name_expr} -a {newer_clause}! -name '.marker_*' -print0 | "
        "xargs -0 -I {} sh -c '\n"
        "f=\"{}\"; "
        "(stat -c \"%Y %n\" \"$f\" 2>/dev/null || stat -f \"%m %N\" \"$f\" 2>/dev/null)\n"
        "' | sort -nr | head -1"
    )

    code, out, err = conn.run(find_command)
    if code != 0 and not out.strip():
        raise RuntimeError(f"Unable to list latest file: {err.strip()}")

    line = out.strip()
    if not line:
        return None

    first_space = line.find(" ")
    if first_space == -1:
        return None

    mtime = int(line[:first_space])
    path = line[first_space + 1 :].strip()

    if path.startswith("./"):
        path = path[2:]

    absolute = f"{remote_dir.rstrip('/')}/{path}"
    return RemoteFileInfo(relative_path=path, absolute_path=absolute, modified_at_epoch=mtime)
