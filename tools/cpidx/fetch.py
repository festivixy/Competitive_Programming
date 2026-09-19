"""Fetching complete problem lists from the judges themselves.

Normative reference: SPEC.md 10.6.

This writes `catalogue.csv`, never `problems.csv`. Everything a judge publishes
about a problem — title, link, native difficulty, contest position — is fetched
here, but a catalogue row carries no taxonomy tag, because SPEC.md 1.2 reserves
classification for a person. A row moves into the curated index only once it
has been tagged.

Network access lives entirely in this module, so nothing else in the package
needs it and CI never touches it.
"""

from __future__ import annotations

import html
import json
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterator

from . import csvio
from .schema import CCC_TIER, CCO_TIER, USACO_TIER

USER_AGENT = "cpidx-fetch/0.1"
DMOJ_PAGES = 8
USACO_MONTHS = ("nov", "dec", "jan", "feb", "mar", "apr", "open")
USACO_YEARS = range(11, 27)

MONTH_NAME = {
    "nov": "November",
    "dec": "December",
    "jan": "January",
    "feb": "February",
    "mar": "March",
    "apr": "April",
    "open": "US Open",
}

CCC_CODE = re.compile(r"^ccc(\d{2})([js])(\d)$")
CCO_CODE = re.compile(r"^cco(\d{2})p(\d)$")

# The division heading carries an <img>, so markup is allowed inside the h2.
USACO_TOKEN = re.compile(
    r"<h2>.{0,300}?(Bronze|Silver|Gold|Platinum).{0,60}?</h2>"
    r"|<b>([^<]{2,80})</b>.{0,400}?cpid=(\d+)",
    re.S | re.I,
)


class FetchError(Exception):
    """A source could not be reached at all."""


def _get(url: str, timeout: float = 30.0) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")


def _full_year(two_digit: str) -> int:
    value = int(two_digit)
    return 1900 + value if value >= 90 else 2000 + value


