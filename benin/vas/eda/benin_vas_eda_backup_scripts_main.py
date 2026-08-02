"""
Example script demonstrating how to download the latest modified folder and its contents.

This script extends the existing backup functionality to work with entire folders
instead of individual files.
"""
from datetime import datetime, timezone
from pathlib import Path
import json
import sys

from remote_ressource import download_remote_resource, get_remote_resource
from modified_period import is_modified_older_than_days
from transfer import download_remote_file 
from ssh_connection import SSHConnection
from remote_files import create_marker, execute_remote_command, remove_marker
from folder_transfer import get_latest_modified_folder, get_latest_modified_folder_by_pattern, download_remote_folder 

from config import load_settings

def download_remote_backup(use_patterns: bool = False) -> None:
    """
    Download the latest modified data from remote server.
    Args:
        use_patterns: If True, find dat by file patterns; if False, find any data
    """
    settings1 = load_settings(".env.eda1")
    settings2 = load_settings(".env.eda2")

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir_eda1 = Path(settings1.local_dir) 
    run_dir_eda2 = Path(settings2.local_dir) 
    report_dir = Path("D:/huawei_dev_project/backups/benin/vas/eda/")
    run_dir_eda1.mkdir(parents=True, exist_ok=True)
    run_dir_eda2.mkdir(parents=True, exist_ok=True)

    report: dict = {
        "run_id": run_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "remote_eda1_dir": settings1.remote_dir,
        "remote_eda2_dir": settings2.remote_dir,
        "remote_eda1_command": settings1.remote_command or None,
        "remote_eda2_command": settings2.remote_command or None,
        "eda1_patterns": settings1.file_patterns,
        "eda2_patterns": settings2.file_patterns,
        "selected_ressouces": None,
        "downloaded_local_path": None,
    }

    try:
        with SSHConnection(settings1) as conn1, SSHConnection(settings2) as conn2:
            marker_name = None
            command_result_eda1 = None
            command_result_eda2 = None

            eda1_lastest_data_selected = get_remote_resource(
                is_file=False,
                conn=conn1,
                remote_dir=settings1.remote_dir,
                patterns=settings1.file_patterns if use_patterns else None,
                newer_than_marker=None,
            )

            eda2_lastest_data_selected = get_remote_resource(
                is_file=False,
                conn=conn2,
                remote_dir=settings2.remote_dir,
                patterns=settings2.file_patterns if use_patterns else None,
                newer_than_marker=None,
            )

            if eda1_lastest_data_selected is None or is_modified_older_than_days(eda1_lastest_data_selected.modified_at_epoch, 14):
                if settings1.remote_command:
                    marker_name = create_marker(conn1, settings1.remote_dir)
                    command_result_eda1 = execute_remote_command(conn1, settings1.remote_dir, settings1.remote_command)
                    report["command_result_eda1"] = {
                        "exit_code": command_result_eda1.exit_code,
                        "stdout": command_result_eda1.stdout,
                        "stderr": command_result_eda1.stderr,
                    }
                    if command_result_eda1.exit_code != 0:
                        raise RuntimeError(f"Remote command failed: {command_result_eda1.stderr.strip()}")

                else:
                    print("No recent data found in EDA1 and no remote command specified to generate new data.")
                    raise FileNotFoundError("No recent data found in EDA1.")
            else:
                print(f"Found recent data in EDA1: {eda1_lastest_data_selected.relative_path}")
                print(f"Starting download... this may take a while for large folders")
                local_path = download_remote_resource(
                    is_file=False,
                    conn=conn1,
                    remote_absolute_path=eda1_lastest_data_selected.absolute_path,
                    remote_relative_path=eda1_lastest_data_selected.relative_path,
                    local_output_dir=run_dir_eda1,
                )

            if eda2_lastest_data_selected is None or is_modified_older_than_days(eda2_lastest_data_selected.modified_at_epoch, 14):
                if settings2.remote_command:
                    marker_name = create_marker(conn2, settings2.remote_dir)
                    command_result_eda2 = execute_remote_command(conn2, settings2.remote_dir, settings2.remote_command)
                    report["command_result_eda2"] = {
                        "exit_code": command_result_eda2.exit_code,
                        "stdout": command_result_eda2.stdout,
                        "stderr": command_result_eda2.stderr,
                    }
                    if command_result_eda2.exit_code != 0:
                        raise RuntimeError(f"Remote command failed: {command_result_eda2.stderr.strip()}")

                else:
                    print("No recent data found in EDA2 and no remote command specified to generate new data.")
                    raise FileNotFoundError("No recent data found in EDA2.")
            else:
                print(f"Found recent data in EDA2: {eda2_lastest_data_selected.relative_path}")
                print(f"Starting download... this may take a while for large folders")
                local_path = download_remote_resource(
                    is_file=False,
                    conn=conn2,
                    remote_absolute_path=eda2_lastest_data_selected.absolute_path,
                    remote_relative_path=eda2_lastest_data_selected.relative_path,
                    local_output_dir=run_dir_eda2,
                )

           
            report["selected_ressouces"] = {
                "eda1_relative_path": eda1_lastest_data_selected.relative_path if eda1_lastest_data_selected else None,
                "eda1_absolute_path": eda1_lastest_data_selected.absolute_path if eda1_lastest_data_selected else None,
                "eda1_modified_at_epoch": eda1_lastest_data_selected.modified_at_epoch if eda1_lastest_data_selected else None,
                "eda2_relative_path": eda2_lastest_data_selected.relative_path if eda2_lastest_data_selected else None,
                "eda2_absolute_path": eda2_lastest_data_selected.absolute_path if eda2_lastest_data_selected else None,
                "eda2_modified_at_epoch": eda2_lastest_data_selected.modified_at_epoch if eda2_lastest_data_selected else None,
            }

            report["downloaded_local_path"] = {
                "eda1_local_path": str(run_dir_eda1),
                "eda2_local_path": str(run_dir_eda2),
            }

            if marker_name:
                remove_marker(conn1, settings1.remote_dir, marker_name)
                remove_marker(conn2, settings2.remote_dir, marker_name )

    except Exception as exc:
        report["error"] = str(exc)
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        (report_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Failed: {exc}")
        print(f"Report: {report_dir / 'report.json'}")
        sys.exit(1)

    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    (report_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Run directory: {report_dir}")
    print(f"Downloaded folder: {report['downloaded_local_path']}")
    print(f"Report: {report_dir / 'report.json'}")


if __name__ == "__main__":
    # Download latest folder (use patterns if available)
    download_remote_backup(use_patterns=False)
