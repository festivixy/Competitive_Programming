"""One test per validation rule in SPEC.md section 9.

Each test starts from a clean row and breaks exactly one thing, so a failure
names the rule that regressed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import TODAY, problem, write_problems, write_progress

from cpidx import validate
from cpidx.cli import Paths
from cpidx.schema import PROBLEM_COLUMNS


def rules(paths: Paths, today=TODAY) -> set[int]:
    return {f.rule for f in validate.run(paths, today=today).findings}


def test_clean_index_passes(index: Paths) -> None:
    report = validate.run(index, today=TODAY)
    assert report.ok, [str(f) for f in report.errors]
    assert report.exit_code() == 0


# --- structural, rules 1-5 ---------------------------------------------------
def test_rule_1_header_mismatch(index: Paths) -> None:
    path = Path(index.problems)
    body = path.read_text(encoding="utf-8").splitlines()[1:]
    path.write_text("\n".join(["wrong,header"] + body) + "\n", encoding="utf-8")
    assert 1 in rules(index)


def test_rule_2_wrong_field_count(index: Paths) -> None:
    path = Path(index.problems)
    path.write_text(path.read_text(encoding="utf-8") + "cses-1002,only,three\n", encoding="utf-8")
    assert 2 in rules(index)


def test_rule_3_unsorted_rows(index: Paths) -> None:
    write_problems(
        Path(index.problems),
        [problem(id="cses-2000"), problem(id="cses-1000")],
    )
    # render() sorts, so rewrite the body in the wrong order deliberately.
    path = Path(index.problems)
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join([lines[0], lines[2], lines[1]]) + "\n", encoding="utf-8")
    assert 3 in rules(index)


def test_rule_4_duplicate_id(index: Paths) -> None:
    write_problems(Path(index.problems), [problem(), problem(title="Other")])
    assert 4 in rules(index)


def test_rule_5_bad_slug(index: Paths) -> None:
    write_problems(Path(index.problems), [problem(id="CSES_1001")])
    assert 5 in rules(index)


# --- referential, rules 6-10 -------------------------------------------------
def test_rule_6_unknown_tag(index: Paths) -> None:
    write_problems(Path(index.problems), [problem(primary_tag="graphs.nope", tags="graphs.nope")])
    assert 6 in rules(index)


def test_rule_7_non_leaf_tag(index: Paths) -> None:
    write_problems(
        Path(index.problems), [problem(primary_tag="graphs.traversal", tags="graphs.traversal")]
    )
    assert 7 in rules(index)


def test_rule_8_deprecated_tag(index: Paths) -> None:
    write_problems(
        Path(index.problems), [problem(primary_tag="dp.basics.old_name", tags="dp.basics.old_name")]
    )
    assert 8 in rules(index)


def test_rule_9_primary_not_in_tags(index: Paths) -> None:
    write_problems(
        Path(index.problems),
        [problem(primary_tag="graphs.traversal.bfs", tags="graphs.traversal.dfs")],
    )
    assert 9 in rules(index)


def test_rule_10_progress_references_unknown_id(index: Paths) -> None:
    from cpidx import csvio

    write_progress(Path(index.progress), [csvio.blank_progress(id="cses-9999", status="solved")])
    assert 10 in rules(index)


def test_rule_10_skipped_when_progress_absent(index: Paths) -> None:
    """The spec's rule 10 cannot run in CI, and must say so rather than pass silently."""
    report = validate.run(index, today=TODAY)
    assert any("rule 10" in note for note in report.skipped)


# --- domain, rules 11-16 -----------------------------------------------------
def test_rule_11_unknown_origin(index: Paths) -> None:
    write_problems(Path(index.problems), [problem(origin="nosuchjudge")])
    assert 11 in rules(index)


def test_rule_11_unknown_host(index: Paths) -> None:
    write_problems(Path(index.problems), [problem(hosts="cses|nosuchhost")])
    assert 11 in rules(index)


def test_rule_12_unknown_format(index: Paths) -> None:
    write_problems(Path(index.problems), [problem(format="freeform")])
    assert 12 in rules(index)


@pytest.mark.parametrize(
    "field,value", [("difficulty", "11"), ("difficulty", "0"), ("quality", "6")]
)
def test_rule_13_out_of_range(index: Paths, field: str, value: str) -> None:
    write_problems(Path(index.problems), [problem(**{field: value})])
    assert 13 in rules(index)


def test_rule_14_year_out_of_range(index: Paths) -> None:
    write_problems(Path(index.problems), [problem(year="1979")])
    assert 14 in rules(index)


def test_rule_14_year_in_the_future(index: Paths) -> None:
    write_problems(Path(index.problems), [problem(year="2099")])
    assert 14 in rules(index)


def test_rule_15_verified_before_added(index: Paths) -> None:
    write_problems(Path(index.problems), [problem(added="2026-05-01", verified="2026-01-01")])
    assert 15 in rules(index)


