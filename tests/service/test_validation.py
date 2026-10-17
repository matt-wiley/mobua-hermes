import pytest

from news.service.channels import ChannelRevisionRejected
from news.service.manifest import PluginRevisionRejected
from news.service.validation import FieldError, ValidationRejected


def test_rejection_carries_its_field_errors() -> None:
    errors = [FieldError("url", "required"), FieldError("timeout", "too small")]

    assert ValidationRejected(errors).errors == errors


def test_message_joins_each_field_and_message() -> None:
    rejected = ValidationRejected(
        [FieldError("url", "required"), FieldError("timeout", "too small")]
    )

    assert str(rejected) == "url: required; timeout: too small"


def test_a_single_error_has_no_separator() -> None:
    assert str(ValidationRejected([FieldError("url", "required")])) == "url: required"


def test_an_empty_field_is_shown_as_the_root() -> None:
    rejected = ValidationRejected([FieldError("", "invalid TOML")])

    assert str(rejected) == "(root): invalid TOML"


def test_no_errors_gives_an_empty_message() -> None:
    assert str(ValidationRejected([])) == ""


def test_field_errors_sort_by_field_then_message() -> None:
    errors = [FieldError("url", "b"), FieldError("interval", "z"), FieldError("url", "a")]

    assert sorted(errors) == [
        FieldError("interval", "z"),
        FieldError("url", "a"),
        FieldError("url", "b"),
    ]


@pytest.mark.parametrize("rejection", [ChannelRevisionRejected, PluginRevisionRejected])
def test_revision_rejections_are_validation_rejections(
    rejection: type[ValidationRejected],
) -> None:
    errors = [FieldError("url", "required"), FieldError("", "not an object")]

    rejected = rejection(errors)

    assert isinstance(rejected, ValidationRejected)
    assert rejected.errors == errors
    assert str(rejected) == "url: required; (root): not an object"
