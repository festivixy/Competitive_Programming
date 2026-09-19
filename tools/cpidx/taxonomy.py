"""Loading and querying the controlled vocabulary.

Normative reference: SPEC.md section 7. The tree encodes kinship; the
prerequisite relation encodes learning order. They are deliberately separate
graphs over the same node set.
"""

from __future__ import annotations

from collections.abc import Sequence

import yaml

from .schema import MAX_TAG_DEPTH


class TaxonomyError(Exception):
    """Raised when taxonomy.yaml cannot be loaded at all."""


class Node:
    """One technique node."""

    __slots__ = (
        "id",
        "name",
        "aliases",
        "status",
        "replaced_by",
        "prerequisites",
        "description",
        "discriminator",
    )

    def __init__(self, raw: dict) -> None:
        self.id = raw["id"]
        self.name = raw.get("name", "")
        self.aliases = tuple(raw.get("aliases") or ())
        self.status = raw.get("status", "")
        self.replaced_by = raw.get("replaced_by")
        self.prerequisites = tuple(raw.get("prerequisites") or ())
        self.description = (raw.get("description") or "").strip()
        self.discriminator = (raw.get("discriminator") or "").strip()

    @property
    def depth(self) -> int:
        return self.id.count(".") + 1

    @property
    def parent_id(self) -> str | None:
        return self.id.rsplit(".", 1)[0] if "." in self.id else None

    @property
    def is_deprecated(self) -> bool:
        return self.status == "deprecated"

    def __repr__(self) -> str:
        return f"Node({self.id!r})"


