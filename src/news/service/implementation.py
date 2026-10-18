"""Validating a Plugin implementation: its Manifest and pinned inline dependencies (ADR 0022).

Promotion uses this now; Draft Test Runs and Plugin Runs reuse it rather than re-parsing.
"""

import re
import tomllib
from typing import Any, cast

from packaging.requirements import InvalidRequirement, Requirement

from news.service.manifest import Manifest, PluginRevisionRejected, parse_manifest
from news.service.validation import FieldError

# The reference expression from PEP 723 (inline script metadata), as uv reads it.
_METADATA_BLOCK = re.compile(
    r"(?m)^# /// (?P<type>[a-zA-Z0-9-]+)$\s(?P<content>(^#(| .*)$\s)+)^# ///$"
)


def validate_implementation(manifest: str, code: dict[str, str]) -> Manifest:
    """Return the parsed Manifest, or raise PluginRevisionRejected with every problem found."""
    errors: list[FieldError] = []
    parsed: Manifest | None = None
    try:
        parsed = parse_manifest(manifest)
    except PluginRevisionRejected as rejected:
        errors += [
            FieldError(f"manifest.{error.field}" if error.field else "manifest", error.message)
            for error in rejected.errors
        ]
    errors += unpinned_dependency_errors(code)
    if parsed is None or errors:
        raise PluginRevisionRejected(errors)
    return parsed


def unpinned_dependency_errors(code: dict[str, str]) -> list[FieldError]:
    """Errors for every Python file whose inline dependencies are not each pinned with `==`."""
    return [
        error
        for path, source in code.items()
        if path.endswith(".py")
        for error in _script_errors(f"code[{path}]", source)
    ]


def _script_errors(field: str, source: str) -> list[FieldError]:
    # The PEP 723 expression only matches LF endings; CRLF must not hide a block from the check.
    blocks = [
        block
        for block in _METADATA_BLOCK.finditer(source.replace("\r\n", "\n"))
        if block["type"] == "script"
    ]
    if not blocks:
        return []
    if len(blocks) > 1:
        return [FieldError(field, "more than one inline script metadata block")]
    content = "".join(
        line[2:] if line.startswith("# ") else line[1:]
        for line in blocks[0]["content"].splitlines(keepends=True)
    )
    try:
        metadata = tomllib.loads(content)
    except tomllib.TOMLDecodeError as error:
        return [FieldError(field, f"invalid inline script metadata: {error}")]
    dependencies: object = metadata.get("dependencies", [])
    if not isinstance(dependencies, list) or not all(
        isinstance(dependency, str) for dependency in cast(list[Any], dependencies)
    ):
        return [FieldError(f"{field}.dependencies", "must be a list of strings")]
    return [
        FieldError(f"{field}.dependencies.{index}", problem)
        for index, dependency in enumerate(cast(list[str], dependencies))
        if (problem := _pin_problem(dependency))
    ]


def _pin_problem(dependency: str) -> str | None:
    try:
        requirement = Requirement(dependency)
    except InvalidRequirement as error:
        return f"not a valid dependency: {error}"
    specifiers = list(requirement.specifier)
    exactly_pinned = (
        requirement.url is None
        and len(specifiers) == 1
        and specifiers[0].operator in {"==", "==="}
        and not specifiers[0].version.endswith(".*")
    )
    if exactly_pinned:
        return None
    return f"{dependency!r} must be pinned to one exact version with =="
