import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


def _env(name: str, default: Optional[str] = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and (value is None or str(value).strip() == ""):
        raise ValueError(f"Missing required .env variable: {name}")
    return "" if value is None else str(value)


def _to_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    ssh_host: str
    ssh_port: int
    ssh_user: str
    ssh_password: str
    ssh_key_path: str
    ssh_key_passphrase: str
    ssh_known_hosts: str
    strict_host_key_checking: bool
    remote_dir: str
    remote_command: str
    file_patterns: list[str]
    local_output_dir: Path


def load_settings(env_path: Optional[Path] = None) -> Settings:
    load_dotenv(dotenv_path=env_path)

    patterns_raw = _env("FILE_PATTERNS", "")
    patterns = [p.strip() for p in patterns_raw.split(",") if p.strip()]

    local_output_dir = Path(_env("LOCAL_OUTPUT_DIR", "./downloads")).expanduser().resolve()

    return Settings(
        ssh_host=_env("SSH_HOST", required=True),
        ssh_port=int(_env("SSH_PORT", "22")),
        ssh_user=_env("SSH_USER", required=True),
        ssh_password=_env("SSH_PASSWORD", ""),
        ssh_key_path=_env("SSH_KEY_PATH", ""),
        ssh_key_passphrase=_env("SSH_KEY_PASSPHRASE", ""),
        ssh_known_hosts=_env("SSH_KNOWN_HOSTS", str(Path.home() / ".ssh" / "known_hosts")),
        strict_host_key_checking=_to_bool(_env("STRICT_HOST_KEY_CHECKING", "true"), default=True),
        remote_dir=_env("REMOTE_DIR", required=True),
        remote_command=_env("REMOTE_COMMAND", ""),
        file_patterns=patterns,
        local_output_dir=local_output_dir,
    )
