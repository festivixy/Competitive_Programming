"""Shared fixtures: a miniature but structurally complete index."""

from __future__ import annotations

import datetime
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cpidx import csvio  # noqa: E402
from cpidx.cli import Paths  # noqa: E402
from cpidx.schema import PROBLEM_COLUMNS, PROGRESS_COLUMNS  # noqa: E402
from cpidx.taxonomy import Taxonomy  # noqa: E402

TODAY = datetime.date(2026, 9, 19)

MINI_TAXONOMY = """
version: 0
nodes:
- id: graphs
  name: Graphs
  status: canonical
  description: Graph techniques.
- id: graphs.traversal
  name: Traversal
  status: canonical
  description: Visiting vertices.
- id: graphs.traversal.bfs
  name: BFS
  aliases: [breadth first search]
  status: canonical
  description: Layered traversal.
  discriminator: Use for unweighted distance.
- id: graphs.traversal.dfs
  name: DFS
  status: canonical
  description: Depth-first traversal.
  discriminator: Use when recursion structure matters.
- id: graphs.shortest_path
  name: Shortest paths
  status: canonical
  description: Cheapest walks.
- id: graphs.shortest_path.dijkstra
  name: Dijkstra
  status: canonical
  prerequisites: [graphs.traversal.bfs]
  description: Non-negative shortest paths.
  discriminator: Default for non-negative weights.
- id: dp
  name: Dynamic programming
  status: canonical
  description: Overlapping subproblems.
- id: dp.basics
  name: Basics
  status: canonical
  description: Standard shapes.
- id: dp.basics.linear
  name: Linear DP
  status: canonical
  description: One positional index.
  discriminator: Default for left-to-right sequences.
- id: dp.basics.old_name
  name: Retired tag
  status: deprecated
  replaced_by: dp.basics.linear
  description: Kept so old links resolve.
  discriminator: Never use; see replaced_by.
"""


def write_problems(path: Path, rows: list[dict]) -> None:
    path.write_text(csvio.render(rows, PROBLEM_COLUMNS), encoding="utf-8", newline="")


def write_progress(path: Path, rows: list[dict]) -> None:
    path.write_text(csvio.render(rows, PROGRESS_COLUMNS), encoding="utf-8", newline="")


def problem(**overrides: str) -> dict:
    """A row that validates cleanly, so each test can break exactly one thing."""
    row = csvio.blank_problem(
        id="cses-1001",
        title="Example Problem",
        origin="cses",
        contest="CSES Problem Set",
        year="2020",
        label="",
        hosts="cses",
        url="https://cses.fi/problemset/task/1001",
        format="standard",
        difficulty="3",
        difficulty_basis="estimated",
        primary_tag="graphs.traversal.bfs",
        tags="graphs.traversal.bfs",
        added="2026-01-01",
        verified="2026-09-01",
    )
    row.update(overrides)
    return row


@pytest.fixture
def mini_taxonomy(tmp_path: Path) -> Taxonomy:
    path = tmp_path / "taxonomy.yaml"
    path.write_text(MINI_TAXONOMY, encoding="utf-8")
    return Taxonomy.load(str(path))


@pytest.fixture
def index(tmp_path: Path) -> Paths:
    """An index root with a valid taxonomy and one valid problem."""
    (tmp_path / "taxonomy.yaml").write_text(MINI_TAXONOMY, encoding="utf-8")
    write_problems(tmp_path / "problems.csv", [problem()])
    return Paths(str(tmp_path))


@pytest.fixture
def real_taxonomy() -> Taxonomy:
    """The shipped taxonomy, so its own invariants are covered."""
    root = Path(__file__).resolve().parents[2]
    return Taxonomy.load(str(root / "taxonomy.yaml"))
