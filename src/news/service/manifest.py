"""Parsing a Plugin Manifest: the TOML declaration stored on each Plugin Revision (ADR 0015)."""

import tomllib
from typing import Any

from jsonschema import Draft202012Validator, SchemaError
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from news.service.validation import FieldError, ValidationRejected


class PluginRevisionRejected(ValidationRejected):
    pass


class Manifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    command: str = Field(min_length=1)
    timeout: int = Field(gt=0, description="Seconds before the Plugin Run is killed.")
    config_schema: dict[str, Any]
    secrets: list[str] = Field(default_factory=list[str])

    @field_validator("config_schema")
    @classmethod
    def _must_be_a_json_schema(cls, schema: dict[str, Any]) -> dict[str, Any]:
        try:
            Draft202012Validator.check_schema(schema)
        except SchemaError as error:
            raise ValueError(f"not a valid JSON Schema: {error.message}") from error
        return schema


def parse_manifest(text: str) -> Manifest:
    try:
        declared = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise PluginRevisionRejected([FieldError("", f"invalid TOML: {error}")]) from error
    try:
        return Manifest.model_validate(declared)
    except ValidationError as error:
        errors = [
            FieldError(".".join(str(part) for part in detail["loc"]), detail["msg"])
            for detail in error.errors()
        ]
        raise PluginRevisionRejected(errors) from error
