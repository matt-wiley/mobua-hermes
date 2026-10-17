"""What the CLI prints on stderr when a command fails (spec review-followups-01, D-6)."""

from pathlib import Path

from news.service.channels import ChannelNotFound
from news.service.credentials import SecretNotFound
from news.service.encryption import EncryptionError
from news.service.readers import ReaderNotFound
from news.service.validation import ValidationRejected

# Failures caused by the user's input; the service layer logs them where they are raised.
EXPECTED_FAILURES = (
    ValidationRejected,
    ChannelNotFound,
    ReaderNotFound,
    SecretNotFound,
    EncryptionError,
)


def expected_failure_lines(error: Exception, log_path: Path) -> list[str]:
    if isinstance(error, ValidationRejected):
        lines = [str(field_error) for field_error in error.errors]
    else:
        lines = [str(error)]
    return [*lines, f"Logged to {log_path}."]


def unexpected_error_line(error: Exception, log_path: Path | None) -> str:
    # Database errors carry the SQL and its parameters on later lines; those belong in the log.
    message = next(iter(str(error).splitlines()), "").removesuffix(".")
    description = f"{type(error).__name__}: {message}" if message else type(error).__name__
    if log_path is None:
        return f"Unexpected error: {description}. No log file was open to record it."
    return f"Unexpected error: {description}. Details logged to {log_path}."
