"""Reading and writing the two CSVs.

Normative reference: SPEC.md section 5.5. UTF-8 without BOM, LF endings,
RFC 4180 quoting, header row exact, rows sorted by `id` in byte order.

The sort is not cosmetic: it is what lets two people adding problems on
different branches produce diffs that git merges by line.
"""

from __future__ import annotations

import csv
import io
import os
from collections.abc import Iterable, Sequence

from .schema import LIST_SEPARATOR, PROBLEM_COLUMNS, PROGRESS_COLUMNS


class CsvFormatError(Exception):
    """Raised when a file cannot be parsed as the expected table at all."""


def split_list(value: str) -> tuple[str, ...]:
    """Pipe-delimited field to tuple. Empty string is the empty list."""
    if not value:
        return ()
    return tuple(part for part in value.split(LIST_SEPARATOR))


def join_list(values: Iterable[str]) -> str:
    return LIST_SEPARATOR.join(values)


def sort_key(row: dict) -> bytes:
    """Byte-order sort on `id`, per SPEC.md 5.5."""
    return row.get("id", "").encode("utf-8")


def _read(
    path: str, columns: Sequence[str], label: str
) -> tuple[list[str], list[tuple[int, list[str]]], Sequence[str], str]:
    if not os.path.exists(path):
        raise CsvFormatError(f"{path} does not exist")
    with open(path, encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise CsvFormatError(f"{path} is empty; expected a header row") from exc
        rows = []
        for lineno, fields in enumerate(reader, start=2):
            if not fields:
                continue
            rows.append((lineno, fields))
    return header, rows, columns, label


def read_table(
    path: str, columns: Sequence[str]
) -> tuple[list[str], list[dict], list[tuple[int, str, str]]]:
    """Rows as dicts, plus the raw header and any structural complaints.

    Returns (header, rows, findings). Rows are dicts keyed by the canonical
    column names; a row with the wrong field count is still returned, padded,
    so downstream rules can report on it rather than crashing.
    """
    header, raw_rows, columns, _ = _read(path, columns, path)
    findings = []
    if tuple(header) != tuple(columns):
        findings.append(
            (
                1,
                path,
                "header does not match the canonical column list; expected {}".format(
                    ", ".join(columns)
                ),
            )
        )
    rows = []
    width = len(columns)
    for lineno, fields in raw_rows:
        if len(fields) != width:
            findings.append(
                (
                    2,
                    f"{path}:{lineno}",
                    f"row has {len(fields)} fields, expected {width}",
                )
            )
        padded = list(fields[:width]) + [""] * max(0, width - len(fields))
        row = dict(zip(columns, padded, strict=True))
        row["_lineno"] = lineno
        rows.append(row)
    return header, rows, findings


def read_problems(path: str) -> tuple[list[str], list[dict], list[tuple[int, str, str]]]:
    return read_table(path, PROBLEM_COLUMNS)


def read_progress(path: str) -> tuple[list[str], list[dict], list[tuple[int, str, str]]]:
    return read_table(path, PROGRESS_COLUMNS)


def is_sorted(rows: Sequence[dict]) -> bool:
    keys = [sort_key(r) for r in rows]
    return keys == sorted(keys)


def render(rows: Sequence[dict], columns: Sequence[str]) -> str:
    """Rows to canonical CSV text: exact header, sorted, LF endings."""
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(columns)
    for row in sorted(rows, key=sort_key):
        writer.writerow([row.get(column, "") or "" for column in columns])
    return buffer.getvalue()


def write_table(path: str, rows: Sequence[dict], columns: Sequence[str]) -> str:
    text = render(rows, columns)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    return text


def write_problems(path: str, rows: Sequence[dict]) -> str:
    return write_table(path, rows, PROBLEM_COLUMNS)


def write_progress(path: str, rows: Sequence[dict]) -> str:
    return write_table(path, rows, PROGRESS_COLUMNS)


def blank_problem(**overrides: str) -> dict:
    row = {column: "" for column in PROBLEM_COLUMNS}
    row.update(overrides)
    return row


def blank_progress(**overrides: str) -> dict:
    row = {column: "" for column in PROGRESS_COLUMNS}
    row.update(overrides)
    return row
