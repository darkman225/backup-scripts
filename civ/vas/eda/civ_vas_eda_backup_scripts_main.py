from datetime import datetime, timezone
from pathlib import Path
import json
import sys
from typing import Optional

from backup_scripts.report_request import execution_report_v2
from remote_ressource import download_remote_resource, get_remote_resource

from modified_period import is_modified_older_than_days
from ssh_connection import SSHConnection
from remote_files import create_marker, execute_remote_command, remove_marker
from keep_last_items import keep_last_5_items

from config import load_settings



def download_remote_backup(use_patterns: bool = False, env_path: str = "./././cers/.env.civ.eda") -> None:
    """
    Download the latest modified data from remote server.
    Args:
        use_patterns: If True, find dat by file patterns; if False, find any data
    """
    settings = load_settings(env_path)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir_yoeda = Path(f"{settings.local_output_dir}/yoeda")
    run_dir_abeda = Path(f"{settings.local_output_dir}/abeda")
    report_dir = Path(f"{settings.local_output_dir}/reports")
    run_dir_yoeda.mkdir(parents=True, exist_ok=True)
    run_dir_abeda.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file_path = report_dir / "report.json"
    remote_yoeda_dir = settings.remote_dir+"/yoeda"
    remote_abeda_dir = settings.remote_dir+"/abeda"

    yoeda_local_path: Optional[Path] = None
    abeda_local_path: Optional[Path] = None

    job_name = "civ_vas_eda_backup"

    report: dict = {
        "run_id": run_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "remote_yoeda_dir": remote_yoeda_dir,
        "remote_abeda_dir": remote_abeda_dir,
        "remote_command": settings.remote_command or None,
        "patterns": settings.file_patterns if use_patterns else None,
        "selected_ressouces": None,
        "downloaded_local_path": None,
    }

    try:
        with SSHConnection(settings) as conn:
            marker_name = None
            command_result_yoeda = None
            command_result_abeda = None

            yoeda_lastest_data_selected = get_remote_resource(
                is_file=False,
                conn=conn,
                remote_dir=remote_yoeda_dir,
                patterns=settings.file_patterns if use_patterns else None,
                newer_than_marker=None,
            )

            abeda_lastest_data_selected = get_remote_resource(
                is_file=False,
                conn=conn,
                remote_dir=remote_abeda_dir,
                patterns=settings.file_patterns if use_patterns else None,
                newer_than_marker=None,
            )

            yoeda_started_at = datetime.now(timezone.utc).isoformat()
            yoeda_error: Optional[str] = None
            try:
                if yoeda_lastest_data_selected is None or is_modified_older_than_days(yoeda_lastest_data_selected.modified_at_epoch, 2):
                    if settings.remote_command:
                        marker_name = create_marker(conn, remote_yoeda_dir)
                        command_result_yoeda = execute_remote_command(conn, remote_yoeda_dir, settings.remote_command)
                        report["command_result_yoeda"] = {
                            "exit_code": command_result_yoeda.exit_code,
                            "stdout": command_result_yoeda.stdout,
                            "stderr": command_result_yoeda.stderr,
                        }
                        if command_result_yoeda.exit_code != 0:
                            raise RuntimeError(f"Remote command failed: {command_result_yoeda.stderr.strip()}")
                        yoeda_lastest_data_selected = get_remote_resource(
                            is_file=False,
                            conn=conn,
                            remote_dir=remote_yoeda_dir,
                            patterns=settings.file_patterns if use_patterns else None,
                            newer_than_marker=marker_name,
                        )
                    else:
                        raise FileNotFoundError("No recent data found in YOEDA.")

                if yoeda_lastest_data_selected is None:
                    raise FileNotFoundError("No backup generated/found in YOEDA after command execution.")

                print(f"Found recent data in YOEDA: {yoeda_lastest_data_selected.relative_path}")
                print("Starting download... this may take a while for large folders")
                yoeda_local_path = download_remote_resource(
                    is_file=False,
                    conn=conn,
                    remote_absolute_path=yoeda_lastest_data_selected.absolute_path,
                    remote_relative_path=yoeda_lastest_data_selected.relative_path,
                    local_output_dir=run_dir_yoeda,
                )

                path_str = str(yoeda_local_path)
                print("path:", yoeda_local_path)
                print("name:", yoeda_local_path.name)
                print("parent directory:", yoeda_local_path.parent)
                keep_last_5_items(path_str)
            except Exception as exc:
                yoeda_error = str(exc)
            finally:
                current_finished_at = datetime.now(timezone.utc).isoformat()
                report["finished_at"] = current_finished_at
                report_file_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
                execution_report_v2(
                    run_id=run_id,
                    node_name="yoeda",
                    country_code="CIV",
                    service="VAS",
                    execution_type='BK',
                    job_name=job_name,
                    started_at=yoeda_started_at,
                    finished_at=current_finished_at,
                    status="FAILED" if yoeda_error else "SUCCESS",
                    local_file_path=yoeda_local_path,
                    remote_absolute_path=(yoeda_lastest_data_selected.absolute_path if yoeda_lastest_data_selected else None),
                    remote_relative_path=(yoeda_lastest_data_selected.relative_path if yoeda_lastest_data_selected else None),
                    error_message=yoeda_error,
                    report_file_path=report_file_path,
                    settings=settings,
                )
                if marker_name:
                    remove_marker(conn, settings.remote_dir+"/yoeda", marker_name)
                    marker_name = None

            if yoeda_error:
                raise RuntimeError(yoeda_error)
                

            abeda_started_at = datetime.now(timezone.utc).isoformat()
            abeda_error: Optional[str] = None
            try:
                if abeda_lastest_data_selected is None or is_modified_older_than_days(abeda_lastest_data_selected.modified_at_epoch, 2):
                    if settings.remote_command:
                        marker_name = create_marker(conn, remote_abeda_dir)
                        command_result_abeda = execute_remote_command(conn, remote_abeda_dir, settings.remote_command)
                        report["command_result_abeda"] = {
                            "exit_code": command_result_abeda.exit_code,
                            "stdout": command_result_abeda.stdout,
                            "stderr": command_result_abeda.stderr,
                        }
                        if command_result_abeda.exit_code != 0:
                            raise RuntimeError(f"Remote command failed: {command_result_abeda.stderr.strip()}")
                        abeda_lastest_data_selected = get_remote_resource(
                            is_file=False,
                            conn=conn,
                            remote_dir=remote_abeda_dir,
                            patterns=settings.file_patterns if use_patterns else None,
                            newer_than_marker=marker_name,
                        )
                    else:
                        raise FileNotFoundError("No recent data found in ABEDA.")

                if abeda_lastest_data_selected is None:
                    raise FileNotFoundError("No backup generated/found in ABEDA after command execution.")

                print(f"Found recent data in ABEDA: {abeda_lastest_data_selected.relative_path}")
                print("Starting download... this may take a while for large folders")
                abeda_local_path = download_remote_resource(
                    is_file=False,
                    conn=conn,
                    remote_absolute_path=abeda_lastest_data_selected.absolute_path,
                    remote_relative_path=abeda_lastest_data_selected.relative_path,
                    local_output_dir=run_dir_abeda,
                )
                path_str = str(abeda_local_path)
                print("path:", abeda_local_path)
                print("name:", abeda_local_path.name)
                print("parent directory:", abeda_local_path.parent)
                keep_last_5_items(path_str)
            except Exception as exc:
                abeda_error = str(exc)
            finally:
                current_finished_at = datetime.now(timezone.utc).isoformat()
                report["finished_at"] = current_finished_at
                report_file_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
                execution_report_v2(
                    run_id=run_id,
                    node_name="abeda",
                    started_at=abeda_started_at,
                    finished_at=current_finished_at,
                    status="FAILED" if abeda_error else "SUCCESS",
                    country_code="CIV",
                    service="VAS",
                    execution_type='BK',
                    job_name=job_name,
                    local_file_path=abeda_local_path,
                    remote_absolute_path=(abeda_lastest_data_selected.absolute_path if abeda_lastest_data_selected else None),
                    remote_relative_path=(abeda_lastest_data_selected.relative_path if abeda_lastest_data_selected else None),
                    error_message=abeda_error,
                    report_file_path=report_file_path,
                    settings=settings,
                )
                if marker_name:
                    remove_marker(conn, settings.remote_dir+"/abeda", marker_name)
                    marker_name = None

            if abeda_error:
                raise RuntimeError(abeda_error)

           
            report["selected_ressouces"] = {
                "yoeda_relative_path": yoeda_lastest_data_selected.relative_path if yoeda_lastest_data_selected else None,
                "yoeda_absolute_path": yoeda_lastest_data_selected.absolute_path if yoeda_lastest_data_selected else None,
                "yoeda_modified_at_epoch": yoeda_lastest_data_selected.modified_at_epoch if yoeda_lastest_data_selected else None,
                "abeda_relative_path": abeda_lastest_data_selected.relative_path if abeda_lastest_data_selected else None,
                "abeda_absolute_path": abeda_lastest_data_selected.absolute_path if abeda_lastest_data_selected else None,
                "abeda_modified_at_epoch": abeda_lastest_data_selected.modified_at_epoch if abeda_lastest_data_selected else None,
            }

            report["downloaded_local_path"] = {
                "yoeda_local_path": str(yoeda_local_path) if yoeda_local_path else None,
                "abeda_local_path": str(abeda_local_path) if abeda_local_path else None,
            }

    except Exception as exc:
        report["error"] = str(exc)
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        report_file_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Failed: {exc}")
        print(f"Report: {report_file_path}")
        sys.exit(1)

    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report_file_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Run directory: {report_dir}")
    print(f"Downloaded folder: {report['downloaded_local_path']}")
    print(f"Report: {report_file_path}")

if __name__ == "__main__":
    # Download latest folder (use patterns if available)
    download_remote_backup(use_patterns=False)
