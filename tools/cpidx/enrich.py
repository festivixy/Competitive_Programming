"""Adopting published classifications instead of inventing them.

Normative reference: SPEC.md 10.7.

SPEC.md 1.2 forbids the tooling from *deciding* a tag. It does not forbid
adopting a classification a person already published, which is what this
module does, from two sources:

  usaco.guide   modules are "the technique this problem teaches", which is
                exactly what `primary_tag` means. Human-curated, open source.
  DMOJ types    the judge's own categories. Most are category-level and map to
                no single leaf, so only the handful that resolve unambiguously
                are used, and only when a problem carries exactly one.

Every tag written here records where it came from in `free_tags`, so it can be
audited, queried and reverted. A mapping that is ambiguous is left out
entirely: a blank tag is honest, a wrong tag is not.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from collections.abc import Callable

from . import csvio

USER_AGENT = "cpidx-enrich/0.1"
GUIDE_REPO = "https://api.github.com/repos/cpinitiative/usaco-guide/git/trees/master?recursive=1"
GUIDE_RAW = "https://raw.githubusercontent.com/cpinitiative/usaco-guide/master/"

PROVENANCE_GUIDE = "via-usaco-guide"
PROVENANCE_DMOJ = "via-dmoj-types"
PROVENANCES = (
    PROVENANCE_GUIDE,
    PROVENANCE_DMOJ,
    "via-dmoj-category",
    "via-usaco-analysis",
    "via-solution-code",
)

CPID = re.compile(r"cpid=(\d+)")

# usaco.guide module id -> taxonomy leaf. Technique name to technique name.
# Modules that name a difficulty round-up rather than a technique
# (`gold-conclusion`), or a bucket too broad to resolve (`ad-hoc`, `casework`),
# are deliberately absent.
GUIDE_MODULE_TAGS = {
    "2DRQ": "data_structures.range_query.fenwick",
    "BCC-2CC": "graphs.components.biconnected",
    "DC-DP": "dp.optimization.divide_conquer_opt",
    "DC-SRQ": "data_structures.static_range.sparse_table",
    "PURS": "data_structures.range_query.segment_tree",
    "RURQ": "data_structures.range_query.lazy_propagation",
    "SCC": "graphs.components.scc_tarjan",
    "all-roots": "dp.tree.rerooting",
    "binary-jump": "trees.ancestors.binary_lifting",
    "binary-search": "search.binary_search.on_answer",
    "binary-search-sorted-array": "search.binary_search.on_answer",
    "bitsets": "bitwise.techniques.bitset_optimization",
    "centroid": "trees.decomposition.centroid",
    "combo": "combinatorics.basics.binomials",
    "complete-rec": "search.exhaustive.backtracking",
    "convex-hull": "geometry.convexity.convex_hull",
    "convex-hull-trick": "dp.optimization.convex_hull_trick",
    "digit-dp": "dp.digit.digit_dp",
    "dp-bitmasks": "dp.subset.subset_dp",
    "dp-broken-profile": "dp.subset.broken_profile",
    "dp-ranges": "dp.basics.interval",
    "dp-sos": "dp.subset.sum_over_subsets",
    "dp-trees": "dp.tree.subtree_dp",
    "dsu": "data_structures.disjoint_set.dsu",
    "eulers-formula": "graphs.special_graphs.planar",
    "fft-ext": "math.algebra.polynomials",
    "flood-fill": "graphs.traversal.connectivity",
    "func-graphs": "graphs.special_graphs.functional_graph",
    "graph-traversal": "graphs.traversal.dfs",
    "greedy-sorting": "greedy.exchange.sorting_order",
    "hashing": "strings.hashing.polynomial_hash",
    "hashmaps": "data_structures.linear.hash_map",
    "hld": "trees.decomposition.hld",
    "intro-bitwise": "bitwise.basics.operators",
    "intro-complete": "search.exhaustive.backtracking",
    "intro-dp": "dp.basics.linear",
    "intro-graphs": "graphs.traversal.dfs",
    "intro-greedy": "greedy.exchange.sorting_order",
    "intro-sets": "data_structures.linear.hash_map",
    "intro-sorted-sets": "data_structures.trees.treap",
    "intro-sorting": "adhoc.simulation.sorting",
    "knapsack": "dp.basics.knapsack",
    "lagrange": "dp.optimization.aliens_trick",
    "lca-euler": "trees.ancestors.lca",
    "lis": "dp.basics.lis",
    "matrix-expo": "dp.optimization.matrix_exponentiation",
    "meet-in-the-middle": "search.exhaustive.meet_in_middle",
    "min-cut": "flows.max_flow.min_cut",
    "modular": "math.algebra.modular_arithmetic",
    "more-prefix-sums": "data_structures.static_range.prefix_sums",
    "mst": "graphs.spanning.mst",
    "paths-grids": "dp.basics.grid",
    "prefix-sums": "data_structures.static_range.prefix_sums",
    "priority-queues": "data_structures.linear.heap",
    "range-sweep": "geometry.sweep.line_sweep",
    "rect-geo": "geometry.primitives.points",
    "segtree-ext": "data_structures.range_query.segment_tree",
    "shortest-paths": "graphs.shortest_path.dijkstra",
    "simulation": "adhoc.simulation.direct",
    "sliding-window": "data_structures.linear.sliding_window",
    "slope-trick": "dp.optimization.slope_trick",
    "sorting-custom": "greedy.exchange.sorting_order",
    "sqrt": "data_structures.sqrt.sqrt_decomposition",
    "stacks": "data_structures.linear.stack",
    "string-search": "strings.matching.kmp",
    "string-suffix": "strings.suffix_structures.suffix_array",
    "sweep-line": "geometry.sweep.line_sweep",
    "ternary-search": "math.numerical.ternary_search",
    "toposort": "graphs.traversal.topological_sort",
    "treaps": "data_structures.trees.treap",
    "tree-euler": "trees.basics.euler_tour",
    "two-pointers": "data_structures.linear.sliding_window",
    "unweighted-shortest-paths": "graphs.traversal.bfs",
}

# usaco.guide per-problem tag -> taxonomy leaf, used when the module names no
# technique. Same rule as everywhere else: a label naming a whole category
# ("DP", "Greedy", "Graphs", "Tree", "Strings", "Number Theory", "Casework",
# "Divide and Conquer") is refused, because collapsing a subtree to one of its
# leaves is a guess.
GUIDE_TAG_TAGS = {
    "2D Prefix Sums": "data_structures.static_range.prefix_sums",
    "BFS": "graphs.traversal.bfs",
    "Binary Search": "search.binary_search.on_answer",
    "Bitmasks": "dp.subset.subset_dp",
    "Bitset": "bitwise.techniques.bitset_optimization",
    "Centroid": "trees.decomposition.centroid",
    "Complete Search": "search.exhaustive.backtracking",
    "Connected Components": "graphs.traversal.connectivity",
    "Constructive": "adhoc.constructive.construction",
    "DFS": "graphs.traversal.dfs",
    "DSU": "data_structures.disjoint_set.dsu",
    "Euler Tour": "trees.basics.euler_tour",
    "Euler's Formula": "graphs.special_graphs.planar",
    "Flood Fill": "graphs.traversal.connectivity",
    "Functional Graph": "graphs.special_graphs.functional_graph",
    "HLD": "trees.decomposition.hld",
    "Hashing": "strings.hashing.polynomial_hash",
    "Inversions": "data_structures.range_query.fenwick",
    "Knapsack": "dp.basics.knapsack",
    "LCA": "trees.ancestors.lca",
    "Lazy SegTree": "data_structures.range_query.lazy_propagation",
    "Map": "data_structures.linear.hash_map",
    "Matrix": "dp.optimization.matrix_exponentiation",
    "Merging": "trees.decomposition.small_to_large",
    "Modular Arithmetic": "math.algebra.modular_arithmetic",
    "MST": "graphs.spanning.mst",
    "PURS": "data_structures.range_query.segment_tree",
    "Prefix Sums": "data_structures.static_range.prefix_sums",
    "Priority Queue": "data_structures.linear.heap",
    "Range DP": "dp.basics.interval",
    "Rectangle": "geometry.primitives.points",
    "Recursion": "search.exhaustive.backtracking",
    "SCC": "graphs.components.scc_tarjan",
    "SegTree": "data_structures.range_query.segment_tree",
    "Shortest Path": "graphs.shortest_path.dijkstra",
    "Simulation": "adhoc.simulation.direct",
    "Sliding Window": "data_structures.linear.sliding_window",
    "Sorted Set": "data_structures.trees.treap",
    "Sorting": "adhoc.simulation.sorting",
    "Sqrt": "data_structures.sqrt.sqrt_decomposition",
    "Stack": "data_structures.linear.stack",
    "Sweep Line": "geometry.sweep.line_sweep",
    "Two Pointers": "data_structures.linear.sliding_window",
}

# Ordered most specific first: a problem tagged both "DP" and "Knapsack" is a
# knapsack problem, and one tagged "Sorting" and "Binary Search" is decided by
# the search, not the sort.
GUIDE_TAG_PRIORITY = [
    "Bitmasks",
    "Knapsack",
    "Range DP",
    "Matrix",
    "Inversions",
    "HLD",
    "Centroid",
    "LCA",
    "Euler Tour",
    "SCC",
    "Functional Graph",
    "Euler's Formula",
    "MST",
    "Lazy SegTree",
    "SegTree",
    "PURS",
    "DSU",
    "Sqrt",
    "Bitset",
    "Merging",
    "Sorted Set",
    "Priority Queue",
    "Stack",
    "Map",
    "Hashing",
    "Sweep Line",
    "Rectangle",
    "Shortest Path",
    "Flood Fill",
    "Connected Components",
    "BFS",
    "DFS",
    "Modular Arithmetic",
    "Two Pointers",
    "Sliding Window",
    "2D Prefix Sums",
    "Prefix Sums",
    "Binary Search",
    "Complete Search",
    "Recursion",
    "Constructive",
    "Sorting",
    "Simulation",
]

# DMOJ category -> taxonomy leaf, only where the category names one technique.
# `graph-theory`, `dynamic-programming`, `data-structures`, `geometry`,
# `string-algorithms`, `simple-math` and the rest are category-level: they
# name a subtree, not a leaf, so they are not here.
DMOJ_TYPE_TAGS = {
    "implementation": "adhoc.simulation.direct",
    "simulation": "adhoc.simulation.direct",
    "brute-force": "search.exhaustive.backtracking",
    "constructive": "adhoc.constructive.construction",
    "interactive": "adhoc.constructive.interactive",
}


PROVENANCE_COARSE = "via-dmoj-category"

# Coarse fallback, applied only by `enrich --coarse` and only to rows nothing
# else resolved. Each category names a whole subtree, so these collapse it to
# one representative leaf. That is a approximation, not a classification: a
# problem tagged `graphs.traversal.dfs` this way is only known to be *a graph
# problem*. The distinct provenance exists so the whole set can be found and
# stripped in one pass.
COARSE_CATEGORY_TAGS = {
    "graph-theory": "graphs.traversal.dfs",
    "dynamic-programming": "dp.basics.linear",
    "data-structures": "data_structures.range_query.segment_tree",
    "geometry": "geometry.primitives.points",
    "string-algorithms": "strings.matching.kmp",
    "regular-expressions": "strings.matching.kmp",
    "game-theory": "game_theory.partisan.minimax_dp",
    "greedy-algorithms": "greedy.exchange.sorting_order",
    "divide-and-conquer": "search.binary_search.on_answer",
    "recursion": "search.exhaustive.backtracking",
    "brute-force": "search.exhaustive.backtracking",
    "constructive": "adhoc.constructive.construction",
    "interactive": "adhoc.constructive.interactive",
    "intermediate-math": "math.algebra.modular_arithmetic",
    "advanced-math": "math.algebra.modular_arithmetic",
    "simple-math": "adhoc.simulation.direct",
    "ad-hoc": "adhoc.simulation.direct",
    "simulation": "adhoc.simulation.direct",
    "implementation": "adhoc.simulation.direct",
}

# Most informative category first: a problem labelled both `implementation`
# and `graph-theory` is better described by the graph half.
COARSE_PRIORITY = [
    "graph-theory",
    "dynamic-programming",
    "data-structures",
    "geometry",
    "string-algorithms",
    "regular-expressions",
    "game-theory",
    "greedy-algorithms",
    "divide-and-conquer",
    "recursion",
    "brute-force",
    "constructive",
    "interactive",
    "advanced-math",
    "intermediate-math",
    "simple-math",
    "ad-hoc",
    "simulation",
    "implementation",
]

# Rows with no category at all. Mis-labelling these as simulation would be a
# claim; `unclassified` states the actual situation and stays countable.
COARSE_DEFAULT = "adhoc.unclassified"


def coarse_tag_for(row: dict) -> str | None:
    """A representative leaf for the row's broadest available category."""
    present = {t for t in csvio.split_list(row.get("free_tags", "")) if not t.startswith("via-")}
    for category in COARSE_PRIORITY:
        if category in present:
            return COARSE_CATEGORY_TAGS[category]
    return COARSE_DEFAULT


