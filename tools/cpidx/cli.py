"""Command-line entry point.

Normative reference: SPEC.md 10.1.
"""

from __future__ import annotations

import argparse
import datetime
import os
import sys
from collections.abc import Sequence

from . import commands, csvio, enrich, exporters, fetch, importtree, validate
from .query import Query, QueryError, parse_range
from .schema import PROBLEM_COLUMNS
from .taxonomy import Taxonomy, TaxonomyError


class Paths:
    """Where the three artefacts live, relative to the index root."""

    def __init__(self, root: str) -> None:
        self.root = root
        self.taxonomy = os.path.join(root, "taxonomy.yaml")
        self.problems = os.path.join(root, "problems.csv")
        self.progress = os.path.join(root, "progress.csv")
        self.catalogue = os.path.join(root, "catalogue.csv")
        self.build = os.path.join(root, "build")


def _load_taxonomy(paths: Paths) -> Taxonomy:
    try:
        return Taxonomy.load(paths.taxonomy)
    except TaxonomyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


def _load_problems(paths: Paths) -> list[dict]:
    _, rows, _ = csvio.read_problems(paths.problems)
    return rows


class UnsafeToWrite(Exception):
    """The file cannot be rewritten without losing data."""


def _load_problems_for_write(paths: Paths) -> list[dict]:
    """Rows for a command that will write them back.

    `read_table` pads short rows and truncates long ones so that the validator
    can report on them instead of crashing. That is the right behaviour for
    reading and a data-loss bug for writing: rewriting a row that had 24 fields
    drops the last two for good. Any structural finding therefore blocks the
    write, and the user is sent to `cpidx validate` to see what is wrong.
    """
    _, rows, findings = csvio.read_problems(paths.problems)
    structural = [f for f in findings if f[0] in (1, 2)]
    if structural:
        raise UnsafeToWrite(
            "refusing to rewrite {}: {}\n  {}\nRun `cpidx validate` for detail; "
            "fix the file by hand first.".format(
                paths.problems,
                f"{len(structural)} structural problem(s) would lose data",
                "\n  ".join("[rule {}] {}: {}".format(*f) for f in structural[:5]),
            )
        )
    return rows


def _load_progress(paths: Paths) -> list[dict]:
    if not os.path.exists(paths.progress):
        return []
    _, rows, _ = csvio.read_progress(paths.progress)
    return rows


def _today(args: argparse.Namespace) -> datetime.date:
    return datetime.date.fromisoformat(args.today) if args.today else datetime.date.today()


# --- commands ----------------------------------------------------------------
def cmd_validate(args: argparse.Namespace, paths: Paths) -> int:
    report = validate.run(paths, today=_today(args))
    for note in report.skipped:
        print(f"skipped: {note}")
    for finding in report.findings:
        print(finding)
    print(
        "\n{} error(s), {} warning(s){}".format(
            len(report.errors),
            len(report.warnings),
            (
                "; rules hit: " + ", ".join(str(r) for r in report.rules_hit())
                if report.findings
                else ""
            ),
        )
    )
    return report.exit_code(strict=args.strict)


def cmd_fmt(args: argparse.Namespace, paths: Paths) -> int:
    rows = _load_problems_for_write(paths)
    before = open(paths.problems, encoding="utf-8-sig", newline="").read()
    after = csvio.render(rows, PROBLEM_COLUMNS)
    if before == after:
        print("problems.csv already canonical")
        return 0
    if args.check:
        print("problems.csv is not canonically formatted; run `cpidx fmt`")
        return 1
    csvio.write_problems(paths.problems, rows)
    print(f"rewrote problems.csv ({len(rows)} rows, sorted by id)")
    return 0


