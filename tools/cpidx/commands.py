"""Commands that are neither validation nor export.

Normative reference: SPEC.md 10.1, 10.2, 7.6.
"""

from __future__ import annotations

import datetime
import re
import urllib.error
import urllib.request
from collections import Counter
from collections.abc import Iterable, Sequence

from . import csvio
from .schema import LIST_SEPARATOR, STALE_VERIFIED_DAYS
from .taxonomy import Taxonomy

Row = dict


# --- add: URL detection, SPEC.md 10.2 ---------------------------------------
class Detection:
    """What a URL alone can tell us. Everything classificatory stays blank."""

    def __init__(self, **fields: str) -> None:
        self.fields: dict[str, str] = {k: v for k, v in fields.items() if v}

    def __repr__(self) -> str:
        return f"Detection({self.fields!r})"


def _full_year(two_digit: str) -> int:
    value = int(two_digit)
    return 1900 + value if value >= 90 else 2000 + value


def detect(url: str) -> Detection:
    """Best-effort field detection from a URL. Never guesses a tag."""
    url = url.strip()

    match = re.search(r"dmoj\.ca/problem/ccc(\d{2})([js])(\d)", url, re.I)
    if match:
        year = _full_year(match.group(1))
        stream = match.group(2).upper()
        label = f"{stream}{match.group(3)}"
        return Detection(
            id=f"ccc-{year}-{label.lower()}",
            origin="ccc",
            year=str(year),
            label=label,
            contest="CCC {} {}".format(year, "Junior" if stream == "J" else "Senior"),
            hosts="dmoj",
            url=url,
            format="standard",
        )

    match = re.search(r"dmoj\.ca/problem/cco(\d{2})p(\d)", url, re.I)
    if match:
        year = _full_year(match.group(1))
        return Detection(
            id=f"cco-{year}-p{match.group(2)}",
            origin="cco",
            year=str(year),
            label=f"P{match.group(2)}",
            contest=f"CCO {year}",
            hosts="dmoj",
            url=url,
            format="standard",
        )

    match = re.search(r"dmoj\.ca/problem/([a-z0-9_]+)", url, re.I)
    if match:
        slug = re.sub(r"[^a-z0-9]+", "", match.group(1).lower())
        return Detection(id=f"dmoj-{slug}", origin="dmoj", hosts="dmoj", url=url, format="standard")

    match = re.search(
        r"codeforces\.com/(?:contest|problemset/problem)/(\d+)/(?:problem/)?([A-Z]\d?)", url, re.I
    )
    if match:
        contest, index = match.group(1), match.group(2).upper()
        return Detection(
            id=f"cf-{contest}-{index.lower()}",
            origin="codeforces",
            label=index,
            contest=f"Codeforces contest {contest}",
            hosts="codeforces",
            url=url,
            format="standard",
        )

    match = re.search(r"usaco\.org/index\.php\?page=viewproblem2&cpid=(\d+)", url, re.I)
    if match:
        return Detection(
            id=f"usaco-cpid{match.group(1)}",
            origin="usaco",
            hosts="usaco-official",
            url=url,
            format="standard",
        )

    match = re.search(r"oj\.uz/problem/view/([A-Za-z0-9_]+)", url)
    if match:
        slug = match.group(1)
        inner = re.match(r"(IOI|APIO|CEOI|JOI|BOI)(\d{2})_([A-Za-z0-9]+)", slug, re.I)
        if inner:
            origin = inner.group(1).lower()
            year = _full_year(inner.group(2))
            name = inner.group(3).lower()
            return Detection(
                id=f"{origin}-{year}-{name}",
                origin=origin if origin in ("ioi", "apio", "ceoi") else "ioi-practice",
                year=str(year),
                contest=f"{inner.group(1).upper()} {year}",
                hosts="oj.uz",
                url=url,
                format="subtask",
            )
        return Detection(
            id="ioi-practice-{}".format(re.sub(r"[^a-z0-9]+", "", slug.lower())),
            hosts="oj.uz",
            url=url,
            format="subtask",
        )

    match = re.search(r"cses\.fi/problemset/task/(\d+)", url)
    if match:
        return Detection(
            id=f"cses-{match.group(1)}",
            origin="cses",
            contest="CSES Problem Set",
            hosts="cses",
            url=url,
            format="standard",
        )

    return Detection(url=url)


def build_row(url: str, today: str, overrides: dict[str, str] | None = None) -> Row:
    """A new problems.csv row from a URL plus explicit overrides."""
    detection = detect(url)
    row = csvio.blank_problem(**detection.fields)
    row.setdefault("added", today)
    row["added"] = row["added"] or today
    row["verified"] = row["verified"] or today
    row["format"] = row["format"] or "standard"
    for key, value in (overrides or {}).items():
        row[key] = value
    if row.get("primary_tag") and not row.get("tags"):
        row["tags"] = row["primary_tag"]
    elif row.get("primary_tag"):
        tags = list(csvio.split_list(row["tags"]))
        if row["primary_tag"] not in tags:
            tags.append(row["primary_tag"])
        row["tags"] = LIST_SEPARATOR.join(tags)
    if row.get("difficulty") and not row.get("difficulty_basis"):
        row["difficulty_basis"] = "estimated"
    return row


