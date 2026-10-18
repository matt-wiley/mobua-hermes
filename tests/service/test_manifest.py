import pytest

from news.service.manifest import PluginRevisionRejected, parse_manifest

VALID = """
name = "rss"
command = "python main.py"
timeout = 60
secrets = ["FEED_TOKEN"]

[config_schema]
type = "object"
required = ["url"]

[config_schema.properties.url]
type = "string"
"""


def test_valid_manifest_is_parsed() -> None:
    manifest = parse_manifest(VALID)

    assert manifest.name == "rss"
    assert manifest.command == "python main.py"
    assert manifest.timeout == 60
    assert manifest.secrets == ["FEED_TOKEN"]
    assert manifest.config_schema == {
        "type": "object",
        "required": ["url"],
        "properties": {"url": {"type": "string"}},
    }


def test_secrets_default_to_empty() -> None:
    manifest = parse_manifest(VALID.replace('secrets = ["FEED_TOKEN"]', ""))

    assert manifest.secrets == []


def test_malformed_toml_is_rejected() -> None:
    with pytest.raises(PluginRevisionRejected) as raised:
        parse_manifest('name = "rss')

    assert raised.value.errors[0].field == ""


def test_missing_config_schema_is_rejected_naming_the_field() -> None:
    manifest_without_schema = VALID.split("[config_schema]")[0]

    with pytest.raises(PluginRevisionRejected) as raised:
        parse_manifest(manifest_without_schema)

    assert [error.field for error in raised.value.errors] == ["config_schema"]


def test_config_schema_that_is_not_a_valid_json_schema_is_rejected() -> None:
    with pytest.raises(PluginRevisionRejected) as raised:
        parse_manifest(VALID.replace('type = "object"', "type = 12"))

    assert [error.field for error in raised.value.errors] == ["config_schema"]


@pytest.mark.parametrize("timeout", [0, -5])
def test_timeout_must_be_positive(timeout: int) -> None:
    with pytest.raises(PluginRevisionRejected) as raised:
        parse_manifest(VALID.replace("timeout = 60", f"timeout = {timeout}"))

    assert [error.field for error in raised.value.errors] == ["timeout"]


def test_minimum_timeout_of_one_second_is_accepted() -> None:
    assert parse_manifest(VALID.replace("timeout = 60", "timeout = 1")).timeout == 1


def test_empty_command_is_rejected() -> None:
    with pytest.raises(PluginRevisionRejected) as raised:
        parse_manifest(VALID.replace('command = "python main.py"', 'command = ""'))

    assert [error.field for error in raised.value.errors] == ["command"]
