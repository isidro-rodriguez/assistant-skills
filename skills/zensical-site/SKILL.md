---
name: zensical-site
description: Create, migrate, check and upgrade a Zensical documentation site with one canonical layout — zensical.toml, docs/ with assets (favicon set, fonts, stylesheets) and site.webmanifest, docs_templates/ (main.html with favicons, manifest and theme colour; Spanish mkdocstrings templates), optional GitHub Pages workflow — a starting typography and theme, and a browser measurement that holds every site to Practical Typography's readability ranges (15–25 px text, 120–145 % line spacing, 45–90 characters per line), whatever its fonts. Use it when the user wants documentation, a website or GitHub Pages for a project ("añade documentación", "web del proyecto", "monta Zensical"), wants an existing docs/ brought onto the common layout, mentions favicons, webmanifest or docs_templates, or wants to update Zensical or fix a build broken by a Zensical release (Dependabot bump, theme moved, overridden template changed).
license: MIT
compatibility: Python 3.11+ (tomllib) and uv. Favicons need Pillow, plus resvg-py for SVG logos (`uv run --with pillow --with resvg-py`); `measure` needs Playwright and Chrome, Edge or `playwright install chromium` (`uv run --with playwright`); none of them enter the project's lock. `upgrade` needs network access (uv, PyPI).
metadata:
  version: "0.2.0"
  author: isidro-rodriguez
---

# Zensical site

Every project's documentation site has the same layout, the same head
(favicons, manifest, theme colour) and the same build gate, so any repo can be
checked against it and upgraded the same way. New sites start from a common
typography and theme; after that the fonts and the look are the project's,
but every site must stay readable by *Practical Typography*'s measures, which
`measure` checks in a real browser. The canonical layout is in
`references/layout.md`; the typography rules in `references/typography.md`.

Works alone (reCocina is not a Python package) or next to `new-python-project`:
that skill owns `AGENTS.md`'s shared block, this one adds a
`<!-- zensical:start -->` block inside the project rules, which `scaffold.py sync`
leaves alone.

## Inputs

| Input | Required | Default if missing |
|---|---|---|
| Project folder | yes | the current repo |
| Mode: `new`, `migrate`, `check`, `upgrade` | yes | infer: no `zensical.toml` → new; "update/bump Zensical" or a failing Dependabot PR → upgrade; otherwise migrate |
| Site name, one-line description (Spanish), author | new | `pyproject.toml` (`name`, `description`, `authors`) |
| Repo URL | new | `git remote get-url origin` |
| Site URL | new | GitHub Pages URL derived from the repo URL |
| Theme colour `#rrggbb` | new | ask; on migrate, take it from the current `theme-color` meta or manifest |
| Logo (SVG or PNG, square) | new | ask; on migrate, the current `theme.logo` |
| Python package for API docs | no | `src/<package>` if the project has one and wants an API reference |
| Publish with GitHub Pages | new | **ask** when the repo is not on GitHub or deploys elsewhere (Vercel); otherwise yes |

`S` below is this skill's folder; run the script from the project root.

## Procedure

### new

1. Gather the inputs; ask only for what can't be read from the repo.
2. Create the layout:
   ```bash
   uv run --with pillow --with resvg-py python S/scripts/site.py new . \
     --name NAME --description TEXT --author AUTHOR --repo-url URL \
     --theme-color '#rrggbb' --logo PATH [--package PKG] [--no-gh-pages]
   ```
   It never overwrites existing files (`--force` does) and prints what it wrote.
3. Add the tools as dev dependencies: `uv add --dev zensical`, plus
   `mkdocstrings-python mkdocs-api-autonav` with `--package`.
4. Put the project's palette in `docs/assets/stylesheets/<slug>.css`. The starting
   `typography.css` and fonts are the project's from now on: change them there if
   the project wants another look. Fill `nav` and `docs/index.md` with real content.
5. Verify (below). On GitHub, remind the user to set **Settings → Pages →
   Source: GitHub Actions** once; that can't be done from the repo.

### migrate (existing docs/)

1. `python S/scripts/site.py check .` — the list of gaps is the work list.
2. `python S/scripts/site.py sync .` — copies `es.html.jinja` (with mkdocstrings)
   and the AGENTS.md block.