def _get(url: str, timeout: float = 30.0) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")


def fetch_guide(log: Callable[[str], None] | None = None) -> dict[str, dict]:
    """usaco.guide's classifications, as {uniqueId: {"mod": str, "tags": [str]}}."""
    tree = json.loads(_get(GUIDE_REPO))
    paths = [t["path"] for t in tree["tree"] if t["path"].endswith(".problems.json")]
    if log:
        log(f"  {len(paths)} module files")
    out: dict[str, dict] = {}
    for path in paths:
        try:
            doc = json.loads(_get(GUIDE_RAW + urllib.parse.quote(path)))
        except Exception:  # noqa: BLE001 - a missing module file is not fatal
            continue
        module = doc.get("MODULE_ID") or ""
        for key, entries in doc.items():
            if key == "MODULE_ID" or not isinstance(entries, list):
                continue
            for entry in entries:
                uid = entry.get("uniqueId")
                if not uid:
                    continue
                # The module a problem is first listed under is the one that
                # teaches it; later appearances are practice references.
                record = out.setdefault(uid, {"mod": module, "tags": []})
                for tag in entry.get("tags") or ():
                    if tag not in record["tags"]:
                        record["tags"].append(tag)
    return out


OJUZ_SLUG = re.compile(r"oj\.uz/problem/view/([A-Za-z]+)(\d{2})_([A-Za-z0-9]+)")
# usaco.guide spells its IOI ids three different ways -- `ioi-11-crocodile`,
# `IOI11_garden`, `ioi-phidias` -- so they are indexed by (two-digit year,
# name) with a name-only fallback rather than matched literally.
GUIDE_ALT_ID = re.compile(r"^(?:ioi|other)[-_]?(\d{2})?[-_]([a-z0-9]+)$", re.I)


