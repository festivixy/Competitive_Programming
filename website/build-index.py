"""Build the Technique Index page from the index data.

    python website/build-index.py              # public site -> website/index.html
    python website/build-index.py --private O  # private copy, with solve status

The public build carries no solve status: `progress.csv` is private by
SPEC.md 3, and GitHub Pages is not.

Run from the repository root. Regenerate after `cpidx fetch` or any edit to
problems.csv, catalogue.csv or taxonomy.yaml.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from cpidx import csvio, importtree  # noqa: E402
from cpidx.taxonomy import Taxonomy  # noqa: E402

TEMPLATE = Path(__file__).resolve().parent / "index.template.html"

# The existing CMS lives behind these pages, so the index carries their links
# and the same sign-in markup site-nav.js drives.
SITE_NAV = """    <div class="sitenav" data-site-nav>
      <span class="lead">Editorials</span>
      <a href="all.html">Find</a>
      <a href="edit.html">Write</a>
      <a href="manage.html" data-review-link hidden>Review</a>
      <span class="site-identity" data-identity hidden></span>
      <button type="button" data-sign-in>Sign in</button>
      <button type="button" data-sign-out hidden>Sign out</button>
    </div>"""

# Deep links to the site root are redirected by the old landing page; keep it.
REDIRECT_SHIM = """    <script>
      const params = new URLSearchParams(location.search);
      if (params.has("slug") || params.has("editorial") || params.has("file"))
        location.replace(`section.html?${params}${location.hash}`);
      else if (params.has("collection") || params.has("section"))
        location.replace(`all.html?${params}${location.hash}`);
    </script>"""

HEAD = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Technique Index</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      rel="stylesheet"
      href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap"
    />
{shim}
  </head>
  <body>
"""

FOOT = """    <script src="site-config.js?v=6"></script>
    <script src="api.js?v=6"></script>
    <script src="site-nav.js?v=6"></script>
  </body>
</html>
"""


def load(include_status: bool) -> dict:
    taxonomy = Taxonomy.load(str(ROOT / "taxonomy.yaml"))
    _, indexed, _ = csvio.read_problems(str(ROOT / "problems.csv"))

    catalogue = []
    catalogue_path = ROOT / "catalogue.csv"
    if catalogue_path.exists():
        _, catalogue, _ = csvio.read_problems(str(catalogue_path))

    solved: set[str] = set()
    if include_status:
        progress_path = ROOT / "progress.csv"
        if progress_path.exists():
            _, progress, _ = csvio.read_progress(str(progress_path))
            solved |= {r["id"] for r in progress if r["status"].startswith("solved")}
        # A solution file on disk counts too; catalogue ids line up with it.
        merged, _ = importtree.derive(str(ROOT))
        solved |= set(merged)

    def pack(row: dict, is_indexed: bool) -> dict:
        out = {
            "id": row["id"], "t": row["title"], "o": row["origin"], "c": row["contest"],
            "y": row["year"], "l": row["label"], "u": row["url"],
            "d": row["difficulty"], "dn": row["difficulty_native"],
            "pt": row["primary_tag"],
            "tg": list(csvio.split_list(row["tags"])),
            "ft": list(csvio.split_list(row["free_tags"])),
            "q": row["quality"],
            "k": 1 if row["canonical"] == "true" else 0,
            "ix": 1 if is_indexed else 0,
            # 1 when the tag is a category-level approximation rather than a
            # classification of this particular problem.
            "cz": 1 if "via-dmoj-category" in csvio.split_list(row["free_tags"]) else 0,
        }
        if include_status:
            out["s"] = 1 if row["id"] in solved else 0
        return out

    problems = [pack(r, True) for r in indexed] + [pack(r, False) for r in catalogue]
    nodes = [
        {"id": t, "name": taxonomy.get(t).name,
         "leaf": taxonomy.is_leaf(t), "depth": taxonomy.get(t).depth}
        for t in sorted(taxonomy.nodes)
    ]
    return {"config": {"status": include_status}, "problems": problems, "nodes": nodes}


def build(out_path: Path, include_status: bool, standalone: bool) -> None:
    payload = load(include_status)
    body = TEMPLATE.read_text(encoding="utf-8")
    body = body.replace("__NAV__", SITE_NAV if standalone else "")
    data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    # Keep the JSON from closing the <script> element early.
    body = body.replace("__DATA__", data.replace("</", "<\\/"))
    assert "__DATA__" not in body and "__NAV__" not in body

    if standalone:
        page = HEAD.format(shim=REDIRECT_SHIM) + body + FOOT
    else:
        page = "<title>Technique Index</title>\n" + body

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8", newline="\n")
    counts: dict[str, int] = {}
    for problem in payload["problems"]:
        counts[problem["o"]] = counts.get(problem["o"], 0) + 1
    print(f"wrote {out_path} ({round(len(page) / 1024)} KB)")
    print(f"  {len(payload['problems'])} problems: " +
          ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])))
    print(f"  solve status: {'included' if include_status else 'stripped'}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private", metavar="PATH",
                        help="also write a private copy that includes solve status")
    args = parser.parse_args()

    build(Path(__file__).resolve().parent / "index.html", include_status=False, standalone=True)
    if args.private:
        build(Path(args.private), include_status=True, standalone=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
