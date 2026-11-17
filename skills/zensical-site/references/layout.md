# Canonical layout

```
zensical.toml                       site config (template: assets/zensical.toml.tmpl)
docs/
├── index.md
├── site.webmanifest                relative paths, start_url "./"
└── assets/
    ├── favicon/                    favicon.ico (16/32/48), favicon-16x16.png,
    │                               favicon-32x32.png, apple-touch-icon.png (180),
    │                               android-chrome-192x192.png, android-chrome-512x512.png
    ├── fonts/                      starting fonts (Charis SIL, Source Sans 3, Source Code
    │                               Pro, latin woff2 + OFL-*.txt); the project's afterwards
    ├── images/                     logo.svg|png (+ screenshots, figures)
    ├── stylesheets/
    │   ├── typography.css          starting typography (new sites); the project's afterwards
    │   └── <slug>.css              the project's own palette and tweaks
    └── javascripts/                only if the site has scripts
docs_templates/
├── main.html                       extrahead: favicons, manifest, theme-color
└── python/material/languages/
    └── es.html.jinja               managed, only with mkdocstrings
.github/workflows/docs.yml          optional: build on PRs, deploy to GitHub Pages from main
AGENTS.md                           zensical block inside the project rules
.gitignore                          site/
```

## Required settings (`zensical.toml`)

| Key | Value | Why |
|---|---|---|
| `[project.theme] custom_dir` | `"docs_templates"` | without it `main.html` is ignored |
| `[project.theme] language` | `"es"` | interface texts in Spanish |
| `[project.theme] favicon` | `"assets/favicon/favicon-32x32.png"` | one favicon folder |
| `[project.theme] logo` | `"assets/images/logo.*"` | |
| `extra_css` | every listed file exists | new sites: `typography.css`, then `<slug>.css`; with `typography.css`, also `font = false`, or the theme's Google Fonts variables override it |
| `[project.extra] theme_color` | `#rrggbb` | read by `main.html`; same value in the manifest |
| `[project.plugins.mkdocstrings] locale` / `custom_templates` | `"es"` / `"docs_templates"` | Spanish API reference |

`features`, palette, Markdown extensions and fonts start from the template;
once a project changes them they are its own and `check` doesn't compare them.
Readability is not optional: `measure` holds every site to Practical
Typography's ranges (see `typography.md`).

## Managed vs. project files

- **Managed** (byte-identical to `assets/site/`, refreshed by `sync`, compared by
  `check`): `es.html.jinja`.
- **Starting files** (copied once by `new`, then the project's): `typography.css`,
  `docs/assets/fonts/*`, `<slug>.css`.
- **Canonical but editable**: `main.html` (must keep the head links; may add
  blocks), `docs.yml` (may add project steps), `zensical.toml`, the manifest.
- **Project**: `<slug>.css`, content, extra templates (`listado.html`, partials).

## Paths

Templates link assets with the `url` filter and a relative path,
`{{ 'assets/favicon/favicon.ico' | url }}`. A leading `/` resolves to the domain
root and breaks every site served under a sub-path, which is how GitHub Pages
serves project sites (`https://user.github.io/<repo>/`). The repo name in
`site_url` is case-sensitive there.

## Known quirk

Zensical copies every non-template file under `custom_dir` into `site/`, so
`site/python/material/languages/es.html.jinja` gets published. It is harmless.
