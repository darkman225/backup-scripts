from datetime import datetime, timezone
from pathlib import Path
import json
import sys

from transfer import download_remote_file 
from ssh_connection import SSHConnection
from remote_files import create_marker, execute_remote_command, remove_marker
from folder_transfer import get_latest_modified_folder, get_latest_modified_folder_by_pattern, download_remote_folder 

from config import load_settings

def download_latest_folder(use_patterns: bool = False) -> None:
    """
    Download the latest modified folder from remote server.
    Args:
        use_patterns: If True, find folders by file patterns; if False, find any folder
    """
    settings = load_settings()

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = settings.local_output_dir / f"run_folder_{run_id}"
    run_dir.mkdir(parents=True, exist_ok=True)

    report: dict = {
        "run_id": run_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "remote_dir": settings.remote_dir,
        "remote_command": settings.remote_command or None,
        "patterns": settings.file_patterns,
        "selected_folder": None,
        "downloaded_local_path": None,
    }

    try:
        with SSHConnection(settings) as conn:
            marker_name = None
            command_result = None

            if settings.remote_command:
                marker_name = create_marker(conn, settings.remote_dir)
                command_result = execute_remote_command(conn, settings.remote_dir, settings.remote_command)
                report["command_result"] = {
                    "exit_code": command_result.exit_code,
                    "stdout": command_result.stdout,
                    "stderr": command_result.stderr,
                }
                if command_result.exit_code != 0:
                    raise RuntimeError(f"Remote command failed: {command_result.stderr.strip()}")

            # Find latest modified folder
            if use_patterns and settings.file_patterns:
                latest_folder = get_latest_modified_folder_by_pattern(
                    conn,
                    remote_dir=settings.remote_dir,
                    patterns=settings.file_patterns,
                    newer_than_marker=marker_name if settings.remote_command else None,
                )
            else:
                latest_folder = get_latest_modified_folder(
                    conn,
                    remote_dir=settings.remote_dir,
                    newer_than_marker=marker_name if settings.remote_command else None,
                )

            # If command didn't generate a matching folder, fallback to latest overall
            if latest_folder is None and settings.remote_command:
                latest_folder = get_latest_modified_folder(
                    conn,
                    remote_dir=settings.remote_dir,
                    newer_than_marker=None,
                )

            if latest_folder is None:
                raise FileNotFoundError("No folder found in remote directory")

            print(f"Found folder: {latest_folder.relative_path}")
            print(f"Starting download... this may take a while for large folders")

            local_path = download_remote_folder(
                conn,
                remote_absolute_path=latest_folder.absolute_path,
                remote_relative_path=latest_folder.relative_path,
                local_output_dir=run_dir,
            )

            report["selected_folder"] = {
                "relative_path": latest_folder.relative_path,
                "absolute_path": latest_folder.absolute_path,
                "modified_at_epoch": latest_folder.modified_at_epoch,
            }
            report["downloaded_local_path"] = str(local_path)

            if marker_name:
                remove_marker(conn, settings.remote_dir, marker_name)

    except Exception as exc:
        report["error"] = str(exc)
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        (run_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Failed: {exc}")
        print(f"Report: {run_dir / 'report.json'}")
        sys.exit(1)

    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    (run_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Run directory: {run_dir}")
    print(f"Downloaded folder: {report['downloaded_local_path']}")
    print(f"Report: {run_dir / 'report.json'}")


if __name__ == "__main__":
    # Download latest folder (use patterns if available)
    download_latest_folder(use_patterns=True)
