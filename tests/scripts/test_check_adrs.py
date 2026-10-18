"""AC-55, AC-56: ADR metadata, reciprocal amendments, and the ADR index agree."""

from pathlib import Path

import pytest

from scripts.check_adrs import check, main

REPO_ADRS = Path(__file__).parents[2] / "docs" / "adr"


def an_adr(
    number: str,
    title: str,
    *,
    metadata: str = "Status: Accepted\nDate: 2026-10-16",
    body: str = "## Context\n\nWhy.\n",
) -> tuple[str, str]:
    return (
        f"{number}-{title.lower().replace(' ', '-')}.md",
        f"# {number}. {title}\n\n{metadata}\n\n{body}",
    )


def an_index(*rows: str) -> str:
    return (
        "# Architecture decision records\n\n"
        "| # | Decision | Status | Amended by |\n"
        "|---|---|---|---|\n" + "".join(f"{row}\n" for row in rows)
    )


def a_row(filename: str, title: str, status: str = "Accepted", amended_by: str = "") -> str:
    return f"| [{filename[:4]}]({filename}) | {title} | {status} | {amended_by} |"


FIRST = an_adr(
    "0001", "Use SQLite", metadata="Status: Accepted\nDate: 2026-10-16\nAmended by: ADR 0002"
)
SECOND = an_adr(
    "0002", "Allow Postgres", metadata="Status: Accepted\nDate: 2026-10-17\nAmends: ADR 0001"
)
CONSISTENT_FILES = dict([FIRST, SECOND])
CONSISTENT_INDEX = an_index(
    a_row(FIRST[0], "Use SQLite", amended_by="0002"), a_row(SECOND[0], "Allow Postgres")
)


def test_consistent_adrs_and_index_have_no_problems() -> None:
    assert check(CONSISTENT_FILES, CONSISTENT_INDEX) == []


def test_no_adrs_and_an_empty_index_have_no_problems() -> None:
    assert check({}, an_index()) == []


def test_an_adr_amended_by_several_lists_them_in_any_order() -> None:
    base = an_adr(
        "0001", "Base", metadata="Status: Accepted\nDate: 2026-10-16\nAmended by: ADRs 0003, 0002"
    )
    second = an_adr("0002", "Two", metadata="Status: Accepted\nDate: 2026-10-16\nAmends: ADR 0001")
    third = an_adr("0003", "Three", metadata="Status: Accepted\nDate: 2026-10-16\nAmends: ADR 0001")
    index = an_index(
        a_row(base[0], "Base", amended_by="0002, 0003"),
        a_row(second[0], "Two"),
        a_row(third[0], "Three"),
    )

    assert check(dict([base, second, third]), index) == []


# AC-55: metadata


@pytest.mark.parametrize("field", ["Status", "Date"])
def test_a_missing_status_or_date_is_a_problem(field: str) -> None:
    metadata = "\n".join(
        line for line in ["Status: Accepted", "Date: 2026-10-16"] if not line.startswith(field)
    )
    filename, text = an_adr("0001", "Use SQLite", metadata=metadata)

    assert check({filename: text}, an_index(a_row(filename, "Use SQLite"))) == [
        f"{filename}: {field}: missing"
    ]


def test_an_empty_status_is_missing() -> None:
    filename, text = an_adr("0001", "Use SQLite", metadata="Status:\nDate: 2026-10-16")

    assert check({filename: text}, an_index(a_row(filename, "Use SQLite", status=""))) == [
        f"{filename}: Status: missing"
    ]


def test_a_date_that_is_not_iso_is_a_problem() -> None:
    filename, text = an_adr("0001", "Use SQLite", metadata="Status: Accepted\nDate: 16 Oct 2026")

    assert check({filename: text}, an_index(a_row(filename, "Use SQLite"))) == [
        f"{filename}: Date: '16 Oct 2026' is not YYYY-MM-DD"
    ]


def test_a_repeated_metadata_line_is_a_problem() -> None:
    filename, text = an_adr(
        "0001", "Use SQLite", metadata="Status: Accepted\nStatus: Proposed\nDate: 2026-10-16"
    )

    assert check({filename: text}, an_index(a_row(filename, "Use SQLite"))) == [
        f"{filename}: Status: appears 2 times"
    ]


def test_metadata_words_in_the_body_are_not_metadata() -> None:
    filename, text = an_adr(
        "0001",
        "Use SQLite",
        metadata="Date: 2026-10-16",
        body="## Context\n\nStatus: Accepted\nAmends: ADR 0009\n",
    )

    assert check({filename: text}, an_index(a_row(filename, "Use SQLite"))) == [
        f"{filename}: Status: missing"
    ]


