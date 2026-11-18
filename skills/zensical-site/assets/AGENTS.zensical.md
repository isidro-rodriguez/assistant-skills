<!-- zensical:start (managed by the zensical-site skill; edit there, not here) -->
### Documentation site (Zensical)

- Theme: [techsical](https://isidro-rodriguez.github.io/techsical/) (`[project.theme] name`, dev dependency). It brings fonts, features, palette, favicons, manifest and `theme-color`; customise only through `[project.extra.techsical]` (colours, fonts, options) or a stylesheet in `extra_css`. Never repeat its head in `docs_templates/main.html`.
- Layout: `zensical.toml`; `docs/` (sources, `docs/site.webmanifest`, `docs/assets/{favicon,images}`); `docs_templates/` only for template overrides (with `custom_dir = "docs_templates"`) and `python/material/languages/es.html.jinja` when mkdocstrings is used. Only `uv run zensical build` writes `site/` (gitignored).
- Template paths are relative (`{{ 'assets/…' | url }}`, never a leading `/`) so the site works under a sub-path such as GitHub Pages.
- Gate: `uv run zensical build` must end with "No issues found"; after changing the layout, run the skill's `site.py check`.
- Upgrading techsical or Zensical: use the skill's `site.py upgrade`, which diffs every template in `docs_templates/` against the new themes before the lock changes land.
<!-- zensical:end -->
