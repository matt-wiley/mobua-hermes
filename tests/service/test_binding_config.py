from news.service.binding_config import validate_binding_config
from news.service.validation import FieldError

URL_REQUIRED = {
    "type": "object",
    "required": ["url"],
    "properties": {"url": {"type": "string"}},
}


def test_config_matching_the_schema_has_no_errors() -> None:
    assert validate_binding_config(URL_REQUIRED, {"url": "https://example.com/feed"}) == []


def test_missing_required_field_is_reported_against_that_field() -> None:
    errors = validate_binding_config(URL_REQUIRED, {})

    assert errors == [FieldError(field="url", message="'url' is a required property")]


def test_unknown_field_is_rejected_when_schema_forbids_additional_properties() -> None:
    schema = {**URL_REQUIRED, "additionalProperties": False}

    errors = validate_binding_config(schema, {"url": "https://example.com", "colour": "red"})

    assert [error.field for error in errors] == ["colour"]


def test_unknown_field_is_allowed_when_schema_permits_additional_properties() -> None:
    config = {"url": "https://example.com", "colour": "red"}

    assert validate_binding_config(URL_REQUIRED, config) == []


def test_nested_field_error_names_the_full_path() -> None:
    schema = {
        "type": "object",
        "properties": {
            "options": {"type": "object", "properties": {"limit": {"type": "integer"}}},
        },
    }

    errors = validate_binding_config(schema, {"options": {"limit": "ten"}})

    assert errors == [FieldError(field="options.limit", message="'ten' is not of type 'integer'")]


def test_every_error_is_reported_in_field_order() -> None:
    schema = {
        "type": "object",
        "required": ["url", "interval"],
        "properties": {"url": {"type": "string"}, "interval": {"type": "integer"}},
    }

    errors = validate_binding_config(schema, {})

    assert [error.field for error in errors] == ["interval", "url"]


def test_empty_config_is_valid_against_a_schema_with_no_requirements() -> None:
    assert validate_binding_config({"type": "object"}, {}) == []


def test_a_config_that_is_not_an_object_is_reported_at_the_root() -> None:
    errors = validate_binding_config(URL_REQUIRED, ["https://example.com"])

    assert [error.field for error in errors] == [""]