def test_a_missing_title_heading_is_a_problem() -> None:
    filename = "0001-use-sqlite.md"
    text = "Status: Accepted\nDate: 2026-10-16\n"

    assert check({filename: text}, an_index(a_row(filename, "Use SQLite"))) == [
        f"{filename}: title: first line is not '# 0001. <title>'"
    ]


def test_a_title_numbered_unlike_its_file_is_a_problem() -> None:
    filename = "0001-use-sqlite.md"
    text = "# 0007. Use SQLite\n\nStatus: Accepted\nDate: 2026-10-16\n"

    assert check({filename: text}, an_index(a_row(filename, "Use SQLite"))) == [
        f"{filename}: title: first line is not '# 0001. <title>'"
    ]


def test_a_file_not_named_like_an_adr_is_a_problem() -> None:
    files = {**CONSISTENT_FILES, "notes.md": "# Notes\n"}

    assert check(files, CONSISTENT_INDEX) == ["notes.md: filename: is not 'NNNN-short-title.md'"]


def test_two_files_with_one_number_are_a_problem() -> None:
    """The first file by name keeps the number for the other checks."""
    duplicate = an_adr("0002", "Also allow MySQL", metadata="Status: Proposed\nDate: 2026-10-17")
    files = {**CONSISTENT_FILES, duplicate[0]: duplicate[1]}

    assert check(files, CONSISTENT_INDEX) == [
        f"{duplicate[0]}: filename: number 0002 is also used by {SECOND[0]}"
    ]


# AC-55: reciprocal amendments


def test_an_amends_without_the_matching_amended_by_is_a_problem() -> None:
    first = an_adr("0001", "Use SQLite")
    index = an_index(a_row(first[0], "Use SQLite"), a_row(SECOND[0], "Allow Postgres"))

    assert check(dict([first, SECOND]), index) == [
        f"{first[0]}: Amended by: lacks ADR 0002, which amends it"
    ]


def test_an_amended_by_without_the_matching_amends_is_a_problem() -> None:
    second = an_adr("0002", "Allow Postgres")
    index = an_index(
        a_row(FIRST[0], "Use SQLite", amended_by="0002"), a_row(second[0], "Allow Postgres")
    )

    assert check(dict([FIRST, second]), index) == [
        f"{second[0]}: Amends: lacks ADR 0001, which lists it under Amended by"
    ]


def test_an_amendment_of_an_unknown_adr_is_a_problem() -> None:
    second = an_adr(
        "0002",
        "Allow Postgres",
        metadata="Status: Accepted\nDate: 2026-10-17\nAmends: ADRs 0001, 0009",
    )
    files = {FIRST[0]: FIRST[1], second[0]: second[1]}

    assert check(files, CONSISTENT_INDEX) == [f"{second[0]}: Amends: ADR 0009 does not exist"]


@pytest.mark.parametrize("value", ["ADR 16", "0001", "ADRs 0001 and 0003", "ADR 0001,"])
def test_a_malformed_amendment_list_is_a_problem(value: str) -> None:
    second = an_adr(
        "0002", "Allow Postgres", metadata=f"Status: Accepted\nDate: 2026-10-17\nAmends: {value}"
    )

    assert check({FIRST[0]: FIRST[1], second[0]: second[1]}, CONSISTENT_INDEX) == [
        f"{second[0]}: Amends: {value!r} is not 'ADR NNNN' or 'ADRs NNNN, NNNN'",
        f"{second[0]}: Amends: lacks ADR 0001, which lists it under Amended by",
    ]


# AC-56: the index


def test_an_adr_missing_from_the_index_is_a_problem() -> None:
    index = an_index(a_row(FIRST[0], "Use SQLite", amended_by="0002"))

    assert check(CONSISTENT_FILES, index) == [f"README.md: 0002: no row for {SECOND[0]}"]


def test_an_adr_listed_twice_is_a_problem() -> None:
    index = CONSISTENT_INDEX + a_row(SECOND[0], "Allow Postgres") + "\n"

    assert check(CONSISTENT_FILES, index) == ["README.md: 0002: listed 2 times"]


@pytest.mark.parametrize("trailing_pipe", [True, False])
def test_a_duplicate_row_without_a_leading_pipe_is_a_problem(trailing_pipe: bool) -> None:
    duplicate = a_row(FIRST[0], "Use SQLite", amended_by="0002").removeprefix("|")
    if not trailing_pipe:
        duplicate = duplicate.removesuffix("|")

    assert check(CONSISTENT_FILES, CONSISTENT_INDEX + duplicate + "\n") == [
        "README.md: 0001: listed 2 times"
    ]