def test_rule_16_mirror_urls_length_mismatch(index: Paths) -> None:
    write_problems(
        Path(index.problems),
        [problem(hosts="cses|dmoj|oj.uz", mirror_urls="https://dmoj.ca/problem/x")],
    )
    assert 16 in rules(index)


def test_rule_16_allows_empty_mirror_urls(index: Paths) -> None:
    """Deviation from the spec text: mirror_urls stays optional when blank."""
    write_problems(Path(index.problems), [problem(hosts="cses|dmoj", mirror_urls="")])
    assert 16 not in rules(index)


def test_rule_16_accepts_matching_length(index: Paths) -> None:
    write_problems(
        Path(index.problems),
        [problem(hosts="cses|dmoj", mirror_urls="https://dmoj.ca/problem/x")],
    )
    assert 16 not in rules(index)


# --- taxonomy, rules 17-20 ---------------------------------------------------
def test_rule_17_prerequisite_cycle(index: Paths) -> None:
    Path(index.taxonomy).write_text(
        """
version: 0
nodes:
- id: a
  name: A
  status: canonical
  description: d
- id: a.x
  name: X
  status: canonical
  prerequisites: [a.y]
  description: d
  discriminator: d
- id: a.y
  name: Y
  status: canonical
  prerequisites: [a.x]
  description: d
  discriminator: d
""",
        encoding="utf-8",
    )
    assert 17 in rules(index)


def test_rule_18_depth_exceeded(index: Paths) -> None:
    Path(index.taxonomy).write_text(
        """
version: 0
nodes:
- id: a
  name: A
  status: canonical
  description: d
- id: a.b
  name: B
  status: canonical
  description: d
- id: a.b.c
  name: C
  status: canonical
  description: d
- id: a.b.c.d
  name: D
  status: canonical
  description: d
- id: a.b.c.d.e
  name: E
  status: canonical
  description: d
  discriminator: d
""",
        encoding="utf-8",
    )
    assert 18 in rules(index)


def test_rule_19_leaf_without_discriminator(index: Paths) -> None:
    Path(index.taxonomy).write_text(
        """
version: 0
nodes:
- id: a
  name: A
  status: canonical
  description: d
- id: a.b
  name: B
  status: canonical
  description: no discriminator here
""",
        encoding="utf-8",
    )
    assert 19 in rules(index)


def test_rule_20_deprecated_without_replacement(index: Paths) -> None:
    Path(index.taxonomy).write_text(
        """
version: 0
nodes:
- id: a
  name: A
  status: canonical
  description: d
- id: a.b
  name: B
  status: deprecated
  description: d
  discriminator: d
""",
        encoding="utf-8",
    )
    assert 20 in rules(index)


# --- warnings, rules 21-24 and additions 25-26 -------------------------------
def test_rule_21_stale_verified_is_a_warning(index: Paths) -> None:
    write_problems(Path(index.problems), [problem(added="2020-01-01", verified="2020-01-01")])
    report = validate.run(index, today=TODAY)
    assert 21 in {f.rule for f in report.warnings}
    assert report.ok  # a stale link does not block CI


def test_rule_22_free_tag_promotion_threshold(index: Paths) -> None:
    rows = [problem(id=f"cses-{1000 + i:04d}", free_tags="heavy-implementation") for i in range(10)]
    write_problems(Path(index.problems), rows)
    assert 22 in rules(index)


def test_rule_23_thin_tag(index: Paths) -> None:
    assert 23 in rules(index)  # the single seed row leaves bfs with one problem


def test_rule_23_silent_for_canonical_tag(index: Paths) -> None:
    write_problems(Path(index.problems), [problem(canonical="true")])
    assert 23 not in rules(index)


def test_rule_24_free_tag_near_canonical_alias(index: Paths) -> None:
    write_problems(Path(index.problems), [problem(free_tags="breadth first serch")])
    assert 24 in rules(index)


def test_rule_25_required_field_empty(index: Paths) -> None:
    write_problems(Path(index.problems), [problem(title="")])
    report = validate.run(index, today=TODAY)
    assert 25 in {f.rule for f in report.errors}


def test_rule_26_unknown_id_prefix_is_a_warning(index: Paths) -> None:
    write_problems(Path(index.problems), [problem(id="zzz-1001")])
    report = validate.run(index, today=TODAY)
    assert 26 in {f.rule for f in report.warnings}
    assert report.ok


# --- report behaviour --------------------------------------------------------
def test_strict_mode_fails_on_warnings(index: Paths) -> None:
    report = validate.run(index, today=TODAY)
    assert report.warnings
    assert report.exit_code(strict=False) == 0
    assert report.exit_code(strict=True) == 1


def test_every_column_is_covered_by_the_canonical_list() -> None:
    assert len(PROBLEM_COLUMNS) == 22
    assert PROBLEM_COLUMNS[0] == "id"
    assert PROBLEM_COLUMNS[-1] == "verified"
