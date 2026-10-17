#!/usr/bin/env python3
"""Build or check the standalone public catalog map using only Python's stdlib."""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
KINDS = {"guide", "policy", "skill", "mcp", "reference"}
STATUSES = {"available", "planned", "reference"}
MARKER = "<!-- CATALOG_DATA -->"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value, name):
    require(isinstance(value, str) and bool(value.strip()), f"{name}: expected nonempty text")


def identifier(value, name):
    text(value, name)
    require(re.fullmatch(r"[a-z][a-z0-9-]*", value), f"{name}: use lowercase kebab-case")


def public_url(value):
    text(value, "url")
    parsed = urlsplit(value)
    require(parsed.scheme == "https" and parsed.hostname, "url: expected an HTTPS source")
    require(not parsed.username and not parsed.password, "url: credentials are not allowed")


def source_path(root, value):
    text(value, "source")
    path = Path(value)
    require(not path.is_absolute() and ".." not in path.parts, "source: use a repository-relative path")
    require(not any(part.startswith(".") for part in path.parts), "source: local/hidden paths are not map sources")
    resolved = (root / path).resolve()
    require(resolved.is_relative_to(root.resolve()), "source: path escapes the repository")
    require(resolved.exists(), f"source: missing {value}")
    return resolved


def payload_paths(root):
    """Find actual reusable source; supporting skill files travel with SKILL.md."""
    found = set()
    for area in ("policies", "mcp"):
        directory = root / area
        if directory.exists():
            for path in directory.rglob("*"):
                relative = path.relative_to(root)
                if path.is_file() and not any(p.startswith(".") for p in relative.parts) and path.name != "README.md":
                    found.add(relative.as_posix())
    directory = root / "skills"
    if directory.exists():
        for path in directory.rglob("SKILL.md"):
            relative = path.relative_to(root)
            if not any(p.startswith(".") for p in relative.parts):
                found.add(relative.as_posix())
    return found


def validate(catalog, root):
    require(isinstance(catalog, dict) and catalog.get("schema_version") == 1, "expected catalog schema_version 1")
    text(catalog.get("title"), "title")
    text(catalog.get("description"), "description")
    groups = catalog.get("groups")
    entries = catalog.get("entries")
    relationships = catalog.get("relationships")
    require(isinstance(groups, list) and groups, "groups: expected a nonempty list")
    require(isinstance(entries, list) and entries, "entries: expected a nonempty list")
    require(isinstance(relationships, list), "relationships: expected a list")
    group_ids = set()
    for group in groups:
        require(isinstance(group, dict), "group: expected an object")
        identifier(group.get("id"), "group.id")
        require(group["id"] not in group_ids, f"duplicate group: {group['id']}")
        group_ids.add(group["id"])
        text(group.get("title"), "group.title")
        text(group.get("description"), "group.description")
    ids, registered = set(), set()
    payload = payload_paths(root)
    for entry in entries:
        require(isinstance(entry, dict), "entry: expected an object")
        identifier(entry.get("id"), "entry.id")
        require(entry["id"] not in ids, f"duplicate entry: {entry['id']}")
        ids.add(entry["id"])
        require(entry.get("group") in group_ids, f"{entry['id']}: unknown group")
        require(entry.get("kind") in KINDS, f"{entry['id']}: unknown kind")
        require(entry.get("status") in STATUSES, f"{entry['id']}: unknown status")
        for key in ("title", "summary", "usage"):
            text(entry.get(key), f"{entry['id']}.{key}")
        for key in ("when", "behavior", "outputs", "tags"):
            values = entry.get(key)
            require(isinstance(values, list) and values, f"{entry['id']}.{key}: expected a nonempty list")
            for value in values:
                text(value, f"{entry['id']}.{key}")
        require(("source" in entry) != ("url" in entry), f"{entry['id']}: provide exactly one source or url")
        if "url" in entry:
            public_url(entry["url"])
            require(entry["kind"] == "reference" and entry["status"] == "reference", "external links must be labeled as references")
        else:
            path = source_path(root, entry["source"])
            require(entry["kind"] != "reference" and entry["status"] != "reference", "references need an external url")
            if entry["status"] == "planned":
                require(path.is_dir(), f"{entry['id']}: planned entries must point to placeholder directories")
                require(not any(p == entry["source"] or p.startswith(entry["source"] + "/") for p in payload),
                        f"{entry['id']}: content exists; replace the planned placeholder with real entries")
            else:
                require(path.is_file(), f"{entry['id']}: available entries need a source file")
                registered.add(entry["source"])
            if entry["kind"] in {"policy", "skill", "mcp"}:
                prefix = {"policy": "policies", "skill": "skills", "mcp": "mcp"}[entry["kind"]]
                require(Path(entry["source"]).parts[0] == prefix, f"{entry['id']}: source does not match its kind")
    require(not payload - registered, "unmapped reusable content: " + ", ".join(sorted(payload - registered)))
    for entry in entries:
        if "explanation" in entry:
            validate_explanation(entry["explanation"], ids, root)
    seen = set()
    for relation in relationships:
        require(isinstance(relation, dict), "relationship: expected an object")
        pair = (relation.get("from"), relation.get("to"))
        require(pair[0] in ids and pair[1] in ids and pair[0] != pair[1], "relationship: invalid endpoints")
        require(pair not in seen, "relationship: duplicate endpoints")
        seen.add(pair)
        text(relation.get("label"), "relationship.label")


