"""Where the CLI writes its logs (spec review-followups-01, D-6)."""

from pathlib import Path


def resolve_log_path(log_file: Path | None, xdg_state_home: str | None, home: Path) -> Path:
    """The explicit log file if given, else `cli.log` in the XDG state directory."""
    if log_file is not None:
        return log_file
    # The XDG Base Directory spec says to ignore an empty or relative XDG_STATE_HOME.
    if xdg_state_home and Path(xdg_state_home).is_absolute():
        state_home = Path(xdg_state_home)
    else:
        state_home = home / ".local" / "state"
    return state_home / "news" / "cli.log"
