---
name: new-python-project
description: Start a new Python project from acodo-template (uv, ruff, ty, pytest, CI, CHANGELOG, backup script) with the package renamed and an AGENTS.md built from the shared rules, or bring an existing repo's CLAUDE.md/AGENTS.md onto those shared rules and keep them in sync. Use it when the user asks to create, start or scaffold a Python project, CLI or library ("crea un proyecto", "nuevo repo Python", "inicializa con la plantilla"), or to migrate, slim down, unify or update the agent instructions (CLAUDE.md/AGENTS.md) of their Python repos.
license: MIT
compatibility: Python 3.11+, git; uv to lock and run the quality gate. Clones https://github.com/isidro-rodriguez/acodo-template unless --template points to a local copy.
metadata:
  version: "0.1.0"
  author: isidro-rodriguez
---

# New Python project

Every project of this maintainer shares the same agent rules: language, tools,
workflow, code style, tests, commits, releases and definition of done. They
live once, in `assets/AGENTS.shared.md`. Each repo's `AGENTS.md` holds that
block between `<!-- shared:start -->` and `<!-- shared:end -->`, followed by
its own **Project rules**. `CLAUDE.md` is a one-line `@AGENTS.md` import, so
every agent reads the same file without a symlink (symlinks break on Windows).

Three jobs:

- **new:** scaffold a project.
- **migrate:** move an existing repo onto the shared block.
- **sync:** refresh the shared block after it changes.

## Inputs

| Input | Required | Default if missing |
|---|---|---|
| Job | yes | Infer it: "crea/nuevo" → new; an existing repo with its own CLAUDE.md → migrate; "actualiza las reglas" → sync |
| Project name (new) | yes | Ask. It must be lowercase kebab-case; the package becomes snake_case |
| One-line description (new) | no | Ask if it isn't obvious from the request; it goes into `pyproject.toml`, the README and `AGENTS.md` |
| Destination folder (new) | no | `./<name>` |
| Python version (new) | no | 3.13 (the template's minimum) |

## Procedure

Scripts run from the skill folder: `python scripts/scaffold.py <command> …`.

### new

1. Run `new <name> --dest <dir> --description "<text>"`. Add `--template <path>`
   to use a local copy of acodo-template instead of cloning it. The script:
   - copies the template, renames `acodo_template`/`acodo-template` everywhere
     and names the console script after the project;
   - sets version 0.1.0 and a fresh `CHANGELOG.md`;
   - writes `AGENTS.md` and `CLAUDE.md`, runs `git init` and `uv lock`.
2. Rewrite the README introduction for the real project. The template's
   paragraph describes the template, not the new project. Keep the README
   minimal: what it is, installation, usage, quality commands and links.
3. Fill in **Project rules** in `AGENTS.md` with what you know: purpose, any
   structure beyond the template, publishing. Leave the placeholder if
   publishing is undecided. Don't edit the shared block: changes made there
   are overwritten on the next sync, and the other repos never see them.
4. Run `uv sync` and the quality gate (`poe check`, or the four `uv run`
   commands). It must pass before you report back.
5. Don't commit. Report what was created and propose
   `chore: estructura inicial desde acodo-template`.

### migrate (existing repo)

The goal is a shorter `AGENTS.md` that keeps every rule the repo really needs.

1. Read the repo's current `CLAUDE.md` and/or `AGENTS.md`, `pyproject.toml`
   and README.
2. Sort every rule into one of three groups:
   - **Covered by the shared block:** drop it. Compare meaning, not wording.
   - **Specific to this repo** (structure, domain conventions, content rules,
     extra quality gates, deploy and publishing, commit policy, "don't touch"
     files): keep it under **Project rules**, tightened but not reworded into
     something else.
   - **Conflicting with the shared block:** keep the project's version under
     Project rules, which take precedence, and list each conflict in your
     report so the user can decide whether it should become shared.
3. Write the new `AGENTS.md`: a title and one-line purpose, then the shared
   block verbatim (copy `assets/AGENTS.shared.md`, markers included), then
   `## Project rules`. Replace `CLAUDE.md` with `assets/CLAUDE.md` (`@AGENTS.md`).
   If the repo's README says where the agent rules live, update that line.
4. Run `scaffold.py check <repo>`, which must say OK. Then run the repo's own
   quality gate to confirm nothing in the code changed.
5. Report: lines before and after, what moved where, any rules dropped as
   covered (one line each), and the conflicts. Don't commit unless the
   project's rules allow it; propose `docs: migra CLAUDE.md a AGENTS.md con
   reglas compartidas`.

### sync

1. For each repo, run `scaffold.py sync <repo>`, then `check <repo>`.
2. Show the diff. It should only touch the shared block. Commit only per the
   project's policy, using `docs: actualiza reglas compartidas de AGENTS.md`.

## Output

- **new:** a project folder that passes its quality gate, with `AGENTS.md`
  (shared block + Project rules), `CLAUDE.md` = `@AGENTS.md`, version 0.1.0,
  `CHANGELOG.md` with `[Unreleased]`, an initialised git repo with nothing
  committed, and a short report.
- **migrate / sync:** the updated `AGENTS.md` and `CLAUDE.md`, `check` OK, and
  a report with the line counts, the rules dropped as covered and the
  conflicts.

## Verification

- [ ] `scaffold.py check <dir>` prints OK.
- [ ] `CLAUDE.md` contains `@AGENTS.md` and nothing that contradicts it.
- [ ] **new:** no `acodo_template`/`acodo-template` left outside `CHANGELOG.md`; the quality gate passes; the README describes the new project.
- [ ] **migrate:** every repo-specific rule of the old file is still present (in Project rules) or reported as covered or conflicting. Nothing was silently lost.
- [ ] Nothing committed or pushed beyond what the project's rules and the user allowed.
