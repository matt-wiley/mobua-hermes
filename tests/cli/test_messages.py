import uuid
from pathlib import Path

from news.cli.messages import expected_failure_lines, unexpected_error_line
from news.service.channels import ChannelNotFound, ChannelRevisionRejected
from news.service.manifest import PluginRevisionRejected
from news.service.readers import ReaderNotFound
from news.service.validation import FieldError

LOG_PATH = Path("/state/news/cli.log")


def test_a_rejection_prints_each_field_error_then_the_log_pointer() -> None:
    error = ChannelRevisionRejected(
        [FieldError("bindings.0.url", "required"), FieldError("name", "too long")]
    )

    assert expected_failure_lines(error, LOG_PATH) == [
        "bindings.0.url: required",
        "name: too long",
        "Logged to /state/news/cli.log.",
    ]


def test_a_root_field_error_is_shown_as_the_root() -> None:
    error = PluginRevisionRejected([FieldError("", "invalid TOML")])

    assert expected_failure_lines(error, LOG_PATH) == [
        "(root): invalid TOML",
        "Logged to /state/news/cli.log.",
    ]


def test_a_missing_reader_or_channel_prints_its_message_then_the_log_pointer() -> None:
    reader_id = uuid.uuid7()

    assert expected_failure_lines(ReaderNotFound(f"no Reader {reader_id}"), LOG_PATH) == [
        f"no Reader {reader_id}",
        "Logged to /state/news/cli.log.",
    ]
    assert expected_failure_lines(ChannelNotFound("no Channel x for this Reader"), LOG_PATH) == [
        "no Channel x for this Reader",
        "Logged to /state/news/cli.log.",
    ]


def test_an_unexpected_error_is_one_line_with_its_type_and_message() -> None:
    line = unexpected_error_line(RuntimeError("disk on fire"), LOG_PATH)

    assert line == (
        "Unexpected error: RuntimeError: disk on fire. Details logged to /state/news/cli.log."
    )


def test_a_multi_line_message_is_cut_to_its_first_line() -> None:
    error = RuntimeError("database is locked\n[SQL: INSERT INTO reader ...]")

    line = unexpected_error_line(error, LOG_PATH)

    assert line == (
        "Unexpected error: RuntimeError: database is locked. Details logged to /state/news/cli.log."
    )


def test_an_error_without_a_message_shows_only_its_type() -> None:
    line = unexpected_error_line(KeyError(), LOG_PATH)

    assert line == "Unexpected error: KeyError. Details logged to /state/news/cli.log."


def test_a_message_ending_in_a_full_stop_does_not_get_a_second_one() -> None:
    line = unexpected_error_line(RuntimeError("Could not determine home directory."), LOG_PATH)

    assert line == (
        "Unexpected error: RuntimeError: Could not determine home directory. "
        "Details logged to /state/news/cli.log."
    )


def test_an_unexpected_error_with_no_log_file_says_it_was_not_logged() -> None:
    line = unexpected_error_line(RuntimeError("disk on fire"), None)

    assert (
        line == "Unexpected error: RuntimeError: disk on fire. No log file was open to record it."
    )
