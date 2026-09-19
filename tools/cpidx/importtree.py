"""Deriving candidate index rows from an existing solutions tree.

SPEC.md 1.2 makes auto-classification a non-goal: tooling may suggest, never
decide. That applies to identity as much as to tagging, because this tree is
not consistently named. `CCC/S/21/21s4.cpp` and `CCC/S/21/dailycommute.cpp`
are the same problem under two conventions, and nothing in the path says so.

So this module writes to a staging file, never to problems.csv. Each candidate
carries the paths it came from, a confidence, and a list of what is still
missing. Promotion into the index is a curatorial act performed by
`cpidx import-tree --promote` after review.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterator, Sequence

from . import csvio
from .schema import CCC_TIER, CCO_TIER, IOI_TIER, PROBLEM_COLUMNS, USACO_TIER

SOURCE_EXTENSIONS = (".cpp", ".cc", ".java", ".py")

# Trailing " 2", " 3" are filesystem copies, not distinct solutions.
COPY_SUFFIX_RE = re.compile(r"\s+\d+$")

STAGING_COLUMNS = PROBLEM_COLUMNS + ("_confidence", "_needs", "_source_paths")

MONTHS = {
    "jan": ("January", "jan"),
    "january": ("January", "jan"),
    "feb": ("February", "feb"),
    "february": ("February", "feb"),
    "dec": ("December", "dec"),
    "december": ("December", "dec"),
    "open": ("US Open", "open"),
    "uso": ("US Open", "open"),
    "mar": ("March", "mar"),
    "march": ("March", "mar"),
}

DIVISIONS = {"B": "Bronze", "S": "Silver", "G": "Gold", "P": "Platinum"}

SEED_DIFFICULTY = {
    "ccc": CCC_TIER,
    "cco": CCO_TIER,
    "usaco": USACO_TIER,
    "ioi": IOI_TIER,
}


def _full_year(two_digit: str) -> int:
    value = int(two_digit)
    # The tree spans 1990s contests to the present; 90-99 are 19xx.
    return 1900 + value if value >= 90 else 2000 + value


def _clean_stem(path: str) -> str:
    stem = os.path.splitext(os.path.basename(path))[0]
    return COPY_SUFFIX_RE.sub("", stem).strip()


def _titleize(slug: str) -> str:
    spaced = re.sub(r"[_\-]+", " ", slug)
    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", spaced)
    return spaced.strip().title()


class Candidate:
    def __init__(self, problem_id: str, confidence: str, **fields: str) -> None:
        self.id = problem_id
        self.confidence = confidence
        self.fields = fields
        self.sources = []
        self.needs = set()

    def to_row(self) -> dict:
        row = csvio.blank_problem(id=self.id, **self.fields)
        row["_confidence"] = self.confidence
        row["_needs"] = "|".join(sorted(self.needs))
        row["_source_paths"] = "|".join(sorted(self.sources))
        return row


def _seed(origin: str, key: str) -> str:
    return str(SEED_DIFFICULTY.get(origin, {}).get(key, "")) if key else ""


# --- per-origin path readers -------------------------------------------------
def _read_ccc(parts: Sequence[str], stem: str) -> Candidate | None:
    # CCC/<J|S>/<yy>/<file>  or  CCC/<yy>/<file>. Filenames appear as
    # `21s4`, `2010j1`, `R25s2`, `s1`, and as bare problem names.
    stream = None
    year = None
    for part in parts[1:]:
        if part in ("J", "S"):
            stream = part
        elif re.fullmatch(r"\d{2}", part):
            year = _full_year(part)
    number = None
    patterns = (
        (r"(\d{4})\s*([jsJS])(\d)", 4),
        (r"(?:^|\D)(\d{2})\s*([jsJS])(\d)", 2),
        (r"^[a-zA-Z]*([jsJS])(\d)$", 0),
    )
    for pattern, digits in patterns:
        match = re.search(pattern, stem)
        if not match:
            continue
        if digits == 4:
            year = int(match.group(1))
            stream, number = match.group(2).upper(), match.group(3)
        elif digits == 2:
            year = year or _full_year(match.group(1))
            stream, number = match.group(2).upper(), match.group(3)
        else:
            stream, number = match.group(1).upper(), match.group(2)
        break

    if year is None:
        return None
    if not (stream and number):
        # A named file such as `dailycommute.cpp`: the year is known from the
        # path but the position within the contest is not recoverable.
        slug = re.sub(r"[^a-z0-9]+", "", stem.lower())
        if not slug:
            return None
        candidate = Candidate(
            f"ccc-{year}-{slug}",
            "low",
            title=_titleize(stem),
            origin="ccc",
            contest="CCC {}{}".format(
                year, " Senior" if stream == "S" else " Junior" if stream == "J" else ""
            ),
            year=str(year),
            hosts="dmoj",
            format="standard",
            difficulty_basis="estimated",
        )
        candidate.needs.add("label")
        return candidate
    label = f"{stream}{number}"
    slug = f"ccc{year % 100:02d}{stream.lower()}{number}"
    return Candidate(
        f"ccc-{year}-{label.lower()}",
        "high",
        title=_titleize(stem) if not re.fullmatch(r"[Rr]?\d*[jsJS]\d", stem) else "",
        origin="ccc",
        contest="CCC {} {}".format(year, "Junior" if stream == "J" else "Senior"),
        year=str(year),
        label=label,
        hosts="dmoj",
        url=f"https://dmoj.ca/problem/{slug}",
        format="standard",
        difficulty=_seed("ccc", label),
        difficulty_basis="estimated",
    )


def _read_cco(parts: Sequence[str], stem: str) -> Candidate | None:
    year = next((_full_year(p) for p in parts[1:] if re.fullmatch(r"\d{2}", p)), None)
    if year is None:
        return None
    return Candidate(
        "cco-{}-{}".format(year, re.sub(r"[^a-z0-9]+", "", stem.lower()) or "unknown"),
        "medium",
        title=_titleize(stem),
        origin="cco",
        contest=f"CCO {year}",
        year=str(year),
        hosts="dmoj",
        format="standard",
        difficulty_basis="estimated",
    )


def _read_ioi(parts: Sequence[str], stem: str) -> Candidate | None:
    match = re.search(r"(?:ioi)?(\d{2})p(\d)", stem, re.I)
    year = next((_full_year(p) for p in parts[1:] if re.fullmatch(r"\d{2}", p)), None)
    number = None
    if match:
        if year is None:
            year = _full_year(match.group(1))
        number = match.group(2)
    if year is None:
        return None
    label = f"P{number}" if number else ""
    suffix = label.lower() if label else re.sub(r"[^a-z0-9]+", "", stem.lower())
    return Candidate(
        "ioi-{}-{}".format(year, suffix or "unknown"),
        "high" if number else "medium",
        title="" if number else _titleize(stem),
        origin="ioi",
        contest=f"IOI {year}",
        year=str(year),
        label=label,
        hosts="oj.uz",
        format="subtask",
        difficulty=_seed("ioi", number or ""),
        difficulty_basis="estimated",
    )


def _read_usaco(parts: Sequence[str], stem: str) -> Candidate | None:
    year = next((_full_year(p) for p in parts[1:] if re.fullmatch(r"\d{2}", p)), None)
    month_key = next((p.lower() for p in parts[1:] if p.lower() in MONTHS), None)
    division = None
    name = stem
    match = re.match(r"^([BSGP])\d*[_\-](.+)$", stem)
    if match:
        division = DIVISIONS[match.group(1)]
        name = match.group(2)
    if year is None:
        return None
    month_name, month_slug = MONTHS.get(month_key, ("", ""))
    contest = " ".join(x for x in ["USACO", str(year), month_name, division] if x)
    id_parts = ["usaco", str(year)]
    if month_slug:
        id_parts.append(month_slug)
    if division:
        id_parts.append(division.lower().replace(" ", ""))
    id_parts.append(re.sub(r"[^a-z0-9]+", "", name.lower()) or "unknown")
    return Candidate(
        "-".join(id_parts),
        "medium",
        title=_titleize(name),
        origin="usaco",
        contest=contest,
        year=str(year),
        label=division or "",
        hosts="usaco-official",
        format="standard",
        difficulty=_seed("usaco", division or ""),
        difficulty_basis="estimated",
        difficulty_native=division or "",
    )


def _read_codeforces(parts: Sequence[str], stem: str) -> Candidate | None:
    contest = next((p for p in parts[1:] if re.fullmatch(r"\d{3,6}", p)), None)
    if contest is None:
        return None
    match = re.match(r"^([A-Ha-h])\d*[_\-](.+)$", stem)
    index = match.group(1).upper() if match else ""
    name = match.group(2) if match else stem
    suffix = index.lower() if index else re.sub(r"[^a-z0-9]+", "", stem.lower())
    url = (
        f"https://codeforces.com/contest/{contest}/problem/{index}"
        if index
        else f"https://codeforces.com/contest/{contest}"
    )
    return Candidate(
        "cf-{}-{}".format(contest, suffix or "unknown"),
        "high" if index else "low",
        title=_titleize(name),
        origin="codeforces",
        contest=f"Codeforces Round, contest {contest}",
        label=index,
        hosts="codeforces",
        url=url,
        format="standard",
        difficulty_basis="estimated",
    )


def _read_cses(parts: Sequence[str], stem: str) -> Candidate | None:
    section = parts[1] if len(parts) > 1 else ""
    slug = re.sub(r"[^a-z0-9]+", "", stem.lower())
    if not slug:
        return None
    return Candidate(
        f"cses-{slug}",
        "medium",
        title=_titleize(stem),
        origin="cses",
        contest="CSES Problem Set{}".format(" - " + _titleize(section) if section else ""),
        hosts="cses",
        format="standard",
        difficulty_basis="estimated",
    )


def _read_simple(
    origin: str, parts: Sequence[str], stem: str, contest_prefix: str
) -> Candidate | None:
    year = next((_full_year(p) for p in parts[1:] if re.fullmatch(r"\d{2}", p)), None)
    slug = re.sub(r"[^a-z0-9]+", "", stem.lower())
    if not slug:
        return None
    pieces = [origin] + ([str(year)] if year else []) + [slug]
    return Candidate(
        "-".join(pieces),
        "low",
        title=_titleize(stem),
        origin=origin,
        contest=f"{contest_prefix} {year}" if year else contest_prefix,
        year=str(year) if year else "",
        format="standard",
        difficulty_basis="estimated",
    )


# `Trivial Competitions/<ORG>/<yy>/<file>` collects the smaller contests.
TRIVIAL_ORIGINS = {
    "CEOI": ("ceoi", "CEOI"),
    "DMOPC": ("dmopc", "DMOPC"),
    "BSSPC": ("bsspc", "BSSPC"),
    "BTS": ("dmoj", "BTS"),
    "April Fools": ("dmoj", "April Fools"),
}


def _read_trivial(parts: Sequence[str], stem: str) -> Candidate | None:
    if len(parts) < 2:
        return None
    origin, prefix = TRIVIAL_ORIGINS.get(parts[1], ("dmoj", parts[1]))
    candidate = _read_simple(origin, parts[1:], stem, prefix)
    if candidate is not None and origin == "ceoi":
        candidate.fields["format"] = "subtask"
    return candidate


READERS = {
    "Trivial Competitions": _read_trivial,
    "CCC": _read_ccc,
    "CCO": _read_cco,
    "IOI": _read_ioi,
    "USACO": _read_usaco,
    "CodeForces": _read_codeforces,
    "CSES": _read_cses,
    "CSES V2": _read_cses,
}

SIMPLE = {
    "COCI": ("coci", "COCI"),
    "BOI": ("boi", "BOI"),
    "NOI": ("noi", "NOI"),
    "ICPC": ("icpc", "ICPC"),
}

# Reference implementations and scratch work, not contest problems.
SKIP_DIRS = frozenset({"Algorithms", "bits", "website", "Notes", "Practice", "build", "tools"})


def walk(root: str) -> Iterator[tuple[list[str], str]]:
    """Every candidate source file under root, as path-part lists."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d
            for d in dirnames
            if not d.startswith(".") and d not in SKIP_DIRS and d != "cmake-build-debug"
        ]
        rel = os.path.relpath(dirpath, root)
        if rel == ".":
            continue
        parts = rel.replace("\\", "/").split("/")
        if parts[0] in SKIP_DIRS:
            continue
        for filename in sorted(filenames):
            if filename.lower().endswith(SOURCE_EXTENSIONS):
                yield parts, filename