def missing_required(row: Row) -> list[str]:
    from .schema import REQUIRED_PROBLEM_COLUMNS

    return sorted(c for c in REQUIRED_PROBLEM_COLUMNS if not str(row.get(c, "")).strip())


# --- stats, SPEC.md 10.1 -----------------------------------------------------
def stats(rows: Sequence[Row], taxonomy: Taxonomy, by: str = "tag") -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    if by == "tag":
        for row in rows:
            for tag in csvio.split_list(row.get("tags", "")):
                counter[tag] += 1
    elif by == "origin":
        for row in rows:
            counter[row.get("origin", "") or "(blank)"] += 1
    elif by == "difficulty":
        for row in rows:
            counter[row.get("difficulty", "") or "(blank)"] += 1
    elif by == "category":
        for row in rows:
            primary = row.get("primary_tag")
            if primary:
                counter[taxonomy.top_level_of(primary)] += 1
    else:
        raise ValueError(f"unknown grouping {by!r}")
    if by == "difficulty":
        # Tiers are stored as text, so sort them as numbers or "10" lands between
        # "1" and "2".
        return sorted(
            counter.items(),
            key=lambda kv: (kv[0] == "(blank)", int(kv[0]) if kv[0].isdigit() else 0),
        )
    return sorted(counter.items(), key=lambda kv: (-kv[1], kv[0]))


def coverage_gaps(rows: Sequence[Row], taxonomy: Taxonomy) -> list[str]:
    """Leaf tags with no problems at all. The reason the Coverage sheet exists."""
    used = {tag for row in rows for tag in csvio.split_list(row.get("tags", ""))}
    return [tag for tag in taxonomy.leaves() if tag not in used]


# --- linkcheck, SPEC.md 10.1 -------------------------------------------------
def stale_rows(
    rows: Sequence[Row], max_age: int = STALE_VERIFIED_DAYS, today: datetime.date | None = None
) -> list[tuple[Row, int]]:
    """Rows whose `verified` date is older than max_age days."""
    today = today or datetime.date.today()
    out = []
    for row in rows:
        try:
            verified = datetime.date.fromisoformat(row.get("verified", ""))
        except ValueError:
            out.append((row, -1))
            continue
        age = (today - verified).days
        if age > max_age:
            out.append((row, age))
    return out


def check_url(url: str, timeout: float = 10.0) -> tuple[str, str]:
    """Probe a URL. Returns (state, detail) where state is ok, dead or blocked.

    `blocked` is a third state on purpose. DMOJ and several other judges sit
    behind a bot filter that answers 403 to any scripted request, and most of
    this index lives on such hosts. Reporting those as dead would make
    linkcheck cry wolf on every run, which is how a link checker gets ignored.
    """
    if not url:
        return ("dead", "no url")

    def fetch(method: str) -> tuple[str, str]:
        request = urllib.request.Request(url, method=method)
        request.add_header("User-Agent", "cpidx-linkcheck/0.1")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return ("ok" if 200 <= response.status < 400 else "dead", str(response.status))

    try:
        return fetch("HEAD")
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 405, 429):  # bot filter, or HEAD not allowed
            try:
                return fetch("GET")
            except urllib.error.HTTPError as inner:
                if inner.code in (403, 429):
                    return ("blocked", f"HTTP {inner.code}")
                return ("dead", f"HTTP {inner.code}")
            except Exception as inner:  # noqa: BLE001 - network errors are data
                return ("blocked", str(inner))
        return ("dead", f"HTTP {exc.code}")
    except Exception as exc:  # noqa: BLE001 - network errors are data here
        return ("blocked", str(exc))


# --- migrate-tags, SPEC.md 7.6 ----------------------------------------------
def migration_map(taxonomy: Taxonomy) -> dict[str, str]:
    """Deprecated tag to its replacement, following chains to the end."""
    mapping = {}
    for tag, node in taxonomy.nodes.items():
        if not node.is_deprecated or not node.replaced_by:
            continue
        target = node.replaced_by
        seen = {tag}
        while target in taxonomy.nodes and taxonomy.get(target).is_deprecated:
            if target in seen:
                break
            seen.add(target)
            nxt = taxonomy.get(target).replaced_by
            if not nxt:
                break
            target = nxt
        mapping[tag] = target
    return mapping


def migrate_rows(rows: Iterable[Row], mapping: dict[str, str]) -> tuple[list[Row], list[str]]:
    """Rewrite deprecated tags. Returns (rows, human-readable changes)."""
    changes = []
    out = []
    for row in rows:
        new_row = dict(row)
        tags = list(csvio.split_list(row.get("tags", "")))
        rewritten = []
        for tag in tags:
            replacement = mapping.get(tag)
            if replacement:
                changes.append("{}: tags {} -> {}".format(row["id"], tag, replacement))
                rewritten.append(replacement)
            else:
                rewritten.append(tag)
        deduped = list(dict.fromkeys(rewritten))
        new_row["tags"] = LIST_SEPARATOR.join(deduped)
        primary = row.get("primary_tag", "")
        if primary in mapping:
            changes.append("{}: primary_tag {} -> {}".format(row["id"], primary, mapping[primary]))
            new_row["primary_tag"] = mapping[primary]
        out.append(new_row)
    return out, changes
