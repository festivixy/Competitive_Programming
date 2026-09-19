# Competitive Programming Problem Index — Specification

**Status:** v0.2 (implemented)
**Owner:** festivixy

> Clauses amended during implementation are marked **[amended]** and are listed
> with their rationale in [section 15](#15-implementation-deviations).

---

## 1. Purpose

A curated, tag-indexed catalogue of competitive programming problems drawn from multiple judges and contests, structured so that a query of the form *"give me problems that test technique X, at difficulty Y, that I have not solved"* returns a useful, ordered answer.

The index stores **metadata and links only**. Problem statements, test data, and submission handling remain on the originating judges.

### 1.1 Goals

| # | Goal | Success criterion |
|---|---|---|
| G1 | Retrieve problems by technique | Any leaf node in the taxonomy resolves to a difficulty-ordered list of problems |
| G2 | Consistent classification | The same technique is always named the same way; a validator rejects unknown tags |
| G3 | Difficulty comparable across judges | A DMOJ 10-point problem and a USACO Gold problem sit on one shared scale |
| G4 | Survive link rot | Every record carries a last-verified date and supports multiple hosts |
| G5 | Split personal from public | Solve history is separable from the shared index without restructuring |

### 1.2 Non-goals

- Rehosting statements, test data, or official editorials.
- Judging, running, or verifying submissions.
- Auto-classification by machine. Tagging is a manual curatorial act; tooling may *suggest*, never *decide*.
- Being exhaustive. Coverage of a technique matters more than coverage of a judge.

---

## 2. Data model overview

Three artefacts, three different rates of change:

```
taxonomy.yaml     the controlled vocabulary          changes rarely
problems.csv      the curated index, every row tagged grows by curation
catalogue.csv     every problem a judge publishes    grows by `cpidx fetch`
progress.csv      personal solve history             changes daily, private
```

`catalogue.csv` is an addition to v0.1, described in section 10.6. It holds the
same 22 columns but carries no taxonomy tag: it is the pool that curation draws
from, so that "which CCC problems exist" is a question the tooling can answer
without anyone having classified them first.

`problems.csv` references `taxonomy.yaml` by tag id. `progress.csv` references `problems.csv` by problem id. Neither reference runs the other way, so the public index can be published without touching the other two.

---

## 3. Repository layout **[amended]**

This index lives inside an existing solutions repository of roughly 850 source
files, organised by origin and contest rather than by problem id. The index
therefore sits at the repository root and does **not** require those files to
move:

```
.
├── SPEC.md
├── taxonomy.yaml
├── problems.csv
├── progress.csv                (gitignored)
├── CCC/  CCO/  CSES/  IOI/  USACO/  ...   existing solutions, untouched
├── notes/
│   └── ccc-2021-s4.md
├── tools/
│   ├── cpidx/
│   ├── tests/
│   └── pyproject.toml
├── build/                      (gitignored, generated)
│   ├── problems.xlsx
│   ├── import-candidates.csv
│   └── by-tag/
└── .github/workflows/validate.yml
```

`notes/` is keyed by problem id, so the link between a row and its prose is
positional, not stored in a column. Existing solution directories keep their
own conventions; `cpidx import-tree` bridges them to problem ids and records
the mapping in the staging file's `_source_paths` column.

---

## 4. Identity scheme

### 4.1 The `id` field **[amended]**

Canonical form: lowercase slug segments joined by hyphens.

```
<origin-prefix>-<year>-<label>
```

Regex: `^[a-z0-9]+(-[a-z0-9]+)*$`

The regex is the only hard constraint. The shape above is a convention with
deliberate exceptions: the leading segment is an origin *prefix* rather than
the origin enum value (`codeforces` → `cf`), the second segment is a contest
number rather than a year for judges organised that way, and the year is
omitted entirely for judges with no contest structure. The origin is therefore
**not** recoverable from the id; read the `origin` column.

| Problem | id |
|---|---|
| CCC 2021 Senior Problem 4 | `ccc-2021-s4` |
| IOI 2019 Day 1 Problem 2 "Split" | `ioi-2019-d1p2` |
| USACO 2020 December Gold Problem 1 | `usaco-2020-dec-gold-1` |
| Codeforces Round 733 Div1 D | `cf-1530-f` |
| DMOJ original problem "Tudor's Nightmare" | `dmoj-tudorsnightmare` |

Validation rule 26 warns when a leading segment matches no known origin prefix.

### 4.2 Origin versus host

**Origin** is who authored the problem. **Host** is where you can submit it. They are frequently different, and one origin may have several hosts.

```
origin: ioi
hosts:  oj.uz | ioi-official
```

The id is keyed on origin because origin is permanent and hosts are not. When a mirror dies, you edit the `hosts` and `url` fields; the id, and therefore every note, solution, and progress row pointing at it, stays valid.

---

## 5. `problems.csv` schema

One row per problem. Column order is fixed and enforced by the formatter.

| # | Column | Type | Required | Notes |
|---|---|---|---|---|
| 1 | `id` | slug | yes | Primary key, unique, §4.1 |
| 2 | `title` | string | yes | Problem title as published |
| 3 | `origin` | enum | yes | §5.1 |
| 4 | `contest` | string | no | Human-readable, e.g. `CCC 2021 Senior` |
| 5 | `year` | int | no | 4-digit; blank for timeless problems |
| 6 | `label` | string | no | Position within contest, e.g. `S4`, `Day 1 P2`, `Div2 E` |
| 7 | `hosts` | list | yes | Pipe-delimited judge slugs, §5.2 |
| 8 | `url` | url | yes | Canonical submit link (first entry of `hosts`) |
| 9 | `mirror_urls` | list | no | Pipe-delimited, aligned with remaining `hosts` |
| 10 | `format` | enum | yes | §5.3, defaults to `standard` |
| 11 | `difficulty` | int 1–10 | yes | Normalized tier, §6 |
| 12 | `difficulty_basis` | enum | yes | `official`, `community`, `estimated` |
| 13 | `difficulty_native` | string | no | Raw value from the judge, e.g. `DMOJ 15p`, `CF 2400`, `Gold` |
| 14 | `primary_tag` | tag path | yes | The single technique this problem is *for*, §7 |
| 15 | `tags` | list | yes | Pipe-delimited tag paths; must contain `primary_tag` |
| 16 | `free_tags` | list | no | Uncontrolled vocabulary, §7.5 |
| 17 | `quality` | int 1–5 | no | Curatorial rating, §5.4 |
| 18 | `canonical` | bool | no | `true` if this is *the* problem to learn `primary_tag` from |
| 19 | `constraints` | string | no | Key bound driving the intended complexity, e.g. `n<=2e5` |
| 20 | `editorial_url` | url | no | Official editorial, when one exists publicly |
| 21 | `added` | date | yes | ISO 8601, `YYYY-MM-DD` |
| 22 | `verified` | date | yes | Date the `url` was last confirmed live |

### 5.1 `origin` enum **[amended]**

```
ioi ceoi apio egoi ioi-practice
ccc cco woburn dmoj dmopc bsspc
usaco usaco-training
noi noi-cn coci poi zco inoi boi
icpc icpc-wf icpc-regional
codeforces atcoder topcoder codechef leetcode
gcj kickstart meta-hacker-cup
projecteuler library-checker cses
```

Adding an origin requires adding it here. An unrecognized origin is a validation error, not a warning.

### 5.2 `hosts` enum

```
dmoj oj.uz codeforces atcoder codechef
usaco-official ioi-official cses acmp
vjudge szkopul eolymp library-checker leetcode
```

### 5.3 `format` enum

Problem format is orthogonal to technique and therefore a column, not a tag.

| Value | Meaning |
|---|---|
| `standard` | Read input, write output, all-or-nothing per test |
| `subtask` | Partial scoring by subtask (IOI, CEOI, APIO) |
| `interactive` | Program converses with a grader |
| `output_only` | Submit answers, not source |
| `optimization` | Scored on solution quality, no exact answer |
| `communication` | Two programs, restricted channel between them |

### 5.4 `quality` scale

This rates the problem's value as a *teaching instrument* for its `primary_tag`, not its beauty.

| Value | Meaning |
|---|---|
| 5 | Isolates the technique cleanly; solving it means you understand the technique |
| 4 | Good drill, some incidental difficulty |
| 3 | Serviceable |
| 2 | Technique present but buried under implementation or a second idea |
| 1 | Included for completeness; do not recommend |

Blank means unrated. Only rate problems you have solved.

Note that this makes `quality` a public column fillable only from private
information, since solve status lives in `progress.csv`. That is a known and
accepted leak in the G5 split.

### 5.5 File format rules

- UTF-8, no BOM, LF line endings.
- RFC 4180 quoting. Fields containing `,`, `"`, or newline are double-quoted.
- Header row required, exactly the 22 names above in order.
- Rows sorted by `id` ascending, byte order.
- List fields use `|` with no surrounding whitespace.
- Empty optional fields are the empty string, never `NULL` or `N/A`.

The sort requirement exists so that two people adding problems on different branches produce diffs that git can merge by line rather than by conflict.

---

## 6. Difficulty normalization

### 6.1 The scale

`difficulty` is an integer tier from 1 to 10. Tiers are anchored to observable outcomes rather than to any single judge's number, because judge scales are not linear with respect to one another.

| Tier | Anchor |
|---|---|
| 1 | Pure implementation, no algorithmic idea |
| 2 | Single standard technique, directly signposted |
| 3 | Single standard technique requiring recognition |
| 4 | Two standard techniques composed, or one with a twist |
| 5 | Non-obvious reduction to a standard technique |
| 6 | Requires a genuine observation before any standard technique applies |
| 7 | Multiple non-obvious observations, or heavy implementation on top of an idea |
| 8 | Solved by a minority of strong contestants under contest conditions |
| 9 | Solved by a handful; typically the hardest problem in a national olympiad |
| 10 | Near-unsolved at the contest it appeared in |

### 6.2 Seed mapping table **[amended]**

Starting estimates for `difficulty` when `difficulty_basis` is `estimated`. These are anchors, not rules; override by judgement and set the basis accordingly.

**Precedence.** A problem frequently matches both an origin row and a host
points row — a CCC S4 hosted on DMOJ at 12 points matches both. **The origin
row wins.** Points are host-local and can be re-scored by the host; origin is
the permanent fact, which is why §4.2 keys the id on it.

| Origin | Native | Tier |
|---|---|---|
| Codeforces | <1200 | 1–2 |
| Codeforces | 1200–1600 | 3 |
| Codeforces | 1700–1900 | 4 |
| Codeforces | 2000–2200 | 5 |
| Codeforces | 2300–2500 | 6–7 |
| Codeforces | 2600–2900 | 8 |
| Codeforces | 3000+ | 9–10 |
| CCC | Junior J1–J3 | 1 |
| CCC | Junior J4–J5, Senior S1 | 2 |
| CCC | Senior S2 | 3 |
| CCC | Senior S3 | 4–5 |
| CCC | Senior S4 | 6–7 |
| CCC | Senior S5 | 7–8 |
| CCO | Day problem 1 | 6 |
| CCO | Day problem 2–3 | 7–9 |
| USACO | Bronze | 1–2 |
| USACO | Silver | 3–4 |
| USACO | Gold | 5–6 |
| USACO | Platinum | 7–9 |
| IOI/APIO/CEOI | Day problem 1 | 6–7 |
| IOI/APIO/CEOI | Day problem 2–3 | 7–10 |
| DMOJ | Points 1–5 | 1–2 |
| DMOJ | Points 7–10 | 3–4 |
| DMOJ | Points 12–17 | 5–6 |
| DMOJ | Points 20+ | 7+ |

### 6.3 Drift control

Tier assignments made early will skew relative to later ones as your own level moves. Mitigation: `difficulty_basis` records where the number came from, and a recalibration pass re-examines all `estimated` rows for a given origin whenever that origin gains 25 new rows.

---

## 7. Taxonomy

### 7.1 Structure

A tree of technique nodes stored in `taxonomy.yaml`. Problems are tagged with **leaf nodes only**; membership in ancestor categories is derived, never stored.

Tag paths are dotted and lowercase:

```
graphs.shortest_path.zero_one_bfs
dp.subset.sum_over_subsets
bitwise.basics.operators
```

Maximum depth is 4. A deeper node means the intermediate level is doing no discriminating work and should be collapsed.

### 7.2 Node schema

```yaml
- id: graphs.shortest_path.zero_one_bfs
  name: 0-1 BFS
  aliases: [01 bfs, zero-one bfs, deque bfs]
  status: canonical
  prerequisites:
    - graphs.traversal.bfs
    - data_structures.linear.deque
  description: >
    Shortest paths on a graph whose edge weights are all 0 or 1,
    using a deque in place of a priority queue for O(V+E).
  discriminator: >
    Use when weights are exactly {0,1} and Dijkstra's log factor
    is the bottleneck, or when the 0-1 structure is created by a
    reduction rather than given.
```

| Field | Required | Purpose |
|---|---|---|
| `id` | yes | Dotted path, unique |
| `name` | yes | Display name |
| `aliases` | no | Search synonyms; also used by the validator to catch near-miss tags |
| `status` | yes | `canonical`, `deprecated`, or `provisional` |
| `replaced_by` | if deprecated | Target id for migration |
| `prerequisites` | no | Other node ids; forms a DAG independent of the tree |
| `description` | yes | What the technique is |
| `discriminator` | leaves only | When to reach for this over its siblings |

`discriminator` is the field that makes the taxonomy useful for learning rather than merely for filing. A tag that cannot be distinguished from its siblings in one sentence is a tag that will be applied inconsistently.

### 7.3 Prerequisites as a DAG

The tree encodes *kinship*; prerequisites encode *learning order*. These are different relations. Sum over subsets DP sits under `dp` in the tree, but its prerequisites are `bitwise.masks.subset_enumeration` and `dp.basics.subset_dp`, which live elsewhere. Keeping them separate lets a query answer "what should I learn before attempting this" without contorting the tree.

Prerequisites must form a DAG. A cycle is a validation error.

### 7.4 Top-level categories

```
math
number_theory
combinatorics
geometry
graphs
trees
flows
dp
data_structures
strings
greedy
search
bitwise
game_theory
optimization
randomized
adhoc
```

`taxonomy.yaml` ships as the normative version; the expansion beneath these
categories is defined there, not here.

### 7.5 Free tags

`free_tags` is an escape hatch for properties that are real but not techniques: `nice-problem`, `heavy-implementation`, `precision-sensitive`, `tricky-constraints`, `needs-fast-io`, `multi-test`.

Governance: when a free tag appears on 10 or more problems, it is reviewed for promotion into the taxonomy or into a dedicated column. Free tags are never a substitute for a missing technique tag; if the technique is absent from the tree, the correct action is to add it to the tree.

### 7.6 Evolution **[amended]**

Tags are never deleted. To retire one:

1. Set `status: deprecated` and populate `replaced_by`.
2. Run `cpidx migrate-tags`, which rewrites affected rows in `problems.csv`.
3. The deprecated node remains in the file permanently so old links and notes resolve.

**Promoting a leaf to a parent** is the other breaking edit, and the spec
originally had no procedure for it. Giving children to a node that problems
already tag invalidates every one of those rows at once, because rule 7 rejects
non-leaf tags. The procedure is:

1. Add the new children.
2. Re-tag every affected row onto a child. `cpidx validate` names them, since
   each becomes a rule 7 error.
3. Do not deprecate the old node; it is now a legitimate interior node.

There is deliberately no automatic migration here: choosing which child a
problem belongs to is a classification decision, and §1.2 forbids the tooling
from making those.

---

## 8. `progress.csv` schema

Private. Gitignored. Joined to `problems.csv` on `id`.

| # | Column | Type | Notes |
|---|---|---|---|
| 1 | `id` | slug | Foreign key; must exist in `problems.csv` |
| 2 | `status` | enum | §8.1 |
| 3 | `attempts` | int | Distinct sittings, not submissions |
| 4 | `first_attempt` | date | |
| 5 | `resolved` | date | Date of the terminal status |
| 6 | `minutes` | int | Total time spent thinking and coding |
| 7 | `confidence` | int 1–5 | Could you redo this cold today? |
| 8 | `failure_mode` | enum | §8.2, blank if solved unaided |
| 9 | `next_review` | date | §8.3 |

### 8.1 `status` enum

| Value | Meaning |
|---|---|
| `untouched` | In the index, never opened |
| `read` | Read, not attempted |
| `attempting` | In progress |
| `solved` | Solved with no external input |
| `solved_hint` | Solved after a nudge short of the full solution |
| `solved_editorial` | Read the editorial, then implemented |
| `abandoned` | Stopped without solving |

### 8.2 `failure_mode` enum

This column is the one that turns the index into a diagnostic instrument. Recording *why* you failed is what makes tag-level aggregation meaningful.

| Value | Meaning |
|---|---|
| `no_idea` | Never found the key observation |
| `wrong_technique` | Recognized a technique, but the wrong one |
| `knew_unknown` | Right technique identified, did not know it |
| `implementation` | Right idea, could not implement it correctly |
| `complexity` | Correct but too slow |
| `edge_case` | Correct approach, failed on boundaries |
| `misread` | Misunderstood the statement |

`knew_unknown` aggregated by `primary_tag` produces a study list. `implementation` aggregated by tag produces a drill list. These are different remedies for different problems, which is why one `solved` boolean is insufficient.

### 8.3 Review scheduling

Out of scope for v1. The `next_review` column is reserved so that adding it later requires no migration.

---

## 9. Validation

`cpidx validate` exits nonzero on any fatal rule below. CI runs it on every push.
Rule numbers are stable and are cited in the tool's output.

**Structural**
1. Header row does not match the canonical column list exactly.
2. Row has wrong field count.
3. File is not sorted by `id`.
4. Duplicate `id`.
5. `id` fails the slug regex.

**Referential**
6. `primary_tag` or any entry in `tags` is absent from `taxonomy.yaml`.
7. A tag resolves to a non-leaf node.
8. A tag resolves to a `deprecated` node.
9. `primary_tag` is not present in `tags`.
10. `progress.csv` references an `id` absent from `problems.csv`. **Local only** — `progress.csv` is gitignored, so this rule cannot run in CI. `validate` reports it as skipped rather than passing silently.

**Domain**
11. `origin` or any `hosts` entry outside the enum.
12. `format`, `difficulty_basis`, `canonical`, `status` or `failure_mode` outside its enum.
13. `difficulty` outside $[1,10]$; `quality` or `confidence` outside $[1,5]$; negative counts.
14. `year` outside $[1990, \text{current year}]$.
15. `verified` earlier than `added`, or either not an ISO date.
16. **[amended]** `mirror_urls` non-empty and $|\text{mirror\_urls}| \neq |\text{hosts}| - 1$. An empty `mirror_urls` is always legal, matching its "Required: no" in §5.

**Taxonomy**
17. Prerequisite graph contains a cycle, or names an unknown node.
18. Node depth exceeds 4, or a parent node is undefined.
19. Leaf node missing `discriminator`.
20. Deprecated node missing `replaced_by`, or `status` outside its enum.

**Warnings** (non-fatal, reported)
21. `verified` more than 365 days old.
22. Free tag appearing on 10+ problems.
23. Tag with fewer than 3 problems and no `canonical` entry.
24. `free_tags` entry within edit distance 2 of an existing canonical `alias`.

**Additions** (not in the original spec)
25. A required field is empty. **Fatal.** The original rule set checked field
    *values* but never their presence, so a row with a blank `primary_tag`
    passed every rule.
26. An `id`'s leading segment matches no known origin prefix. **Warning**, not
    an error, because §4.1 permits ids that do not encode their origin.

---

## 10. Tooling

A Python package in `tools/`, installed as `cpidx`.

### 10.1 Commands

```
cpidx add <url>
cpidx validate [--strict]
cpidx fmt [--check]
cpidx query [filters]
cpidx export --format {xlsx,json,md}
cpidx linkcheck [--max-age 365] [--offline] [--stale-only]
cpidx stats [--by tag|origin|difficulty|category] [--gaps]
cpidx migrate-tags [--dry-run]
cpidx import-tree [--source DIR] [--promote]     # addition, §10.5
```

### 10.2 `add`

```
$ cpidx add https://dmoj.ca/problem/ccc21s4
  id                 ccc-2021-s4    [detected]
  origin             ccc            [detected]
  year               2021           [detected]
  label              S4             [detected]
  hosts              dmoj           [detected]
  difficulty         ?
  primary_tag        ?
  tags               ?

not written: difficulty, difficulty_basis, primary_tag, tags, title still
needed. Classification is never inferred (SPEC.md 1.2); supply them with
--set field=value.
```

Detection is best-effort from URL patterns. Everything classificatory is
supplied explicitly, never inferred, and the row is not written until it would
pass validation. Patterns recognized: DMOJ (CCC, CCO, originals), Codeforces,
USACO, oj.uz (IOI/APIO/CEOI), CSES.

### 10.3 `query`

```
cpidx query --tag graphs.shortest_path.zero_one_bfs \
            --difficulty 4-6 \
            --status untouched \
            --min-quality 4 \
            --sort difficulty \
            --limit 10
```

| Flag | Behaviour |
|---|---|
| `--tag` | Matches the node and all descendants |
| `--tag-exact` | Matches the node only |
| `--primary` | Matches `primary_tag` only |
| `--difficulty`, `--quality`, `--year` | Single value or inclusive range (`4-6`, `-6`, `4-`) |
| `--origin`, `--format` | Repeatable enum filters |
| `--status` | Reads `progress.csv`; absent rows count as `untouched` |
| `--canonical` | Only rows flagged `canonical` |
| `--missing-prereqs` | Problems whose `primary_tag` has unmet prerequisites given your progress |
| `--ready` | The inverse: prerequisites all demonstrated |
| `--sort` | `difficulty`, `quality`, `year`, `random`, `id` |
| `--limit`, `--ids-only` | Output shaping |

`--ready --status untouched` gives the drill list: techniques whose prerequisites you have demonstrated, which you have not yet attempted.

### 10.4 `export --format xlsx`

Generates `build/problems.xlsx`:

- Sheet `All`: every row, frozen header, autofilter on all columns.
- One sheet per top-level taxonomy category, containing problems whose `primary_tag` descends from it.
- Sheet `Coverage`: matrix of leaf tags against difficulty tiers, cells holding problem counts, conditionally formatted so gaps in coverage are visible.
- Sheet `Taxonomy`: flattened tree with descriptions and discriminators.

The XLSX is a generated artefact. It is never edited and never committed.

### 10.5 `fetch` (addition)

Pulls complete problem lists from the judges into `catalogue.csv`, never into
`problems.csv`.

```
cpidx fetch [--source ccc|cco|usaco]
```

| Source | Via | Coverage |
|---|---|---|
| CCC | DMOJ's JSON API | 262 problems, 1996-2026 |
| CCO | DMOJ's JSON API | 185 problems, 1996-2026 |
| USACO | usaco.org contest result pages | 518 problems, 2014-2025 |

USACO result pages before 2014 exist but contain no problem links, so those
contests are not reachable from the site and are not in the catalogue.

A catalogue row carries everything the judge owns — title, canonical URL,
contest position, native difficulty — plus a `difficulty` seeded from the
section 6.2 table, and DMOJ's own category strings in `free_tags`, which is the
uncontrolled vocabulary section 7.5 provides for exactly this. It carries no
`primary_tag` and no `tags`.

Re-running `fetch` is safe: it refreshes only the fields the judge owns, fills a
blank difficulty, leaves every curatorial column alone, and drops any row that
has since been tagged into `problems.csv`.

### 10.6 `import-tree` (addition)

Walks an existing solutions tree and derives **candidate** rows into
`build/import-candidates.csv`. It never writes to `problems.csv`.

Each candidate carries three extra columns: `_confidence` (`high`, `medium`,
`low`), `_needs` (the fields still missing), and `_source_paths` (the files it
was derived from). Rows whose `_needs` is empty can be moved into the index
with `--promote`; everything else waits for a human.

The staging step exists because this tree is not consistently named.
`CCC/S/21/21s4.cpp` and `CCC/S/21/dailycommute.cpp` are the same problem under
two conventions and nothing in either path says so, which is exactly the kind
of judgement §1.2 reserves for a person.

---

## 11. Public release

The index is published at `website/index.html`, built by
`python website/build-index.py` from `problems.csv`, `catalogue.csv` and
`taxonomy.yaml`. That page replaced the editorial CMS landing page and carries
its links, its sign-in markup and its deep-link redirect shim, so nothing behind
it became unreachable.

**The public build strips solve status.** `progress.csv` is private by section
3 and GitHub Pages is not, so the site build omits the column, the filter and
the figure. Only `build-index.py --private PATH` includes them.

Remaining public-release work, constrained now so that it requires no
restructuring:

1. `problems.csv`, `taxonomy.yaml`, and `notes/` are public by construction; `progress.csv` is not.
2. Contribution gate: `cpidx validate --strict` passing in CI, plus one human review of tag assignment.
3. `CONTRIBUTING.md` will require a `discriminator` for any newly proposed leaf, since the absence of that field is the mechanism by which taxonomies rot.
4. Browsable output: `cpidx export --format md` emits `build/by-tag/<path>.md`, servable by any static site generator.

---

## 12. Milestones

| M | Deliverable | Done when | Status |
|---|---|---|---|
| M0 | Schema and taxonomy frozen at v0 | `taxonomy.yaml` covers the top-level categories to leaf depth for `graphs`, `dp`, `data_structures` | **done** — 233 nodes, 160 leaves, all discriminated |
| M1 | 50 problems entered by hand | `problems.csv` has 50 valid rows spanning 4+ origins | **done** — 142 rows across cses, ioi, usaco, ccc |
| M2 | `validate` and `fmt` | CI blocks an invalid push | **done** — 26 rules, 115 tests |
| M3 | `add` with URL detection | DMOJ, Codeforces, USACO, oj.uz patterns recognized | **done** — plus CSES |
| M4 | `query` | §10.3 flags implemented against both CSVs | **done** |
| M5 | `export --format xlsx` | Coverage sheet renders | **done** — plus json and md |
| M6 | 250 problems, recalibration pass | Difficulty tiers reviewed per §6.3 | open |

M1 preceded M2 deliberately. Note that the ordering argument changes in a
repository that already holds ~850 solutions: `cpidx import-tree` discovers
schema problems against ten origins at once, far faster than hand entry does.

---

## 13. Rejected alternatives

**YAML file per problem.** Better for multi-line fields and conflict-free merges, worse for the thing you asked for: it is not a spreadsheet, and bulk edits across 300 files require tooling that a CSV gets from Excel for free. Reconsider if concurrent public contribution makes per-row merge conflicts common.

**SQLite as source of truth.** Better queries, but a binary blob in git has no meaningful diff and no hand-editability. *Implementation note:* the spec suggested `query` would load the CSV into an in-memory SQLite table. It does not — both the tag filter and the prerequisite filter work over pipe-delimited list fields and a tree closure, neither of which SQL expresses without exploding the rows or round-tripping through Python regardless.

**Flat tag vocabulary.** Simpler to validate, but "show me all graph problems" then requires a hand-maintained category mapping, which is a tree wearing a disguise.

**Multi-axis tagging** (separate algorithm / data structure / trick / archetype columns). Richer queries, roughly triple the tagging effort per problem. The tree with free tags approximates it; if `free_tags` converges on a stable set of archetype labels, promoting that axis to a column is a small migration.

**Storing derived ancestor tags in each row.** Would make naive grep faster, at the cost of every taxonomy edit rewriting large parts of the CSV. `export --format json` computes them at export time instead.

---

## 14. Open questions

1. **Multi-technique problems.** A problem needing both SOS DP and a linear basis has one `primary_tag` by fiat. Does `quality` then mean quality-for-the-primary-tag only? Current answer is yes, which understates such problems in sibling queries. A single nullable `secondary_tag` column would dissolve this at almost no tagging cost, and is the cheapest thing to try first.
2. **Problem series.** USACO training pages and CSES sections are pedagogically ordered sets. There is no column expressing "do this after that one" within an origin.
3. **Language and availability.** Szkopuł, acm.timus, and Chinese OI sites carry statements in languages that gate access. A `statement_lang` column may be warranted.
4. **Contest-versus-practice difficulty.** Tier anchors in §6.1 mix both framings. The USACO Platinum tiers in particular read differently under contest conditions than in untimed practice.
5. **Seeding `progress.csv`.** There is no command for it. The initial file was derived from which solution files exist on disk, which conflates "a file exists" with "solved". A `cpidx import-tree --progress` mode would make that derivation repeatable and explicit about the assumption.

---

## 15. Implementation deviations

Every difference between v0.1 and the built system, with rationale.

| § | Change | Why |
|---|---|---|
| 3 | Layout does not relocate existing solutions | The spec's `solutions/<id>/main.cpp` would require restructuring ~850 files that are already organised by origin and contest. `import-tree` bridges the two instead. |
| 4.1 | Id documented as convention, not derivation | The spec's own examples (`cf-1530-f`, `dmoj-tudorsnightmare`) contradict the stated `<origin>-<year>-<label>` shape. The regex is the real constraint; rule 26 warns on unknown prefixes. |
| 5.1 | Added `cses`, `boi`, `dmopc`, `bsspc`, `leetcode` | `cses` was listed as a host but not an origin, leaving the largest body of problems in this repository with no legal origin value. |
| 6.2 | Added a precedence rule: origin beats host points | The spec's own `add` example suggests tier 5 for CCC 2021 S4 via DMOJ's 15 points, while its CCC row says 6–7. Both rules matched; nothing said which won. |
| 7.6 | Added a leaf-promotion procedure | Deprecation was covered; giving children to a tagged leaf was not, and it invalidates every row tagging that leaf at once via rule 7. |
| 9.10 | Marked local-only | `progress.csv` is gitignored, so a green CI badge could never have included this check. It is now reported as skipped. |
| 9.16 | Applies only when `mirror_urls` is non-empty | As written the rule made `mirror_urls` mandatory whenever `hosts` had more than one entry, contradicting its "Required: no" in the §5 table. |
| 9 | Added rules 25 and 26 | Nothing checked that required fields were present; a row with a blank `primary_tag` passed every rule in the original set. |
| 10.1 | Added `import-tree` | Needed to reach M1 against an existing corpus rather than by hand entry. |
| 2, 10.5 | Added `catalogue.csv` and `fetch` | "Every CCC problem" is a useful question, and answering it cannot wait on 965 classification decisions. Keeping those rows out of `problems.csv` preserves the invariant that every indexed row is tagged. |
| 13 | `query` filters in Python, not SQLite | List fields and tree closures do not map onto SQL without exploding rows. |

### Curation note

The seeded `problems.csv` carries 142 rows whose ids, titles, URLs and native
difficulty were taken from the live judges (cses.fi, DMOJ's API, usaco.org,
oj.uz), so `verified` is a real claim rather than an assumption. Tags, tiers
and quality are hand-assigned.

An earlier draft of the seed contained 18 CCC rows tagged from the problem
*code* alone. Checking them against DMOJ's own categories showed 12 of 18 were
wrong — a "Substrings" problem tagged as Dijkstra, a "Twenty-four" problem
tagged as Floyd-Warshall. Those rows were dropped rather than guessed at, which
is why the CCC coverage is three rows. This is the failure mode §1.2 exists to
prevent, and it is worth recording that it is easy to fall into.
