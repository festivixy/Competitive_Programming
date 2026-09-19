"""The validation rules.

Normative reference: SPEC.md section 9. Rule numbers here are the spec's own,
so a CI failure cites a clause you can look up.

Two rules are additions, both documented in SPEC.md section 9 under
"Additions":
  25  a required field is empty                       (fatal)
  26  an id's leading segment matches no known origin (warning)

One spec rule cannot run in CI:
  10  progress.csv references an unknown id
`progress.csv` is gitignored, so this rule is local-only. It is skipped, with
a note, when the file is absent.
"""

from __future__ import annotations

import datetime
import os
from collections import Counter
from collections.abc import Iterable, Sequence
from typing import TYPE_CHECKING

from . import csvio
from .schema import (
    DATE_RE,
    DIFFICULTY_BASES,
    FAILURE_MODES,
    FORMATS,
    FREE_TAG_PROMOTION_THRESHOLD,
    HOSTS,
    KNOWN_ID_PREFIXES,
    MIN_YEAR,
    ORIGINS,
    PROBLEM_COLUMNS,
    PROGRESS_COLUMNS,
    REQUIRED_PROBLEM_COLUMNS,
    SLUG_RE,
    STALE_VERIFIED_DAYS,
    STATUSES,
    THIN_TAG_THRESHOLD,
)

if TYPE_CHECKING:
    from .cli import Paths
    from .taxonomy import Taxonomy

FATAL_RULES = frozenset(range(1, 21)) | {25}
WARNING_RULES = frozenset({21, 22, 23, 24, 26})


class Finding:
    """One rule violation, tied to a spec clause and a location."""

    __slots__ = ("rule", "location", "message", "fatal")

    def __init__(self, rule: int, location: str, message: str) -> None:
        self.rule = rule
        self.location = location
        self.message = message
        self.fatal = rule in FATAL_RULES

    @property
    def level(self) -> str:
        return "error" if self.fatal else "warning"

    def __str__(self) -> str:
        return f"{self.level.upper()}: [rule {self.rule:>2}] {self.location}: {self.message}"

    def __repr__(self) -> str:
        return f"Finding({self.rule}, {self.location!r})"


class Report:
    def __init__(self, findings: Iterable[Finding], skipped: Iterable[str] = ()) -> None:
        self.findings = list(findings)
        self.skipped = list(skipped)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.fatal]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if not f.fatal]

    @property
    def ok(self) -> bool:
        return not self.errors

    def rules_hit(self) -> list[int]:
        return sorted({f.rule for f in self.findings})

    def exit_code(self, strict: bool = False) -> int:
        if self.errors:
            return 1
        if strict and self.warnings:
            return 1
        return 0


def _parse_date(value: str) -> datetime.date | None:
    if not value or not DATE_RE.match(value):
        return None
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        return None