def validate_explanation(explanation, ids, root):
    """Optional rich explanations share the catalog's public-source boundary."""
    require(isinstance(explanation, dict), "explanation: expected an object")
    example = explanation.get("example")
    require(isinstance(example, dict), "explanation.example: expected an object")
    for key in ("situation", "youType", "youGet"):
        text(example.get(key), "explanation.example." + key)
    for values in (example.get("whatHappens"), explanation.get("adaptation_notes")):
        require(isinstance(values, list) and values, "explanation: expected nonempty text list")
        for value in values:
            text(value, "explanation text")
    calls = explanation.get("calls")
    require(isinstance(calls, list), "explanation.calls: expected a list")
    require(all(isinstance(key, str) and key in ids for key in calls), "explanation: unknown called item")
    flows = explanation.get("flows")
    require(isinstance(flows, list) and flows, "explanation.flows: expected nonempty list")
    for flow in flows:
        require(isinstance(flow, list) and flow, "explanation.flow: expected nonempty list")
        for step in flow:
            text(step, "explanation.flow step")
            require(not step.startswith("@") or step[1:] in ids, "explanation: unknown flow item")
    sources = explanation.get("sources")
    require(isinstance(sources, list) and sources, "explanation.sources: expected nonempty list")
    for source in sources:
        require(isinstance(source, dict), "explanation.source: expected an object")
        text(source.get("label"), "explanation.source.label")
        require(("source" in source) != ("url" in source), "explanation.source: provide one path or URL")
        if "url" in source:
            public_url(source["url"])
        else:
            require(source_path(root, source["source"]).is_file(), "explanation.source: expected file")


def render(catalog, template, root):
    validate(catalog, root)
    require(template.count(MARKER) == 1, "template must contain exactly one catalog marker")
    data = json.loads(json.dumps(catalog))
    for entry in data["entries"]:
        entry["href"] = entry.get("url") or "../../" + quote(entry["source"], safe="/")
    canonical = json.dumps(catalog, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    data["digest"] = hashlib.sha256(canonical.encode()).hexdigest()[:12]
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    encoded = encoded.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return template.replace(MARKER, '<script type="application/json" id="catalog-data">' + encoded + "</script>")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the generated viewer is missing or stale")
    args = parser.parse_args()
    try:
        directory = ROOT / "docs/map"
        catalog = json.loads((directory / "catalog.json").read_text(encoding="utf-8"))
        output = render(catalog, (directory / "viewer.template.html").read_text(encoding="utf-8"), ROOT)
        path = directory / "index.html"
        if args.check:
            require(path.exists() and path.read_bytes() == output.encode(), "map is stale; run python3 scripts/build_map.py")
            print(f"Map is current: {len(catalog['entries'])} entries, {len(catalog['relationships'])} relationships.")
        else:
            path.write_bytes(output.encode())
            print(f"Built docs/map/index.html: {len(catalog['entries'])} entries.")
    except (ValueError, OSError, TypeError, KeyError) as error:
        print(f"Map build failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
