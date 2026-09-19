"""Parsing tests for the fetch module. No network: fixtures are real markup."""

from __future__ import annotations

import pytest

from cpidx import csvio, fetch

DMOJ = [
    {
        "code": "ccc21s4",
        "name": "CCC '21 S4 - Daily Commute",
        "points": 12.0,
        "types": ["Graph Theory"],
    },
    {"code": "ccc10j1", "name": "CCC '10 J1 - What is n, Daddy?", "points": 3.0, "types": []},
    {
        "code": "cco12p1",
        "name": "CCO '12 P1 - Choose Your Own Arithmetic",
        "points": 7.0,
        "types": ["Brute Force"],
    },
    {"code": "cco14p5", "name": "CCO '14 P5 - Tinted Glass", "points": 25.0, "types": []},
    {"code": "aplusb", "name": "A Plus B", "points": 3.0, "types": ["Simple Math"]},
]

USACO_PAGE = """
<h2><img src="current/images/medal_platinum.png"/> USACO 2017 January Contest, Platinum</h2>
<div class='panel historypanel'><h1>1</h1><div><b>Promotion Counting</b><br/>
<a href='index.php?page=viewproblem2&cpid=696'>View problem</a> |
<a href='current/data/promote_platinum_jan17.zip'>Test data</a></div></div>
<h2><img src="current/images/medal_bronze.png"/> USACO 2017 January Contest, Bronze</h2>
<div class='panel historypanel'><h1>1</h1><div><b>Don't Be Last!</b><br/>
<a href='index.php?page=viewproblem2&cpid=687'>View problem</a></div></div>
"""


def test_ccc_rows_map_label_and_tier() -> None:
    rows = {r["id"]: r for r in fetch.ccc_rows(DMOJ, "2026-09-19")}
    assert set(rows) == {"ccc-2021-s4", "ccc-2010-j1"}
    s4 = rows["ccc-2021-s4"]
    assert s4["title"] == "Daily Commute"
    assert s4["label"] == "S4"
    assert s4["difficulty"] == "6"  # SPEC.md 6.2: origin beats host points
    assert s4["difficulty_native"] == "DMOJ 12p"
    assert s4["url"] == "https://dmoj.ca/problem/ccc21s4"
    assert s4["free_tags"] == "graph-theory"
    assert not s4["primary_tag"] and not s4["tags"]


def test_cco_day_two_reopens_at_the_day_one_tier() -> None:
    rows = {r["id"]: r for r in fetch.cco_rows(DMOJ, "2026-09-19")}
    assert rows["cco-2012-p1"]["difficulty"] == "6"
    assert rows["cco-2014-p5"]["difficulty"] == "8"


def test_unrelated_dmoj_problems_are_ignored() -> None:
    ids = [r["id"] for r in fetch.ccc_rows(DMOJ, "2026-09-19")]
    ids += [r["id"] for r in fetch.cco_rows(DMOJ, "2026-09-19")]
    assert not any("aplusb" in i for i in ids)


def test_merge_keeps_curated_rows_and_skips_indexed_ids() -> None:
    existing = [
        csvio.blank_problem(
            id="ccc-2021-s4", title="Daily Commute", primary_tag="graphs.traversal.bfs", quality="4"
        )
    ]
    fetched = list(fetch.ccc_rows(DMOJ, "2026-09-19"))
    rows, added, _ = fetch.merge(existing, fetched, index_ids={"ccc-2021-s4"})
    ids = [r["id"] for r in rows]
    assert "ccc-2021-s4" not in ids  # already in the curated index
    assert "ccc-2010-j1" in ids
    assert added == 1


def test_merge_preserves_hand_added_tags() -> None:
    existing = [
        csvio.blank_problem(
            id="ccc-2010-j1",
            title="old title",
            primary_tag="adhoc.simulation.direct",
            tags="adhoc.simulation.direct",
            quality="3",
        )
    ]
    fetched = list(fetch.ccc_rows(DMOJ, "2026-09-19"))
    rows, added, refreshed = fetch.merge(existing, fetched, index_ids=set())
    kept = next(r for r in rows if r["id"] == "ccc-2010-j1")
    assert kept["primary_tag"] == "adhoc.simulation.direct"  # curation survives
    assert kept["quality"] == "3"
    assert kept["title"] == "What is n, Daddy?"  # judge's field refreshed
    assert refreshed >= 1


