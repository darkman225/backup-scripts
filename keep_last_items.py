import os
import shutil
from pathlib import Path

def keep_last_5_items(path_to_manage: str) -> None:
    target_path = Path(path_to_manage)

    if target_path.is_file():
        folder = target_path.parent
    elif target_path.is_dir():
        folder = target_path
    else:
        raise NotADirectoryError(f"Le chemin est introuvable ou invalide : {path_to_manage}")

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