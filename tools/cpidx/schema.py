"""Canonical column lists, enums, and regexes for the problem index.

Normative reference: SPEC.md sections 4, 5, 6.
"""

import re

# --- problems.csv, SPEC.md 5 -------------------------------------------------
# Order is fixed and enforced by the formatter.
PROBLEM_COLUMNS = (
    "id",
    "title",
    "origin",
    "contest",
    "year",
    "label",
    "hosts",
    "url",
    "mirror_urls",
    "format",
    "difficulty",
    "difficulty_basis",
    "difficulty_native",
    "primary_tag",
    "tags",
    "free_tags",
    "quality",
    "canonical",
    "constraints",
    "editorial_url",
    "added",
    "verified",
)

REQUIRED_PROBLEM_COLUMNS = frozenset(
    {
        "id",
        "title",
        "origin",
        "hosts",
        "url",
        "format",
        "difficulty",
        "difficulty_basis",
        "primary_tag",
        "tags",
        "added",
        "verified",
    }
)

LIST_COLUMNS = frozenset({"hosts", "mirror_urls", "tags", "free_tags"})

# --- progress.csv, SPEC.md 8 -------------------------------------------------
PROGRESS_COLUMNS = (
    "id",
    "status",
    "attempts",
    "first_attempt",
    "resolved",
    "minutes",
    "confidence",
    "failure_mode",
    "next_review",
)

# --- enums, SPEC.md 5.1 / 5.2 / 5.3 / 8.1 / 8.2 ------------------------------
# Deviation from SPEC.md 5.1: cses, boi, dmopc, bsspc, leetcode added. The
# spec listed `cses` as a host but not as an origin, which left the largest
# body of problems in this repository with no legal origin value.
ORIGINS = frozenset("""
    ioi ceoi apio egoi ioi-practice
    ccc cco woburn dmoj dmopc bsspc
    usaco usaco-training
    noi noi-cn coci poi zco inoi boi
    icpc icpc-wf icpc-regional
    codeforces atcoder topcoder codechef leetcode
    gcj kickstart meta-hacker-cup
    projecteuler library-checker cses
    joi izho rmi balkanoi coi ejoi sgnoi info1cup loi innopolis koi
    """.split())

HOSTS = frozenset("""
    dmoj oj.uz codeforces atcoder codechef
    usaco-official ioi-official cses acmp
    vjudge szkopul eolymp library-checker leetcode
    """.split())

FORMATS = frozenset(
    {"standard", "subtask", "interactive", "output_only", "optimization", "communication"}
)

DIFFICULTY_BASES = frozenset({"official", "community", "estimated"})

STATUSES = frozenset(
    {
        "untouched",
        "read",
        "attempting",
        "solved",
        "solved_hint",
        "solved_editorial",
        "abandoned",
    }
)

SOLVED_STATUSES = frozenset({"solved", "solved_hint", "solved_editorial"})

FAILURE_MODES = frozenset(
    {
        "no_idea",
        "wrong_technique",
        "knew_unknown",
        "implementation",
        "complexity",
        "edge_case",
        "misread",
    }
)

# --- formats, SPEC.md 4.1 / 5.5 ----------------------------------------------
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
TAG_PATH_RE = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# SPEC.md 6.2 seed tiers, midpoints of the ranges given there. Keyed by origin,
# which wins over any host-local points value.
CCC_TIER = {
    "J1": 1,
    "J2": 1,
    "J3": 1,
    "J4": 2,
    "J5": 2,
    "S1": 2,
    "S2": 3,
    "S3": 4,
    "S4": 6,
    "S5": 7,
}
# CCO runs two days of three problems, so P4 opens day 2 at the day-1 tier.
CCO_TIER = {"1": 6, "2": 8, "3": 8, "4": 6, "5": 8, "6": 8}
USACO_TIER = {"Bronze": 2, "Silver": 4, "Gold": 6, "Platinum": 8}
IOI_TIER = {"1": 6, "2": 8, "3": 8}

# CSES publishes no difficulty, but its sections are ordered pedagogically.
# Midpoints, used only as an `estimated` seed.
CSES_SECTION_TIER = {
    "Introductory Problems": 2,
    "Sorting and Searching": 3,
    "Dynamic Programming": 4,
    "Graph Algorithms": 4,
    "Tree Algorithms": 4,
    "Range Queries": 5,
    "Mathematics": 5,
    "String Algorithms": 5,
    "Geometry": 5,
    "Bitwise Operations": 5,
    "Construction Problems": 5,
    "Sliding Window Problems": 4,
    "Interactive Problems": 5,
    "Counting Problems": 6,
    "Advanced Techniques": 7,
    "Advanced Graph Problems": 6,
    "Additional Problems I": 6,
    "Additional Problems II": 7,
}

# oj.uz-hosted olympiads, by how hard the contest runs overall. SPEC.md 6.2
# anchors IOI/APIO/CEOI at 6-10; the junior and national events sit lower.
OJUZ_TIER = {
    "ioi": 7,
    "apio": 7,
    "ceoi": 7,
    "balkanoi": 6,
    "boi": 6,
    "joi": 6,
    "poi": 6,
    "coci": 4,
    "coi": 6,
    "izho": 7,
    "rmi": 7,
    "egoi": 6,
    "ejoi": 4,
    "sgnoi": 5,
    "info1cup": 5,
    "inoi": 5,
    "loi": 5,
    "innopolis": 5,
    "koi": 5,
}

MIN_YEAR = 1990
MAX_TAG_DEPTH = 4
STALE_VERIFIED_DAYS = 365
FREE_TAG_PROMOTION_THRESHOLD = 10
THIN_TAG_THRESHOLD = 3
LIST_SEPARATOR = "|"

# Deviation from SPEC.md 4.1: the id scheme is documented as
# `<origin>-<year>-<label>`, but the spec's own examples (`cf-1530-f`) use an
# abbreviation rather than the origin enum value, and omit the year entirely
# (`dmoj-tudorsnightmare`). The slug regex is therefore the only hard
# constraint; this map drives a non-fatal warning when an id's first segment
# matches no known origin.
ORIGIN_ID_PREFIXES = {
    "codeforces": "cf",
    "meta-hacker-cup": "mhc",
    "library-checker": "lc",
    "usaco-training": "usacotr",
    "ioi-practice": "ioip",
    "icpc-wf": "icpcwf",
    "icpc-regional": "icpcreg",
    "projecteuler": "pe",
    "noi-cn": "noicn",
}


def id_prefix(origin: str) -> str:
    """Expected leading id segment for an origin."""
    return ORIGIN_ID_PREFIXES.get(origin, origin)


KNOWN_ID_PREFIXES = frozenset(id_prefix(o) for o in ORIGINS) | set(ORIGINS)
