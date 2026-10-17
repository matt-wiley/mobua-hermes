"""Validating a Plugin Binding's config against its Plugin Revision's config schema."""

import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, cast

from jsonschema import Draft202012Validator, ValidationError


@dataclass(frozen=True, order=True)
class ConfigError:
    """One problem with a Binding's config, located by its dotted field path ("" is the root)."""

    field: str
    message: str


def validate_binding_config(schema: dict[str, Any], config: Any) -> list[ConfigError]:
    validator = Draft202012Validator(schema)
    # types-jsonschema leaves one iter_errors overload partially unknown.
    iter_errors = validator.iter_errors  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
    schema_errors: list[ValidationError] = list(iter_errors(config))
    errors = {
        config_error
        for schema_error in schema_errors
        for config_error in _field_errors(schema_error)
    }
    return sorted(errors)


def _field_errors(error: ValidationError) -> Iterator[ConfigError]:
    # jsonschema reports "required" and "additionalProperties" on the parent object, but the
    # Reader needs to see which field is missing or unexpected.
    parent = [str(part) for part in error.absolute_path]
    if error.validator == "required":
        for name in _missing_fields(error):
            yield ConfigError(_join(parent, name), f"'{name}' is a required property")
    elif error.validator == "additionalProperties" and error.validator_value is False:
        for name in _unexpected_fields(error):
            yield ConfigError(_join(parent, name), f"'{name}' is not an allowed field")
    else:
        yield ConfigError(_join(parent), error.message)


def _missing_fields(error: ValidationError) -> list[str]:
    instance = cast(dict[str, Any], error.instance)
    required = cast(list[str], error.validator_value)
    return [name for name in required if name not in instance]


def _unexpected_fields(error: ValidationError) -> list[str]:
    instance = cast(dict[str, Any], error.instance)
    schema = cast(dict[str, Any], error.schema)
    properties = cast(dict[str, Any], schema.get("properties", {}))
    patterns = cast(dict[str, Any], schema.get("patternProperties", {}))
    return [
        name
        for name in instance
        if name not in properties and not any(re.search(pattern, name) for pattern in patterns)
    ]


def _join(parent: list[str], name: str | None = None) -> str:
    return ".".join([*parent, name] if name is not None else parent)
