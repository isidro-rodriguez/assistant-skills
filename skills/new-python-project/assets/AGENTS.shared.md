<!-- shared:start — managed by assistant-skills/new-python-project (scaffold.py sync). Edit there, not here. -->
## Shared rules

**Language.** Code and identifiers in English. Docstrings, comments, README, `docs/`,
CHANGELOG, commits and user-facing messages in Spanish. This file stays in English.

**Tools.** `uv` only, never `pip install`; run everything from the project root.
Quality gate: `uv run ruff format --check .`, `uv run ruff check .`, `uv run ty check`,
`uv run pytest`. The same gate as `poe check`, if Poe the Poet is installed globally; poe is
never a project dependency, and everything must also work with plain `uv run`.

**Workflow.**

1. Read `README.md`, `pyproject.toml`, this file and the related tests before changing code.
2. Make the smallest change that solves the task: no unrelated refactors, no formatting of
   untouched files, no new dependency without a reason (prefer the standard library).
3. Don't change CI, tool configuration or project structure unless the task needs it.
4. Don't run a failing command more than twice: stop, give the root cause and the exact error,
   propose the minimal fix and ask.
5. Don't run state-changing git commands (commit, push, tag, reset, rebase) unless the user
   asks or the commit policy in **Project rules** allows it. Never `--no-verify`.
6. Leave no secrets, temporary files or TODOs without context. Never hand-edit `uv.lock`.

**Code.** Strict type hints on every signature. Google-style docstrings: complete for public
identifiers, one line for private ones; a public docstring's `Raises` also lists the
exceptions raised by the private functions it calls. Comments explain the *why*. Prefer
simple, explicit code; `pathlib` over `os.path`. Ruff and ty enforce the rest; don't fight
them with ignores.

**Tests.** `pytest` in `tests/`. Cover relevant logic and every fixed bug; they must pass on
Linux and Windows.

**Commits.** Conventional Commits in Spanish (`feat:`, `fix:`, `docs:`, `test:`,
`refactor:`, `chore:`), one intent per commit, explaining the *why*.

**Releases.** Only for versioned projects (a real version and `CHANGELOG.md`). Before
pushing changes to the package, use the `python-release` skill. Without it: SemVer bump,
`## [Unreleased]` → `## [X.Y.Z] - YYYY-MM-DD` in `CHANGELOG.md`, `uv lock`, then
`chore: bump versión a X.Y.Z`. Never tag without confirmation.

**Done** when the quality gate and any extra gate in **Project rules** pass, and the README
and docs reflect any change in usage.

Project rules below take precedence over these. Shared rules change in assistant-skills
(`scaffold.py sync`), not by hand here.
<!-- shared:end -->
