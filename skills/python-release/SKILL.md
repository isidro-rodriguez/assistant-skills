---
name: python-release
description: Prepare a release of a uv-based Python project — choose the SemVer bump from the commits, write the CHANGELOG entries (Keep a Changelog, in Spanish), bump the version, re-lock uv.lock and propose the release commits — with a script that does the mechanical edits and validates the result. Use it whenever changes to a versioned package are about to be pushed or published, or the user says "release", "publica", "sube la versión", "bump", "prepara la versión", "actualiza el CHANGELOG" or "sube esto" in a project with pyproject.toml and CHANGELOG.md. Not for projects without a version (0.0.0 / no CHANGELOG) unless the user asks to start versioning.
license: MIT
compatibility: Python 3.13+, git, and uv for the lockfile step. Works with static [project].version and with dynamic versions read from a file ([tool.hatch.version] path), in standalone projects and uv workspace members (--project).
metadata:
  version: "0.1.1"
  author: isidro-rodriguez
---

# Python release

Prepares a release the same way every time. The script handles the edits that
are easy to get subtly wrong (version string, CHANGELOG heading and date,
lockfile). You handle the judgement: which bump, and what the entries say.

## Inputs

| Input | Required | Default if missing |
|---|---|---|
| Project directory | no | Repo root. In a uv workspace, the member being released (`--project packages/x`) |
| Bump level | no | Suggested from the commits since the last tag (see step 2); confirm with the user if it is MAJOR |
| What changed | no | Commits since the last tag plus `git diff` of uncommitted work |
| Project rules | yes (read them) | The project's `AGENTS.md`/`CLAUDE.md`: commit policy, commit scopes, publishing, extra release checks |

The project's own instructions win over this skill where they differ (for
example, a project that lets the agent commit directly, or that also requires
reviewing `README.md` because it is the PyPI page).

## Procedure

Run the script from the skill folder: `python scripts/release.py --project <dir> <command>`.

1. **Status.** Run `status`. It reports the version and where it lives, the
   CHANGELOG state, commits since the last tag with their Conventional Commit
   types, a suggested bump, uncommitted changes and whether `uv.lock` is in sync.
   - If it says the project **is not versioned** (version `0.0.0` or no
     `CHANGELOG.md`), stop: there is nothing to release. Tell the user, and
     run `init` only if they want to start versioning.
   - On a shallow clone, fetch more history first
     (`git fetch --depth=200 --tags`). Otherwise the commit list, and so the
     suggestion, is incomplete.
2. **Choose the bump.** Use SemVer:
   - **MAJOR:** breaking changes for users of the public API, or of the CLI for
     command-line tools (removed or renamed commands and options, changed
     config keys). Commits with `!` or `BREAKING CHANGE` suggest it, but
     confirm with the user before choosing MAJOR: it is the one choice that is
     costly to undo.
   - **MINOR:** new backwards-compatible functionality (`feat:`).
   - **PATCH:** fixes, internal refactors, and docs that ship with the package.
   - If you're unsure between PATCH and MINOR, choose MINOR. Under-signalling a
     new feature is worse than an extra minor number.
   - Pre-releases (`1.2.0-beta.3`) are fine as explicit versions. `bump patch`
     on a pre-release produces the final release (`1.2.0`).
3. **Write the CHANGELOG entries** under the pending heading, `## [Unreleased]`
   or its Spanish form `## [Sin publicar]`. Use whichever the file or the project's
   rules already use, and create it at the top if it's missing:
   - Group them under `### Added`, `Changed`, `Fixed`, `Removed`, `Deprecated`
     and `Security`. If the file already uses the Spanish names (`Añadido`,
     `Cambiado`, `Corregido`…), keep them; don't mix languages in one file.
   - Write in Spanish, for users rather than developers. Say what changed and
     why it matters, not which files moved: the CHANGELOG often becomes the
     release notes.
   - One bullet per change. Merge commits that are the same change, and leave
     out what users can't notice (CI tweaks, test-only changes) unless the
     project's rules say otherwise.
4. **Bump.** Run `bump <major|minor|patch|X.Y.Z>`. It writes the version (in
   `pyproject.toml` or the dynamic version file) and turns `[Unreleased]` into
   `## [X.Y.Z] - today`, keeping a fresh empty `[Unreleased]` on top. It then
   runs `uv lock` and validates the CHANGELOG. If it fails, fix the cause it
   names and run it again; never edit the version or the lock by hand.
5. **Project-specific checks.** Apply any release step in the project's rules,
   such as reviewing `README.md` when it is the PyPI page. Then run the
   project's quality gate (`poe check`, or the `uv run` commands in its
   `AGENTS.md`).
6. **Validate.** Run `check`. It must exit 0: the CHANGELOG is well formed,
   its top release equals the project version, that release has entries, and
   `uv.lock` is in sync.
7. **Commits.** Follow the project's commit policy. By default, don't commit:
   show `git status` and the proposed messages, and wait for the user. Use
   Conventional Commits in Spanish:
   - `chore: bump versión a X.Y.Z`
   - `docs: actualiza CHANGELOG para X.Y.Z`

   Use the scope the project uses in workspaces, for example
   `chore(framework): …`. Make a single commit if the change and the release
   can't be separated.
8. **Publish only as the project says.** Some projects publish on push to
   `main`, others on a `vX.Y.Z` tag or a manual workflow run. Never create or
   push tags, and never push, without the user's explicit confirmation.

## Output

- Version bumped in its source file, `CHANGELOG.md` with a dated `[X.Y.Z]`
  section and an empty `[Unreleased]`, and `uv.lock` re-locked if it records
  the version.
- A short report to the user: old → new version and why that level, the new
  CHANGELOG section, the `check` result, and the proposed commit messages and
  publishing step, waiting for confirmation unless the project allows
  committing directly.

## Verification

- [ ] `release.py check` exits 0.
- [ ] The bump level matches the changes (MAJOR only after the user confirmed).
- [ ] The CHANGELOG entries are in Spanish, user-facing, explain the why, and use the section names the file already used.
- [ ] The project's quality gate passes.
- [ ] Nothing was committed, tagged or pushed beyond what the project's rules and the user allowed.
