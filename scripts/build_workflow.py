#!/usr/bin/env python3
"""Build the separate AK SDLC map from shared catalog entries and workflow navigation."""
import argparse
import hashlib
import html
import importlib.util
import ast
import json
import re
import sys
from urllib.parse import quote
from build_map import ROOT, require, text, identifier, source_path, validate

def validate_workflow(workflow, entries, root):
    """Check navigation against real stages without importing executable source."""
    require(isinstance(workflow, dict), "workflow: expected an object")
    source_path(root, workflow.get("source"))
    stage_source = source_path(root, workflow.get("stage_source"))
    tree = ast.parse(stage_source.read_text(encoding="utf-8"))
    declarations = [node.value for node in tree.body if isinstance(node, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "STAGES" for t in node.targets)]
    require(len(declarations) == 1, "workflow: missing unique STAGES declaration")
    canonical = ast.literal_eval(declarations[0])
    text(workflow.get("description"), "workflow.description")
    entry_by_id = {entry["id"]: entry for entry in entries}
    covered = set()

    def records(key):
        rows = workflow.get(key)
        require(isinstance(rows, list) and rows, f"workflow.{key}: expected nonempty list")
        seen = set()
        for row in rows:
            require(isinstance(row, dict), f"workflow.{key}: expected object")
            identifier(row.get("id"), key + ".id")
            require(row["id"] not in seen, f"workflow.{key}: duplicate id")
            seen.add(row["id"])
        return rows

    def references(values, skill_only=False):
        require(isinstance(values, list) and values, "workflow: expected nonempty item references")
        require(all(isinstance(v, str) for v in values), "workflow: invalid item reference")
        require(len(values) == len(set(values)), "workflow: duplicate item reference")
        for value in values:
            require(value in entry_by_id, f"workflow: unknown item {value}")
            entry = entry_by_id[value]
            require(entry["status"] == "available", "workflow: item must be available")
            require(not skill_only or entry["kind"] in {"skill", "guide"}, "workflow: step needs a skill or guide")
            covered.add(value)

    phases = records("phases")
    for phase in phases:
        for key in ("title", "summary"):
            text(phase.get(key), "workflow.phase." + key)
    phase_ids = [phase["id"] for phase in phases]
    stages = records("stages")
    for stage in stages:
        for key in ("title", "summary", "gate", "handoff"):
            text(stage.get(key), "workflow.stage." + key)
        require(stage.get("phase") in phase_ids, "workflow: unknown phase")
        steps = stage.get("steps")
        require(isinstance(steps, list) and steps, "workflow: expected nonempty steps")
        for step in steps:
            require(isinstance(step, dict), "workflow: invalid step")
            text(step.get("label"), "workflow.step.label")
            references(step.get("skills"), skill_only=True)
    phase_order = [phase_ids.index(stage["phase"]) for stage in stages]
    require(phase_order == sorted(phase_order) and set(phase_order) == set(range(len(phases))),
            "workflow: phases must be ordered and populated")
    excluded = records("excluded_stages")
    for row in excluded:
        text(row.get("reason"), "workflow.excluded.reason")
    shown = [stage["id"] for stage in stages]
    omitted = {row["id"] for row in excluded}
    require(not set(shown) & omitted and set(shown) | omitted == set(canonical),
            "workflow: stages must account for the canonical stage set")
    require(shown == [stage for stage in canonical if stage not in omitted],
            "workflow: stage order differs from canonical order")
    anytime_ids = set()
    for group in records("anytime"):
        text(group.get("title"), "workflow.anytime.title")
        text(group.get("description"), "workflow.anytime.description")
        references(group.get("items"))
        require(not anytime_ids.intersection(group["items"]), "workflow: duplicate anytime item")
        anytime_ids.update(group["items"])
    triggers = workflow.get("triggers")
    require(isinstance(triggers, dict) and set(triggers) == anytime_ids,
            "workflow: every anytime item needs exactly one contextual trigger")
    for value in triggers.values():
        text(value, "workflow.trigger")
    for field, keys in (("node_labels", covered), ("category_titles", set(shown)),
                        ("group_titles", {g["id"] for g in workflow["anytime"]})):
        values = workflow.get(field)
        require(isinstance(values, dict) and set(values) == keys, f"workflow: incomplete {field}")
        for value in values.values():
            for label in value if isinstance(value, list) else [value]:
                text(label, field)
                require(len(label) <= 48, f"workflow: {field} label too long")
    chained = {"design", "plan", "pr-review", "correction", "self-verification"}
    for stage in stages:
        expected = 1 if stage["id"] in chained else sum(len(step["skills"]) for step in stage["steps"])
        titles = workflow["category_titles"][stage["id"]]
        require(isinstance(titles, list) and len(titles) == expected, "workflow: category count mismatch")
    skills = {entry["id"] for entry in entries if entry["kind"] == "skill"}
    require(not skills - covered, "workflow: unmapped skills: " + ", ".join(sorted(skills - covered)))



