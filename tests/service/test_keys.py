import base64
from pathlib import Path

import pytest
from structlog.testing import capture_logs

from news.service.keys import read_master_key

KEY = b"m" * 32
ENCODED = base64.urlsafe_b64encode(KEY).decode()


def test_master_key_can_come_from_environment() -> None:
    assert read_master_key({"NEWS_MASTER_KEY": ENCODED}) == KEY


def test_docker_secret_file_is_read_without_changing_it(tmp_path: Path) -> None:
    path = tmp_path / "master-key"
    path.write_text(ENCODED + "\n")
    with capture_logs() as logs:
        assert read_master_key({"NEWS_MASTER_KEY_FILE": str(path)}) == KEY
    assert path.read_text() == ENCODED + "\n"
    assert ENCODED not in repr(logs)


@pytest.mark.parametrize(
    "environ",
    [
        {},
        {"NEWS_MASTER_KEY": ""},
        {"NEWS_MASTER_KEY": "sentinel-invalid-key"},
        {"NEWS_MASTER_KEY": base64.urlsafe_b64encode(b"short").decode()},
        {"NEWS_MASTER_KEY": ENCODED, "NEWS_MASTER_KEY_FILE": "/unused"},
        {"NEWS_MASTER_KEY_FILE": "/nonexistent-mobua-test-master-key"},
    ],
)
def test_invalid_missing_and_conflicting_sources_fail_without_logging_key_values(
    environ: dict[str, str],
) -> None:
    with capture_logs() as logs, pytest.raises(ValueError, match="Master Key"):
        read_master_key(environ)
    assert len(logs) == 1
    assert logs[0]["event"] == "keys.source_failed"
    assert ENCODED not in repr(logs)
    assert "sentinel-invalid-key" not in repr(logs)


def test_non_ascii_key_files_are_reported_safely(tmp_path: Path) -> None:
    path = tmp_path / "master-key"
    path.write_bytes(b"\xff\xfe")
    with pytest.raises(ValueError, match="Master Key"):
        read_master_key({"NEWS_MASTER_KEY_FILE": str(path)})
