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
from .schema import CCC_TIER, CCO_TIER, CSES_SECTION_TIER, OJUZ_TIER, USACO_TIER

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

CCC_CODE = re.compile(r"^ccc(\d{2})([js])(\d)([a-z]*)$")
CCC_QR = re.compile(r"^cccjqrp(\d+)$")
CCO_CODE = re.compile(r"^cco(\d{2})(?:l(\d))?p(\d)([a-z]*)$")
CCO_PREP = re.compile(r"^ccoprep(\d+)p(\d+)$")
CCO_QR = re.compile(r"^ccoqr(\d{2})p(\d+)$")

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
            qr = CCC_QR.match(obj["code"])
            if qr:
                # Junior qualification round practice set, no contest year.
                yield csvio.blank_problem(
                    id=f"ccc-qr-p{qr.group(1)}",
                    title=obj["name"].split(" - ", 1)[-1],
                    origin="ccc",
                    contest="CCC Junior Qualification Round",
                    label=f"QR{qr.group(1)}",
                    hosts="dmoj",
                    url=f"https://dmoj.ca/problem/{obj['code']}",
                    format="standard",
                    difficulty="1",
                    difficulty_basis="estimated",
                    difficulty_native=f"DMOJ {obj['points']:g}p",
                    free_tags="|".join(
                        str(t).lower().replace(" ", "-") for t in obj.get("types") or ()
                    ),
                    added=today,
                    verified=today,
                )
            continue
        year = _full_year(match.group(1))
        stream = match.group(2).upper()
        # A trailing word marks a harder rejudged variant of the same slot.
        variant = match.group(4)
        label = f"{stream}{match.group(3)}" + (f" ({variant})" if variant else "")
        yield csvio.blank_problem(
            id=f"ccc-{year}-{re.sub(r'[^a-z0-9]+', '-', label.lower()).strip('-')}",
            title=obj["name"].split(" - ", 1)[-1],
            origin="ccc",
            contest=f"CCC {year} {'Senior' if stream == 'S' else 'Junior'}",
            year=str(year),
            label=label,
            hosts="dmoj",
            url=f"https://dmoj.ca/problem/{obj['code']}",
            format="standard",
            # A rejudged "hard" variant sits in the same contest slot, so it
            # takes that slot's tier.
            difficulty=str(CCC_TIER.get(f"{stream}{match.group(3)}", "")),
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
            qr = CCO_QR.match(obj["code"])
            if qr:
                year = _full_year(qr.group(1))
                yield csvio.blank_problem(
                    id=f"cco-{year}-qr-p{qr.group(2)}",
                    title=obj["name"].split(" - ", 1)[-1],
                    origin="cco",
                    contest=f"CCO {year} Qualification Round",
                    year=str(year),
                    label=f"QR P{qr.group(2)}",
                    hosts="dmoj",
                    url=f"https://dmoj.ca/problem/{obj['code']}",
                    format="standard",
                    difficulty="5",
                    difficulty_basis="estimated",
                    difficulty_native=f"DMOJ {obj['points']:g}p",
                    free_tags="|".join(
                        str(t).lower().replace(" ", "-") for t in obj.get("types") or ()
                    ),
                    added=today,
                    verified=today,
                )
                continue
            prep = CCO_PREP.match(obj["code"])
            if prep:
                yield csvio.blank_problem(
                    id=f"cco-prep{prep.group(1)}-p{prep.group(2)}",
                    title=obj["name"].split(" - ", 1)[-1],
                    origin="cco",
                    contest=f"CCO Preparation Contest {prep.group(1)}",
                    label=f"P{prep.group(2)}",
                    hosts="dmoj",
                    url=f"https://dmoj.ca/problem/{obj['code']}",
                    format="standard",
                    difficulty="6",
                    difficulty_basis="estimated",
                    difficulty_native=f"DMOJ {obj['points']:g}p",
                    free_tags="|".join(
                        str(t).lower().replace(" ", "-") for t in obj.get("types") or ()
                    ),
                    added=today,
                    verified=today,
                )
            continue
        year = _full_year(match.group(1))
        level = match.group(2)
        number = match.group(3)
        variant = match.group(4)
        yield csvio.blank_problem(
            id=(
                f"cco-{year}-"
                + (f"l{level}" if level else "")
                + f"p{number}"
                + (f"-{variant}" if variant else "")
            ),
            title=obj["name"].split(" - ", 1)[-1],
            origin="cco",
            contest=f"CCO {year}",
            year=str(year),
            label=f"P{number}" + (f" (L{level})" if level else ""),
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


# --- USACO --------------------------------------------------------------------
# The contest results pages only link problems from 2014 onward, and miss the
# newest contests entirely, so the problem system itself is the source of
# truth: every task has a cpid and a page naming its contest and division.
USACO_PROBLEM_URL = "https://www.usaco.org/index.php?page=viewproblem2&cpid={cpid}"
USACO_MAX_CPID = 1700
USACO_H2 = re.compile(r"<h2>([^<]{0,90})</h2>")
USACO_YEAR = re.compile(r"USACO\s+(\d{4})")
USACO_DIVISION = re.compile(r"(Bronze|Silver|Gold|Platinum)", re.I)
USACO_ROUND = re.compile(
    r"(US Open|January|February|December|November|March|April|"
    r"First Contest|Second Contest|Third Contest|Fourth Contest)",
    re.I,
)
ROUND_SLUG = {
    "us open": "open",
    "january": "jan",
    "february": "feb",
    "december": "dec",
    "november": "nov",
    "march": "mar",
    "april": "apr",
    "first contest": "c1",
    "second contest": "c2",
    "third contest": "c3",
    "fourth contest": "c4",
}


def usaco_problem(cpid: int) -> dict | None:
    """One USACO task, or None when the cpid is unused."""
    try:
        body = _get(USACO_PROBLEM_URL.format(cpid=cpid), timeout=25)
    except Exception:  # noqa: BLE001 - an unused cpid is normal
        return None
    headings = USACO_H2.findall(body)
    if len(headings) < 2:
        return None
    header = html.unescape(headings[0]).strip()
    title = re.sub(r"^Problem\s+\d+\.\s*", "", html.unescape(headings[1]).strip())
    if not title:
        return None
    return {"cpid": cpid, "header": header, "title": title}


def usaco_rows(
    today: str,
    pause: float = 0.0,
    log: Callable[[str], None] | None = None,
    max_cpid: int = USACO_MAX_CPID,
    workers: int = 8,
):
    """Every USACO task, by sweeping the problem system's whole id space."""
    from concurrent.futures import ThreadPoolExecutor

    rows = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for found in pool.map(usaco_problem, range(1, max_cpid + 1)):
            if not found:
                continue
            header, title = found["header"], found["title"]
            year_match = USACO_YEAR.search(header)
            year = year_match.group(1) if year_match else ""
            div_match = USACO_DIVISION.search(header)
            division = div_match.group(1).capitalize() if div_match else ""
            round_match = USACO_ROUND.search(header)
            round_slug = ROUND_SLUG.get(round_match.group(1).lower(), "") if round_match else ""
            slug = re.sub(r"[^a-z0-9]+", "", title.lower()) or f"cpid{found['cpid']}"
            parts = ["usaco", year, round_slug, division.lower(), slug]
            rows.append(
                csvio.blank_problem(
                    id="-".join(p for p in parts if p),
                    title=title,
                    origin="usaco",
                    contest=header,
                    year=year,
                    label=division,
                    hosts="usaco-official",
                    url=USACO_PROBLEM_URL.format(cpid=found["cpid"]),
                    format="standard",
                    # A contest whose divisions are not published yet still
                    # needs a tier; the mid-scale value says "unknown".
                    difficulty=str(USACO_TIER.get(division, 5)),
                    difficulty_basis="estimated",
                    difficulty_native=division,
                    added=today,
                    verified=today,
                )
            )
    if log:
        log(f"  USACO: {len(rows)} problems across cpid 1-{max_cpid}")
    return rows


# --- oj.uz-hosted olympiads ---------------------------------------------------
OJUZ_SOURCE_INDEX = "https://oj.uz/problems/source/{source}"
OJUZ_YEAR = re.compile(r'href="/problems/source/([a-z0-9]+)(\d{4})"')
OJUZ_PROBLEM = re.compile(r'href="/problem/view/([A-Za-z0-9_]+)"[^>]*>([^<]+)<')

# oj.uz also mirrors CCO, which DMOJ already supplies with contest positions
# in the id; fetching both would double every CCO row under two schemes.
OJUZ_SOURCES = tuple(sorted(set(OJUZ_TIER)))

CONTEST_NAME = {
    "ioi": "IOI",
    "apio": "APIO",
    "ceoi": "CEOI",
    "balkanoi": "Balkan OI",
    "boi": "BOI",
    "joi": "JOI",
    "poi": "POI",
    "coci": "COCI",
    "coi": "COI",
    "izho": "IZhO",
    "rmi": "RMI",
    "egoi": "EGOI",
    "ejoi": "EJOI",
    "sgnoi": "SGNOI",
    "info1cup": "info(1) cup",
    "inoi": "INOI",
    "loi": "LOI",
    "innopolis": "Innopolis Open",
    "koi": "KOI",
}


def ojuz_rows(
    source: str, today: str, pause: float = 0.1, log: Callable[[str], None] | None = None
):
    """Every problem oj.uz hosts for one olympiad.

    Sources nest to varying depths: IOI lists years directly, JOI lists
    `joisc` / `joifinal` first, and POI and COCI list two-year seasons
    (`coci20142015`). So this walks children until it reaches problem links,
    taking the year from the first four digits of the deepest slug.
    """
    rows: list[dict] = []
    seen_pages: set[str] = set()
    seen_ids: set[str] = set()

    def walk(slug: str, depth: int) -> None:
        if slug in seen_pages or depth > 3:
            return
        seen_pages.add(slug)
        body = _get(OJUZ_SOURCE_INDEX.format(source=slug))
        time.sleep(pause)

        found = OJUZ_PROBLEM.findall(body)
        children = sorted(set(re.findall(r'href="/problems/source/([a-z0-9]+)"', body)))
        if found:
            year_match = re.search(r"(\d{4})", slug)
            year = year_match.group(1) if year_match else ""
            for problem_slug, raw_name in found:
                tail = problem_slug.split("_", 1)[-1].lower()
                name = re.sub(r"[^a-z0-9]+", "", tail)
                if not name:
                    continue
                problem_id = f"{source}-{year}-{name}" if year else f"{source}-{name}"
                if problem_id in seen_ids:
                    continue
                seen_ids.add(problem_id)
                rows.append(
                    csvio.blank_problem(
                        id=problem_id,
                        title=html.unescape(raw_name).strip(),
                        origin=source,
                        contest=(f"{CONTEST_NAME.get(source, source.upper())} {year}".strip()),
                        year=year,
                        hosts="oj.uz",
                        url=f"https://oj.uz/problem/view/{problem_slug}",
                        # Olympiad tasks are scored by subtask.
                        format="subtask",
                        difficulty=str(OJUZ_TIER.get(source, "")),
                        difficulty_basis="estimated",
                        added=today,
                        verified=today,
                    )
                )

        # Some pages list problems *and* sub-pages, and a child's slug does not
        # always start with its parent's, so descend unconditionally.
        for child in children:
            if child != slug and child not in seen_pages and child.startswith(source):
                walk(child, depth + 1)

    walk(source, 0)
    if log:
        log(f"  {source}: {len(rows)} problems")
    return rows


def ioi_rows(today: str, pause: float = 0.12, log: Callable[[str], None] | None = None):
    """Kept as a named entry point; IOI is one oj.uz source among many."""
    return ojuz_rows("ioi", today, pause=pause, log=log)


# --- CSES ---------------------------------------------------------------------
CSES_TASK = re.compile(r'<h2>([^<]+)</h2>|<a href="/problemset/task/(\d+)">([^<]+)</a>')


def cses_rows(today: str, log: Callable[[str], None] | None = None):
    """The whole CSES problem set, section by section."""
    body = _get("https://cses.fi/problemset/")
    section = ""
    rows = []
    for match in CSES_TASK.finditer(body):
        if match.group(1):
            section = html.unescape(match.group(1)).strip()
            continue
        task_id, name = match.group(2), html.unescape(match.group(3)).strip()
        rows.append(
            csvio.blank_problem(
                id=f"cses-{task_id}",
                title=name,
                origin="cses",
                contest=f"CSES Problem Set - {section}" if section else "CSES Problem Set",
                hosts="cses",
                url=f"https://cses.fi/problemset/task/{task_id}",
                format="standard",
                difficulty=str(CSES_SECTION_TIER.get(section, 4)),
                difficulty_basis="estimated",
                added=today,
                verified=today,
            )
        )
    if log:
        log(f"  CSES: {len(rows)} problems")
    return rows


# --- assembly ----------------------------------------------------------------
SOURCES = ("ccc", "cco", "usaco", "cses") + OJUZ_SOURCES


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
    if "cses" in sources:
        if log:
            log("fetching the CSES problem set...")
        rows += cses_rows(today, log=log)
    wanted = [s for s in OJUZ_SOURCES if s in sources]
    if wanted:
        if log:
            log(f"fetching {len(wanted)} oj.uz source(s)...")
        for source in wanted:
            rows += ojuz_rows(source, today, log=log)
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
