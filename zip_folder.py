from pathlib import Path
from typing import Optional
import shutil

def zip_downloaded_folder(downloaded_folder: Path, archive_name: Optional[str] = None) -> Path:
    if not downloaded_folder.exists():
        raise FileNotFoundError(f"Le dossier n'existe pas : {downloaded_folder}")

    parent_dir = downloaded_folder.parent
    archive_base = archive_name or downloaded_folder.name
    archive_path = shutil.make_archive(
        str(parent_dir / archive_base),  # chemin sans l'extension
        "zip",
        root_dir=str(parent_dir),
        base_dir=downloaded_folder.name,
    )
    return Path(archive_path)