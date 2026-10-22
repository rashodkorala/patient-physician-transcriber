#!/usr/bin/env python3
"""Validate the DDSE decision layer in openspec/tdr/ and its links to OpenSpec changes and code.

Checks:
  - record file names, ids, folders, front matter fields, status values, required sections
  - openspec/tdr/index.md lists every record with the right status
  - every TDR id cited in changes, records, guides, and code exists
  - @implements annotations in code point to accepted records
  - TDMs past their expiry date
Reports the human review queue: proposed records and task groups waiting on them.

Usage: python3 scripts/check_tdr.py [--json]
Exit code 1 if any error is found. Standard library only.
"""
import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TDR_DIR = ROOT / "openspec" / "tdr"
CHANGES_DIR = ROOT / "openspec" / "changes"
TYPES = ("mdd", "adr", "cdr", "edr", "idr", "tdm")
STATUSES = {"proposed", "accepted", "rejected", "superseded", "deprecated"}
REQUIRED_FIELDS = ("id", "title", "status", "date", "authors", "reviewers", "decision_owner",
                   "proposed_by", "category", "related_decisions", "ai_context")
AI_CONTEXT_KEYS = ("implementation_priorities", "framework_hints", "validation_rules")
REQUIRED_SECTIONS = ("Summary", "Context", "Decision", "Alternatives Considered", "Consequences", "Implementation")
CDR_SECTIONS = ("Contract Specification", "Data Schemas", "Evolution Strategy", "Testing Requirements")
FILE_RE = re.compile(r"^(mdd|adr|cdr|edr|idr|tdm)-(\d{3})-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
REF_RE = re.compile(r"\b(MDD|ADR|CDR|EDR|IDR|TDM)-(\d{3})\b")
IMPLEMENTS_RE = re.compile(r"@implements\s+(MDD|ADR|CDR|EDR|IDR|TDM)-(\d{3})")
CODE_DIRS = ("server", "web")
CODE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx"}


def parse_front_matter(text):
    """Parse the simple YAML subset used by TDR front matter."""
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text
    lines = text[4:end].splitlines()
    data, parent, last_key = {}, None, None
    for raw in lines:
        line = raw.split(" #", 1)[0].rstrip() if not raw.strip().startswith("- ") else raw.rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        target = data[parent] if (parent and indent > 0) else data
        if indent == 0:
            parent = None
        if stripped.startswith("- "):
            item = stripped[2:].strip().strip('"')
            if last_key is not None and isinstance(target.get(last_key), list):
                target[last_key].append(item)
            continue
        key, _, value = stripped.partition(":")
        key, value = key.strip(), value.strip()
        if value == "":
            if indent == 0:
                data[key] = {}
                parent, last_key = key, key
            else:
                target[key] = []
                last_key = key
            continue
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            target[key] = [v.strip().strip('"') for v in inner.split(",")] if inner else []
        else:
            target[key] = value.strip('"')
        last_key = key
    return data, text[end + 5:]


def load_records(errors, warnings):
    records = {}
    for folder in TYPES + ("archived",):
        for path in sorted((TDR_DIR / folder).glob("*.md")):
            rel = path.relative_to(ROOT).as_posix()
            m = FILE_RE.match(path.name)
            if not m:
                errors.append(f"{rel}: file name must be <type>-<NNN>-<kebab-title>.md")
                continue
            rtype, num = m.group(1), m.group(2)
            if folder != "archived" and folder != rtype:
                errors.append(f"{rel}: {rtype.upper()} record is in the {folder}/ folder")
            fm, body = parse_front_matter(path.read_text(encoding="utf-8"))
            if fm is None:
                errors.append(f"{rel}: missing or malformed front matter")
                continue
            rid = f"{rtype}-{num}"
            if fm.get("id") != rid:
                errors.append(f"{rel}: id '{fm.get('id')}' does not match file name '{rid}'")
            for field in REQUIRED_FIELDS:
                if field not in fm:
                    errors.append(f"{rel}: missing front matter field '{field}'")
            status = fm.get("status")
            if status not in STATUSES:
                errors.append(f"{rel}: status '{status}' not in {sorted(STATUSES)}")
            if folder == "archived" and status not in ("superseded", "deprecated", "rejected"):
                warnings.append(f"{rel}: archived record has status '{status}'")
            if fm.get("proposed_by") not in ("human", "agent"):
                errors.append(f"{rel}: proposed_by must be 'human' or 'agent'")
            try:
                datetime.date.fromisoformat(str(fm.get("date")))
            except ValueError:
                errors.append(f"{rel}: date '{fm.get('date')}' is not YYYY-MM-DD")
            ai = fm.get("ai_context")
            if isinstance(ai, dict):
                for k in AI_CONTEXT_KEYS:
                    if k not in ai:
                        errors.append(f"{rel}: ai_context missing '{k}'")
            elif ai is not None:
                errors.append(f"{rel}: ai_context must be a mapping")
            if rtype == "tdm":
                exp = fm.get("expires")
                try:
                    if datetime.date.fromisoformat(str(exp)) < datetime.date.today() and status == "accepted":
                        warnings.append(f"{rel}: TDM expired on {exp}; renew, promote, or deprecate it")
                except ValueError:
                    errors.append(f"{rel}: TDM needs 'expires: YYYY-MM-DD'")
            headings = set(re.findall(r"^## (.+?)\s*$", body, flags=re.M))
            needed = REQUIRED_SECTIONS + (CDR_SECTIONS if rtype == "cdr" else ())
            for sec in needed:
                if sec not in headings:
                    errors.append(f"{rel}: missing section '## {sec}'")
            if rid in records:
                errors.append(f"{rel}: duplicate id {rid.upper()}")
            records[rid] = {"path": rel, "status": status, "title": fm.get("title"),
                            "related": fm.get("related_decisions") or []}
    return records


def check_index(records, errors):
    index = TDR_DIR / "index.md"
    if not index.exists():
        errors.append("openspec/tdr/index.md is missing")
        return
    listed = {}
    for line in index.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*\[(\w{3}-\d{3})\]\([^)]+\)\s*\|.*\|\s*(\w+)\s*\|[^|]*\|[^|]*\|\s*$", line)
        if m:
            listed[m.group(1).lower()] = m.group(2)
    for rid, rec in records.items():
        if rid not in listed:
            errors.append(f"index.md: {rid.upper()} is not listed")
        elif listed[rid] != rec["status"]:
            errors.append(f"index.md: {rid.upper()} status '{listed[rid]}' but record says '{rec['status']}'")
    for rid in listed:
        if rid not in records:
            errors.append(f"index.md: {rid.upper()} listed but no record file exists")


