"""Check that ADR metadata, reciprocal amendments, and the ADR index agree (AC-55, AC-56).

Usage: `uv run python -m scripts.check_adrs [docs/adr]`. Prints one line per discrepancy as
`<file>: <field>: <problem>` and exits 1 if there are any.
"""

import re
import sys
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path

INDEX = "README.md"
FILENAME = re.compile(r"(\d{4})-[a-z0-9]+(?:-[a-z0-9]+)*\.md")
METADATA = re.compile(r"(Status|Date|Amends|Amended by):(.*)")
FIELDS = ("Status", "Date", "Amends", "Amended by")
AMENDMENTS = re.compile(r"ADRs? (\d{4}(?:, \d{4})*)")
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
INDEX_LINK = re.compile(r"\[(\d{4})\]\(([^)]+)\)")
INDEX_NUMBERS = re.compile(r"(?:\d{4}(?:, \d{4})*)?")
SEPARATOR_ROW = re.compile(r"\|[-:| ]+\|")


@dataclass(frozen=True)
class Adr:
    number: str
    filename: str
    title: str | None
    status: str | None
    amends: frozenset[str]
    amended_by: frozenset[str]


@dataclass(frozen=True)
class IndexRow:
    number: str
    link: str
    title: str
    status: str
    amended_by_cell: str
    amended_by: frozenset[str]


def check(files: Mapping[str, str], index: str | None) -> list[str]:
    """Every discrepancy, by ADR file in name order, then the index by ADR number."""
    adrs: dict[str, Adr] = {}
    problems: dict[str, list[str]] = {}
    for filename in sorted(files):
        problems[filename] = []
        match = FILENAME.fullmatch(filename)
        if match is None:
            problems[filename].append("filename: is not 'NNNN-short-title.md'")
            continue
        adr = _parse_adr(filename, match[1], files[filename], problems[filename])
        if adr.number in adrs:
            problems[filename].append(
                f"filename: number {adr.number} is also used by {adrs[adr.number].filename}"
            )
            continue
        adrs[adr.number] = adr

    for adr in adrs.values():
        problems[adr.filename].extend(_amendment_problems(adr, adrs))

    report = [
        f"{filename}: {problem}" for filename in sorted(problems) for problem in problems[filename]
    ]
    if index is None:
        return [*report, f"{INDEX}: missing"]
    return report + [f"{INDEX}: {problem}" for problem in _index_problems(index, adrs)]


def _parse_adr(filename: str, number: str, text: str, problems: list[str]) -> Adr:
    lines = text.splitlines()
    heading = re.fullmatch(rf"# {number}\. (.+)", lines[0]) if lines else None
    if heading is None:
        problems.append(f"title: first line is not '# {number}. <title>'")

    values: dict[str, list[str]] = {field: [] for field in FIELDS}
    for line in _header_block(lines):
        if metadata := METADATA.fullmatch(line):
            values[metadata[1]].append(metadata[2].strip())

    for field in ("Status", "Date"):
        if not any(values[field]):
            problems.append(f"{field}: missing")
    for field, found in values.items():
        if len(found) > 1:
            problems.append(f"{field}: appears {len(found)} times")
    if values["Date"] and values["Date"][0] and not _is_iso_date(values["Date"][0]):
        problems.append(f"Date: {values['Date'][0]!r} is not YYYY-MM-DD")

    return Adr(
        number=number,
        filename=filename,
        title=None if heading is None else heading[1],
        status=values["Status"][0] if values["Status"] else None,
        amends=_amendments("Amends", values["Amends"], problems),
        amended_by=_amendments("Amended by", values["Amended by"], problems),
    )


def _header_block(lines: list[str]) -> Iterator[str]:
    """The metadata lines sit under the title, before the first section."""
    for line in lines:
        if line.startswith("## "):
            return
        yield line


def _is_iso_date(value: str) -> bool:
    if ISO_DATE.fullmatch(value) is None:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _amendments(field: str, found: list[str], problems: list[str]) -> frozenset[str]:
    if not found:
        return frozenset()
    match = AMENDMENTS.fullmatch(found[0])
    if match is None:
        problems.append(f"{field}: {found[0]!r} is not 'ADR NNNN' or 'ADRs NNNN, NNNN'")
        return frozenset()
    return frozenset(match[1].split(", "))


