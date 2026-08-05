# """
# Example script demonstrating how to download the latest modified folder and its contents.

# This script extends the existing backup functionality to work with entire folders
# instead of individual files.
# """
# from datetime import datetime, timezone
# import os
# from pathlib import Path
# import json
# import sys

# from remote_ressource import download_remote_resource, get_remote_resource
# from modified_period import is_modified_older_than_days
# from transfer import download_remote_file 
# from ssh_connection import SSHConnection
# from remote_files import create_marker, execute_remote_command, remove_marker
# from folder_transfer import get_latest_modified_folder, get_latest_modified_folder_by_pattern, download_remote_folder 
# from backup_scripts.report_request import execution_report_v2

# from config import load_settings

# def download_remote_backup(use_patterns: bool = False) -> None:
#     """
#     Download the latest modified data from remote server.
#     Args:
#         use_patterns: If True, find dat by file patterns; if False, find any data
#     """
#     settings1 = load_settings(".env.eda1")
#     settings2 = load_settings(".env.eda2")

#     run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
#     run_dir_eda1 = Path(settings1.local_output_dir)
#     run_dir_eda2 = Path(settings2.local_output_dir)
#     report_dir = Path("D:/huawei_dev_project/backups/benin/vas/eda/")
#     run_dir_eda1.mkdir(parents=True, exist_ok=True)
#     run_dir_eda2.mkdir(parents=True, exist_ok=True)
#     report_dir.mkdir(parents=True, exist_ok=True)

#     eda1_local_path: Path | None = None
#     eda2_local_path: Path | None = None

#     report: dict = {
#         "run_id": run_id,
#         "started_at": datetime.now(timezone.utc).isoformat(),
#         "remote_eda1_dir": settings1.remote_dir,
#         "remote_eda2_dir": settings2.remote_dir,
#         "remote_eda1_command": settings1.remote_command or None,
#         "remote_eda2_command": settings2.remote_command or None,
#         "eda1_patterns": settings1.file_patterns,
#         "eda2_patterns": settings2.file_patterns,
#         "selected_ressouces": None,
#         "downloaded_local_path": None,
#     }

#     try:
#         with SSHConnection(settings1) as conn1, SSHConnection(settings2) as conn2:
#             marker_name = None
#             command_result_eda1 = None
#             command_result_eda2 = None

#             eda1_lastest_data_selected = get_remote_resource(
#                 is_file=False,
#                 conn=conn1,
#                 remote_dir=settings1.remote_dir,
#                 patterns=settings1.file_patterns if use_patterns else None,
#                 newer_than_marker=None,
#             )

#             eda2_lastest_data_selected = get_remote_resource(
#                 is_file=False,
#                 conn=conn2,
#                 remote_dir=settings2.remote_dir,
#                 patterns=settings2.file_patterns if use_patterns else None,
#                 newer_than_marker=None,
#             )

#             eda1_started_at = datetime.now(timezone.utc).isoformat()
#             eda1_error: str | None = None
#             try:
#                 if eda1_lastest_data_selected is None or is_modified_older_than_days(eda1_lastest_data_selected.modified_at_epoch, 14):
#                     if settings1.remote_command:
#                         marker_name = create_marker(conn1, settings1.remote_dir)
#                         command_result_eda1 = execute_remote_command(conn1, settings1.remote_dir, settings1.remote_command)
#                         report["command_result_eda1"] = {
#                             "exit_code": command_result_eda1.exit_code,
#                             "stdout": command_result_eda1.stdout,
#                             "stderr": command_result_eda1.stderr,
#                         }
#                         if command_result_eda1.exit_code != 0:
#                             raise RuntimeError(f"Remote command failed: {command_result_eda1.stderr.strip()}")
#                         eda1_lastest_data_selected = get_remote_resource(
#                             is_file=False,
#                             conn=conn1,
#                             remote_dir=settings1.remote_dir,
#                             patterns=settings1.file_patterns if use_patterns else None,
#                             newer_than_marker=marker_name,
#                         )
#                     else:
#                         print("No recent data found in EDA1 and no remote command specified to generate new data.")
#                         raise FileNotFoundError("No recent data found in EDA1.")

#                 if eda1_lastest_data_selected is None:
#                     raise FileNotFoundError("No recent data found in EDA1 after command execution.")

#                 print(f"Found recent data in EDA1: {eda1_lastest_data_selected.relative_path}")
#                 print(f"Starting download... this may take a while for large folders")
#                 eda1_local_path = download_remote_resource(
#                     is_file=False,
#                     conn=conn1,
#                     remote_absolute_path=eda1_lastest_data_selected.absolute_path,
#                     remote_relative_path=eda1_lastest_data_selected.relative_path,
#                     local_output_dir=run_dir_eda1,
#                 )
#             except Exception as exc:
#                 eda1_error = str(exc)
#             finally:
#                 eda1_finished_at = datetime.now(timezone.utc).isoformat()
#                 report["finished_at_eda1"] = eda1_finished_at
#                 execution_report_v2(
#                     run_id=run_id,
#                     node_name="eda1",
#                     started_at=eda1_started_at,
#                     finished_at=eda1_finished_at,
#                     status="FAILED" if eda1_error else "SUCCESS",
#                     country_code=os.getenv("COUNTRY_CODE", "BJ"),
#                     service=os.getenv("SERVICE_DOMAIN", "VAS"),
#                     execution_type=os.getenv("EXECUTION_TYPE", "BK"),
#                     job_name=os.getenv("JOB_NAME", "benin_vas_eda_backup"),
#                     local_file_path=eda1_local_path,
#                     remote_absolute_path=(eda1_lastest_data_selected.absolute_path if eda1_lastest_data_selected else None),
#                     remote_relative_path=(eda1_lastest_data_selected.relative_path if eda1_lastest_data_selected else None),
#                     error_message=eda1_error,
#                     report_file_path=report_dir / "report.json",
#                     settings=settings1,
#                 )
#                 if marker_name:
#                     remove_marker(conn1, settings1.remote_dir, marker_name)
#                     marker_name = None

