from datetime import datetime, timezone
import json
import mimetypes
import os
from pathlib import Path
from urllib import error, request


def _storage_path_from_local_root(file_path: Path, local_root: Path) -> str:
    try:
        return str(file_path.resolve().relative_to(local_root.resolve())).replace("\\", "/")
    except ValueError:
        return file_path.name

def _artifact_from_path(file_path: Path, local_root: Path, remote_absolute_path: str | None, remote_relative_path: str | None) -> dict:
    stat = file_path.stat()
    file_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"

    storage_path = _storage_path_from_local_root(file_path, local_root)

    return {
        "role": "BACKUP_ARCHIVE",
        "storageBackend": os.getenv("EXECUTION_REPORT_STORAGE_BACKEND", "LOCAL_FS"),
        "storageRootAlias": os.getenv("EXECUTION_REPORT_STORAGE_ROOT_ALIAS", "local_backup"),
        "storagePath": storage_path,
        "fileName": file_path.name,
        "fileType": file_type,
        "sizeBytes": stat.st_size,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "source": {
            "remoteAbsolutePath": remote_absolute_path,
            "remoteRelativePath": remote_relative_path,
        },
    }


def execution_report_v2(
    *,
    run_id: str,
    node_name: str,
    started_at: str,
    finished_at: str,
    status: str,
    country_code: str,
    service: str,
    execution_type: str,
    job_name: str,
    local_file_path: Path | None,
    remote_absolute_path: str | None,
    remote_relative_path: str | None,
    error_message: str | None,
    report_file_path: Path,
    settings,
) -> None:
    report_url = os.getenv("EXECUTION_REPORT_V2_URL", "").strip()
    api_key = os.getenv("EXECUTION_REPORT_API_KEY", "").strip()
    if not report_url or not api_key:
        print(
            f"[report/v2] skipped for node={node_name}: missing EXECUTION_REPORT_V2_URL or EXECUTION_REPORT_API_KEY"
        )
        return

    artifacts: list[dict] = []
    if local_file_path is not None and local_file_path.exists() and local_file_path.is_file():
        artifacts.append(
            _artifact_from_path(
                local_file_path,
                settings.local_output_dir,
                remote_absolute_path,
                remote_relative_path,
            )
        )

    if report_file_path.exists() and report_file_path.is_file():
        artifacts.append(
            {
                "role": "EXECUTION_REPORT",
                "storageBackend": os.getenv("EXECUTION_REPORT_STORAGE_BACKEND", "LOCAL_FS"),
                "storageRootAlias": os.getenv("EXECUTION_REPORT_STORAGE_ROOT_ALIAS", "local_backup"),
                "storagePath": _storage_path_from_local_root(report_file_path, settings.local_output_dir),
                "fileName": report_file_path.name,
                "fileType": "application/json",
                "sizeBytes": report_file_path.stat().st_size,
                "createdAt": datetime.now(timezone.utc).isoformat(),
            }
        )

    payload = {
        "type": execution_type,
        "service": service,
        "equipment": node_name.upper(),
        "countryCode": country_code,
        "status": status,
        "startedAt": started_at,
        "finishedAt": finished_at,
        "resultSummary": error_message or f"Backup node {node_name} completed.",
        "run": {
            "runId": f"{run_id}-{node_name}",
            "jobName": job_name,
            "environment": os.getenv("APP_ENV", "prod"),
            "scriptVersion": os.getenv("SCRIPT_VERSION", "1.0.0"),
            "hostName": os.getenv("HOSTNAME", "localhost"),
            "triggerMode": "SCHEDULED",
            "remoteCommand": settings.remote_command or None,
        },
        "artifacts": artifacts,
    }

    if not artifacts:
        payload["resultSummary"] = (
            f"{payload['resultSummary']} No artifact file attached for node {node_name}."
        )


    req = _request_post(report_url, payload, api_key)
    status_code, response_body = req
    print(f"[report/v2] node={node_name} sent (status={status_code})")
    if status_code < 200 or status_code >= 300:
        raise RuntimeError(
            f"report/v2 failed for node={node_name}: status={status_code}, body={response_body[:400]}"
        )


def _request_header(api_key: str) -> dict:
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

def _request_post(url: str, payload: dict, api_key: str, timeout: int = 15) -> tuple[int, str]:
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=_request_header(api_key),
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return response.status, body
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body
    except Exception as exc:  # pragma: no cover - network dependent
        return 0, str(exc)

def _request_get(url: str, api_key: str, timeout: int = 15) -> tuple[int, str]:
    req = request.Request(
        url,
        headers=_request_header(api_key),
        method="GET",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return response.status, body
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body
    except Exception as exc:  # pragma: no cover - network dependent
            return 0, str(exc)