@pytest.mark.parametrize(
    ("row", "problem"),
    [
        (
            a_row("0003-gone.md", "Gone"),
            "0003: no ADR file",
        ),
        (
            "| malformed |",
            "row: 'malformed |' does not have 4 cells",
        ),
    ],
)
def test_invalid_rows_without_a_leading_pipe_are_reported(row: str, problem: str) -> None:
    index = CONSISTENT_INDEX + row.removeprefix("|") + "\n"

    assert check(CONSISTENT_FILES, index) == [f"README.md: {problem}"]


@pytest.mark.parametrize("header", [True, False])
def test_consistent_index_rows_can_omit_leading_pipes(header: bool) -> None:
    lines = CONSISTENT_INDEX.splitlines()
    if not header:
        lines.remove("| # | Decision | Status | Amended by |")
    index = "\n".join(line.removeprefix("|") for line in lines)

    assert check(CONSISTENT_FILES, index) == []


def test_prose_with_pipes_outside_the_index_table_is_ignored() -> None:
    index = "Use a pipe | to separate cells.\n\n" + CONSISTENT_INDEX
    index += "\nOuter pipes | are optional.\n"

    assert check(CONSISTENT_FILES, index) == []


@pytest.mark.parametrize(
    ("first_row", "problem"),
    [
        (
            a_row(FIRST[0], "Use SQLite", amended_by="0002"),
            "0001: listed 2 times",
        ),
        (a_row("0003-gone.md", "Gone"), "0003: no ADR file"),
        ("| malformed |", "row: '| malformed |' does not have 4 cells"),
    ],
)
def test_an_entry_replacing_the_header_is_validated(first_row: str, problem: str) -> None:
    index = CONSISTENT_INDEX.replace("| # | Decision | Status | Amended by |", first_row)

    assert check(CONSISTENT_FILES, index) == [f"README.md: {problem}"]


@pytest.mark.parametrize(
    ("first_row", "problem"),
    [
        (
            a_row(FIRST[0], "Wrong title", amended_by="0002"),
            "Decision 'Wrong title' does not match title 'Use SQLite'",
        ),
        (
            a_row(FIRST[0], "Use SQLite", status="Proposed", amended_by="0002"),
            "Status 'Proposed' does not match 'Accepted'",
        ),
        (
            a_row(FIRST[0], "Use SQLite"),
            "Amended by '' does not match '0002'",
        ),
        (
            a_row("0001-renamed.md", "Use SQLite", amended_by="0002"),
            f"links to '0001-renamed.md', not {FIRST[0]!r}",
        ),
    ],
)
def test_the_first_entry_without_a_header_has_its_fields_checked(
    first_row: str, problem: str
) -> None:
    index = f"{first_row}\n|---|---|---|---|\n{a_row(SECOND[0], 'Allow Postgres')}\n"

    assert check(CONSISTENT_FILES, index) == [f"README.md: 0001: {problem}"]


def test_a_header_is_recognized_by_its_cells_despite_spacing() -> None:
    index = CONSISTENT_INDEX.replace(
        "| # | Decision | Status | Amended by |", "  |#|  Decision |Status| Amended by|  "
    )

    assert check(CONSISTENT_FILES, index) == []


def test_a_row_without_an_adr_file_is_a_problem() -> None:
    index = CONSISTENT_INDEX + a_row("0003-gone.md", "Gone") + "\n"

    assert check(CONSISTENT_FILES, index) == ["README.md: 0003: no ADR file"]


def test_a_row_linking_to_another_file_is_a_problem() -> None:
    index = an_index(
        a_row(FIRST[0], "Use SQLite", amended_by="0002"), a_row("0002-renamed.md", "Allow Postgres")
    )

    assert check(CONSISTENT_FILES, index) == [
        f"README.md: 0002: links to '0002-renamed.md', not {SECOND[0]!r}"
    ]


def test_a_row_whose_title_differs_is_a_problem() -> None:
    index = an_index(
        a_row(FIRST[0], "Use SQLite", amended_by="0002"), a_row(SECOND[0], "Allow MySQL")
    )

    assert check(CONSISTENT_FILES, index) == [
        "README.md: 0002: Decision 'Allow MySQL' does not match title 'Allow Postgres'"
    ]


def test_a_row_whose_status_differs_is_a_problem() -> None:
    index = an_index(
        a_row(FIRST[0], "Use SQLite", amended_by="0002"),
        a_row(SECOND[0], "Allow Postgres", status="Proposed"),
    )

    assert check(CONSISTENT_FILES, index) == [
        "README.md: 0002: Status 'Proposed' does not match 'Accepted'"
    ]


