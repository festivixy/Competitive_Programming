"""Querying the index.

Normative reference: SPEC.md 10.3.

Deviation: SPEC.md 13 names an in-memory SQLite table as the intended
implementation. Filtering in Python instead, because both the tag and the
prerequisite filters work over pipe-delimited list fields and a tree closure,
neither of which SQL expresses without either exploding the rows or
round-tripping through Python anyway.
"""

from __future__ import annotations

import random
from collections.abc import Sequence
from typing import TYPE_CHECKING

from . import csvio
from .schema import SOLVED_STATUSES

if TYPE_CHECKING:
    from .taxonomy import Taxonomy


class QueryError(Exception):
    """Raised for a malformed filter, such as an unparseable range."""


def parse_range(text: str | None, low: int, high: int) -> tuple[int, int] | None:
    """`4`, `4-6`, `-6` and `4-` all parse. Returns an inclusive (lo, hi)."""
    if text is None:
        return None
    text = text.strip()
    if not text:
        return None
    if "-" not in text:
        try:
            value = int(text)
        except ValueError as exc:
            raise QueryError(f"{text!r} is not a number or a range") from exc
        return (value, value)
    left, _, right = text.partition("-")
    try:
        lo = int(left) if left.strip() else low
        hi = int(right) if right.strip() else high
    except ValueError as exc:
        raise QueryError(f"{text!r} is not a valid range") from exc
    if lo > hi:
        raise QueryError(f"range {text!r} is inverted")
    return (lo, hi)


class Query:
    """A filter set, applied against the two tables."""

    def __init__(self, taxonomy: Taxonomy) -> None:
        self.taxonomy = taxonomy
        self.tag = None
        self.tag_exact = None
        self.primary = None
        self.difficulty = None
        self.quality = None
        self.min_quality = None
        self.origin = None
        self.format = None
        self.year = None
        self.status = None
        self.canonical_only = False
        self.missing_prereqs = None  # None, True or False
        self.sort = "difficulty"
        self.limit = None
        self.seed = None
        self._target_source: str | None = None

    # -- tag matching ---------------------------------------------------------
    def _tag_targets(self) -> set[str] | None:
        """The set of leaf tags a `--tag` filter accepts, per SPEC.md 10.3.

        Also records which filter produced the set, so matching cannot use one
        filter's targets under another filter's rule.
        """
        self._target_source = None
        if self.tag:
            if self.tag not in self.taxonomy:
                raise QueryError(f"unknown tag {self.tag}")
            self._target_source = "tag"
            return set(self.taxonomy.descendants(self.tag))
        if self.tag_exact:
            if self.tag_exact not in self.taxonomy:
                raise QueryError(f"unknown tag {self.tag_exact}")
            self._target_source = "tag_exact"
            return {self.tag_exact}
        if self.primary:
            if self.primary not in self.taxonomy:
                raise QueryError(f"unknown tag {self.primary}")
            self._target_source = "primary"
            return set(self.taxonomy.descendants(self.primary))
        return None

    def _row_matches_tags(self, row: dict, targets: set[str] | None) -> bool:
        if targets is None:
            return True
        if self._target_source == "primary":
            return row["primary_tag"] in targets
        return bool(targets & set(csvio.split_list(row["tags"])))

    # -- prerequisite readiness ----------------------------------------------
    def _demonstrated(
        self, progress_by_id: dict[str, dict], problems_by_id: dict[str, dict]
    ) -> set[str]:
        """Leaf tags you have solved at least one problem for."""
        done = set()
        for problem_id, progress in progress_by_id.items():
            if progress.get("status") not in SOLVED_STATUSES:
                continue
            problem = problems_by_id.get(problem_id)
            if problem:
                done.update(csvio.split_list(problem["tags"]))
        return done

    def _unmet(self, row: dict, demonstrated: set[str]) -> set[str]:
        needed = self.taxonomy.transitive_prerequisites(row["primary_tag"])
        return {tag for tag in needed if tag not in demonstrated}

    # -- execution ------------------------------------------------------------
    def run(self, problem_rows: Sequence[dict], progress_rows: Sequence[dict] = ()) -> list[dict]:
        targets = self._tag_targets()
        progress_by_id = {r["id"]: r for r in progress_rows}
        problems_by_id = {r["id"]: r for r in problem_rows}
        demonstrated = (
            self._demonstrated(progress_by_id, problems_by_id)
            if self.missing_prereqs is not None
            else set()
        )

        results = []
        for row in problem_rows:
            if not self._row_matches_tags(row, targets):
                continue
            if self.origin and row["origin"] not in self.origin:
                continue
            if self.format and row["format"] not in self.format:
                continue
            if self.canonical_only and row["canonical"] != "true":
                continue
            if not _in_range(row["difficulty"], self.difficulty):
                continue
            if not _in_range(row["year"], self.year):
                continue
            if self.min_quality is not None:
                quality = _as_int(row["quality"])
                if quality is None or quality < self.min_quality:
                    continue
            if not _in_range(row["quality"], self.quality):
                continue
            if self.status:
                current = progress_by_id.get(row["id"], {}).get("status") or "untouched"
                if current not in self.status:
                    continue
            if self.missing_prereqs is not None:
                unmet = self._unmet(row, demonstrated)
                if self.missing_prereqs != bool(unmet):
                    continue
                row = dict(row, _unmet="|".join(sorted(unmet)))
            results.append(row)

        results = self._sort(results)
        if self.limit:
            results = results[: self.limit]
        return results

    def _sort(self, rows: Sequence[dict]) -> list[dict]:
        if self.sort == "random":
            shuffled = list(rows)
            random.Random(self.seed).shuffle(shuffled)
            return shuffled
        if self.sort == "quality":
            return sorted(rows, key=lambda r: (-(_as_int(r["quality"]) or 0), r["id"]))
        if self.sort == "year":
            return sorted(rows, key=lambda r: (_as_int(r["year"]) or 0, r["id"]))
        if self.sort == "id":
            return sorted(rows, key=csvio.sort_key)
        return sorted(rows, key=lambda r: (_as_int(r["difficulty"]) or 0, r["id"]))


def _as_int(value: str | None) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _in_range(value: str, bounds: tuple[int, int] | None) -> bool:
    if bounds is None:
        return True
    number = _as_int(value)
    if number is None:
        return False
    return bounds[0] <= number <= bounds[1]
