# assistant-skills

Personal library of agent skills. The goal: stop rewriting the same context
boilerplate for every agent task, and make recurring tasks repeatable and
predictable.

Skills follow the open [Agent Skills specification](https://agentskills.io/specification),
so they work in Claude (Claude Code, claude.ai) and in other capable assistants
that read `SKILL.md` (Codex, Gemini CLI, Cursor, etc.).

## Catalog

| Skill | What it does |
|---|---|
| [`typeset-pdf`](skills/typeset-pdf/SKILL.md) | Turns Markdown/HTML into a well-typeset PDF following Butterick's *Practical Typography*, as a casual document or a formal report (cover, contents, numbered headings): 75 characters per line, LaTeX math, Mermaid flowcharts, wide tables, and an automatic quality check. |

## Layout

```
skills/<skill-name>/      one folder per skill
  SKILL.md                frontmatter + instructions (required)
  scripts/                executable helpers
  references/             docs loaded on demand
  assets/                 templates, stylesheets, static files
  evals/<case>/           test cases: prompt.md, case.yaml, graders/
templates/
  skill-template/         starting point for new skills
  AGENTS.template.md      base always-on context to copy into projects
scripts/validate_skills.py  frontmatter / naming validator (also run in CI)
```

## Installing a skill

Copy or symlink the skill folder into your agent's skills directory:

```bash
# Claude Code (user-level)
ln -s "$PWD/skills/typeset-pdf" ~/.claude/skills/typeset-pdf

# Windows (PowerShell, admin or developer mode)
New-Item -ItemType SymbolicLink -Path "$HOME\.claude\skills\typeset-pdf" -Target "$PWD\skills\typeset-pdf"
```

For claude.ai, upload a packaged `.skill` file under Settings → Capabilities →
Skills. Build it with skill-creator's `package_skill.py` (it leaves out
`evals/`, `node_modules/` and caches), or zip the skill folder without those.

## Creating a new skill

1. Copy `templates/skill-template/` to `skills/<new-name>/`.
2. Fill in every section of `SKILL.md`; delete the folders you don't use.
3. Write 2–3 test cases as `evals/<case-name>/` folders (see the template's
   `example-case`).
4. Run `python scripts/validate_skills.py`.
5. Test and iterate with the skill-creator workflow described in `AGENTS.md`.

## Skills vs. always-on context

- **Always-on context** (who I am, working modes, language, output format) goes
  in an `AGENTS.md` per project — start from `templates/AGENTS.template.md`.
- **Skills** hold procedures that are loaded only when a task needs them.
