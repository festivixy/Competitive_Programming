"""End-to-end exercise of every subcommand, via main()."""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import problem, write_problems

from cpidx import csvio
from cpidx.cli import main


def run(index, *args: str) -> int:
    return main(["--root", index.root, "--today", "2026-09-19", *args])


@pytest.fixture
def populated(index):
    """A handful of rows spanning tags, difficulties and canonical flags."""
    write_problems(
        Path(index.problems),
        [
            problem(
                id="cses-1001",
                title="Labyrinth",
                primary_tag="graphs.traversal.bfs",
                tags="graphs.traversal.bfs",
                difficulty="3",
                quality="5",
                canonical="true",
            ),
            problem(
                id="cses-1002",
                title="Shortest Routes",
                primary_tag="graphs.shortest_path.dijkstra",
                tags="graphs.shortest_path.dijkstra",
                difficulty="5",
                quality="4",
            ),
            problem(
                id="cses-1003",
                title="Dice Combinations",
                primary_tag="dp.basics.linear",
                tags="dp.basics.linear",
                difficulty="2",
                quality="5",
                canonical="true",
            ),
        ],
    )
    return index


def test_validate_exit_codes(populated, capsys) -> None:
    assert run(populated, "validate") == 0
    assert "0 error(s)" in capsys.readouterr().out


def test_validate_reports_errors(index, capsys) -> None:
    write_problems(Path(index.problems), [problem(origin="nope")])
    assert run(index, "validate") == 1
    assert "rule 11" in capsys.readouterr().out


def test_fmt_check_passes_on_canonical_file(populated, capsys) -> None:
    assert run(populated, "fmt", "--check") == 0
    assert "already canonical" in capsys.readouterr().out


def test_fmt_rewrites_unsorted_file(index, capsys) -> None:
    path = Path(index.problems)
    write_problems(path, [problem(id="cses-1"), problem(id="cses-2")])
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join([lines[0], lines[2], lines[1]]) + "\n", encoding="utf-8")
    assert run(index, "fmt", "--check") == 1
    assert run(index, "fmt") == 0
    assert run(index, "fmt", "--check") == 0


def test_query_filters_and_prints(populated, capsys) -> None:
    assert run(populated, "query", "--tag", "graphs", "--sort", "difficulty") == 0
    out = capsys.readouterr().out
    assert "cses-1001" in out and "cses-1003" not in out
    assert "2 problem(s)" in out


def test_query_ids_only(populated, capsys) -> None:
    assert run(populated, "query", "--canonical", "--ids-only") == 0
    # default sort is by difficulty, so the tier-2 row leads
    assert capsys.readouterr().out.split() == ["cses-1003", "cses-1001"]


def test_query_reports_no_matches(populated, capsys) -> None:
    assert run(populated, "query", "--difficulty", "9-10") == 0
    assert "no problems match" in capsys.readouterr().out


def test_query_rejects_unknown_tag(populated, capsys) -> None:
    assert run(populated, "query", "--tag", "not.real") == 2


def test_query_rejects_bad_range(populated) -> None:
    assert run(populated, "query", "--difficulty", "9-2") == 2


def test_stats_by_each_grouping(populated, capsys) -> None:
    for grouping in ("tag", "origin", "difficulty", "category"):
        assert run(populated, "stats", "--by", grouping) == 0
        assert capsys.readouterr().out.strip()


def test_stats_gaps_lists_unused_leaves(populated, capsys) -> None:
    assert run(populated, "stats", "--by", "tag", "--gaps") == 0
    assert "graphs.traversal.dfs" in capsys.readouterr().out


def test_export_each_format(populated, tmp_path, capsys) -> None:
    out = tmp_path / "out"
    for fmt, expected in (("json", "problems.json"), ("xlsx", "problems.xlsx")):
        assert run(populated, "export", "--format", fmt, "--out", str(out)) == 0
        assert (out / expected).exists()
    assert run(populated, "export", "--format", "md", "--out", str(out)) == 0
    assert (out / "by-tag" / "index.md").exists()


def test_add_refuses_without_classification(populated, capsys) -> None:
    assert run(populated, "add", "https://cses.fi/problemset/task/2000") == 1
    assert "Classification is never inferred" in capsys.readouterr().out


def test_add_writes_when_fully_specified(populated, capsys) -> None:
    code = run(
        populated,
        "add",
        "https://cses.fi/problemset/task/2000",
        "--set",
        "title=New Problem",
        "--set",
        "difficulty=4",
        "--set",
        "primary_tag=dp.basics.linear",
    )
    assert code == 0
    _, rows, _ = csvio.read_problems(populated.problems)
    assert any(r["id"] == "cses-2000" and r["tags"] == "dp.basics.linear" for r in rows)
    assert run(populated, "validate") == 0


