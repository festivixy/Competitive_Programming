"""Adopting published classifications. No network: the guide map is injected."""

from __future__ import annotations

from conftest import problem

from cpidx import csvio, enrich
from cpidx.taxonomy import Taxonomy

GUIDE = {"usaco-696": "tree-euler", "usaco-123": "dsu", "usaco-999": "gold-conclusion"}


def row(**kw: str) -> dict:
    base = {"id": "usaco-x", "primary_tag": "", "tags": "", "free_tags": "", "url": ""}
    base.update(kw)
    return csvio.blank_problem(**base)


def test_every_mapped_tag_is_a_real_leaf(real_taxonomy: Taxonomy) -> None:
    """The mapping is only safe while every target still exists as a leaf."""
    assert enrich.unknown_tags(real_taxonomy) == []


def test_guide_module_becomes_the_primary_tag() -> None:
    rows = [row(id="a", url="https://www.usaco.org/index.php?page=viewproblem2&cpid=696")]
    out, stats = enrich.apply(rows, GUIDE)
    assert out[0]["primary_tag"] == "trees.basics.euler_tour"
    assert out[0]["tags"] == "trees.basics.euler_tour"
    assert stats["guide"] == 1


def test_provenance_is_recorded() -> None:
    rows = [row(id="a", url="...cpid=123")]
    out, _ = enrich.apply(rows, GUIDE)
    assert enrich.PROVENANCE_GUIDE in csvio.split_list(out[0]["free_tags"])


def test_a_module_that_names_no_technique_is_left_alone() -> None:
    """`gold-conclusion` is a difficulty round-up, not a technique."""
    rows = [row(id="a", url="...cpid=999")]
    out, stats = enrich.apply(rows, GUIDE)
    assert out[0]["primary_tag"] == ""
    assert stats["unresolved"] == 1


def test_single_unambiguous_dmoj_type_is_adopted() -> None:
    rows = [row(id="a", free_tags="implementation")]
    out, stats = enrich.apply(rows, {})
    assert out[0]["primary_tag"] == "adhoc.simulation.direct"
    assert stats["dmoj"] == 1
    free = csvio.split_list(out[0]["free_tags"])
    assert "implementation" in free and enrich.PROVENANCE_DMOJ in free


def test_category_level_dmoj_types_are_refused() -> None:
    """`graph-theory` names a subtree, not a leaf, so it must not be adopted."""
    for coarse in ("graph-theory", "dynamic-programming", "data-structures", "simple-math"):
        out, stats = enrich.apply([row(id="a", free_tags=coarse)], {})
        assert out[0]["primary_tag"] == "", coarse
        assert stats["unresolved"] == 1


def test_multiple_dmoj_types_are_refused() -> None:
    """Two categories means the single-technique reading is not available."""
    out, stats = enrich.apply([row(id="a", free_tags="implementation|graph-theory")], {})
    assert out[0]["primary_tag"] == ""
    assert stats["unresolved"] == 1


def test_an_existing_tag_is_never_overwritten() -> None:
    rows = [row(id="a", url="...cpid=696", primary_tag="dp.basics.linear", tags="dp.basics.linear")]
    out, stats = enrich.apply(rows, GUIDE)
    assert out[0]["primary_tag"] == "dp.basics.linear"
    assert stats["already"] == 1


def test_guide_wins_over_dmoj_when_both_resolve() -> None:
    rows = [row(id="a", url="...cpid=123", free_tags="implementation")]
    out, _ = enrich.apply(rows, GUIDE)
    assert out[0]["primary_tag"] == "data_structures.disjoint_set.dsu"


def test_enriched_rows_satisfy_the_index_schema(real_taxonomy: Taxonomy) -> None:
    """A promoted row has to pass the same rules as a hand-curated one."""
    base = problem(primary_tag="", tags="", free_tags="implementation", id="ccc-2000-j1")
    out, _ = enrich.apply([base], {})
    assert real_taxonomy.resolution_error(out[0]["primary_tag"]) is None
    assert out[0]["primary_tag"] in csvio.split_list(out[0]["tags"])


# --- lexicon ------------------------------------------------------------------
def test_lexicon_targets_are_all_leaves(real_taxonomy: Taxonomy) -> None:
    from cpidx import lexicon

    assert [t for t in sorted(lexicon.targets()) if not real_taxonomy.is_leaf(t)] == []


def test_lexicon_prefers_the_more_specific_technique() -> None:
    from cpidx import lexicon

    # An editorial for a convex-hull-trick problem also says "dynamic programming".
    assert (
        lexicon.classify_prose("We speed up the dynamic programming with the convex hull trick.")
        == "dp.optimization.convex_hull_trick"
    )
    # One about lazy propagation also says "segment tree".
    assert (
        lexicon.classify_prose("Build a segment tree with lazy propagation over the range.")
        == "data_structures.range_query.lazy_propagation"
    )


def test_lexicon_refuses_bare_category_words() -> None:
    from cpidx import lexicon

    assert lexicon.classify_prose("This is a graph problem about a tree.") is None
    assert lexicon.classify_prose("Consider the string and the array.") is None


# --- coarse fallback ----------------------------------------------------------
def test_coarse_targets_are_leaves(real_taxonomy: Taxonomy) -> None:
    for tag in set(enrich.COARSE_CATEGORY_TAGS.values()) | {enrich.COARSE_DEFAULT}:
        assert real_taxonomy.is_leaf(tag), tag


def test_coarse_covers_every_category_it_prioritises() -> None:
    assert sorted(enrich.COARSE_PRIORITY) == sorted(enrich.COARSE_CATEGORY_TAGS)


def test_coarse_is_off_by_default() -> None:
    out, stats = enrich.apply([row(id="a", free_tags="graph-theory")], {})
    assert out[0]["primary_tag"] == ""
    assert stats["unresolved"] == 1


def test_coarse_prefers_the_more_informative_category() -> None:
    out, _ = enrich.apply([row(id="a", free_tags="implementation|graph-theory")], {}, coarse=True)
    assert out[0]["primary_tag"] == "graphs.traversal.dfs"


def test_coarse_marks_its_own_provenance() -> None:
    out, stats = enrich.apply([row(id="a", free_tags="dynamic-programming")], {}, coarse=True)
    assert enrich.PROVENANCE_COARSE in csvio.split_list(out[0]["free_tags"])
    assert stats["coarse"] == 1


def test_coarse_still_defers_to_precise_sources() -> None:
    """A guide module must win over the category bucket."""
    rows = [row(id="a", url="...cpid=123", free_tags="graph-theory")]
    out, stats = enrich.apply(rows, GUIDE, coarse=True)
    assert out[0]["primary_tag"] == "data_structures.disjoint_set.dsu"
    assert stats["guide"] == 1 and stats["coarse"] == 0


def test_coarse_gives_uncategorised_rows_the_default() -> None:
    out, _ = enrich.apply([row(id="a", free_tags="")], {}, coarse=True)
    assert out[0]["primary_tag"] == enrich.COARSE_DEFAULT