def _parse_int(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _edit_distance_within(a: str, b: str, limit: int) -> bool:
    """True when Levenshtein(a, b) <= limit. Short-circuits on length gap."""
    if abs(len(a) - len(b)) > limit:
        return False
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        current = [i]
        for j, cb in enumerate(b, start=1):
            current.append(
                min(
                    previous[j] + 1,
                    current[j - 1] + 1,
                    previous[j - 1] + (ca != cb),
                )
            )
        if min(current) > limit:
            return False
        previous = current
    return previous[-1] <= limit


# --- structural, SPEC.md 9 rules 1-5 ----------------------------------------
def check_structure(
    path: str,
    rows: Sequence[dict],
    header_findings: Sequence[tuple[int, str, str]],
    columns: Sequence[str],
) -> list[Finding]:
    findings = [Finding(rule, loc, msg) for rule, loc, msg in header_findings]
    if not csvio.is_sorted(rows):
        findings.append(
            Finding(3, path, "rows are not sorted by id ascending in byte order; run `cpidx fmt`")
        )
    counts = Counter(row["id"] for row in rows)
    for problem_id, count in sorted(counts.items()):
        if count > 1:
            findings.append(Finding(4, path, f"duplicate id {problem_id!r} appears {count} times"))
    for row in rows:
        where = "{}:{}".format(path, row["_lineno"])
        if not SLUG_RE.match(row["id"]):
            findings.append(
                Finding(5, where, "id {!r} does not match the slug regex".format(row["id"]))
            )
    return findings


# --- domain, SPEC.md 9 rules 11-16, plus additions 25 and 26 ----------------
def check_domain(
    path: str, rows: Sequence[dict], today: datetime.date | None = None
) -> list[Finding]:
    today = today or datetime.date.today()
    findings = []
    for row in rows:
        where = "{}:{}".format(path, row["_lineno"])

        for column in PROBLEM_COLUMNS:
            if column in REQUIRED_PROBLEM_COLUMNS and not row[column].strip():
                findings.append(Finding(25, where, f"required field {column!r} is empty"))

        if row["origin"] and row["origin"] not in ORIGINS:
            findings.append(
                Finding(11, where, "origin {!r} is not in the enum".format(row["origin"]))
            )
        hosts = csvio.split_list(row["hosts"])
        for host in hosts:
            if host not in HOSTS:
                findings.append(Finding(11, where, f"host {host!r} is not in the enum"))

        if row["format"] and row["format"] not in FORMATS:
            findings.append(
                Finding(12, where, "format {!r} is not in the enum".format(row["format"]))
            )

        difficulty = _parse_int(row["difficulty"])
        if row["difficulty"] and (difficulty is None or not 1 <= difficulty <= 10):
            findings.append(
                Finding(13, where, "difficulty {!r} is outside 1-10".format(row["difficulty"]))
            )
        quality = _parse_int(row["quality"])
        if row["quality"] and (quality is None or not 1 <= quality <= 5):
            findings.append(
                Finding(13, where, "quality {!r} is outside 1-5".format(row["quality"]))
            )

        if row["difficulty_basis"] and row["difficulty_basis"] not in DIFFICULTY_BASES:
            findings.append(
                Finding(
                    12,
                    where,
                    "difficulty_basis {!r} is not in the enum".format(row["difficulty_basis"]),
                )
            )

        year = _parse_int(row["year"])
        if row["year"] and (year is None or not MIN_YEAR <= year <= today.year):
            findings.append(
                Finding(
                    14,
                    where,
                    "year {!r} is outside {}-{}".format(row["year"], MIN_YEAR, today.year),
                )
            )

        added = _parse_date(row["added"])
        verified = _parse_date(row["verified"])
        if row["added"] and added is None:
            findings.append(
                Finding(15, where, "added {!r} is not an ISO date".format(row["added"]))
            )
        if row["verified"] and verified is None:
            findings.append(
                Finding(15, where, "verified {!r} is not an ISO date".format(row["verified"]))
            )
        if added and verified and verified < added:
            findings.append(
                Finding(15, where, f"verified {verified} is earlier than added {added}")
            )
        if verified and (today - verified).days > STALE_VERIFIED_DAYS:
            findings.append(Finding(21, where, f"verified {verified} is more than a year old"))

        mirrors = csvio.split_list(row["mirror_urls"])
        # Deviation from SPEC.md 9 rule 16: mirror_urls stays genuinely
        # optional, matching its "Required: no" in the section 5 table. The
        # length check applies only once the field is non-empty.
        if mirrors and len(mirrors) != max(0, len(hosts) - 1):
            findings.append(
                Finding(
                    16,
                    where,
                    f"mirror_urls has {len(mirrors)} entries, expected "
                    f"{max(0, len(hosts) - 1)} for {len(hosts)} hosts",
                )
            )

        if row["canonical"] and row["canonical"] not in ("true", "false"):
            findings.append(
                Finding(12, where, "canonical {!r} must be true or false".format(row["canonical"]))
            )

        prefix = row["id"].split("-", 1)[0]
        if row["id"] and prefix not in KNOWN_ID_PREFIXES:
            findings.append(Finding(26, where, f"id prefix {prefix!r} matches no known origin"))
    return findings


# --- referential, SPEC.md 9 rules 6-9 ---------------------------------------
def check_tags(path: str, rows: Sequence[dict], taxonomy: Taxonomy) -> list[Finding]:
    findings = []
    for row in rows:
        where = "{}:{}".format(path, row["_lineno"])
        tags = csvio.split_list(row["tags"])
        primary = row["primary_tag"]

        for tag in tags:
            error = taxonomy.resolution_error(tag)
            if error:
                findings.append(Finding(error[0], where, error[1]))
        if primary:
            error = taxonomy.resolution_error(primary)
            if error:
                findings.append(Finding(error[0], where, "primary_tag: " + error[1]))
            if primary not in tags:
                findings.append(Finding(9, where, f"primary_tag {primary} is not listed in tags"))
    return findings


# --- warnings, SPEC.md 9 rules 22-24 ----------------------------------------
def check_curation(path: str, rows: Sequence[dict], taxonomy: Taxonomy) -> list[Finding]:
    findings = []
    free_counts = Counter()
    tag_counts = Counter()
    canonical_tags = set()
    for row in rows:
        for free in csvio.split_list(row["free_tags"]):
            free_counts[free] += 1
        for tag in csvio.split_list(row["tags"]):
            tag_counts[tag] += 1
        if row["canonical"] == "true" and row["primary_tag"]:
            canonical_tags.add(row["primary_tag"])

    for free, count in sorted(free_counts.items()):
        if count >= FREE_TAG_PROMOTION_THRESHOLD:
            findings.append(
                Finding(
                    22,
                    path,
                    f"free tag {free!r} is on {count} problems; review it for promotion",
                )
            )

    aliases = taxonomy.alias_index()
    for free in sorted(free_counts):
        if free in aliases:
            findings.append(
                Finding(
                    24,
                    path,
                    f"free tag {free!r} is an alias of canonical tag {aliases[free]}",
                )
            )
            continue
        for alias, target in sorted(aliases.items()):
            if _edit_distance_within(free, alias, 2):
                findings.append(
                    Finding(
                        24,
                        path,
                        f"free tag {free!r} is within edit distance 2 of "
                        f"alias {alias!r} ({target})",
                    )
                )
                break

    for tag in taxonomy.leaves():
        count = tag_counts.get(tag, 0)
        if 0 < count < THIN_TAG_THRESHOLD and tag not in canonical_tags:
            findings.append(
                Finding(
                    23,
                    path,
                    f"tag {tag} has only {count} problem(s) and no canonical entry",
                )
            )
    return findings


# --- progress, SPEC.md 9 rule 10 (local only) -------------------------------
def check_progress(path: str, rows: Sequence[dict], problem_ids: set[str]) -> list[Finding]:
    findings = []
    for row in rows:
        where = "{}:{}".format(path, row["_lineno"])
        if row["id"] and row["id"] not in problem_ids:
            findings.append(
                Finding(10, where, "progress references unknown problem id {!r}".format(row["id"]))
            )
        if row["status"] and row["status"] not in STATUSES:
            findings.append(
                Finding(12, where, "status {!r} is not in the enum".format(row["status"]))
            )
        if row["failure_mode"] and row["failure_mode"] not in FAILURE_MODES:
            findings.append(
                Finding(
                    12, where, "failure_mode {!r} is not in the enum".format(row["failure_mode"])
                )
            )
        confidence = _parse_int(row["confidence"])
        if row["confidence"] and (confidence is None or not 1 <= confidence <= 5):
            findings.append(
                Finding(13, where, "confidence {!r} is outside 1-5".format(row["confidence"]))
            )
        for column in ("attempts", "minutes"):
            value = _parse_int(row[column])
            if row[column] and (value is None or value < 0):
                findings.append(
                    Finding(
                        13,
                        where,
                        f"{column} {row[column]!r} is not a non-negative integer",
                    )
                )
    return findings


# --- entry point -------------------------------------------------------------
def run(paths: Paths, today: datetime.date | None = None) -> Report:
    """Validate the whole index. `paths` is a Paths object from cli."""
    from .taxonomy import Taxonomy, TaxonomyError

    findings = []
    skipped = []

    try:
        taxonomy = Taxonomy.load(paths.taxonomy)
    except TaxonomyError as exc:
        return Report([Finding(6, paths.taxonomy, str(exc))])

    for rule, location, message in taxonomy.structural_findings():
        findings.append(Finding(rule, f"{paths.taxonomy}:{location}", message))

    header, rows, header_findings = csvio.read_problems(paths.problems)
    findings += check_structure(paths.problems, rows, header_findings, PROBLEM_COLUMNS)
    findings += check_domain(paths.problems, rows, today=today)
    findings += check_tags(paths.problems, rows, taxonomy)
    findings += check_curation(paths.problems, rows, taxonomy)

    if os.path.exists(paths.progress):
        _, progress_rows, progress_header = csvio.read_table(paths.progress, PROGRESS_COLUMNS)
        findings += [Finding(r, loc, msg) for r, loc, msg in progress_header]
        findings += check_progress(paths.progress, progress_rows, {row["id"] for row in rows})
    else:
        skipped.append(
            f"rule 10 (progress references): {paths.progress} is absent, which is expected in CI "
            "since it is gitignored"
        )

    findings.sort(key=lambda f: (not f.fatal, f.rule, f.location))
    return Report(findings, skipped)
