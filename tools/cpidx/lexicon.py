"""Algorithm names as they appear in prose, mapped to taxonomy leaves.

Normative reference: SPEC.md 10.7.

Used to read a published editorial, or the repository's own solution code, and
recover which technique it names. Ordered most specific first, because an
editorial for a convex-hull-trick problem also says "dynamic programming", and
one about Dijkstra also says "graph".

Only distinctive names are listed. Words that merely describe a problem domain
("graph", "tree", "string") are absent: they name a category, and collapsing a
category to one of its leaves is the guess this whole design refuses to make.
"""

from __future__ import annotations

import re

# (regex, leaf). Order is priority order.
PHRASES: list[tuple[str, str]] = [
    # --- DP optimisations, the most distinctive names --------------------
    (r"convex hull trick|\bCHT\b|li ?chao", "dp.optimization.convex_hull_trick"),
    (r"divide and conquer optimi[sz]ation", "dp.optimization.divide_conquer_opt"),
    (r"knuth('s)? optimi[sz]ation|quadrangle inequality", "dp.optimization.knuth_opt"),
    (r"alien'?s trick|lagrangian relaxation|wqs binary search", "dp.optimization.aliens_trick"),
    (r"slope trick", "dp.optimization.slope_trick"),
    (r"matrix exponentiation|matrix power", "dp.optimization.matrix_exponentiation"),
    (r"digit dp", "dp.digit.digit_dp"),
    (r"sum over subsets|\bSOS dp\b|zeta transform", "dp.subset.sum_over_subsets"),
    (r"broken profile|plug dp", "dp.subset.broken_profile"),
    (r"bitmask dp|dp over (sub)?sets|bitmask", "dp.subset.subset_dp"),
    (r"reroot", "dp.tree.rerooting"),
    (r"knapsack", "dp.basics.knapsack"),
    (r"longest increasing subsequence|\bLIS\b", "dp.basics.lis"),
    (r"interval dp|range dp", "dp.basics.interval"),
    # --- trees ------------------------------------------------------------
    (r"small[ -]to[ -]large|dsu on tree", "trees.decomposition.small_to_large"),
    (r"heavy[ -]light|\bHLD\b", "trees.decomposition.hld"),
    (r"centroid decomposition", "trees.decomposition.centroid"),
    (r"binary lifting|jump pointer|binary jumping", "trees.ancestors.binary_lifting"),
    (r"lowest common ancestor|\bLCA\b", "trees.ancestors.lca"),
    (r"euler tour|tin\b.*tout", "trees.basics.euler_tour"),
    (r"diameter of the tree|tree diameter", "trees.basics.diameter"),
    # --- data structures ---------------------------------------------------
    (r"link[ -]cut tree", "data_structures.trees.link_cut"),
    (r"segment tree beats", "data_structures.range_query.segment_tree_beats"),
    (r"persistent segment tree|persistence", "data_structures.range_query.persistent"),
    (r"lazy propagation|lazy segment tree|lazily", "data_structures.range_query.lazy_propagation"),
    (r"merge sort tree|wavelet tree", "data_structures.range_query.merge_sort_tree"),
    (r"segment tree|segtree", "data_structures.range_query.segment_tree"),
    (r"fenwick|binary indexed tree|\bBIT\b", "data_structures.range_query.fenwick"),
    (r"sparse table", "data_structures.static_range.sparse_table"),
    (r"prefix sum|cumulative sum|difference array", "data_structures.static_range.prefix_sums"),
    (r"union[ -]?find|disjoint[ -]set|\bDSU\b", "data_structures.disjoint_set.dsu"),
    (r"mo'?s algorithm", "data_structures.offline.mos"),
    (
        r"sqrt decomposition|square root decomposition|block decomposition",
        "data_structures.sqrt.sqrt_decomposition",
    ),
    (r"monotonic stack|monotone stack|monotonic deque", "data_structures.linear.monotonic_stack"),
    (r"sliding window|two[ -]pointer", "data_structures.linear.sliding_window"),
    (r"priority queue|\bheap\b", "data_structures.linear.heap"),
    (
        r"\btreap\b|balanced (binary search )?tree|order statistic tree",
        "data_structures.trees.treap",
    ),
    # --- flows and matching -------------------------------------------------
    (r"min(imum)?[ -]cost (max(imum)?[ -])?flow", "flows.max_flow.min_cost_flow"),
    (r"min(imum)?[ -]cut|max[ -]?flow min[ -]?cut|project selection", "flows.max_flow.min_cut"),
    (r"max(imum)?[ -]flow|dinic|edmonds[ -]karp", "flows.max_flow.dinic"),
    (r"hungarian algorithm|assignment problem", "graphs.matching.hungarian"),
    (r"hopcroft", "graphs.matching.hopcroft_karp"),
    (r"bipartite matching|maximum matching|kuhn", "graphs.matching.bipartite_kuhn"),
    # --- graphs -------------------------------------------------------------
    (r"0-1 bfs|zero[ -]one bfs", "graphs.shortest_path.zero_one_bfs"),
    (r"dijkstra", "graphs.shortest_path.dijkstra"),
    (r"bellman[ -]ford|\bSPFA\b|negative cycle", "graphs.shortest_path.bellman_ford"),
    (r"floyd[ -]warshall|all[ -]pairs shortest", "graphs.shortest_path.floyd_warshall"),
    (r"topological (sort|order)", "graphs.traversal.topological_sort"),
    (r"strongly connected|\bSCC\b|tarjan", "graphs.components.scc_tarjan"),
    (r"articulation point|cut vertex", "graphs.components.articulation_points"),
    (r"\bbridges?\b(?! of)", "graphs.components.bridges"),
    (r"2-?sat", "graphs.components.two_sat"),
    (r"minimum spanning tree|\bMST\b|kruskal|prim'?s", "graphs.spanning.mst"),
    (r"functional graph|successor graph", "graphs.special_graphs.functional_graph"),
    (r"eulerian (path|circuit|tour)|hierholzer", "graphs.traversal.euler_tour"),
    (r"flood ?fill|connected component", "graphs.traversal.connectivity"),
    (r"breadth[ -]first|\bBFS\b", "graphs.traversal.bfs"),
    (r"depth[ -]first|\bDFS\b", "graphs.traversal.dfs"),
    # --- strings ------------------------------------------------------------
    (r"aho[ -]corasick", "strings.multi_pattern.aho_corasick"),
    (r"suffix automaton", "strings.suffix_structures.suffix_automaton"),
    (r"suffix array", "strings.suffix_structures.suffix_array"),
    (r"manacher", "strings.matching.manacher"),
    (r"\bKMP\b|prefix function|failure function", "strings.matching.kmp"),
    (r"z[ -]function|z[ -]algorithm", "strings.matching.z_function"),
    (r"\btrie\b", "strings.multi_pattern.trie"),
    (r"polynomial hash|string hash|rolling hash|rabin[ -]karp", "strings.hashing.polynomial_hash"),
    # --- geometry -----------------------------------------------------------
    (r"convex hull", "geometry.convexity.convex_hull"),
    (r"rotating calipers", "geometry.convexity.rotating_calipers"),
    (r"sweep ?line|line sweep|sweeping", "geometry.sweep.line_sweep"),
    (r"closest pair", "geometry.sweep.closest_pair"),
    # --- maths --------------------------------------------------------------
    (r"inclusion[ -]exclusion", "combinatorics.inclusion_exclusion.pie"),
    (r"burnside|polya", "combinatorics.inclusion_exclusion.burnside"),
    (r"binomial coefficient|\bn choose k\b|pascal", "combinatorics.basics.binomials"),
    (r"catalan", "combinatorics.basics.catalan"),
    (r"m[oö]bius", "number_theory.divisibility.mobius_inversion"),
    (r"chinese remainder|\bCRT\b", "number_theory.divisibility.crt"),
    (r"sieve of eratosthenes|\bsieve\b", "number_theory.primes.sieve"),
    (r"\bgcd\b|euclidean algorithm", "number_theory.divisibility.gcd"),
    (r"\bFFT\b|\bNTT\b|fast fourier", "math.algebra.polynomials"),
    (r"gaussian elimination|linear system", "math.algebra.linear_algebra"),
    (r"modular inverse|modular arithmetic|fermat'?s little", "math.algebra.modular_arithmetic"),
    (r"ternary search", "math.numerical.ternary_search"),
    # --- bitwise, games, search --------------------------------------------
    (r"linear basis|xor basis", "bitwise.structures.linear_basis"),
    (r"binary trie|xor trie", "bitwise.structures.trie_xor"),
    (r"bitset", "bitwise.techniques.bitset_optimization"),
    (r"gray code", "bitwise.techniques.gray_code"),
    (r"grundy|sprague", "game_theory.impartial.sprague_grundy"),
    (r"\bnim\b", "game_theory.impartial.nim"),
    (r"meet in the middle", "search.exhaustive.meet_in_middle"),
    (r"binary search", "search.binary_search.on_answer"),
    (r"brute[ -]force|complete search|try (all|every)|backtrack", "search.exhaustive.backtracking"),
    (r"greedy|greedily|exchange argument", "greedy.exchange.sorting_order"),
    (r"simulat", "adhoc.simulation.direct"),
    (r"\bsort(ing|ed)?\b", "adhoc.simulation.sorting"),
]