#             if eda1_error:
#                 raise RuntimeError(eda1_error)

#             eda2_started_at = datetime.now(timezone.utc).isoformat()
#             eda2_error: str | None = None
#             try:
#                 if eda2_lastest_data_selected is None or is_modified_older_than_days(eda2_lastest_data_selected.modified_at_epoch, 14):
#                     if settings2.remote_command:
#                         marker_name = create_marker(conn2, settings2.remote_dir)
#                         command_result_eda2 = execute_remote_command(conn2, settings2.remote_dir, settings2.remote_command)
#                         report["command_result_eda2"] = {
#                             "exit_code": command_result_eda2.exit_code,
#                             "stdout": command_result_eda2.stdout,
#                             "stderr": command_result_eda2.stderr,
#                         }
#                         if command_result_eda2.exit_code != 0:
#                             raise RuntimeError(f"Remote command failed: {command_result_eda2.stderr.strip()}")
#                         eda2_lastest_data_selected = get_remote_resource(
#                             is_file=False,
#                             conn=conn2,
#                             remote_dir=settings2.remote_dir,
#                             patterns=settings2.file_patterns if use_patterns else None,
#                             newer_than_marker=marker_name,
#                         )
#                     else:
#                         print("No recent data found in EDA2 and no remote command specified to generate new data.")
#                         raise FileNotFoundError("No recent data found in EDA2.")

#                 if eda2_lastest_data_selected is None:
#                     raise FileNotFoundError("No recent data found in EDA2 after command execution.")

#                 print(f"Found recent data in EDA2: {eda2_lastest_data_selected.relative_path}")
#                 print(f"Starting download... this may take a while for large folders")
#                 eda2_local_path = download_remote_resource(
#                     is_file=False,
#                     conn=conn2,
#                     remote_absolute_path=eda2_lastest_data_selected.absolute_path,
#                     remote_relative_path=eda2_lastest_data_selected.relative_path,
#                     local_output_dir=run_dir_eda2,
#                 )
#             except Exception as exc:
#                 eda2_error = str(exc)
#             finally:
#                 eda2_finished_at = datetime.now(timezone.utc).isoformat()
#                 report["finished_at_eda2"] = eda2_finished_at
#                 execution_report_v2(
#                     run_id=run_id,
#                     node_name="eda2",
#                     started_at=eda2_started_at,
#                     finished_at=eda2_finished_at,
#                     status="FAILED" if eda2_error else "SUCCESS",
#                     country_code=os.getenv("COUNTRY_CODE", "BJ"),
#                     service=os.getenv("SERVICE_DOMAIN", "VAS"),
#                     execution_type=os.getenv("EXECUTION_TYPE", "BK"),
#                     job_name=os.getenv("JOB_NAME", "benin_vas_eda_backup"),
#                     local_file_path=eda2_local_path,
#                     remote_absolute_path=(eda2_lastest_data_selected.absolute_path if eda2_lastest_data_selected else None),
#                     remote_relative_path=(eda2_lastest_data_selected.relative_path if eda2_lastest_data_selected else None),
#                     error_message=eda2_error,
#                     report_file_path=report_dir / "report.json",
#                     settings=settings2,
#                 )
#                 if marker_name:
#                     remove_marker(conn2, settings2.remote_dir, marker_name)
#                     marker_name = None

#             if eda2_error:
#                 raise RuntimeError(eda2_error)

           
#             report["selected_ressouces"] = {
#                 "eda1_relative_path": eda1_lastest_data_selected.relative_path if eda1_lastest_data_selected else None,
#                 "eda1_absolute_path": eda1_lastest_data_selected.absolute_path if eda1_lastest_data_selected else None,
#                 "eda1_modified_at_epoch": eda1_lastest_data_selected.modified_at_epoch if eda1_lastest_data_selected else None,
#                 "eda2_relative_path": eda2_lastest_data_selected.relative_path if eda2_lastest_data_selected else None,
#                 "eda2_absolute_path": eda2_lastest_data_selected.absolute_path if eda2_lastest_data_selected else None,
#                 "eda2_modified_at_epoch": eda2_lastest_data_selected.modified_at_epoch if eda2_lastest_data_selected else None,
#             }

#             report["downloaded_local_path"] = {
#                 "eda1_local_path": str(eda1_local_path) if eda1_local_path else None,
#                 "eda2_local_path": str(eda2_local_path) if eda2_local_path else None,
#             }

#     except Exception as exc:
#         report["error"] = str(exc)
#         report["finished_at"] = datetime.now(timezone.utc).isoformat()
#         (report_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
#         print(f"Failed: {exc}")
#         print(f"Report: {report_dir / 'report.json'}")
#         sys.exit(1)

#     report["finished_at"] = datetime.now(timezone.utc).isoformat()
#     (report_dir / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

#     print(f"Run directory: {report_dir}")
#     print(f"Downloaded folder: {report['downloaded_local_path']}")
#     print(f"Report: {report_dir / 'report.json'}")


# if __name__ == "__main__":
#     # Download latest folder (use patterns if available)
#     download_remote_backup(use_patterns=False)