def _amendment_problems(adr: Adr, adrs: Mapping[str, Adr]) -> Iterator[str]:
    for target in sorted(adr.amends - adrs.keys()):
        yield f"Amends: ADR {target} does not exist"
    for target in sorted(adr.amended_by - adrs.keys()):
        yield f"Amended by: ADR {target} does not exist"
    for other in sorted(adrs.values(), key=lambda other: other.number):
        if adr.number in other.amended_by and other.number not in adr.amends:
            yield f"Amends: lacks ADR {other.number}, which lists it under Amended by"
    for other in sorted(adrs.values(), key=lambda other: other.number):
        if adr.number in other.amends and other.number not in adr.amended_by:
            yield f"Amended by: lacks ADR {other.number}, which amends it"


def _index_problems(index: str, adrs: Mapping[str, Adr]) -> list[str]:
    rows: list[IndexRow] = []
    problems: list[str] = []
    for line in _table_rows(index):
        row = _parse_row(line, problems)
        if row is not None:
            rows.append(row)

    counts = Counter(row.number for row in rows)
    first_rows = {row.number: row for row in reversed(rows)}
    for number in sorted(adrs.keys() | counts.keys()):
        adr, row = adrs.get(number), first_rows.get(number)
        if row is None:
            problems.append(f"{number}: no row for {adrs[number].filename}")
        elif adr is None:
            problems.append(f"{number}: no ADR file")
        elif counts[number] > 1:
            problems.append(f"{number}: listed {counts[number]} times")
        else:
            problems.extend(f"{number}: {problem}" for problem in _row_problems(row, adr))
    return problems


def _table_rows(index: str) -> Iterator[str]:
    """Table lines, without the header and separator rows."""
    table = [line.strip() for line in index.splitlines() if line.strip().startswith("|")]
    yield from (line for line in table[1:] if SEPARATOR_ROW.fullmatch(line) is None)


def _parse_row(line: str, problems: list[str]) -> IndexRow | None:
    cells = [cell.strip() for cell in line.strip("|").split("|")]
    if len(cells) != 4:
        problems.append(f"row: {line!r} does not have 4 cells")
        return None
    link_cell, title, status, amended_by = cells
    link = INDEX_LINK.fullmatch(link_cell)
    if link is None:
        problems.append(f"row: {link_cell!r} is not '[NNNN](file.md)'")
        return None
    if INDEX_NUMBERS.fullmatch(amended_by) is None:
        problems.append(f"row: Amended by {amended_by!r} is not 'NNNN, NNNN'")
        return None
    return IndexRow(
        number=link[1],
        link=link[2],
        title=title,
        status=status,
        amended_by_cell=amended_by,
        amended_by=frozenset(amended_by.split(", ")) if amended_by else frozenset(),
    )


def _row_problems(row: IndexRow, adr: Adr) -> Iterator[str]:
    if row.link != adr.filename:
        yield f"links to {row.link!r}, not {adr.filename!r}"
    if adr.title is not None and row.title != adr.title:
        yield f"Decision {row.title!r} does not match title {adr.title!r}"
    if adr.status and row.status != adr.status:
        yield f"Status {row.status!r} does not match {adr.status!r}"
    if row.amended_by != adr.amended_by:
        expected = ", ".join(sorted(adr.amended_by))
        yield f"Amended by {row.amended_by_cell!r} does not match {expected!r}"


def main(argv: Sequence[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    directory = Path(arguments[0] if arguments else "docs/adr")
    if not directory.is_dir():
        print(f"{directory}: not a directory", file=sys.stderr)
        return 1

    files = {
        path.name: path.read_text(encoding="utf-8")
        for path in directory.glob("*.md")
        if path.name != INDEX
    }
    index_path = directory / INDEX
    index = index_path.read_text(encoding="utf-8") if index_path.is_file() else None

    problems = check(files, index)
    for problem in problems:
        print(f"{directory}/{problem}", file=sys.stderr)
    if problems:
        return 1
    print(f"{len(files)} ADRs and index are consistent: {directory}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
