"""Parsing tests for the fetch module. No network: fixtures are real markup."""

from __future__ import annotations

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


def test_usaco_division_comes_from_the_heading(monkeypatch) -> None:
    monkeypatch.setattr(
        fetch, "_get", lambda url, timeout=30.0: USACO_PAGE if "jan17" in url else ""
    )
    monkeypatch.setattr(fetch, "USACO_YEARS", range(17, 18))
    monkeypatch.setattr(fetch, "USACO_MONTHS", ("jan",))
    rows = {r["title"]: r for r in fetch.usaco_rows("2026-09-19", pause=0)}
    assert rows["Promotion Counting"]["label"] == "Platinum"
    assert rows["Promotion Counting"]["difficulty"] == "8"
    assert rows["Don't Be Last!"]["label"] == "Bronze"
    assert rows["Don't Be Last!"]["difficulty"] == "2"
    assert "cpid=696" in rows["Promotion Counting"]["url"]


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