def guide_alt_index(guide: dict[str, dict]) -> dict[tuple[str, str], dict]:
    """Index of guide records by (two-digit year, name), for non-USACO ids."""
    index: dict[tuple[str, str], dict] = {}
    for uid, record in guide.items():
        match = GUIDE_ALT_ID.match(uid)
        if not match:
            continue
        year = match.group(1) or ""
        name = match.group(2).lower()
        index.setdefault((year, name), record)
        index.setdefault(("", name), record)
    return index


def _tag_from_record(record: dict) -> str | None:
    tag = GUIDE_MODULE_TAGS.get(record.get("mod") or "")
    if tag:
        return tag
    present = set(record.get("tags") or ())
    for candidate in GUIDE_TAG_PRIORITY:
        if candidate in present:
            return GUIDE_TAG_TAGS[candidate]
    return None


def guide_tag_for_ojuz(row: dict, alt: dict[tuple[str, str], dict]) -> str | None:
    """The leaf usaco.guide implies for an oj.uz-hosted problem."""
    match = OJUZ_SLUG.search(row.get("url", ""))
    if not match:
        return None
    year, name = match.group(2), match.group(3).lower()
    record = alt.get((year, name)) or alt.get(("", name))
    return _tag_from_record(record) if record else None


def guide_tag_for(row: dict, guide: dict[str, dict]) -> str | None:
    """The leaf tag usaco.guide implies for a catalogue row, if any.

    The teaching module is the better signal, so it is tried first. Failing
    that -- the module may name a difficulty round-up rather than a technique
    -- the problem's own tags are consulted, most specific first.
    """
    match = CPID.search(row.get("url", ""))
    if not match:
        return None
    record = guide.get(f"usaco-{match.group(1)}")
    if not record:
        return None
    if isinstance(record, str):  # older cache shape
        record = {"mod": record, "tags": []}
    return _tag_from_record(record)


