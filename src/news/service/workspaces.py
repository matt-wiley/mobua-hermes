"""Text-file workspaces with version metadata outside the runnable implementation tree."""

import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from typing import Literal, NoReturn
from unicodedata import normalize

import structlog
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from news.service.models import PluginDraft
from news.service.validation import FieldError, ValidationRejected

MARKER = ".news-draft.json"
IMPLEMENTATION = "implementation"
MANIFEST = "manifest.toml"
# Interim rule until the Plugin design session: a workspace holds a Manifest and one code file.
CODE = "main.py"
log = structlog.get_logger(__name__)


class _Marker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: Literal[1] = 1
    reader_id: uuid.UUID
    plugin_id: uuid.UUID
    draft_id: uuid.UUID
    version: int = Field(gt=0, strict=True)


class WorkspaceError(Exception):
    pass


@dataclass(frozen=True)
class Workspace:
    reader_id: uuid.UUID
    plugin_id: uuid.UUID
    draft_id: uuid.UUID
    version: int
    manifest: str
    code: dict[str, str]


def implementation_files(manifest: str, code: dict[str, str]) -> dict[str, str]:
    """Select only implementation text and reject paths that cannot form a safe file tree."""
    normalized_names = {normalize("NFC", name).casefold() for name in code}
    paths: dict[str, str] = {}
    for name in code:
        parts = name.split("/")
        if (
            any(part in {"", ".", ".."} for part in parts)
            or any(character in name for character in ("\\", "\x00", ":"))
            or normalize("NFC", parts[0]).casefold() in {MANIFEST, MARKER}
        ):
            raise ValidationRejected(
                [
                    FieldError(
                        "code",
                        "use relative file paths; Manifest and version-marker names are reserved",
                    )
                ]
            )
        parents = [str(parent) for parent in PurePosixPath(name).parents if str(parent) != "."]
        if any(normalize("NFC", parent).casefold() in normalized_names for parent in parents):
            raise ValidationRejected(
                [FieldError("code", "a code file is also used as a directory")]
            )
        for path in [name, *parents]:
            normalized = normalize("NFC", path).casefold()
            if normalized in paths and paths[normalized] != path:
                raise ValidationRejected(
                    [
                        FieldError(
                            "code",
                            "file paths collide on a "
                            "case-insensitive or Unicode-normalizing filesystem",
                        )
                    ]
                )
            paths[normalized] = path
    return {MANIFEST: manifest, **code}


def export_workspace(draft: PluginDraft, directory: Path) -> None:
    try:
        if set(draft.code) - {CODE}:
            _fail(
                directory,
                "export",
                f"saved code has files other than {CODE}; edit it through the API",
            )
        files = implementation_files(draft.manifest, draft.code)
        if directory.exists() or directory.is_symlink():
            _fail(directory, "export", "destination already exists; choose a new directory")
        directory.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix=".news-export-", dir=directory.parent) as staging:
            root = Path(staging) / "workspace"
            root.mkdir()
            for name, content in files.items():
                target = root / IMPLEMENTATION / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8", newline="")
            marker = _Marker(
                reader_id=draft.reader_id,
                plugin_id=draft.plugin_id,
                draft_id=draft.id,
                version=draft.version,
            )
            (root / MARKER).write_text(marker.model_dump_json() + "\n", encoding="utf-8")
            root.rename(directory)
    except (OSError, UnicodeError) as error:
        _fail(directory, "export", "cannot write all files; check the path and permissions", error)
    except ValidationRejected as error:
        _fail(directory, "export", "saved code contains unsafe or conflicting file paths", error)


def read_workspace(
    directory: Path,
    reader_id: uuid.UUID,
    plugin_id: uuid.UUID,
    draft_id: uuid.UUID,
) -> Workspace:
    try:
        marker = _read_marker(directory, reader_id, plugin_id, draft_id)
        implementation = directory / IMPLEMENTATION
        _require_directory(implementation)
        if not (implementation / MANIFEST).exists():
            _fail(directory, "read", f"missing {IMPLEMENTATION}/{MANIFEST}")
        manifest = _read_text(implementation / MANIFEST)
        code_path = implementation / CODE
        # Other files (.DS_Store, __pycache__, editor backups) are local clutter, not Plugin code.
        code = {CODE: _read_text(code_path)} if code_path.exists() or code_path.is_symlink() else {}
        return Workspace(reader_id, plugin_id, draft_id, marker.version, manifest, code)
    except (OSError, UnicodeError) as error:
        _fail(
            directory,
            "read",
            "cannot read all UTF-8 files; check paths, links and permissions",
            error,
        )
    except ValidationError as error:
        _fail(directory, "read", "invalid version marker; export again", error)


def read_marker_version(
    directory: Path,
    reader_id: uuid.UUID,
    plugin_id: uuid.UUID,
    draft_id: uuid.UUID,
) -> int:
    """The Draft version the workspace was exported or last saved at; files are not read."""
    try:
        return _read_marker(directory, reader_id, plugin_id, draft_id).version
    except (OSError, UnicodeError) as error:
        _fail(
            directory,
            "read",
            "cannot read the version marker; check paths, links and permissions",
            error,
        )
    except ValidationError as error:
        _fail(directory, "read", "invalid version marker; export again", error)


def _read_marker(
    directory: Path,
    reader_id: uuid.UUID,
    plugin_id: uuid.UUID,
    draft_id: uuid.UUID,
) -> _Marker:
    _require_directory(directory)
    marker_path = directory / MARKER
    _require_file(marker_path)
    marker = _Marker.model_validate_json(marker_path.read_text(encoding="utf-8"))
    if (marker.reader_id, marker.plugin_id, marker.draft_id) != (reader_id, plugin_id, draft_id):
        _fail(directory, "read", "version marker belongs to a different Reader, Plugin or Draft")
    return marker


def advance_marker(directory: Path, workspace: Workspace, version: int) -> None:
    """Call only after commit. A failure must say that the database save already succeeded."""
    marker = _Marker(
        reader_id=workspace.reader_id,
        plugin_id=workspace.plugin_id,
        draft_id=workspace.draft_id,
        version=version,
    )
    try:
        _require_directory(directory)
        _require_file(directory / MARKER)
        with TemporaryDirectory(prefix=".news-marker-", dir=directory) as staging:
            temporary = Path(staging) / MARKER
            temporary.write_text(marker.model_dump_json() + "\n", encoding="utf-8")
            temporary.replace(directory / MARKER)
    except OSError as error:
        _fail(
            directory,
            "update marker",
            f"Draft saved at version {version}, but marker could not be updated; export again",
            error,
        )


def _require_directory(path: Path) -> None:
    if path.is_symlink() or not path.is_dir():
        raise OSError("expected a directory without symbolic links")


def _require_file(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise OSError("expected a regular file without symbolic links")


def _read_text(path: Path) -> str:
    _require_file(path)
    # newline="" retains CRLF and unfinished source exactly as saved by the editor.
    with path.open(encoding="utf-8", newline="") as source:
        return source.read()


def _fail(directory: Path, operation: str, reason: str, cause: Exception | None = None) -> NoReturn:
    log.info(
        "plugin_workspace.failed", operation=operation, directory=str(directory), reason=reason
    )
    raise WorkspaceError(f"Cannot {operation} workspace {directory}: {reason}.") from cause
