from datetime import datetime, timezone
from pathlib import Path
import json
import sys


# import remote_ressource

# from ....remote_ressource import download_remote_resource, get_remote_resource

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

    report: dict = {
        "run_id": run_id,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "remote_yoeda_dir": settings.remote_dir+"/yoeda",
        "remote_abeda_dir": settings.remote_dir+"/abeda",
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
                remote_dir=settings.remote_dir+"/yoeda",
                patterns=settings.file_patterns if use_patterns else None,
                newer_than_marker=None,
            )

            abeda_lastest_data_selected = get_remote_resource(
                is_file=False,
                conn=conn,
                remote_dir=settings.remote_dir+"/abeda",
                patterns=settings.file_patterns if use_patterns else None,
                newer_than_marker=None,
            )

            if yoeda_lastest_data_selected is None or is_modified_older_than_days(yoeda_lastest_data_selected.modified_at_epoch, 2):
                if settings.remote_command:
                    marker_name = create_marker(conn, settings.remote_dir+"/yoeda")
                    command_result_yoeda = execute_remote_command(conn, settings.remote_dir+"/yoeda", settings.remote_command)
                    report["command_result_yoeda"] = {
                        "exit_code": command_result_yoeda.exit_code,
                        "stdout": command_result_yoeda.stdout,
                        "stderr": command_result_yoeda.stderr,
                    }
                    if command_result_yoeda.exit_code != 0:
                        raise RuntimeError(f"Remote command failed: {command_result_yoeda.stderr.strip()}")
                else:
                    print("No recent data found in YOEDA and no remote command specified to generate new data.")
                    raise FileNotFoundError("No recent data found in YOEDA.")
            else:
                print(f"Found recent data in YOEDA: {yoeda_lastest_data_selected.relative_path}")
                print(f"Starting download... this may take a while for large folders")
                yoeda_local_path = download_remote_resource(
                    is_file=False,
                    conn=conn,
                    remote_absolute_path=yoeda_lastest_data_selected.absolute_path,
                    remote_relative_path=yoeda_lastest_data_selected.relative_path,
                    local_output_dir=run_dir_yoeda,
                )

                path_str = str(yoeda_local_path)
                name_only = yoeda_local_path.name
                parent_dir = yoeda_local_path.parent
                print("path:", yoeda_local_path)
                print("name:", yoeda_local_path.name)
                print("parent directory:", yoeda_local_path.parent)
                keep_last_5_items(path_str)

            if abeda_lastest_data_selected is None or is_modified_older_than_days(abeda_lastest_data_selected.modified_at_epoch, 2):
                if settings.remote_command:
                    marker_name = create_marker(conn, settings.remote_dir+"/abeda")
                    command_result_abeda = execute_remote_command(conn, settings.remote_dir+"/abeda", settings.remote_command)
                    report["command_result_abeda"] = {
                        "exit_code": command_result_abeda.exit_code,
                        "stdout": command_result_abeda.stdout,
                        "stderr": command_result_abeda.stderr,
                    }
                    if command_result_abeda.exit_code != 0:
                        raise RuntimeError(f"Remote command failed: {command_result_abeda.stderr.strip()}")

                else:
                    print("No recent data found in ABE DA and no remote command specified to generate new data.")
                    raise FileNotFoundError("No recent data found in ABE DA.")
            else:
                print(f"Found recent data in ABE DA: {abeda_lastest_data_selected.relative_path}")
                print(f"Starting download... this may take a while for large folders")
                abeda_local_path = download_remote_resource(
                    is_file=False,
                    conn=conn,
                    remote_absolute_path=abeda_lastest_data_selected.absolute_path,
                    remote_relative_path=abeda_lastest_data_selected.relative_path,
                    local_output_dir=run_dir_abeda,
                )
                path_str = str(abeda_local_path)
                name_only = abeda_local_path.name
                parent_dir = abeda_local_path.parent
                print("path:", abeda_local_path)
                print("name:", abeda_local_path.name)
                print("parent directory:", abeda_local_path.parent)
                keep_last_5_items(path_str)

           
            report["selected_ressouces"] = {
                "yoeda_relative_path": yoeda_lastest_data_selected.relative_path if yoeda_lastest_data_selected else None,
                "yoeda_absolute_path": yoeda_lastest_data_selected.absolute_path if yoeda_lastest_data_selected else None,
                "yoeda_modified_at_epoch": yoeda_lastest_data_selected.modified_at_epoch if yoeda_lastest_data_selected else None,
                "abeda_relative_path": abeda_lastest_data_selected.relative_path if abeda_lastest_data_selected else None,
                "abeda_absolute_path": abeda_lastest_data_selected.absolute_path if abeda_lastest_data_selected else None,
                "abeda_modified_at_epoch": abeda_lastest_data_selected.modified_at_epoch if abeda_lastest_data_selected else None,
            }

            report["downloaded_local_path"] = {
                "yoeda_local_path": str(yoeda_local_path),
                "abeda_local_path": str(abeda_local_path),
            }

            if marker_name:
                remove_marker(conn, settings.remote_dir+"/yoeda", marker_name)
                remove_marker(conn, settings.remote_dir+"/abeda", marker_name )

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
