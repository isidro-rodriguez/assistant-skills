---
name: skill-name
description: One sentence on what this skill does, then when to use it — list concrete triggers (user phrases, file types, tasks). Max 1024 characters.
license: MIT
compatibility: List runtime requirements (e.g. Python 3.9+, packages, CLI tools). Delete if none.
metadata:
  version: "0.1.0"
  author: isidro-rodriguez
---

# Skill Title

One or two sentences: the outcome this skill guarantees.

## Inputs

What the agent needs before starting. For each, say what to do if it's missing
(ask, or use the stated default).

| Input | Required | Default if missing |
|---|---|---|
| … | yes/no | … |

## Procedure

Numbered, verifiable steps. Reference bundled files by relative path
(`scripts/…`, `references/…`, `assets/…`).

1. …
2. …

## Output

The exact shape of the deliverable: file type, name pattern, sections, format.

## Verification

Checklist the agent must pass before delivering. Prefer automated checks
(`scripts/…`) over judgment.

- [ ] …

## References

- `references/…` — when to read it.
