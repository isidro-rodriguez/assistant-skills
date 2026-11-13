# AGENTS.md — working in this repository

Instructions for any agent (Claude, GPT, Gemini…) editing this repo.

## Purpose

A library of portable agent skills. Each skill must make a recurring task
**repeatable and predictable**: same inputs → same procedure → same output shape.

## Conventions

- **Spec:** follow <https://agentskills.io/specification>. Frontmatter uses only
  standard fields: `name`, `description`, `license`, `compatibility`,
  `metadata`, `allowed-tools`. Put anything else under `metadata`.
- **Language:** skills, scripts and docs in English. Conversation with the
  maintainer may be in Spanish.
- **Naming:** `name` = folder name, kebab-case, ≤ 64 chars.
- **Description:** says what the skill does *and when to use it* (concrete
  triggers), ≤ 1024 chars.
- **Structure of every `SKILL.md`:** Inputs → Procedure → Output → Verification.
  Start from `templates/skill-template/SKILL.md`.
- **Progressive disclosure:** keep `SKILL.md` under ~500 lines; move long
  material to `references/`, one level deep (no reference chains).
- **Scripts:** Python 3.9+, standard CLI (`--help`), deterministic, non-zero
  exit code on failure. Declare dependencies in `compatibility`.
- **No vendor lock-in:** don't rely on tools only one assistant has unless the
  skill says so in `compatibility`.
- **Evals:** each skill ships `evals/evals.json` with at least one case.

## Before committing

```bash
python scripts/validate_skills.py
```

Update the catalog table in `README.md` when adding a skill.

## Working modes

The maintainer uses four modes; default is **plan** unless told otherwise:

- **ask** — answer the question; change nothing.
- **brainstorm** — give a reasoned opinion on an idea in this project's context.
- **plan** — analyse and lay out how you'd implement it; don't implement.
- **code** — implement directly (also the default for trivial changes).