# --- DMOJ: CCC and CCO -------------------------------------------------------
def dmoj_problems(pages: int = DMOJ_PAGES, pause: float = 0.4) -> list[dict]:
    """Every public DMOJ problem, from its JSON API."""
    out: list[dict] = []
    for page in range(1, pages + 1):
        try:
            payload = json.loads(_get(f"https://dmoj.ca/api/v2/problems?page={page}"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:  # ran past the last page
                break
            raise FetchError(f"DMOJ page {page}: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 - network failure is the message
            raise FetchError(f"DMOJ page {page}: {exc}") from exc
        data = payload["data"]
        out.extend(data["objects"])
        if not data.get("has_more"):
            break
        time.sleep(pause)
    return out


def ccc_rows(problems: list[dict], today: str) -> Iterator[dict]:
    for obj in problems:
        match = CCC_CODE.match(obj["code"])
        if not match:
            continue
        year = _full_year(match.group(1))
        stream = match.group(2).upper()
        label = f"{stream}{match.group(3)}"
        yield csvio.blank_problem(
            id=f"ccc-{year}-{label.lower()}",
            title=obj["name"].split(" - ", 1)[-1],
            origin="ccc",
            contest=f"CCC {year} {'Senior' if stream == 'S' else 'Junior'}",
            year=str(year),
            label=label,
            hosts="dmoj",
            url=f"https://dmoj.ca/problem/{obj['code']}",
            format="standard",
            difficulty=str(CCC_TIER.get(label, "")),
            difficulty_basis="estimated",
            difficulty_native=f"DMOJ {obj['points']:g}p",
            free_tags="|".join(str(t).lower().replace(" ", "-") for t in obj.get("types") or ()),
            added=today,
            verified=today,
        )


def cco_rows(problems: list[dict], today: str) -> Iterator[dict]:
    for obj in problems:
        match = CCO_CODE.match(obj["code"])
        if not match:
            continue
        year = _full_year(match.group(1))
        number = match.group(2)
        yield csvio.blank_problem(
            id=f"cco-{year}-p{number}",
            title=obj["name"].split(" - ", 1)[-1],
            origin="cco",
            contest=f"CCO {year}",
            year=str(year),
            label=f"P{number}",
            hosts="dmoj",
            url=f"https://dmoj.ca/problem/{obj['code']}",
            format="standard",
            difficulty=str(CCO_TIER.get(number, "")),
            difficulty_basis="estimated",
            difficulty_native=f"DMOJ {obj['points']:g}p",
            free_tags="|".join(str(t).lower().replace(" ", "-") for t in obj.get("types") or ()),
            added=today,
            verified=today,
        )


# --- USACO -------------------------------------------------------------------
def usaco_rows(today: str, pause: float = 0.12, log: Callable[[str], None] | None = None):
    """Every problem on a USACO contest results page."""
    seen: dict[str, dict] = {}
    for yy in USACO_YEARS:
        for month in USACO_MONTHS:
            page = f"{month}{yy:02d}results"
            try:
                body = _get(f"http://www.usaco.org/index.php?page={page}")
            except Exception:  # noqa: BLE001 - a missing contest page is normal
                continue
            if "cpid=" not in body:
                continue
            division = ""
            count = 0
            for match in USACO_TOKEN.finditer(body):
                if match.group(1):
                    division = match.group(1).capitalize()
                    continue
                cpid = match.group(3)
                title = html.unescape(match.group(2)).strip()
                year = 2000 + yy
                slug = "".join(c for c in title.lower() if c.isalnum())
                seen[cpid] = csvio.blank_problem(
                    id=f"usaco-{year}-{month}-{division.lower()}-{slug}",
                    title=title,
                    origin="usaco",
                    contest=f"USACO {year} {MONTH_NAME.get(month, month)} {division}".strip(),
                    year=str(year),
                    label=division,
                    hosts="usaco-official",
                    url=f"https://www.usaco.org/index.php?page=viewproblem2&cpid={cpid}",
                    format="standard",
                    difficulty=str(USACO_TIER.get(division, "")),
                    difficulty_basis="estimated",
                    difficulty_native=division,
                    added=today,
                    verified=today,
                )
                count += 1
            if count and log:
                log(f"  {page}: {count}")
            time.sleep(pause)
    return list(seen.values())


# --- assembly ----------------------------------------------------------------
SOURCES = ("ccc", "cco", "usaco")


def build(today: str, sources=SOURCES, log: Callable[[str], None] | None = None) -> list[dict]:
    rows: list[dict] = []
    if "ccc" in sources or "cco" in sources:
        if log:
            log("fetching DMOJ problem list...")
        dmoj = dmoj_problems()
        if log:
            log(f"  {len(dmoj)} DMOJ problems")
        if "ccc" in sources:
            rows += list(ccc_rows(dmoj, today))
        if "cco" in sources:
            rows += list(cco_rows(dmoj, today))
    if "usaco" in sources:
        if log:
            log("fetching USACO contest pages...")
        rows += usaco_rows(today, log=log)
    return rows


def merge(
    existing: list[dict], fetched: list[dict], index_ids: set[str]
) -> tuple[list[dict], int, int]:
    """Keep hand-edited catalogue rows; add new ones; drop anything now indexed.

    Returns (rows, added, refreshed).
    """
    by_id = {row["id"]: row for row in existing if row["id"] not in index_ids}
    added = refreshed = 0
    for row in fetched:
        if row["id"] in index_ids:
            continue
        current = by_id.get(row["id"])
        if current is None:
            by_id[row["id"]] = row
            added += 1
            continue
        # Refresh only what the judge owns; leave curatorial columns alone.
        for column in ("title", "url", "difficulty_native", "contest", "verified"):
            if row[column] and current[column] != row[column]:
                current[column] = row[column]
                refreshed += 1
        # Filling a blank is not overwriting a decision.
        if row["difficulty"] and not current["difficulty"]:
            current["difficulty"] = row["difficulty"]
            current["difficulty_basis"] = row["difficulty_basis"]
            refreshed += 1
    return sorted(by_id.values(), key=csvio.sort_key), added, refreshed
