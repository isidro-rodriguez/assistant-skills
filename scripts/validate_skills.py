#!/usr/bin/env python3
"""Validate every skills/*/SKILL.md against the Agent Skills spec + repo rules.

Usage: python scripts/validate_skills.py [skills_dir]
Exit code 1 if any skill fails.
"""
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("Missing dependency: pip install pyyaml")

ALLOWED_FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_BODY_LINES = 500


def parse(path: Path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        raise ValueError("missing YAML frontmatter delimited by ---")
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


def check(skill_dir: Path) -> list[str]:
    errors = []
    md = skill_dir / "SKILL.md"
    if not md.exists():
        return ["SKILL.md not found"]
    try:
        fm, body = parse(md)
    except Exception as e:  # noqa: BLE001
        return [f"frontmatter: {e}"]

    extra = set(fm) - ALLOWED_FIELDS
    if extra:
        errors.append(f"non-standard fields (move under metadata): {sorted(extra)}")

    name = fm.get("name")
    if not isinstance(name, str) or not NAME_RE.match(name) or len(name) > 64:
        errors.append("name must be kebab-case, ≤64 chars")
    elif name != skill_dir.name:
        errors.append(f"name '{name}' must match folder '{skill_dir.name}'")

    desc = fm.get("description")
    if not isinstance(desc, str) or not desc.strip():
        errors.append("description is required")
    elif len(desc) > 1024:
        errors.append(f"description too long ({len(desc)} > 1024)")

    comp = fm.get("compatibility")
    if comp is not None and (not isinstance(comp, str) or len(comp) > 500):
        errors.append("compatibility must be a string ≤500 chars")

    if "metadata" in fm and not isinstance(fm["metadata"], dict):
        errors.append("metadata must be a mapping")

    if len(body.splitlines()) > MAX_BODY_LINES:
        errors.append(f"SKILL.md body over {MAX_BODY_LINES} lines; move content to references/")

    for section in ("## Inputs", "## Procedure", "## Output", "## Verification"):
        if section not in body:
            errors.append(f"missing section '{section}'")

    evals = skill_dir / "evals" / "evals.json"
    if not evals.exists():
        errors.append("evals/evals.json missing")
    else:
        try:
            data = json.loads(evals.read_text(encoding="utf-8"))
            if not data.get("evals"):
                errors.append("evals/evals.json has no cases")
        except json.JSONDecodeError as e:
            errors.append(f"evals/evals.json invalid JSON: {e}")

    # Relative file references in the body must exist.
    for ref in re.findall(r"`((?:scripts|references|assets|evals)/[^`\s]+)`", body):
        if not (skill_dir / ref).exists():
            errors.append(f"referenced file not found: {ref}")
    return errors


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent.parent / "skills")
    skills = sorted(p for p in root.iterdir() if p.is_dir())
    if not skills:
        print(f"No skills found in {root}")
        return 1
    failed = 0
    for d in skills:
        errs = check(d)
        status = "OK " if not errs else "FAIL"
        print(f"[{status}] {d.name}")
        for e in errs:
            print(f"       - {e}")
        failed += bool(errs)
    print(f"\n{len(skills) - failed}/{len(skills)} skills valid")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