def test_add_rejects_duplicate_id(populated, capsys) -> None:
    args = [
        "add",
        "https://cses.fi/problemset/task/4321",
        "--set",
        "title=Dup",
        "--set",
        "difficulty=4",
        "--set",
        "primary_tag=dp.basics.linear",
    ]
    assert run(populated, *args) == 0
    assert run(populated, *args) == 1


def test_add_rejects_unknown_column(populated) -> None:
    assert run(populated, "add", "https://cses.fi/problemset/task/3000", "--set", "nope=1") == 2


def test_linkcheck_offline_is_network_free(populated, capsys) -> None:
    write_problems(Path(populated.problems), [problem(added="2020-01-01", verified="2020-01-01")])
    assert run(populated, "linkcheck", "--offline") == 0
    assert "stale" in capsys.readouterr().out


def test_migrate_tags_dry_run_then_apply(index, capsys) -> None:
    write_problems(
        Path(index.problems),
        [problem(primary_tag="dp.basics.old_name", tags="dp.basics.old_name")],
    )
    assert run(index, "migrate-tags", "--dry-run") == 0
    _, rows, _ = csvio.read_problems(index.problems)
    assert rows[0]["primary_tag"] == "dp.basics.old_name"  # unchanged

    assert run(index, "migrate-tags") == 0
    _, rows, _ = csvio.read_problems(index.problems)
    assert rows[0]["primary_tag"] == "dp.basics.linear"
    assert run(index, "validate") == 0


def test_import_tree_stages_without_writing_index(index, capsys) -> None:
    target = Path(index.root) / "CCC" / "S" / "21" / "21s4.cpp"
    target.parent.mkdir(parents=True)
    target.write_text("int main(){}", encoding="utf-8")
    before = Path(index.problems).read_text(encoding="utf-8")
    assert run(index, "import-tree") == 0
    out = capsys.readouterr().out
    assert "Nothing was written to problems.csv" in out
    assert Path(index.problems).read_text(encoding="utf-8") == before
    assert (Path(index.root) / "build" / "import-candidates.csv").exists()


def test_import_tree_promote_skips_rows_needing_curation(index, capsys) -> None:
    target = Path(index.root) / "CCC" / "S" / "21" / "21s4.cpp"
    target.parent.mkdir(parents=True)
    target.write_text("int main(){}", encoding="utf-8")
    assert run(index, "import-tree", "--promote") == 0
    assert "every staged row still needs curation" in capsys.readouterr().out


def test_missing_problems_file_is_reported(tmp_path, capsys) -> None:
    (tmp_path / "taxonomy.yaml").write_text("version: 0\nnodes: []\n", encoding="utf-8")
    assert main(["--root", str(tmp_path), "query"]) == 2


def test_bad_taxonomy_is_reported(tmp_path, capsys) -> None:
    (tmp_path / "taxonomy.yaml").write_text("not: a taxonomy\n", encoding="utf-8")
    write_problems(tmp_path / "problems.csv", [problem()])
    with pytest.raises(SystemExit):
        main(["--root", str(tmp_path), "query"])


# --- regressions from code review -------------------------------------------
def test_fmt_refuses_to_rewrite_a_malformed_row(index, capsys) -> None:
    """A 24-field row must not be silently truncated back to 22 on rewrite."""
    path = Path(index.problems)
    path.write_text(
        path.read_text(encoding="utf-8") + "cses-9999,T,cses,,,,cses,u,,standard,3,"
        "estimated,,graphs.traversal.bfs,graphs.traversal.bfs,,,,,,2026-01-01,"
        "2026-09-01,EXTRA,DATA\n",
        encoding="utf-8",
    )
    assert run(index, "fmt") == 1
    assert "refusing to rewrite" in capsys.readouterr().err
    assert "EXTRA,DATA" in path.read_text(encoding="utf-8")


def test_add_refuses_on_a_malformed_file(index, capsys) -> None:
    path = Path(index.problems)
    path.write_text(path.read_text(encoding="utf-8") + "cses-9999,too,few\n", encoding="utf-8")
    code = run(
        index,
        "add",
        "https://cses.fi/problemset/task/2000",
        "--set",
        "title=X",
        "--set",
        "difficulty=3",
        "--set",
        "primary_tag=dp.basics.linear",
    )
    assert code == 1
    assert "refusing to rewrite" in capsys.readouterr().err


def test_migrate_tags_refuses_on_a_malformed_file(index, capsys) -> None:
    path = Path(index.problems)
    write_problems(path, [problem(primary_tag="dp.basics.old_name", tags="dp.basics.old_name")])
    path.write_text(path.read_text(encoding="utf-8") + "cses-9999,too,few\n", encoding="utf-8")
    assert run(index, "migrate-tags") == 1
    assert "refusing to rewrite" in capsys.readouterr().err


def test_tag_filters_are_mutually_exclusive(populated) -> None:
    """--tag-exact with --primary silently applied the wrong rule before."""
    with pytest.raises(SystemExit):
        run(populated, "query", "--tag-exact", "graphs.traversal.bfs", "--primary", "dp")
