from pathlib import Path

from ssh_connection import SSHConnection


def download_remote_file(
    conn: SSHConnection,
    remote_absolute_path: str,
    remote_relative_path: str,
    local_output_dir: Path,
) -> Path:
    local_output_dir.mkdir(parents=True, exist_ok=True)
    local_path = local_output_dir / remote_relative_path
    local_path.parent.mkdir(parents=True, exist_ok=True)

    with conn.open_sftp() as sftp:
        sftp.get(remote_absolute_path, str(local_path))

    return local_path
