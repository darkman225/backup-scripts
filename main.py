from datetime import datetime, timezone
from pathlib import Path

from civ.vas.eda.civ_vas_eda_backup_scripts_main import download_remote_backup


from run_loop_func import run_loop_func
from transfer import download_remote_file


def main() -> None:

   run_loop_func(download_remote_backup, days=1)


if __name__ == "__main__":
    main()
