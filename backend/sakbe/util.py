"""Small helpers shared by engines and network code."""

import subprocess


class CommandError(RuntimeError):
    pass


def run(cmd: list[str], check: bool = True, input: str | None = None) -> str:
    """Run a host command and return its stdout. Tests replace this function."""
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True, input=input)
    except FileNotFoundError:
        if check:
            raise CommandError(f"{cmd[0]}: command not found") from None
        return ""
    if check and proc.returncode != 0:
        raise CommandError(f"{' '.join(cmd)}: {proc.stderr.strip() or proc.stdout.strip()}")
    return proc.stdout