def map_data(workflow, catalog):
    """Adapt existing navigation/entries to the upstream renderer's data contract."""
    source = {"label": "Authoritative AK SDLC routing", "url": "../../" + workflow["source"]}
    tones = {"understand": "plan", "shape": "design", "prove": "test", "deliver": "deploy"}
    stages = [{"id": stage["id"], "name": stage["title"], "tone": tones[stage["phase"]],
               "principle": stage["summary"] + " Handoff: " + stage["handoff"],
               "when": [stage["gate"]], "sources": [source]} for stage in workflow["stages"]]
    stages[-1]["principle"] += " " + " ".join(row["reason"] for row in workflow["excluded_stages"])
    categories = []
    titles = workflow["category_titles"]
    for stage in workflow["stages"]:
        # Alternatives are separate branches. Only genuine ordered method paths get arrows.
        if stage["id"] in {"design", "plan", "pr-review", "correction", "self-verification"}:
            chain = [skill for step in stage["steps"] for skill in step["skills"]]
            categories.append({"id": stage["id"] + "-methods", "stage": stage["id"],
                               "name": titles[stage["id"]][0], "blurb": stage["summary"],
                               "principle": stage["gate"],
                               "when": [str(i + 1) + ". " + step["label"] + " → " + ", ".join(step["skills"])
                                        for i, step in enumerate(stage["steps"])],
                               "chain": chain,
                               "chainWhy": "Follow the numbered conditions; optional methods are not mandatory. " + stage["handoff"],
                               "sources": [source]})
        else:
            n = 0
            for step in stage["steps"]:
                for skill in step["skills"]:
                    categories.append({"id": stage["id"] + "-" + str(n + 1), "stage": stage["id"],
                                       "name": titles[stage["id"]][n], "blurb": step["label"],
                                       "principle": stage["gate"], "when": [step["label"] + " → " + skill],
                                       "chain": [skill], "chainWhy": stage["handoff"], "sources": [source]})
                    n += 1
    mapped = {skill for category in categories for skill in category["chain"]}
    mapped.update(skill for group in workflow["anytime"] for skill in group["items"])
    contexts = {}
    for stage in workflow["stages"]:
        for step in stage["steps"]:
            for skill in step["skills"]:
                contexts.setdefault(skill, []).append(stage["title"] + ": " + step["label"])
    skills = {}
    for entry in catalog["entries"]:
        if entry["id"] not in mapped:
            continue
        key = entry["id"]
        skills[key] = {"name": key, "command": None, "platforms": [],
                       "trigger": workflow["node_labels"][key],
                       "when": [workflow["triggers"][key]] if key in workflow["triggers"] else contexts.get(key, entry["when"]),
                       "whatItIs": entry["summary"],
                       "howItWorks": [entry["usage"]] + entry["behavior"] + ["Expected result: " + result for result in entry["outputs"]],
                       "sources": [{"label": entry["source"], "url": "../../" + quote(entry["source"], safe="/")}],
                       "next": []}
        explanation = entry.get("explanation")
        if explanation:
            skills[key].update(when=entry["when"], example=explanation["example"],
                               behindTheScenes=explanation["flows"], calls=explanation["calls"])
            skills[key]["howItWorks"].extend("AK adaptation: " + note for note in explanation["adaptation_notes"])
            skills[key]["sources"].extend({"label": source["label"],
                                           "url": source.get("url") or "../../" + quote(source["source"], safe="/")}
                                          for source in explanation["sources"])
    digest = hashlib.sha256(json.dumps([workflow, catalog], sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
    return {"meta": {"id": "ak-sdlc", "name": workflow["title"],
                     "version": f"{len(stages)} stages · {sum(e['kind'] == 'skill' for e in catalog['entries'])} skills · " + digest,
                     "tagline": "AK SDLC PR route. Read stages left to right; open categories for conditions. Anytime methods apply across stages.",
                     "sources": [source, {"label": "Map engine: Eric Tech / super-board (MIT)", "url": "https://github.com/EricTechPro/super-board"},
                                 {"label": "Usage & maintenance", "url": "workflow.md"}]},
            "stages": stages, "categories": categories,
            "anytime": [{"id": group["id"], "name": workflow["group_titles"][group["id"]],
                         "blurb": group["description"], "items": group["items"]} for group in workflow["anytime"]],
            "skills": skills}


def build(root):
    directory = root / "docs/map"
    catalog = json.loads((directory / "catalog.json").read_text(encoding="utf-8"))
    workflow = json.loads((directory / "workflow.json").read_text(encoding="utf-8"))
    validate(catalog, root)
    validate_workflow(workflow, catalog["entries"], root)
    data = map_data(workflow, catalog)
    vendor = directory / "vendor/super-board"
    spec = importlib.util.spec_from_file_location("ak_sdlc_map_layout", vendor / "layout_sdlc.py")
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    model = engine.build(data, directory)
    read = lambda name: (vendor / name).read_text(encoding="utf-8")
    nav = read("sitenav.html").replace('href="../"', 'href="../../README.md"').replace('>super-board</a>', '>agent-dotfiles</a>')
    icon = '<svg class="ni" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="6" height="6" rx="1"/><rect x="15" y="15" width="6" height="6" rx="1"/><path d="M6 9v9h9M9 6h9v9"/></svg>'
    nav = nav.replace("%%MAPNAV%%", '<a class="lk" href="index.html" aria-label="Catalog map">' + icon + '<span class="nl">Catalog map</span></a><a class="lk" href="workflow.html" aria-label="AK SDLC map" aria-current="page">' + icon + '<span class="nl">AK SDLC map</span></a>')
    nav = nav.replace('href="https://github.com/EricTechPro/super-board"', 'href="https://github.com/hwanjjang/agent-dotfiles"')
    order = "".join(f'<div class="step {color}"><i>{html.escape(number)}</i><span><b>{html.escape(title)}</b><small>{html.escape(summary)}</small></span></div>'
                    for number, title, summary, color in model["order"])
    values = {"TITLE": html.escape(model["title"]), "PLOGO": "", "FAV": "", "VERSION": html.escape(model["version"]),
              "SUBTITLE": model["subtitle"], "NAV": nav, "FILTER": "", "TOOLS": "", "SVG": model["svg"],
              "LEGEND": "", "ORDER": order, "FOOTER": model["footer"],
              "SHELLCSS": read("shell.css") + "\n:root{--mapw:%dpx}" % model["mapw"],
              "SMCSS": read("skillmap.css"), "PAGECSS": model["css"], "SMJS": read("skillmap.js"),
              "PAGEJS": model["js"], "SHELLJS": read("shell.js"), "CANVASJS": read("canvas.js")}
    output = (directory / "workflow.template.html").read_text(encoding="utf-8")
    for key, value in values.items():
        output = output.replace("%%" + key + "%%", value)
    require(not re.search(r"%%[A-Z]+%%", output), "unfilled template marker")
    license_notice = "<!-- Map engine: Eric Tech / super-board.\n" + read("LICENSE") + "-->\n"
    return output.replace("<html", license_notice + "<html", 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail on missing or stale workflow HTML")
    args = parser.parse_args()
    try:
        output = build(ROOT)
        path = ROOT / "docs/map/workflow.html"
        if args.check:
            require(path.exists() and path.read_bytes() == output.encode(),
                    "workflow map is stale; run python3 scripts/build_workflow.py")
            print("AK SDLC workflow map is current.")
        else:
            path.write_bytes(output.encode())
            print("Built docs/map/workflow.html.")
    except (ValueError, OSError, TypeError, KeyError, SyntaxError) as error:
        print(f"Workflow map build failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