def cmd_query(args: argparse.Namespace, paths: Paths) -> int:
    taxonomy = _load_taxonomy(paths)
    query = Query(taxonomy)
    query.tag = args.tag
    query.tag_exact = args.tag_exact
    query.primary = args.primary
    query.canonical_only = args.canonical
    query.sort = args.sort
    query.limit = args.limit
    query.seed = args.seed
    query.min_quality = args.min_quality
    query.origin = set(args.origin) if args.origin else None
    query.format = set(args.format) if args.format else None
    query.status = set(args.status) if args.status else None
    if args.missing_prereqs:
        query.missing_prereqs = True
    elif args.ready:
        query.missing_prereqs = False
    try:
        query.difficulty = parse_range(args.difficulty, 1, 10)
        query.quality = parse_range(args.quality, 1, 5)
        query.year = parse_range(args.year, 1990, 2100)
        rows = query.run(_load_problems(paths), _load_progress(paths))
    except QueryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not rows:
        print("no problems match")
        return 0
    if args.ids_only:
        for row in rows:
            print(row["id"])
        return 0
    id_width = max(len(r["id"]) for r in rows)
    tag_width = max(len(r["primary_tag"] or "") for r in rows)
    for row in rows:
        line = "{:<{w}}  t{:<2}  {:<{t}}  {}".format(
            row["id"],
            row["difficulty"] or "?",
            row["primary_tag"] or "",
            row["title"] or "",
            w=id_width,
            t=tag_width,
        )
        if row.get("_unmet"):
            line += "   [unmet: {}]".format(row["_unmet"].replace("|", ", "))
        print(line)
    print(f"\n{len(rows)} problem(s)")
    return 0


def cmd_export(args: argparse.Namespace, paths: Paths) -> int:
    taxonomy = _load_taxonomy(paths)
    rows = _load_problems(paths)
    out_dir = args.out or paths.build
    written = exporters.EXPORTERS[args.format](rows, taxonomy, out_dir)
    for path in written[:5]:
        print(f"wrote {path}")
    if len(written) > 5:
        print(f"... and {len(written) - 5} more")
    return 0


