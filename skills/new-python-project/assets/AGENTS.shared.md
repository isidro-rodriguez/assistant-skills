<!-- shared:start — managed by assistant-skills/new-python-project (scaffold.py sync). Edit there, not here. -->
## Language

- **Code and identifiers in English**: variables, functions, classes, modules and tests.
- **Human-facing text in Spanish**: docstrings, comments, README, `docs/`, CHANGELOG, commits
  and messages shown to users. Exception names and internal identifiers stay in English.
- This file is in English so the agent does not need to translate instructions.

## Tools and canonical commands

`uv` only: never `pip install`. Run everything from the project root.

```bash
uv sync                      # install the project and its dev group
uv add <pkg>                 # runtime dependency (uv add --dev <pkg> for dev)
uv run ruff format .
uv run ruff check .
uv run ty check
uv run pytest
```

Optional Poe the Poet shortcuts (`uv tool install poethepoet`) live in `[tool.poe]`:
`poe check` (format check, lint, types, tests), `poe fix`, `poe backup`. Poe is not a project
dependency: CI, hooks and docs must work with plain `uv run`.

## Agent workflow

1. Before changing anything, read `README.md`, `pyproject.toml`, this file and the related tests.
2. Make the smallest change that solves the task. Do not refactor unrelated code or format
   unrelated files.
3. New dependency only with a reason; if the standard library solves it, use that.
4. Do not change CI, tool configuration (Ruff, ty, pytest) or the project structure unless the
   task requires it.
5. Do not re-run a failing command more than twice: stop, state the root cause and the exact
   error, and propose the minimal fix.
6. Do not leave secrets, temporary files or TODOs without context.
7. If you cannot ask, choose the minimal change and state the assumption in your report.

## Code rules

- PEP 8, idiomatic Python, strict type annotations on every signature; `pathlib` over `os.path`.
- Google-style docstrings: complete for public identifiers (with an example when it helps),
  one line for private ones. A public docstring lists in `Raises` what it lets propagate.
- Comments explain the *why*, never the *what*.
- Prefer simple, explicit code over abstractions; small functions with clear English names.

## Tests

- `pytest`, files in `tests/`, run with `uv run pytest` from the root.
- Cover relevant logic and every fixed bug. Useful, readable tests over coverage numbers.
- Tests must pass on Linux and Windows.

## Commits

- Conventional Commits in Spanish (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`),
  atomic, explaining the *why*. Do not mix unrelated changes.
- Never use `git commit --no-verify` unless the user asks.
- Commit policy for this project: see **Project rules** below.

## Releases

Versioned projects (a real version and `CHANGELOG.md`): before pushing changes that affect the
package, prepare the release with the **`python-release`** skill. Without that skill: bump the
version (SemVer), move `## [Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD` in `CHANGELOG.md`
(Keep a Changelog, Spanish), run `uv lock`, and commit `chore: bump versión a X.Y.Z`.
Never create or push tags without explicit confirmation. How the project publishes: see
**Project rules**.

## Definition of done

- `poe check` passes (or `uv run ruff format --check .`, `uv run ruff check .`,
  `uv run ty check` and `uv run pytest`), plus any extra gate listed in **Project rules**.
- README and docs updated if usage or the public API changed.

## Limits

- Do not modify this file without a justified reason; shared sections change in
  assistant-skills, not here.
- Do not hand-edit `uv.lock`; regenerate it with `uv`.
- Do not add unnecessary dependencies or rewrite code the task does not need.
<!-- shared:end -->
