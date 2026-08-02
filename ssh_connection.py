import shlex
from pathlib import Path

import paramiko

from config import Settings, load_settings



class SSHConnection:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = paramiko.SSHClient()

    def __enter__(self) -> "SSHConnection":
        self._connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def _connect(self) -> None:
        known_hosts = Path(self.settings.ssh_known_hosts)
        if known_hosts.exists():
            self.client.load_host_keys(str(known_hosts))
            policy = paramiko.RejectPolicy() if self.settings.strict_host_key_checking else paramiko.WarningPolicy()
            self.client.set_missing_host_key_policy(policy)
        else:
            self.client.set_missing_host_key_policy(paramiko.WarningPolicy())

        connect_kwargs = {
            "hostname": self.settings.ssh_host,
            "port": self.settings.ssh_port,
            "username": self.settings.ssh_user,
            "timeout": 20,
        }

        # if self.settings.ssh_key_path:
        #     pkey = paramiko.RSAKey.from_private_key_file(
        #         self.settings.ssh_key_path,
        #         password=self.settings.ssh_key_passphrase or None,
        #     )
        #     connect_kwargs["pkey"] = pkey
        if self.settings.ssh_password:
            connect_kwargs["password"] = self.settings.ssh_password
        else:
            raise ValueError("SSH_PASSWORD or SSH_KEY_PATH is required")

        self.client.connect(**connect_kwargs)

    def run(self, command: str) -> tuple[int, str, str]:
        _, stdout, stderr = self.client.exec_command(command)
        out = stdout.read().decode("utf-8", errors="ignore")
        err = stderr.read().decode("utf-8", errors="ignore")
        code = stdout.channel.recv_exit_status()
        return code, out, err

    def run_in_dir(self, remote_dir: str, command: str) -> tuple[int, str, str]:
        full = f"cd {shlex.quote(remote_dir)} && {command}"
        return self.run(full)

    def open_sftp(self) -> paramiko.SFTPClient:
        return self.client.open_sftp()

    def close(self) -> None:
        self.client.close()

# def test_ssh_connection():
#     settings = load_settings()
#     try:
#         with SSHConnection(settings) as conn:
#             code, out, err = conn.run("echo Hello, SSH!")
#             assert code == 0, f"Command failed with error: {err.strip()}"
#             assert out.strip() == "Hello, SSH!", f"Unexpected command output: {out.strip()}"
#     except Exception as e:
#         print(f"Test failed with error: {e}")
# if __name__ == "__main__":
#     test_ssh_connection()

