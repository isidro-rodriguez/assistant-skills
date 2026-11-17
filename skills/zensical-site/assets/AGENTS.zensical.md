<!-- zensical:start (managed by the zensical-site skill; edit there, not here) -->
### Documentation site (Zensical)

- Layout: `zensical.toml`; `docs/` (sources, `docs/site.webmanifest`, `docs/assets/{favicon,fonts,images,stylesheets}`); `docs_templates/` (`main.html`: favicons, manifest and `[project.extra] theme_color`; `python/material/languages/es.html.jinja` when mkdocstrings is used). Only `uv run zensical build` writes `site/` (gitignored).
- Readability follows Practical Typography: body text 15–25 px, line spacing 120–145 %, 45–90 characters per line. Fonts and look are the project's; after any style change, build and run the skill's `site.py measure` (exit 1 when a page is out of range).
- Template paths are relative (`{{ 'assets/…' | url }}`, never a leading `/`) so the site works under a sub-path such as GitHub Pages.
- Gate: `uv run zensical build` must end with "No issues found"; after changing the layout, run the skill's `site.py check`.
- Upgrading Zensical: use the skill's `site.py upgrade`, which diffs every template in `docs_templates/` against the new theme before the lock changes land.
<!-- zensical:end -->