def dmoj_tag_for(row: dict) -> str | None:
    """The leaf tag DMOJ's categories imply, only when they are unambiguous."""
    types = [t for t in csvio.split_list(row.get("free_tags", "")) if not t.startswith("via-")]
    if len(types) != 1:
        return None
    return DMOJ_TYPE_TAGS.get(types[0])


def apply(
    rows: list[dict], guide: dict[str, dict], coarse: bool = False
) -> tuple[list[dict], dict[str, int]]:
    """Fill blank tags from the available sources. Never overwrites a tag.

    With `coarse`, any row the precise sources leave blank falls back to a
    representative leaf for its broadest category. See COARSE_CATEGORY_TAGS
    for what that does and does not mean.
    """
    stats = {"guide": 0, "dmoj": 0, "coarse": 0, "already": 0, "unresolved": 0}
    alt = guide_alt_index(guide)
    out = []
    for row in rows:
        row = dict(row)
        if row.get("primary_tag"):
            stats["already"] += 1
            out.append(row)
            continue

        tag = guide_tag_for(row, guide) or guide_tag_for_ojuz(row, alt)
        source = PROVENANCE_GUIDE
        if not tag:
            tag = dmoj_tag_for(row)
            source = PROVENANCE_DMOJ
        if not tag and coarse:
            tag = coarse_tag_for(row)
            source = PROVENANCE_COARSE
        if not tag:
            stats["unresolved"] += 1
            out.append(row)
            continue

        row["primary_tag"] = tag
        row["tags"] = tag
        free = [f for f in csvio.split_list(row.get("free_tags", "")) if f not in PROVENANCES]
        row["free_tags"] = csvio.join_list([*free, source])
        stats[{PROVENANCE_GUIDE: "guide", PROVENANCE_DMOJ: "dmoj"}.get(source, "coarse")] += 1
        out.append(row)
    return out, stats


def unknown_tags(taxonomy) -> list[str]:
    """Mapped tags that are not leaves of the current taxonomy."""
    bad = []
    for table in (GUIDE_MODULE_TAGS, GUIDE_TAG_TAGS, DMOJ_TYPE_TAGS, COARSE_CATEGORY_TAGS):
        for tag in sorted(set(table.values())):
            if not taxonomy.is_leaf(tag):
                bad.append(tag)
    return sorted(set(bad))
