# Canonical layout

```
zensical.toml                       site config (template: assets/zensical.toml.tmpl)
docs/
├── index.md
├── site.webmanifest                relative paths, start_url "./", theme_color = site colour
└── assets/
    ├── favicon/                    favicon.ico (16/32/48), favicon-16x16.png,
    │                               favicon-32x32.png, apple-touch-icon.png (180),
    │                               android-chrome-192x192.png, android-chrome-512x512.png
    ├── images/                     logo.svg|png (+ screenshots, figures)
    ├── stylesheets/                only if the project needs its own CSS (extra_css)
    ├── fonts/                      only for fonts the theme doesn't ship
    └── javascripts/                only if the site has scripts
docs_templates/                     only what the site needs:
├── main.html, partials/…           template overrides (then custom_dir = "docs_templates")
└── python/material/languages/
    └── es.html.jinja               managed, only with mkdocstrings
.github/workflows/docs.yml          optional: build on PRs, deploy to GitHub Pages from main
AGENTS.md                           zensical block inside the project rules
.gitignore                          site/
pyproject.toml                      techsical in the dev group (it brings zensical)
```

## What techsical provides

[techsical](https://isidro-rodriguez.github.io/techsical/) (`[project.theme] name =
"techsical"`) extends Zensical's theme and sets the defaults every site shared by
hand before: `language = "es"`, its own fonts (`font = false`), `features`, the
light/dark/system palette, `favicon = "assets/favicon/favicon-32x32.png"`, and a
head hook that links `favicon.ico`, the 16 px PNG, `apple-touch-icon.png`,
`site.webmanifest` and `theme-color`, with relative paths. It also styles
mkdocstrings pages. A site's `main.html` must not repeat any of that.

## Settings (`zensical.toml`)

| Key | Value | Why |
|---|---|---|
| `[project.theme] name` | `"techsical"` | the common theme |
| `[project.theme] logo` | `"assets/images/logo.*"` | |
| `[project.theme] custom_dir` | `"docs_templates"` only with template overrides | without overrides it would publish the folder |
| `[project.extra.techsical] primary` | `#rrggbb` | brand colour; also the browser bar and the manifest colour unless `theme_color` is set there |
| `[project.plugins.mkdocstrings] locale` / `custom_templates` | `"es"` / `"docs_templates"` | Spanish API reference |
| `features` | not `navigation.instant` | it cancels techsical's page transitions |

Other `[project.extra.techsical]` options (accent, dark colours, fonts, widths,
`toc`, `framed`, `footer_nav`, `transitions`, `math`, `header_nav`, `favicons`,
`manifest`) are documented in the theme's guide, *Personalización*. `[project.theme]`
keys such as `palette`, `features` or `font` override the theme's: set them only
when the project really differs.

## Managed vs. project files

- **Managed** (byte-identical to `assets/site/`, refreshed by `sync`, compared by
  `check`): `es.html.jinja`.
- **Canonical but editable**: `docs.yml` (may add project steps), `zensical.toml`,
  the manifest.
- **Project**: content, its own stylesheet and fonts, template overrides
  (`listado.html`, partials).

## Paths

Templates link assets with the `url` filter and a relative path,
`{{ 'assets/images/x.png' | url }}`. A leading `/` resolves to the domain root and
breaks every site served under a sub-path, which is how GitHub Pages serves
project sites (`https://user.github.io/<repo>/`). The repo name in `site_url` is
case-sensitive there.

## Known quirk

Zensical copies every non-template file under `custom_dir` into `site/`, so with
template overrides `site/python/material/languages/es.html.jinja` gets published.
It is harmless.