def test_merge_fills_a_blank_difficulty_but_does_not_overwrite() -> None:
    existing = [
        csvio.blank_problem(id="cco-2014-p5", difficulty=""),
        csvio.blank_problem(id="cco-2012-p1", difficulty="9", difficulty_basis="official"),
    ]
    rows = {
        r["id"]: r
        for r in fetch.merge(existing, list(fetch.cco_rows(DMOJ, "2026-09-19")), set())[0]
    }
    assert rows["cco-2014-p5"]["difficulty"] == "8"
    assert rows["cco-2012-p1"]["difficulty"] == "9"
    assert rows["cco-2012-p1"]["difficulty_basis"] == "official"


IOI_INDEX = """
<a href="/problems/source/ioi2015">2015</a>
<a href="/problems/source/ioi2011">2011</a>
"""
IOI_YEAR = """
<a href="/problem/view/IOI15_boxes">Boxes with souvenirs</a>
<a href="/problem/view/IOI15_horses">Horses</a>
"""


def test_ioi_rows_walk_every_year(monkeypatch) -> None:
    def fake(url, timeout=30.0):
        return IOI_INDEX if url.endswith("/source/ioi") else IOI_YEAR

    monkeypatch.setattr(fetch, "_get", fake)
    rows = {r["id"]: r for r in fetch.ioi_rows("2026-09-19", pause=0)}
    assert "ioi-2015-boxes" in rows and "ioi-2011-horses" in rows
    row = rows["ioi-2015-boxes"]
    assert row["title"] == "Boxes with souvenirs"
    assert row["origin"] == "ioi"
    assert row["format"] == "subtask"  # every IOI task is subtask-scored
    assert row["url"] == "https://oj.uz/problem/view/IOI15_boxes"
    assert not row["primary_tag"]


@pytest.mark.parametrize(
    "code,expected_id",
    [
        ("ccc21s4", "ccc-2021-s4"),
        ("ccc00s5hard", "ccc-2000-s5-hard"),  # rejudged harder variant
        ("cccjqrp3", "ccc-qr-p3"),  # junior qualification practice
    ],
)
def test_ccc_variant_codes_are_not_dropped(code: str, expected_id: str) -> None:
    problems = [{"code": code, "name": f"CCC - {code}", "points": 5.0, "types": []}]
    assert [r["id"] for r in fetch.ccc_rows(problems, "2026-09-19")] == [expected_id]


def test_ccc_hard_variant_inherits_its_contest_slot_tier() -> None:
    problems = [{"code": "ccc00s5hard", "name": "CCC - x", "points": 25.0, "types": []}]
    row = next(iter(fetch.ccc_rows(problems, "2026-09-19")))
    assert row["difficulty"] == "7"  # same tier as S5


@pytest.mark.parametrize(
    "code,expected_id",
    [
        ("cco12p1", "cco-2012-p1"),
        ("cco26l2p1", "cco-2026-l2p1"),  # second-level contest
        ("cco24p4hard", "cco-2024-p4-hard"),
        ("ccoprep1p2", "cco-prep1-p2"),
        ("ccoqr16p1", "cco-2016-qr-p1"),
    ],
)
def test_cco_variant_codes_are_not_dropped(code: str, expected_id: str) -> None:
    problems = [{"code": code, "name": f"CCO - {code}", "points": 10.0, "types": []}]
    assert [r["id"] for r in fetch.cco_rows(problems, "2026-09-19")] == [expected_id]


USACO_PAGE = """
<h2> USACO 2011 November Contest, Bronze Division </h2>
<h2> Problem 1. Contest Timing </h2>
"""
USACO_NO_DIVISION = """
<h2> USACO 2026 US Open </h2>
<h2> Problem 1. Arranging Cows </h2>
"""


def test_usaco_sweep_reads_the_problem_page_not_the_results_page(monkeypatch) -> None:
    """Results pages omit pre-2014 and the newest contests; cpids do not."""
    monkeypatch.setattr(
        fetch, "_get", lambda url, timeout=30.0: USACO_PAGE if "cpid=84" in url else ""
    )
    rows = fetch.usaco_rows("2026-09-19", max_cpid=84, workers=1)
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == "usaco-2011-nov-bronze-contesttiming"
    assert row["year"] == "2011"
    assert row["label"] == "Bronze"
    assert row["difficulty"] == "2"


def test_usaco_contest_without_a_published_division_still_gets_a_tier(monkeypatch) -> None:
    monkeypatch.setattr(fetch, "_get", lambda url, timeout=30.0: USACO_NO_DIVISION)
    row = fetch.usaco_rows("2026-09-19", max_cpid=1, workers=1)[0]
    assert row["label"] == ""
    assert row["difficulty"] == "5"


def test_unused_cpid_yields_nothing(monkeypatch) -> None:
    monkeypatch.setattr(fetch, "_get", lambda url, timeout=30.0: "<html>no problem</html>")
    assert fetch.usaco_rows("2026-09-19", max_cpid=3, workers=1) == []