COMPILED: list[tuple[re.Pattern, str]] = [(re.compile(p, re.I), tag) for p, tag in PHRASES]

# Identifiers that betray a technique in source code, where prose words do not
# appear. Applied to the repository's own solutions.
CODE_HINTS: list[tuple[str, str]] = [
    (r"\bpriority_queue\b.*\bdist\b|\bdijkstra\b", "graphs.shortest_path.dijkstra"),
    (
        r"\bfind\s*\(\s*\w+\s*\).*\bunion\b|\bdsu\b|\bdisjoint\b|par\[.*\]\s*=\s*find",
        "data_structures.disjoint_set.dsu",
    ),
    (
        r"\bsegtree\b|\bsegment_tree\b|\bbuild\s*\(.*node",
        "data_structures.range_query.segment_tree",
    ),
    (r"\bfenwick\b|\bbit\[\b|\blowbit\b", "data_structures.range_query.fenwick"),
    (r"\blca\b|\bup\[\w+\]\[\w+\]", "trees.ancestors.binary_lifting"),
    (r"\bmanacher\b", "strings.matching.manacher"),
    (r"\bkmp\b|\bpi\[\b|\bfail\[\b", "strings.matching.kmp"),
    (r"\btrie\b", "strings.multi_pattern.trie"),
    (r"\bbitset<", "bitwise.techniques.bitset_optimization"),
    (r"\bqueue<.*>\s*q\b|\bbfs\b", "graphs.traversal.bfs"),
    (r"\bdfs\b", "graphs.traversal.dfs"),
    (r"\b__gcd\b|\bgcd\s*\(", "number_theory.divisibility.gcd"),
    (r"\bnext_permutation\b", "search.exhaustive.backtracking"),
    (r"\bsort\s*\(", "adhoc.simulation.sorting"),
]

COMPILED_CODE: list[tuple[re.Pattern, str]] = [
    (re.compile(p, re.I | re.S), t) for p, t in CODE_HINTS
]


def classify_prose(text: str) -> str | None:
    """The most specific technique named in a piece of prose."""
    for pattern, tag in COMPILED:
        if pattern.search(text):
            return tag
    return None


def classify_code(source: str) -> str | None:
    """The most specific technique a solution's source betrays."""
    for pattern, tag in COMPILED_CODE:
        if pattern.search(source):
            return tag
    return None


def targets() -> set[str]:
    return {tag for _, tag in PHRASES} | {tag for _, tag in CODE_HINTS}
