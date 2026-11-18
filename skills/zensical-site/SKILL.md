---
name: zensical-site
description: Create, migrate, check and upgrade a Zensical documentation site built on the techsical theme with one canonical layout — zensical.toml with `name = "techsical"` and `[project.extra.techsical]`, docs/ with the favicon set, logo and site.webmanifest, docs_templates/ only for overrides and the Spanish mkdocstrings templates, optional GitHub Pages workflow. Use it when the user wants documentation, a website or GitHub Pages for a project ("añade documentación", "web del proyecto", "monta Zensical"), wants an existing site moved onto techsical or the common layout, mentions favicons, webmanifest or docs_templates, or wants to update techsical or Zensical or fix a build broken by a new release (Dependabot bump, theme moved, overridden template changed).
license: MIT
compatibility: Python 3.11+ (tomllib) and uv. Favicons need Pillow, plus resvg-py for SVG logos (`uv run --with pillow --with resvg-py`); they don't enter the project's lock. `upgrade` needs network access (uv, PyPI).
metadata:
  version: "0.3.0"
  author: isidro-rodriguez
---

# Zensical site

Every project's documentation site uses the same theme,
[techsical](https://isidro-rodriguez.github.io/techsical/), the same layout and
the same build gate, so any repo can be checked against it and upgraded the same
way. The theme owns the look (fonts, palette, features, page styles, API pages)
and the head (favicons, manifest, `theme-color`); a site only gives its content,
logo, favicons, manifest and `[project.extra.techsical]` settings (colours,
options). The canonical layout is in `references/layout.md`; the theme's options
are in its guide, *Personalización*.

Works alone (reCocina is not a Python package) or next to `new-python-project`:
that skill owns `AGENTS.md`'s shared block, this one adds a
`<!-- zensical:start -->` block inside the project rules, which `scaffold.py sync`
leaves alone.

## Inputs

| Input | Required | Default if missing |
|---|---|---|
| Project folder | yes | the current repo |
| Mode: `new`, `migrate`, `check`, `upgrade` | yes | infer: no `zensical.toml` → new; "update/bump techsical or Zensical" or a failing Dependabot PR → upgrade; otherwise migrate |
| Site name, one-line description (Spanish), author | new | `pyproject.toml` (`name`, `description`, `authors`) |
| Repo URL | new | `git remote get-url origin` |
| Site URL | new | GitHub Pages URL derived from the repo URL |
| Primary colour `#rrggbb` | new | ask; on migrate, the current `theme_color` or primary of the site's stylesheet |
| Accent colour | no | techsical's |
| Logo (SVG or PNG, square) | new | ask; on migrate, the current `theme.logo` |
| Python package for API docs | no | `src/<package>` if the project has one and wants an API reference |
| Publish with GitHub Pages | new | **ask** when the repo is not on GitHub or deploys elsewhere (Vercel); otherwise yes |
| Own fonts on migrate | migrate | **ask**: keep the site's fonts (`font_text`/`font_ui`/`font_code` plus its `@font-face`) or take techsical's |

`S` below is this skill's folder; run the script from the project root.

## Procedure

### new

1. Gather the inputs; ask only for what can't be read from the repo.
2. Create the layout:
   ```bash
   uv run --with pillow --with resvg-py python S/scripts/site.py new . \
     --name NAME --description TEXT --author AUTHOR --repo-url URL \
     --primary '#rrggbb' [--accent '#rrggbb'] --logo PATH [--package PKG] [--no-gh-pages]
   ```
   It never overwrites existing files (`--force` does) and prints what it wrote.
3. Add the tools as dev dependencies: `uv add --dev techsical` (it brings
   `zensical`), plus `mkdocstrings-python mkdocs-api-autonav` with `--package`.
4. Fill `nav` and `docs/index.md` with real content. A front page with a hero
   uses `template: home.html` (see the theme's guide, *Páginas*). Add theme
   options only when the project asks for them.
5. Verify (below). On GitHub, remind the user to set **Settings → Pages →
   Source: GitHub Actions** once; that can't be done from the repo.

### migrate (existing site)

1. `python S/scripts/site.py check .` — the list of gaps is the work list.
2. `uv add --dev techsical`; drop a direct `zensical` dev dependency only if
   nothing else needs it pinned (techsical keeps a compatible range).
3. `zensical.toml`, by hand, keeping comments and project content:
   - `[project.theme] name = "techsical"`; remove keys that only restated the old
     common setup: `language`, `font`, `favicon`, the standard `features` and
     `palette`, `custom_dir` when no override is left, and `navigation.instant`
     (+ `.prefetch`) in any case;
   - move `[project.extra] theme_color` to `[project.extra.techsical] primary`
     (and `theme_color` there only if the browser bar must differ);
   - keep the project's own extensions, plugins, nav and options.
4. Fonts: ask (Inputs). To keep the site's own, set `font_text`/`font_ui`/`font_code`
   and keep the `@font-face` rules and files they need; otherwise remove the
   site's font files, `@font-face` rules and Google Fonts setting.
5. `docs_templates/main.html`: remove the head the theme now writes (favicons,
   manifest, `theme-color`). Delete the file if nothing else is left; keep the
   project's own blocks. Never override `partials/icons.html` (the theme's head
   hook).
6. Stylesheets: remove rules the theme already covers (palette `--md-*` colours,
   fonts, typography, widths) and keep only what is the project's own; list what
   was removed. Drop the file and its `extra_css` entry if it ends up empty.
7. Favicons: `git mv` existing ones into `docs/assets/favicon/` with the canonical
   names, then `uv run --with pillow --with resvg-py python S/scripts/site.py
   favicons . --logo LOGO --missing-only`. Fix every path that pointed to the old
   location (manifest, templates, tests, service worker precache lists).
8. `docs/site.webmanifest`: relative icon paths, `"start_url": "./"`, the site
   colour as `theme_color`.
9. `python S/scripts/site.py sync .` — `es.html.jinja` (with mkdocstrings) and the
   AGENTS.md block.
10. Workflow: if `.github/workflows/docs.yml` exists, compare it with
    `S/assets/site/.github/workflows/docs.yml` and take the canonical one unless the
    project has steps of its own (atril's screenshots, a `workflow_call`): then
    only align the shared steps. Never add a Pages workflow to a project that
    deploys elsewhere.
11. Build, `check` again, and look at a few pages (Verification).

### check

`python S/scripts/site.py check .` — layout only; exit 1 on any FAIL. Report FAILs
and WARNs; INFO lines (template overrides, customised workflow, own palette) are
expected in projects with their own templates.

### upgrade (new techsical or Zensical release, failing Dependabot PR)

1. Start from a clean tree on a new branch; `uv sync` so the installed themes are
   the current ones.
2. `python S/scripts/site.py upgrade . [--to X.Y.Z]` — snapshots techsical's and
   Zensical's templates, moves an exact `zensical==` pin in `pyproject.toml`, runs
   `uv lock --upgrade-package` for zensical, zensical-ui and techsical (techsical
   keeps Zensical in a narrow range: a new Zensical usually needs a new techsical
   first), `uv sync`, then reports per template in `docs_templates/`, resolved as
   Zensical does (docs_templates → techsical → Zensical):
   - `ok … all its blocks still exist` / `upstream unchanged`: nothing to do;
   - `REVIEW … upstream changed`: a whole-file override whose original (in
     techsical or Zensical) changed: port the shown diff into the override,
     keeping the project's own changes;
   - `REVIEW … blocks no longer exist` or `… override is dead`: rewrite it;
   - `REVIEW tests/… old theme package`: make the code look in the new package
     first (the theme moved from `zensical` to `zensical_ui` in 0.1).
   It then builds (`--strict` when the project builds strictly) and exits 1 if
   anything needs review. If uv can't resolve the requested Zensical, techsical
   doesn't support it yet: stop and say so.
3. Fix every REVIEW item, then run the project's full gate (its tests may read the
   theme too) and the build chain it really uses (`vercel.json`, Poe tasks).
4. Commit the lock and the template fixes as separate intents
   (`chore: actualiza techsical a X.Y.Z`, `fix: adapta … al tema nuevo`).

## Output

- **new / migrate**: the files written, changed or removed, and a final `check`
  with no FAIL.
- **check**: FAIL/WARN/INFO lines and a count.
- **upgrade**: old → new versions, one line per template, the build result, and
  the changes made for each REVIEW item.

Then follow the project's commit policy: never commit or push unless it allows it.

## Verification

1. `uv run zensical build` ends with "No issues found" (with `--strict` where the
   project uses it).
2. `python S/scripts/site.py check .` reports no FAIL.
3. `site/index.html` links the favicons and `site.webmanifest` once each, with
   relative paths, and has one `theme-color` meta with the site colour.
4. Look at the home page and one content page (`uv run zensical serve` or a
   headless screenshot), light and dark: theme fonts or the chosen ones, the
   site's colours, nothing clipped, no leftover rule from the old stylesheet
   fighting the theme.
5. The project's own quality gate still passes.
