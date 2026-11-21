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
- **Scripts:** Python 3.13+ (no older versions), standard CLI (`--help`), deterministic, non-zero
  exit code on failure. Declare dependencies in `compatibility`.
- **No vendor lock-in:** don't rely on tools only one assistant has unless the
  skill says so in `compatibility`.
- **Evals:** each skill ships at least one test case as a folder
  `evals/<case-name>/` with `prompt.md`, `case.yaml` and `graders/` (one
  verifiable statement per file, worded about the result, not the process).
  This is the skill-creator layout, also run by `claude plugin eval`. Input
  files go in the case's `files/` with a `place-files.sh`. Copy
  `templates/skill-template/evals/example-case/`.

## Creating or improving a skill

Use the **skill-creator** skill when the agent has it (Claude: `/skill-creator`):

1. Capture intent and edge cases; draft `SKILL.md` from the template.
2. Write 2–3 realistic test prompts as case folders.
3. Run each case with and without the skill (or with the previous version),
   in independent sub-agents, into `../<skill>-workspace/iteration-N/`
   (outside the repo).
4. Grade with scripts where possible, aggregate the benchmark, and review the
   outputs in the eval viewer before changing anything.
5. Improve the skill and repeat. Explain the *why* behind rules rather than
   piling on MUSTs.
6. Finally, optimise the `description` for triggering (20 should/shouldn't
   trigger queries).

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