def scan_files():
    files = list(CHANGES_DIR.rglob("*.md"))
    files += [p for p in TDR_DIR.rglob("*.md") if "templates" not in p.parts]
    files += [p for p in (ROOT / "AGENTS.md", ROOT / "README.md") if p.exists()]
    for d in CODE_DIRS:
        base = ROOT / d
        if base.exists():
            files += [p for p in base.rglob("*") if p.suffix in CODE_SUFFIXES
                      and "node_modules" not in p.parts and ".venv" not in p.parts]
    return files


def check_references(records, errors):
    for path in scan_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel = path.relative_to(ROOT).as_posix()
        for t, n in set(REF_RE.findall(text)):
            if f"{t.lower()}-{n}" not in records:
                errors.append(f"{rel}: cites {t}-{n}, which does not exist")
        if path.suffix in CODE_SUFFIXES:
            for t, n in set(IMPLEMENTS_RE.findall(text)):
                rec = records.get(f"{t.lower()}-{n}")
                if rec and rec["status"] != "accepted":
                    errors.append(f"{rel}: @implements {t}-{n} but its status is '{rec['status']}'")
    for rid, rec in records.items():
        for parent in rec["related"]:
            if parent and parent.lower() not in records:
                errors.append(f"{rec['path']}: related_decisions lists '{parent}', which does not exist")


def review_queue(records):
    pending = sorted(r.upper() for r, rec in records.items() if rec["status"] == "proposed")
    blocked = []
    for tasks in sorted(CHANGES_DIR.glob("*/tasks.md")):
        group = None
        for line in tasks.read_text(encoding="utf-8").splitlines():
            h = re.match(r"^## (.+)$", line)
            if h:
                group = h.group(1).strip()
                continue
            m = re.match(r"^TDRs:\s*(.+)$", line.strip())
            if m and group:
                ids = [i.strip() for i in m.group(1).split(",")]
                waiting = [i for i in ids if records.get(i.lower(), {}).get("status") != "accepted"]
                if waiting and not group.startswith("0."):
                    blocked.append({"change": tasks.parent.name, "group": group, "waiting_on": waiting})
    return pending, blocked


def main():
    errors, warnings = [], []
    records = load_records(errors, warnings)
    check_index(records, errors)
    check_references(records, errors)
    pending, blocked = review_queue(records)
    if "--json" in sys.argv:
        print(json.dumps({"records": len(records), "errors": errors, "warnings": warnings,
                          "awaiting_human_review": pending, "blocked_task_groups": blocked}, indent=2))
    else:
        counts = {}
        for rec in records.values():
            counts[rec["status"]] = counts.get(rec["status"], 0) + 1
        print(f"TDR records: {len(records)} ({', '.join(f'{v} {k}' for k, v in sorted(counts.items()))})")
        for w in warnings:
            print(f"WARNING  {w}")
        for e in errors:
            print(f"ERROR    {e}")
        if pending:
            print(f"\nAwaiting human review ({len(pending)}): {', '.join(pending)}")
        for b in blocked:
            print(f"  blocked: {b['change']} / {b['group']} waits on {', '.join(b['waiting_on'])}")
        print("\nOK" if not errors else f"\n{len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
