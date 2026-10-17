"""Field-level validation errors shared by everything that rejects user input."""

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class FieldError:
    """One problem with some input, located by its dotted field path ("" is the root)."""

    field: str
    message: str


class ValidationRejected(Exception):
    """Input rejected for one or more field errors, all reported together."""

    def __init__(self, errors: list[FieldError]) -> None:
        super().__init__(
            "; ".join(f"{error.field or '(root)'}: {error.message}" for error in errors)
        )
        self.errors = errors
