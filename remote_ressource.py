#remote_ressource.py

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from folder_transfer import download_remote_folder, get_latest_modified_folder
from remote_files import get_latest_modified_file
from ssh_connection import SSHConnection
from transfer import download_remote_file   
from zip_folder import zip_downloaded_folder

@dataclass
class RemoteRessourceInfo:
    relative_path: str
    absolute_path: str
    modified_at_epoch: int

def get_remote_resource(
    is_file: bool,
    conn: SSHConnection,
    remote_dir: str,
    patterns: Optional[list[str]] = None,
    newer_than_marker: Optional[str] = None,
) -> Optional[RemoteRessourceInfo]:
    if is_file:
        latest_resource = get_latest_modified_file(
            conn,
            remote_dir=remote_dir,
            patterns=patterns,
            newer_than_marker=newer_than_marker,
        )
        return RemoteRessourceInfo(
            relative_path=latest_resource.relative_path,
            absolute_path=latest_resource.absolute_path,
            modified_at_epoch=latest_resource.modified_at_epoch,
        )
    else:
        latest_resource = get_latest_modified_folder(
            conn,
            remote_dir=remote_dir,
            newer_than_marker=newer_than_marker,
        )
        return RemoteRessourceInfo(
            relative_path=latest_resource.relative_path,
            absolute_path=latest_resource.absolute_path,
            modified_at_epoch=latest_resource.modified_at_epoch,
        )

def download_remote_resource(
    is_file: bool,
    conn: SSHConnection,
    remote_absolute_path: str,
    remote_relative_path: str,
    local_output_dir: Path,
) -> Path:
    if is_file:
        return download_remote_file(
            conn,
            remote_absolute_path=remote_absolute_path,
            remote_relative_path=remote_relative_path,
            local_output_dir=local_output_dir,
        )
    else:
        downloaded_path = download_remote_folder(
            conn,
            remote_absolute_path=remote_absolute_path,
            remote_relative_path=remote_relative_path,
            local_output_dir=local_output_dir,
        )
        zip_path = zip_downloaded_folder(downloaded_path)
        print(zip_path)
        return zip_path