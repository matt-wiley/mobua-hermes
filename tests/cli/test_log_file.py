from pathlib import Path

from news.cli.log_file import resolve_log_path

HOME = Path("/home/ada")


def test_an_explicit_log_file_wins() -> None:
    path = resolve_log_path(Path("/var/log/news.log"), "/state", HOME)

    assert path == Path("/var/log/news.log")


def test_xdg_state_home_is_used_when_no_log_file_is_given() -> None:
    assert resolve_log_path(None, "/state", HOME) == Path("/state/news/cli.log")


def test_home_local_state_is_the_fallback_when_xdg_state_home_is_unset() -> None:
    assert resolve_log_path(None, None, HOME) == Path("/home/ada/.local/state/news/cli.log")


def test_an_empty_xdg_state_home_is_treated_as_unset() -> None:
    assert resolve_log_path(None, "", HOME) == Path("/home/ada/.local/state/news/cli.log")


def test_a_relative_xdg_state_home_is_ignored_as_the_xdg_spec_requires() -> None:
    assert resolve_log_path(None, "state", HOME) == Path("/home/ada/.local/state/news/cli.log")


def test_a_relative_explicit_log_file_is_kept_as_given() -> None:
    assert resolve_log_path(Path("cli.log"), None, HOME) == Path("cli.log")