@pytest.mark.parametrize("amended_by", ["", "0002, 0003", "0003"])
def test_a_row_whose_amended_by_differs_is_a_problem(amended_by: str) -> None:
    index = an_index(
        a_row(FIRST[0], "Use SQLite", amended_by=amended_by), a_row(SECOND[0], "Allow Postgres")
    )

    assert check(CONSISTENT_FILES, index) == [
        f"README.md: 0001: Amended by {amended_by!r} does not match '0002'"
    ]


def test_a_malformed_row_is_a_problem() -> None:
    index = CONSISTENT_INDEX + "| [0003](0003-gone.md) | Gone |\n"

    assert check(CONSISTENT_FILES, index) == [
        "README.md: row: '| [0003](0003-gone.md) | Gone |' does not have 4 cells"
    ]


@pytest.mark.parametrize(
    ("row", "cell"),
    [
        ("| 0003 | Gone | Accepted |  |", "'0003' is not '[NNNN](file.md)'"),
        (
            "| [0002](0002-allow-postgres.md) | Allow Postgres | Accepted | 0003 and 0004 |",
            "Amended by '0003 and 0004' is not 'NNNN, NNNN'",
        ),
    ],
)
def test_a_malformed_cell_is_a_problem(row: str, cell: str) -> None:
    index = an_index(a_row(FIRST[0], "Use SQLite", amended_by="0002"), row)

    assert check(CONSISTENT_FILES, index)[0] == f"README.md: row: {cell}"


def test_a_missing_index_is_a_problem() -> None:
    assert check(CONSISTENT_FILES, None) == ["README.md: missing"]


def test_every_problem_is_reported_in_file_order() -> None:
    first = an_adr("0001", "Use SQLite", metadata="Date: 2026-10-16")
    index = an_index(a_row(first[0], "Use SQLite", amended_by="0002"))

    assert check(dict([SECOND, first]), index) == [
        f"{first[0]}: Status: missing",
        f"{first[0]}: Amended by: lacks ADR 0002, which amends it",
        "README.md: 0001: Amended by '0002' does not match ''",
        f"README.md: 0002: no row for {SECOND[0]}",
    ]


# The local script


def test_the_repository_adrs_pass(capsys: pytest.CaptureFixture[str]) -> None:
    """ADRs 0024 and 0025 amend several others; the current set must stay consistent."""
    assert main([str(REPO_ADRS)]) == 0
    assert "ADRs and index are consistent" in capsys.readouterr().out


def test_the_script_reads_a_directory_and_exits_nonzero_on_problems(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    for filename, text in CONSISTENT_FILES.items():
        (tmp_path / filename).write_text(text)
    (tmp_path / "README.md").write_text(an_index(a_row(FIRST[0], "Use SQLite", amended_by="0002")))

    assert main([str(tmp_path)]) == 1
    assert capsys.readouterr().err == f"{tmp_path}/README.md: 0002: no row for {SECOND[0]}\n"


def test_the_script_ignores_files_that_are_not_markdown(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    for filename, text in CONSISTENT_FILES.items():
        (tmp_path / filename).write_text(text)
    (tmp_path / "README.md").write_text(CONSISTENT_INDEX)
    (tmp_path / ".DS_Store").write_bytes(b"\x00\x01")

    assert main([str(tmp_path)]) == 0
    capsys.readouterr()


def test_the_script_reports_a_duplicate_in_place_of_the_index_header(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    for filename, text in CONSISTENT_FILES.items():
        (tmp_path / filename).write_text(text)
    index = CONSISTENT_INDEX.replace(
        "| # | Decision | Status | Amended by |", a_row(FIRST[0], "Use SQLite", amended_by="0002")
    )
    (tmp_path / "README.md").write_text(index)

    assert main([str(tmp_path)]) == 1
    captured = capsys.readouterr()
    assert captured.err == f"{tmp_path}/README.md: 0001: listed 2 times\n"
    assert captured.out == ""


def test_the_script_rejects_a_missing_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = tmp_path / "adr"

    assert main([str(missing)]) == 1
    assert capsys.readouterr().err == f"{missing}: not a directory\n"


def test_the_script_reports_a_duplicate_without_a_leading_pipe(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    for filename, text in CONSISTENT_FILES.items():
        (tmp_path / filename).write_text(text)
    duplicate = a_row(FIRST[0], "Use SQLite", amended_by="0002").removeprefix("|")
    (tmp_path / "README.md").write_text(CONSISTENT_INDEX + duplicate + "\n")

    assert main([str(tmp_path)]) == 1
    captured = capsys.readouterr()
    assert captured.err == f"{tmp_path}/README.md: 0001: listed 2 times\n"
    assert captured.out == ""
