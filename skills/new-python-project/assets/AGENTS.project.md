## Project rules

### Structure

```
.
├── .github/                # CI (ubuntu + windows) and Dependabot
├── AGENTS.md               # This file (CLAUDE.md imports it)
├── CHANGELOG.md            # Keep a Changelog, Spanish
├── pyproject.toml          # Project, dependencies and tool configuration
├── uv.lock                 # Lockfile, tracked by git
├── scripts/backup.py       # poe backup: git bundle of the repository
├── src/{package}/          # Source code; __init__.py exposes __version__
└── tests/                  # pytest
```

- Python {python}+. `acodo` is the utility library (`acodo>=0.3,<1`); use it before writing
  helpers of your own.
- Every `__init__.py` has a short docstring. `README.md` stays minimal: what it is,
  installation, usage, quality commands and links.

### Commit policy

Never commit automatically: report the result and wait for confirmation.

### Publishing

Not published yet. When it is, describe here how (PyPI on push, `vX.Y.Z` tag, manual
workflow) and which files are the public page (for example `README.md` on PyPI).
