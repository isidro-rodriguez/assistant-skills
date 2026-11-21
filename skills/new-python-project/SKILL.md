---
name: new-python-project
description: Start a new Python project from acodo-template (uv, ruff, ty, pytest, CI, CHANGELOG, backup script) with the package renamed and an AGENTS.md built from the shared rules, or bring an existing repo's CLAUDE.md/AGENTS.md onto those shared rules and keep them in sync. Use it when the user asks to create, start or scaffold a Python project, CLI or library ("crea un proyecto", "nuevo repo Python", "inicializa con la plantilla"), or to migrate, slim down, unify or update the agent instructions (CLAUDE.md/AGENTS.md) of their Python repos.
license: MIT
compatibility: Python 3.13+, git; uv to lock and run the quality gate. Clones https://github.com/isidro-rodriguez/acodo-template unless --template points to a local copy.
metadata:
  version: "0.3.3"
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

## Procedure

Scripts run from the skill folder: `python scripts/scaffold.py <command> …`.

### new

The template (acodo-template) carries its own `AGENTS.md` (shared block + Project rules
written for a derived project) and marks template-only text in `README.md` and `AGENTS.md`
with `<!-- template-only:start -->` / `<!-- template-only:end -->` lines. The script relies on
that, so improvements to the project rules are made once, in the template.

1. Run `new <name> --dest <dir> --description "<text>"` (`--template <path>` for a local copy).
   The script copies the template without caches or build output, renames
   `acodo_template`/`acodo-template` everywhere (package, project, command, URLs), removes the
   template-only blocks, puts the description under the README title, sets version 0.1.0 and a
   fresh `CHANGELOG.md`, rebuilds `AGENTS.md` from the template's Project rules with the
   current shared block, writes `CLAUDE.md`, runs `git init` and `uv lock`. It refuses to
   finish if a template-only marker is left unbalanced.
2. Read the result with the user's goal in mind: adjust **Project rules** (purpose,
   publishing once decided) and the README usage if the project is not a CLI. Don't edit the
   shared block: changes made there are overwritten on the next sync.
3. If the project needs a documentation site, also use the `zensical-site` skill (`new`)
   now: it adds `docs/` on the techsical theme, the Pages workflow and its own block to the
   Project rules, which `sync` leaves alone. The two skills can be used together or apart.
4. Run `uv sync` and the quality gate (`poe check`, or the four `uv run` commands); it must
   pass before you report back.
5. Don't commit. Report what was created and propose
   `chore: estructura inicial desde acodo-template`.

### migrate (existing repo)

The goal is an `AGENTS.md` that tells an agent the truth about the repo **as it is now**,
with the shared rules in one block and only what is specific underneath. The old file is
evidence, not the source of truth: it can describe a layout that no longer exists (acodo's
still described a monorepo long gone), and rules that matter can live only in configuration
(acodo publishes to PyPI on every push to `main` that touches the package, which only
`publish.yml` said).

1. **Gather the evidence.** Read the old `CLAUDE.md`/`AGENTS.md`, the README, `pyproject.toml`
   (including `[tool.poe]`, `[tool.ruff]`, `[tool.ty]`, build backend), the file tree
   (`git ls-files`), `.github/workflows/*` (CI steps, publishing, docs deploy),
   `.pre-commit-config.yaml` and any deploy config (`vercel.json`…).
2. **Check every old rule against the repo.** For each rule, confirm the paths, commands and
   structure it mentions. A rule is **stale** only when the repo shows it was replaced: the
   layout changed (a workspace became one package, a folder was renamed), a command or flag
   was superseded, a migration it describes is finished. Drop stale rules and list them in the
   report, because an agent would act on them.
   A path that is simply missing is **not** evidence by itself: a rule may describe code that
   is not written yet, or a part this checkout lacks. When the rule states an intent
   (gettext for messages, `Decimal` for money, generated fixtures, how to publish) and nothing
   in the repo contradicts it, keep it and mark it as unverified in the report. Losing a valid
   rule silently is worse than keeping one the user can strike out.
3. **Harvest rules that only live in configuration.** Anything an agent must know to avoid
   a surprise: CI steps stricter than the shared gate (a coverage threshold, a strict
   docs build, extra linters), how and when the project publishes (on push, on tag,
   manual), generated files, extra Poe tasks, deploy chains. Before documenting a flag as
   stricter, check it really changes the result (`ty --error-on-warning`, for instance, is
   already ty's default behaviour and adds nothing).
   Known redundant settings to clean up while migrating, each in its own commit and
   mentioned in the report: `--error-on-warning` on `ty check` in CI or publish workflows
   (`ci: quita --error-on-warning de ty`).
4. **Sort what remains:**
   - **Covered by the shared block:** drop it. Compare meaning, not wording.
   - **Specific to this repo** (purpose, structure, domain conventions, extra gates,
     publishing, commit policy, "don't touch" files): keep it under **Project rules**,
     tightened but not reworded into something else.
   - **Conflicting with the shared block:** keep the project's version under Project rules
     (they take precedence) and list each conflict in the report for the user to decide.
5. **Write the project rules** to a temporary file starting with `## Project rules` (a short
   "what it is" paragraph first, then `###` subsections), and let the script assemble the
   file so the layout is identical in every repo:
   `scaffold.py assemble <repo> --rules <file> --name <name> --description "<one line>"`.
   It writes `AGENTS.md` (header + shared block + your rules) and `CLAUDE.md` (`@AGENTS.md`).
   Update any README or comment that points to `CLAUDE.md`.
6. **Verify.** `scaffold.py check <repo>` says OK, and the repo's full gate (shared + extra
   gates you documented) passes, confirming nothing but the instructions changed.
7. **Report:** lines before → after; stale rules dropped (one line each, with what the repo
   has instead); rules kept but unverified; rules harvested from configuration; rules dropped
   as covered; conflicts.
   Don't commit unless the project's rules allow it; propose
   `docs: migra CLAUDE.md a AGENTS.md con reglas compartidas`.

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
- [ ] **new:** no `acodo_template`/`acodo-template` or template-only text left outside `CHANGELOG.md`; the command is named after the project; the quality gate passes; the README describes the new project.
- [ ] **migrate:** every rule of the old file is kept (verified or not), or reported as covered, stale (with what replaced it) or conflicting — nothing silently lost; every path and command in Project rules exists in the repo; CI-only constraints and the publishing method are documented.
- [ ] Nothing committed or pushed beyond what the project's rules and the user allowed.