def derive(root: str) -> tuple[dict[str, Candidate], list[str]]:
    """Candidate rows, merged by derived id. Returns (candidates, unmatched)."""
    merged = {}
    unmatched = []
    for parts, filename in walk(root):
        top = parts[0]
        stem = _clean_stem(filename)
        relpath = "/".join(parts + [filename])
        if top in READERS:
            candidate = READERS[top](parts, stem)
        elif top in SIMPLE:
            origin, prefix = SIMPLE[top]
            candidate = _read_simple(origin, parts, stem, prefix)
        else:
            candidate = None
        if candidate is None:
            unmatched.append(relpath)
            continue
        existing = merged.get(candidate.id)
        if existing is None:
            merged[candidate.id] = candidate
            existing = candidate
        elif not existing.fields.get("title") and candidate.fields.get("title"):
            existing.fields["title"] = candidate.fields["title"]
        existing.sources.append(relpath)

    for candidate in merged.values():
        for column in ("title", "hosts", "url", "difficulty", "primary_tag", "tags"):
            if not candidate.fields.get(column):
                candidate.needs.add(column)
        if len(candidate.sources) > 1:
            candidate.needs.add("dedupe")
    return merged, unmatched


def stage(root: str, out_path: str, today: str) -> tuple[list[dict], list[str]]:
    """Write the staging file. Returns (rows, unmatched)."""
    merged, unmatched = derive(root)
    rows = []
    for candidate in merged.values():
        candidate.fields.setdefault("added", today)
        candidate.fields.setdefault("verified", today)
        rows.append(candidate.to_row())
    rows.sort(key=csvio.sort_key)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as handle:
        handle.write(csvio.render(rows, STAGING_COLUMNS))
    return rows, unmatched
