import os
import shutil
from pathlib import Path

def keep_last_5_items(folder_path: str) -> None:
    folder = Path(folder_path)

    if not folder.exists() or not folder.is_dir():
        raise NotADirectoryError(f"Le dossier est introuvable : {folder_path}")

    # Récupère tous les éléments du dossier
    items = [item for item in folder.iterdir()]

    # Trie par date de modification décroissante (les plus récents en premier)
    items.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    # Garde seulement les 5 premiers
    items_to_keep = items[:5]
    items_to_delete = items[5:]

    for item in items_to_delete:
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

    print(f"Saved : {[str(item) for item in items_to_keep]}")
    print(f"Deleted : {[str(item) for item in items_to_delete]}")
