from collections.abc import Iterator
from pathlib import Path

import pytest
import structlog


@pytest.fixture(autouse=True)
def log_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Keep CLI logs out of the real state directory, and leave structlog as it was."""
    path = tmp_path / "logs" / "cli.log"
    monkeypatch.setenv("NEWS_CLI_LOG_FILE", str(path))
    yield path
    structlog.reset_defaults()