class Taxonomy:
    """The technique tree, plus the prerequisite DAG laid over it."""

    def __init__(self, nodes: Sequence[Node], version: int = 0) -> None:
        self.version = version
        self.nodes = {n.id: n for n in nodes}
        self._children = {}
        for node in nodes:
            self._children.setdefault(node.id, [])
        for node in nodes:
            parent = node.parent_id
            if parent is not None and parent in self._children:
                self._children[parent].append(node.id)

    # -- construction ---------------------------------------------------------
    @classmethod
    def load(cls, path: str) -> Taxonomy:
        try:
            with open(path, encoding="utf-8") as handle:
                raw = yaml.safe_load(handle)
        except OSError as exc:
            raise TaxonomyError(f"cannot read {path}: {exc}") from exc
        except yaml.YAMLError as exc:
            raise TaxonomyError(f"{path} is not valid YAML: {exc}") from exc
        if not isinstance(raw, dict) or "nodes" not in raw:
            raise TaxonomyError(f"{path} must be a mapping with a `nodes` key")
        entries = raw["nodes"] or []
        seen = set()
        nodes = []
        for entry in entries:
            if not isinstance(entry, dict) or "id" not in entry:
                raise TaxonomyError("every taxonomy entry needs an `id`")
            if entry["id"] in seen:
                raise TaxonomyError("duplicate taxonomy id: {}".format(entry["id"]))
            seen.add(entry["id"])
            nodes.append(Node(entry))
        return cls(nodes, version=raw.get("version", 0))

    # -- tree queries ---------------------------------------------------------
    def __contains__(self, tag: str) -> bool:
        return tag in self.nodes

    def get(self, tag: str) -> Node | None:
        return self.nodes.get(tag)

    def children(self, tag: str) -> tuple[str, ...]:
        return tuple(self._children.get(tag, ()))

    def is_leaf(self, tag: str) -> bool:
        return tag in self.nodes and not self._children.get(tag)

    def leaves(self) -> tuple[str, ...]:
        return tuple(sorted(i for i in self.nodes if self.is_leaf(i)))

    def top_level(self) -> tuple[str, ...]:
        return tuple(sorted(i for i in self.nodes if "." not in i))

    def ancestors(self, tag: str) -> tuple[str, ...]:
        """Proper ancestors of a tag, nearest first. Derived, never stored."""
        out = []
        parts = tag.split(".")
        for cut in range(len(parts) - 1, 0, -1):
            candidate = ".".join(parts[:cut])
            if candidate in self.nodes:
                out.append(candidate)
        return tuple(out)

    def descendants(self, tag: str) -> tuple[str, ...]:
        """The tag and everything beneath it, which is what `--tag` matches."""
        if tag not in self.nodes:
            return ()
        prefix = tag + "."
        return tuple(sorted(i for i in self.nodes if i == tag or i.startswith(prefix)))

    def top_level_of(self, tag: str) -> str:
        return tag.split(".", 1)[0]

    # -- alias index ----------------------------------------------------------
    def alias_index(self) -> dict[str, str]:
        """Every searchable surface form mapped to its node id."""
        index = {}
        for node in self.nodes.values():
            index.setdefault(node.id.rsplit(".", 1)[-1], node.id)
            index.setdefault(node.name.lower(), node.id)
            for alias in node.aliases:
                index.setdefault(str(alias).lower(), node.id)
        return index

    # -- prerequisite DAG -----------------------------------------------------
    def prerequisite_cycles(self) -> list[list[str]]:
        """Every cycle in the prerequisite relation, as lists of node ids."""
        cycles = []
        colour = {}  # 0 unvisited, 1 on stack, 2 done
        stack = []

        def walk(tag: str) -> None:
            colour[tag] = 1
            stack.append(tag)
            node = self.nodes.get(tag)
            for prereq in node.prerequisites if node else ():
                if prereq not in self.nodes:
                    continue
                state = colour.get(prereq, 0)
                if state == 0:
                    walk(prereq)
                elif state == 1:
                    cycles.append(stack[stack.index(prereq) :] + [prereq])
            stack.pop()
            colour[tag] = 2

        for tag in sorted(self.nodes):
            if colour.get(tag, 0) == 0:
                walk(tag)
        return cycles

    def transitive_prerequisites(self, tag: str) -> set[str]:
        """All prerequisites reachable from a tag, cycle-safe."""
        out = set()
        frontier = [tag]
        while frontier:
            current = frontier.pop()
            node = self.nodes.get(current)
            for prereq in node.prerequisites if node else ():
                if prereq not in out:
                    out.add(prereq)
                    frontier.append(prereq)
        return out

    # -- structural problems, surfaced by `validate` --------------------------
    def structural_findings(self) -> list[tuple[int, str, str]]:
        """(rule_number, node_id, message) for SPEC.md 9 taxonomy rules 17-20."""
        findings = []
        for cycle in self.prerequisite_cycles():
            findings.append((17, cycle[0], "prerequisite cycle: " + " -> ".join(cycle)))
        for tag, node in sorted(self.nodes.items()):
            if node.depth > MAX_TAG_DEPTH:
                findings.append((18, tag, f"depth {node.depth} exceeds maximum {MAX_TAG_DEPTH}"))
            if self.is_leaf(tag) and not node.discriminator:
                findings.append((19, tag, "leaf node has no discriminator"))
            if node.is_deprecated and not node.replaced_by:
                findings.append((20, tag, "deprecated node has no replaced_by"))
            if node.replaced_by and node.replaced_by not in self.nodes:
                findings.append((20, tag, f"replaced_by points at unknown node {node.replaced_by}"))
            parent = node.parent_id
            if parent is not None and parent not in self.nodes:
                findings.append((18, tag, f"parent {parent} is not defined"))
            if node.status not in ("canonical", "deprecated", "provisional"):
                findings.append((20, tag, f"unknown status {node.status!r}"))
            for prereq in node.prerequisites:
                if prereq not in self.nodes:
                    findings.append((17, tag, f"unknown prerequisite {prereq}"))
        return findings

    def resolution_error(self, tag: str) -> tuple[int, str] | None:
        """Why a problem row may not use this tag, or None if it may.

        Returns (rule_number, message) matching SPEC.md 9 rules 6, 7 and 8.
        """
        node = self.nodes.get(tag)
        if node is None:
            return (6, f"tag {tag} is not in taxonomy.yaml")
        if not self.is_leaf(tag):
            return (7, f"tag {tag} is not a leaf")
        if node.is_deprecated:
            target = node.replaced_by or "?"
            return (8, f"tag {tag} is deprecated, replaced by {target}")
        return None
