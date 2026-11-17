# CLAUDE.md

## Structure (uv workspace)
- packages/core/src/medida/ — core library
- packages/cli/src/medida_cli/ — Typer CLI
- Always `uv sync --all-packages`; member dependencies go in each member's pyproject.

## Commands
`uv run ruff check .`, `uv run ty check`, `uv run pytest`.

## Commits
Conventional Commits in Spanish. Scope by member: `feat(cli): ...`. Never commit automatically.
