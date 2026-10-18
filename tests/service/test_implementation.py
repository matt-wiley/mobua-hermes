"""Validating a saved implementation before promotion, testing or running it (AC-49, D-25)."""

import pytest

from news.service.implementation import unpinned_dependency_errors, validate_implementation
from news.service.manifest import PluginRevisionRejected
from news.service.validation import FieldError
from tests.service.factories import OPEN_PLUGIN_MANIFEST


def script(*dependencies: str) -> str:
    # TOML literal strings, so markers may contain double quotes.
    listed = ", ".join(f"'{dependency}'" for dependency in dependencies)
    return f'# /// script\n# dependencies = [{listed}]\n# ///\n\nprint("hi")\n'


def test_an_exactly_pinned_dependency_is_accepted() -> None:
    assert unpinned_dependency_errors({"main.py": script("feedparser==6.0.11")}) == []


def test_a_lower_bound_dependency_is_rejected_naming_its_position() -> None:
    errors = unpinned_dependency_errors({"main.py": script("feedparser==6.0.11", "feedparser>=6")})

    assert [error.field for error in errors] == ["code[main.py].dependencies.1"]
    assert "feedparser>=6" in errors[0].message
    assert "==" in errors[0].message


@pytest.mark.parametrize(
    "dependency",
    [
        "feedparser",
        "feedparser~=6.0",
        "feedparser==6.*",
        "feedparser>=6,<7",
        "feedparser==6.0.11,!=6.0.10",
        "feedparser @ https://example.com/feedparser.whl",
    ],
)
def test_anything_short_of_one_exact_version_is_rejected(dependency: str) -> None:
    assert [
        error.field for error in unpinned_dependency_errors({"main.py": script(dependency)})
    ] == ["code[main.py].dependencies.0"]


@pytest.mark.parametrize(
    "dependency",
    [
        "feedparser===6.0.11",
        "requests[socks]==2.32.3",
        'tomli==2.2.1; python_version < "3.11"',
    ],
)
def test_exact_pins_with_extras_markers_or_arbitrary_equality_are_accepted(
    dependency: str,
) -> None:
    assert unpinned_dependency_errors({"main.py": script(dependency)}) == []


@pytest.mark.parametrize(
    "source",
    [
        "",
        'print("no inline metadata")\n',
        "# /// script\n# dependencies = []\n# ///\n",
        '# /// script\n# requires-python = ">=3.14"\n# ///\n',
    ],
    ids=["empty", "no-block", "empty-list", "no-dependencies-key"],
)
def test_scripts_without_dependencies_are_accepted(source: str) -> None:
    assert unpinned_dependency_errors({"main.py": source}) == []


def test_windows_line_endings_do_not_hide_the_metadata_block() -> None:
    source = script("feedparser>=6").replace("\n", "\r\n")

    assert len(unpinned_dependency_errors({"main.py": source})) == 1


def test_only_python_files_are_read_and_every_one_is_checked() -> None:
    code = {
        "main.py": script("feedparser==6.0.11"),
        "lib/helpers.py": script("requests"),
        "README.md": script("anything"),
    }

    assert [error.field for error in unpinned_dependency_errors(code)] == [
        "code[lib/helpers.py].dependencies.0"
    ]


@pytest.mark.parametrize(
    "source,message",
    [
        ("# /// script\n# dependencies = [\n# ///\n", "invalid inline script metadata"),
        (
            "# /// script\n# dependencies = []\n# ///\nx = 1\n"
            "# /// script\n# dependencies = []\n# ///\n",
            "more than one",
        ),
        ('# /// script\n# dependencies = "feedparser==6.0.11"\n# ///\n', "list of strings"),
        ("# /// script\n# dependencies = [6]\n# ///\n", "list of strings"),
        ('# /// script\n# dependencies = ["not a requirement!"]\n# ///\n', "not a valid"),
    ],
    ids=["bad-toml", "two-blocks", "not-a-list", "not-strings", "bad-requirement"],
)
def test_malformed_metadata_is_rejected_rather_than_skipped(source: str, message: str) -> None:
    [error] = unpinned_dependency_errors({"main.py": source})

    assert error.field.startswith("code[main.py]")
    assert message in error.message


def test_a_valid_implementation_returns_its_parsed_manifest() -> None:
    manifest = validate_implementation(OPEN_PLUGIN_MANIFEST, {"main.py": script("a==1")})

    assert manifest.name == "scraper"


def test_manifest_and_dependency_errors_are_reported_together() -> None:
    manifest = 'name = "x"\ncommand = "python main.py"\ntimeout = 0\nconfig_schema = {}\n'

    with pytest.raises(PluginRevisionRejected) as raised:
        validate_implementation(manifest, {"main.py": script("feedparser>=6")})

    assert [error.field for error in raised.value.errors] == [
        "manifest.timeout",
        "code[main.py].dependencies.0",
    ]


def test_invalid_toml_is_reported_at_the_manifest_root() -> None:
    with pytest.raises(PluginRevisionRejected) as raised:
        validate_implementation('name = "unfinished', {})

    assert [error.field for error in raised.value.errors] == ["manifest"]
    assert isinstance(raised.value.errors[0], FieldError)