def cmd_stats(args: argparse.Namespace, paths: Paths) -> int:
    taxonomy = _load_taxonomy(paths)
    rows = _load_problems(paths)
    pairs = commands.stats(rows, taxonomy, by=args.by)
    if not pairs:
        print("no rows")
        return 0
    width = max(len(k) for k, _ in pairs)
    total = sum(v for _, v in pairs)
    for key, count in pairs:
        bar = "#" * min(40, count * 40 // max(1, max(v for _, v in pairs)))
        print("{:<{w}}  {:>5}  {}".format(key, count, bar, w=width))
    print(f"\n{total} across {len(pairs)} group(s)")
    if args.by == "tag" and args.gaps:
        gaps = commands.coverage_gaps(rows, taxonomy)
        print(f"\n{len(gaps)} leaf tag(s) with no problems:")
        for tag in gaps:
            print(f"  {tag}")
    return 0


def cmd_linkcheck(args: argparse.Namespace, paths: Paths) -> int:
    rows = _load_problems(paths)
    stale = commands.stale_rows(rows, max_age=args.max_age, today=_today(args))
    for row, age in stale:
        print(
            "stale: {} verified {} ({})".format(
                row["id"],
                row["verified"] or "(never)",
                "unparseable" if age < 0 else f"{age}d",
            )
        )
    print(f"{len(stale)} row(s) past the {args.max_age}-day mark")
    if args.offline:
        return 0
    dead = 0
    blocked = 0
    targets = stale if args.stale_only else [(r, 0) for r in rows]
    for row, _ in targets:
        state, detail = commands.check_url(row["url"], timeout=args.timeout)
        if state == "ok":
            print("ok      {}".format(row["id"]))
        elif state == "blocked":
            blocked += 1
            print("blocked {}  {}  {}".format(row["id"], row["url"], detail))
        else:
            dead += 1
            print("DEAD    {}  {}  {}".format(row["id"], row["url"], detail))
    print(
        f"{dead} dead, {blocked} blocked (host refuses bots, not a broken link), "
        f"{len(targets)} checked"
    )
    return 1 if dead else 0


def cmd_migrate_tags(args: argparse.Namespace, paths: Paths) -> int:
    taxonomy = _load_taxonomy(paths)
    mapping = commands.migration_map(taxonomy)
    if not mapping:
        print("no deprecated tags in taxonomy.yaml")
        return 0
    rows = _load_problems_for_write(paths)
    migrated, changes = commands.migrate_rows(rows, mapping)
    for change in changes:
        print(change)
    if not changes:
        print("no rows reference a deprecated tag")
        return 0
    if args.dry_run:
        print(f"\n{len(changes)} change(s); rerun without --dry-run to apply")
        return 0
    csvio.write_problems(paths.problems, migrated)
    print(f"\napplied {len(changes)} change(s) to problems.csv")
    return 0


def cmd_add(args: argparse.Namespace, paths: Paths) -> int:
    overrides = {}
    for pair in args.set or []:
        if "=" not in pair:
            print(f"error: --set expects field=value, got {pair!r}", file=sys.stderr)
            return 2
        key, _, value = pair.partition("=")
        if key not in PROBLEM_COLUMNS:
            print(f"error: unknown column {key!r}", file=sys.stderr)
            return 2
        overrides[key] = value

    row = commands.build_row(args.url, _today(args).isoformat(), overrides)
    for column in PROBLEM_COLUMNS:
        value = row.get(column, "")
        marker = "[detected]" if value and column not in overrides else ""
        print("  {:<18} {} {}".format(column, value or "?", marker).rstrip())

    missing = commands.missing_required(row)
    if missing:
        print(
            "\nnot written: {} still needed. Classification is never inferred "
            "(SPEC.md 1.2); supply them with --set field=value.".format(", ".join(missing))
        )
        return 1

    rows = _load_problems_for_write(paths)
    if any(existing["id"] == row["id"] for existing in rows):
        print("\nerror: id {!r} is already in the index".format(row["id"]), file=sys.stderr)
        return 1
    rows.append(row)
    csvio.write_problems(paths.problems, rows)
    print("\nadded {} ({} rows total)".format(row["id"], len(rows)))
    return 0


def cmd_fetch(args: argparse.Namespace, paths: Paths) -> int:
    """Pull complete problem lists from the judges into catalogue.csv."""
    today = _today(args).isoformat()
    sources = tuple(args.source) if args.source else fetch.SOURCES
    try:
        fetched = fetch.build(today, sources=sources, log=lambda m: print(m))
    except fetch.FetchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    index_ids = {r["id"] for r in _load_problems(paths)}
    existing: list[dict] = []
    if os.path.exists(paths.catalogue):
        _, existing, _ = csvio.read_problems(paths.catalogue)
    rows, added, refreshed = fetch.merge(existing, fetched, index_ids)
    csvio.write_problems(paths.catalogue, rows)

    by_origin: dict[str, int] = {}
    for row in rows:
        by_origin[row["origin"]] = by_origin.get(row["origin"], 0) + 1
    print(f"\n{len(rows)} catalogue row(s) in {paths.catalogue}")
    for origin in sorted(by_origin, key=lambda o: -by_origin[o]):
        print(f"  {origin:<8} {by_origin[origin]}")
    print(
        f"  {added} new, {refreshed} field(s) refreshed, " f"{len(fetched) - added} already known"
    )
    print(
        "\nCatalogue rows carry no tag: classification is never inferred "
        "(SPEC.md 1.2). Tag one and move it into problems.csv to index it."
    )
    return 0


def cmd_enrich(args: argparse.Namespace, paths: Paths) -> int:
    """Adopt published classifications for catalogue rows that have no tag."""
    taxonomy = _load_taxonomy(paths)
    bad = enrich.unknown_tags(taxonomy)
    if bad:
        print("error: mapping points at non-leaf tags: " + ", ".join(bad), file=sys.stderr)
        return 2
    if not os.path.exists(paths.catalogue):
        print(f"error: {paths.catalogue} does not exist; run `cpidx fetch` first", file=sys.stderr)
        return 2

    _, rows, _ = csvio.read_problems(paths.catalogue)
    guide: dict[str, str] = {}
    if not args.no_guide:
        print("fetching usaco.guide classifications...")
        try:
            guide = enrich.fetch_guide(log=lambda m: print(m))
        except Exception as exc:  # noqa: BLE001 - network failure is the message
            print(f"error: usaco.guide unreachable: {exc}", file=sys.stderr)
            return 2
        print(f"  {len(guide)} classified problems")

    tagged, stats = enrich.apply(rows, guide, coarse=args.coarse)
    csvio.write_problems(paths.catalogue, tagged)
    print(f"\n{stats['guide']} tagged from usaco.guide, {stats['dmoj']} from DMOJ categories")
    print(f"  {stats['already']} already tagged, {stats['unresolved']} still unresolved")
    print(
        "\nEvery adopted tag records its source in free_tags, so it can be "
        "audited or reverted. Rows left blank are ones no published source "
        "resolves to a single leaf."
    )
    if args.promote:
        return _promote_catalogue(paths, tagged)
    print(f"\nRun with --promote to move tagged rows into {paths.problems}.")
    return 0


def _promote_catalogue(paths: Paths, tagged: list[dict]) -> int:
    """Move fully-specified catalogue rows into the curated index."""
    existing = _load_problems_for_write(paths)
    known = {r["id"] for r in existing}
    ready, staying = [], []
    for row in tagged:
        clean = {c: row.get(c, "") for c in PROBLEM_COLUMNS}
        if clean["id"] in known or not clean["primary_tag"] or commands.missing_required(clean):
            staying.append(row)
        else:
            ready.append(clean)
    if not ready:
        print("nothing ready to promote")
        return 0
    csvio.write_problems(paths.problems, existing + ready)
    csvio.write_problems(paths.catalogue, staying)
    print(
        f"promoted {len(ready)} row(s) into {paths.problems}; "
        f"{len(staying)} left in the catalogue"
    )
    return 0


def cmd_import_tree(args: argparse.Namespace, paths: Paths) -> int:
    out_path = args.out or os.path.join(paths.build, "import-candidates.csv")
    rows, unmatched = importtree.stage(
        args.source or paths.root, out_path, _today(args).isoformat()
    )
    by_confidence: dict[str, int] = {}
    for row in rows:
        by_confidence[row["_confidence"]] = by_confidence.get(row["_confidence"], 0) + 1
    print(f"staged {len(rows)} candidate(s) to {out_path}")
    for level in ("high", "medium", "low"):
        if level in by_confidence:
            print(f"  {level:<7} {by_confidence[level]}")
    needing = sum(1 for r in rows if r["_needs"])
    print(f"  {needing} need curation before promotion")
    print(f"  {len(unmatched)} source file(s) matched no origin pattern")
    if args.show_unmatched:
        for path in unmatched:
            print(f"    {path}")
    print(
        "\nNothing was written to problems.csv. Review the staging file, then "
        "promote rows with `cpidx import-tree --promote`."
    )
    if args.promote:
        return _promote(paths, out_path, args)
    return 0


def _promote(paths: Paths, staging_path: str, args: argparse.Namespace) -> int:
    """Move fully-specified staged rows into the index."""
    _, staged, _ = csvio.read_table(staging_path, importtree.STAGING_COLUMNS)
    existing = _load_problems_for_write(paths)
    known = {row["id"] for row in existing}
    promoted = []
    for row in staged:
        if row["id"] in known or row["_needs"]:
            continue
        promoted.append({c: row.get(c, "") for c in PROBLEM_COLUMNS})
    if not promoted:
        print("nothing to promote: every staged row still needs curation")
        return 0
    csvio.write_problems(paths.problems, existing + promoted)
    print(f"promoted {len(promoted)} row(s) into problems.csv")
    return 0


# --- parser ------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cpidx", description="Competitive programming problem index."
    )
    parser.add_argument("--root", default=".", help="index root holding problems.csv (default: .)")
    parser.add_argument("--today", help="override today's date, ISO 8601, for tests")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("validate", help="check the index against SPEC.md 9")
    p.add_argument("--strict", action="store_true", help="treat warnings as failures")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("fmt", help="rewrite problems.csv in canonical form")
    p.add_argument("--check", action="store_true", help="exit nonzero instead of rewriting")
    p.set_defaults(func=cmd_fmt)

    p = sub.add_parser("query", help="filter the index")
    tag_filter = p.add_mutually_exclusive_group()
    tag_filter.add_argument("--tag", help="match this node and all descendants")
    tag_filter.add_argument("--tag-exact", help="match this node only")
    tag_filter.add_argument("--primary", help="match primary_tag only")
    p.add_argument("--difficulty", help="tier or inclusive range, e.g. 4-6")
    p.add_argument("--quality", help="quality or inclusive range")
    p.add_argument("--min-quality", type=int)
    p.add_argument("--year", help="year or inclusive range")
    p.add_argument("--origin", action="append")
    p.add_argument("--format", action="append")
    p.add_argument("--status", action="append", help="requires progress.csv")
    p.add_argument("--canonical", action="store_true", help="only canonical entries")
    p.add_argument(
        "--missing-prereqs", action="store_true", help="primary_tag has unmet prerequisites"
    )
    p.add_argument("--ready", action="store_true", help="inverse: prerequisites all demonstrated")
    p.add_argument(
        "--sort", default="difficulty", choices=["difficulty", "quality", "year", "random", "id"]
    )
    p.add_argument("--seed", type=int, help="seed for --sort random")
    p.add_argument("--limit", type=int)
    p.add_argument("--ids-only", action="store_true")
    p.set_defaults(func=cmd_query)

    p = sub.add_parser("export", help="generate a view into build/")
    p.add_argument("--format", required=True, choices=sorted(exporters.EXPORTERS))
    p.add_argument("--out", help="output directory (default: <root>/build)")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("stats", help="counts by group")
    p.add_argument("--by", default="tag", choices=["tag", "origin", "difficulty", "category"])
    p.add_argument("--gaps", action="store_true", help="also list leaf tags with no problems")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("linkcheck", help="find stale or dead links")
    p.add_argument("--max-age", type=int, default=365)
    p.add_argument("--offline", action="store_true", help="check dates only, no network")
    p.add_argument("--stale-only", action="store_true", help="only fetch rows past --max-age")
    p.add_argument("--timeout", type=float, default=10.0)
    p.set_defaults(func=cmd_linkcheck)

    p = sub.add_parser("migrate-tags", help="rewrite deprecated tags, SPEC.md 7.6")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_migrate_tags)

    p = sub.add_parser("add", help="add a problem from a URL")
    p.add_argument("url")
    p.add_argument("--set", action="append", metavar="FIELD=VALUE")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("fetch", help="pull full problem lists from the judges into catalogue.csv")
    p.add_argument(
        "--source",
        action="append",
        choices=list(fetch.SOURCES),
        help="limit to one source; repeatable (default: all)",
    )
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("enrich", help="adopt published classifications for untagged rows")
    p.add_argument(
        "--promote", action="store_true", help="move newly tagged rows into problems.csv"
    )
    p.add_argument(
        "--no-guide", action="store_true", help="skip usaco.guide; use DMOJ categories only"
    )
    p.add_argument(
        "--coarse",
        action="store_true",
        help="fall back to one representative leaf per category; approximate, "
        "recorded as via-dmoj-category",
    )
    p.set_defaults(func=cmd_enrich)

    p = sub.add_parser("import-tree", help="stage candidates from an existing solutions tree")
    p.add_argument("--source", help="tree to walk (default: index root)")
    p.add_argument("--out", help="staging file path")
    p.add_argument("--promote", action="store_true", help="also promote fully-specified rows")
    p.add_argument("--show-unmatched", action="store_true")
    p.set_defaults(func=cmd_import_tree)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = Paths(args.root)
    try:
        return args.func(args, paths)
    except UnsafeToWrite as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except csvio.CsvFormatError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
