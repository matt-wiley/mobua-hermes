import io
import json
from collections.abc import Iterator

import pytest
import structlog

from news.service.observability import configure_logging


@pytest.fixture(autouse=True)
def restore_structlog_defaults() -> Iterator[None]:
    yield
    structlog.reset_defaults()


def test_logs_are_json_lines_on_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging()

    structlog.get_logger("test").info("channel_revision.rejected", channel_id="c1")

    line = json.loads(capsys.readouterr().out.strip())
    assert line["event"] == "channel_revision.rejected"
    assert line["level"] == "info"
    assert line["channel_id"] == "c1"
    assert "timestamp" in line


def test_logs_go_to_the_given_stream_and_not_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    stream = io.StringIO()
    configure_logging(stream=stream)

    structlog.get_logger("test").info("channel_revision.rejected", channel_id="c1")

    line = json.loads(stream.getvalue())
    assert line["event"] == "channel_revision.rejected"
    assert line["level"] == "info"
    assert "timestamp" in line
    assert capsys.readouterr().out == ""