3. Edit `zensical.toml` by hand, keeping comments and project choices:
   `custom_dir = "docs_templates"`, `favicon = "assets/favicon/favicon-32x32.png"`,
   `[project.extra] theme_color`. Keep the project's fonts, `features`, palette,
   extensions and plugins: only the structure is canonical.
4. Favicons: `git mv` existing ones into `docs/assets/favicon/` with the
   canonical names, then `uv run --with pillow --with resvg-py python
   S/scripts/site.py favicons . --logo LOGO --missing-only` for the rest. Fix
   every path that pointed to the old location (manifest, templates, tests,
   service worker precache lists).
5. `docs_templates/main.html`: put the canonical `extrahead` block in it, merged
   with any project blocks. When `main.html` extends a local page template
   (reCocina: `main.html → page.html → base.html`), the block goes in that root
   template so every page gets it.
6. `docs/site.webmanifest`: relative icon paths, `"start_url": "./"`, same
   `theme_color`.
7. Workflow: if `.github/workflows/docs.yml` exists, compare it with
   `S/assets/site/.github/workflows/docs.yml` and take the canonical one unless the
   project has steps of its own (atril's screenshots, a `workflow_call`): then
   only align the shared steps. Never add a Pages workflow to a project that
   deploys elsewhere.
8. Build and run `measure` (below). Fix every FAIL in the project's own
   stylesheet, keeping its fonts: usually `line-height` (the theme uses 160–180 %)
   and a `max-width` in `ch` on paragraphs, lists, quotes and admonitions, tuned
   until the measured line length is near 75 characters. Don't copy the starting
   `typography.css` into an existing site unless the user asks for the common look.
9. Remove what the canonical layout replaced (old favicon copies) and verify.

### check

`python S/scripts/site.py check .` — layout only; exit 1 on any FAIL. Report FAILs
and WARNs; INFO lines (customised `main.html` or workflow) are expected in
projects with their own templates.

### measure (readability)

After `uv run zensical build`:
`uv run --with playwright python S/scripts/site.py measure .` opens the home page
and the largest pages at 1280 and 1920 px wide and measures the body paragraphs
(median per page): text 15–25 px, line spacing 120–145 %, 45–90 characters per
line. Exit 1 on any page out of range. It names the body fonts and warns about
system fonts (Arial, Times New Roman…), but any font passes.

### upgrade (new Zensical release, failing Dependabot PR)

1. Start from a clean tree on a new branch; `uv sync` so the installed theme is
   the current one.
2. `python S/scripts/site.py upgrade . [--to X.Y.Z]` — snapshots the theme,
   moves an exact `zensical==` pin in `pyproject.toml`, runs `uv lock
   --upgrade-package zensical` and `uv sync`, then reports per template in
   `docs_templates/`:
   - `ok … all its blocks still exist` / `upstream unchanged`: nothing to do;
   - `REVIEW … upstream changed`: a whole-file override (e.g. `partials/header.html`)
     whose original changed: port the shown diff into the override, keeping the
     project's own changes;
   - `REVIEW … blocks no longer exist` or `… override is dead`: rewrite it;
   - `REVIEW tests/… old theme package`: make the code look in the new package
     first (the theme moved from `zensical` to `zensical_ui` in 0.1).
   It then builds (`--strict` when the project builds strictly) and exits 1 if
   anything needs review.
3. Fix every REVIEW item, then run the project's full gate (its tests may read the
   theme too) and the build chain it really uses (`vercel.json`, Poe tasks).
4. Commit the lock and the template fixes as separate intents
   (`chore: actualiza zensical a X.Y.Z`, `fix: adapta … al tema nuevo`).

## Output

- **new / migrate**: the files written or changed, and a final `check` with no FAIL.
- **check**: FAIL/WARN/INFO lines and a count.
- **upgrade**: old → new version, one line per template, the build result, and
  the changes made for each REVIEW item.

Then follow the project's commit policy: never commit or push unless it allows it.

## Verification

1. `uv run zensical build` ends with "No issues found" (with `--strict` where the
   project uses it).
2. `python S/scripts/site.py check .` reports no FAIL.
3. `measure` reports no FAIL.
4. `site/index.html` has the favicon links, `site.webmanifest` and the
   `theme-color` meta.
5. Look at one page (`uv run zensical serve` or a headless screenshot): headings
   clearly distinct from the text, tables and code at full width, nothing clipped.
6. The project's own quality gate still passes.
