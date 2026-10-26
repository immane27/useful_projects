import re
import shlex
from collections.abc import Iterator
from contextlib import contextmanager
from typing import BinaryIO

import paramiko

from app.config import get_settings

# Dated folders (backup/20170101 etc.) differ per operator and are created by processing, not setup.
DATED = re.compile(r"/\d{6,}(/|$)")


@contextmanager
def connection() -> Iterator[paramiko.SSHClient]:
    s = get_settings()
    with paramiko.SSHClient() as client:
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(s.ssh_host, username=s.ssh_user, key_filename=s.ssh_key_path, timeout=15)
        except Exception as e:
            raise RuntimeError(f"SSH login failed ({s.ssh_user}@{s.ssh_host}, key {s.ssh_key_path}): {e}") from e
        yield client


def run(command: str) -> str:
    with connection() as client:
        _, stdout, stderr = client.exec_command(command)
        out = stdout.read().decode()
        if stdout.channel.recv_exit_status():
            raise RuntimeError(f"{command}: {stderr.read().decode().strip()}")
        return out


def tree(operator: str) -> set[str]:
    """Relative directory paths under the operator folder; empty if the folder does not exist."""
    path = shlex.quote(f"{get_settings().data_root}/{operator}")
    out = run(f"test -d {path} && cd {path} && find . -type d || true")
    return {line for line in out.splitlines() if not DATED.search(line)}


def missing_dirs(operator: str) -> list[str]:
    return sorted(tree(get_settings().ref_operator) - tree(operator))


def create_dirs(operator: str, paths: list[str]) -> None:
    root = f"{get_settings().data_root}/{operator}"
    run("mkdir -p " + " ".join(shlex.quote(f"{root}/{p}") for p in paths))


def upload(data: BinaryIO, folder: str, name: str) -> None:
    """Write under a temporary name, then rename, so processing never picks up a partial file."""
    target = f"{folder}/{name}"
    with connection() as client, client.open_sftp() as sftp:
        try:
            sftp.stat(target)
            raise FileExistsError(f"{target} already exists")
        except FileNotFoundError:
            pass
        sftp.putfo(data, target + ".part")
        sftp.posix_rename(target + ".part", target)
