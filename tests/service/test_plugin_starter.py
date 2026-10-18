import shlex
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from structlog.testing import capture_logs

from news.service.manifest import parse_manifest
from news.service.models import Plugin, PluginRevision
from news.service.plugins import create_plugin
from news.service.validation import ValidationRejected
from tests.service.factories import a_reader


@pytest.mark.parametrize(
    "name",
    [
        "Reader Plugin",
        'Quotes " and π 😀\nnext',
        "delete\x7fcharacter",
        "controls \x01\x08\x0b\x0c\x1b\x1f and \\ backslash \\u0041",
        "\u0080 C1 and \u2028 separators",
    ],
)
def test_new_plugin_has_a_valid_noop_starter(session: Session, tmp_path: Path, name: str) -> None:
    reader = a_reader(session)

    revision = create_plugin(session, reader.id, name)
    session.commit()

    plugin = session.get_one(Plugin, revision.plugin_id)
    manifest = parse_manifest(revision.manifest)
    assert plugin.name == manifest.name == name
    assert plugin.reader_id == revision.reader_id == reader.id
    assert revision.created_by == str(reader.id)
    assert revision.number == 1
    assert revision.parent_revision_id is None
    assert plugin.current_revision_id == revision.id
    assert session.scalar(select(func.count()).select_from(PluginRevision)) == 1
    assert manifest.config_schema == {"type": "object", "additionalProperties": False}
    assert manifest.secrets == []
    for filename, content in revision.code.items():
        (tmp_path / filename).write_text(content, encoding="utf-8")
    command = shlex.split(manifest.command)
    assert command[0] == "python"
    result = subprocess.run(
        [sys.executable, *command[1:]], cwd=tmp_path, capture_output=True, check=False
    )
    assert (result.returncode, result.stdout, result.stderr) == (0, b"", b"")


@pytest.mark.parametrize("name", ["", " \n\t"])
def test_blank_name_rejected_without_rows_or_payload_logs(session: Session, name: str) -> None:
    reader = a_reader(session)
    with capture_logs() as logs, pytest.raises(ValidationRejected) as raised:
        create_plugin(session, reader.id, name)
    assert [error.field for error in raised.value.errors] == ["name"]
    assert not session.new
    assert session.scalar(select(func.count()).select_from(Plugin)) == 0
    assert logs[0]["event"] == "plugin.rejected"
    assert "name" not in logs[0]
