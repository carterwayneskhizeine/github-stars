# `data/c-code-repos.json` schema reference

This is the single source of truth for what's inside the user's local code folder
(default: `C:\Users\gotmo\Code` on Windows). Both bundled scripts (`scan_inventory.py`,
`clone_repo.py`) read and write this file.

## Top-level shape

```json
{
  "_meta": { ... },
  "repos": [ { ... }, { ... }, ... ]
}
```

### `_meta` (object, required)

| Field | Type | Required | Notes |
| --- | --- | ---: | --- |
| `description` | string | yes | Human-readable purpose. Don't change. |
| `root_path` | string | yes | Absolute path to the local code folder. `C:\Users\gotmo\Code` on Windows, `~/Code` on macOS, etc. **Change this when moving the project to another machine.** |
| `schema_version` | integer | yes | Currently `1`. Bumped if the schema changes. |
| `last_full_scan` | string (ISO 8601) | yes | When `scan_inventory.py` last regenerated this file. |
| `gh_user` | string | yes | GitHub username used to detect user-owned repos. Default: `carterwayneskhizeine`. |

### `repos[]` (array, required)

One entry per subdirectory of `root_path`. Order is not significant; the scripts
sort by `type` then `name` when writing.

## Repo entry fields

| Field | Type | Required | Always present for |
| --- | --- | ---: | --- |
| `name` | string | yes | all |
| `type` | enum | yes | all — one of `original`, `fork`, `upstream-clone`, `no-remote-git`, `non-git` |
| `origin` | string \| null | no | git repos with a remote |
| `upstream` | string \| null | no | forks |
| `parent` | string \| null | no | forks — `owner/repo` form |
| `is_fork` | boolean | no | user-owned repos (`original` and `fork`) |
| `source_star` | string \| null | no | entries cloned from a starred repo |
| `last_scanned` | string (ISO 8601) | yes | all |
| `notes` | string \| null | no | free-form, e.g. "原仓已被删" or "本地叫 goldie-fork 但 origin 指向 claude-mem" |

### `type` values

| Value | When |
| --- | --- |
| `original` | User's own repo, `is_fork: false`. Detected by `gh api` on origin. |
| `fork` | User's own repo, `is_fork: true`. Has both `origin` and `upstream`. |
| `upstream-clone` | Third-party repo, cloned directly. `origin` is non-user. |
| `no-remote-git` | Has `.git/` but no remotes at all. |
| `non-git` | No `.git/` directory. Plain folder. |

## Field semantics

### `name`

The **exact folder name** on disk, no prefix. So:
- `MVPaint` (not `3DTopia-MVPaint`)
- `a2ui` (not `a2ui-project-a2ui`)
- `goldie-fork` is allowed — the local name genuinely differs from the upstream name (this is a quirk of one of the user's forks, preserved for fidelity)

### `origin`

The value of `git remote get-url origin`. Preserved verbatim including protocol
(`https://` or `git@`). Useful for:
- Detecting protocol preference (SSH vs HTTPS)
- Verifying a clone target
- Auditing

### `upstream` and `parent`

For forks only. `upstream` is the raw `git remote get-url upstream` value;
`parent` is the normalized `owner/repo` form (derived from `upstream`).

`is_fork` is set to `true` for forks and `false` for originals. The
`scan_inventory.py` script also uses `is_fork` to skip the `gh api` fork check
for entries where the answer is already known.

### `source_star`

The filename in `stars-readme/` (e.g. `a2ui-project-a2ui.md`) that prompted
this clone, if the user cloned the repo from a starred one. `null` for
pre-existing clones or non-clones.

`source_star` is set by `clone_repo.py` when the user invokes it with a
`stars-readme/...` path. The scan script preserves it for existing entries.

### `last_scanned`

ISO 8601 timestamp (with timezone) of when this specific entry was last seen by
the scanner. Used for:
- Detecting entries that haven't been seen in N scans (might have been deleted)
- Showing the user how fresh the data is

`last_scanned != _meta.last_full_scan` is normal — the full scan is the newest
scan, and individual entries get the timestamp from the scan that last saw them.

## Example entry

```json
{
  "name": "a2ui",
  "type": "upstream-clone",
  "origin": "git@github.com:a2ui-project/a2ui.git",
  "upstream": null,
  "parent": null,
  "is_fork": false,
  "source_star": "a2ui-project-a2ui.md",
  "last_scanned": "2026-06-27T17:30:00+08:00",
  "notes": null
}
```

## Cross-references

- `data/stars_mapping.json` maps `Owner-Repo.md` → GitHub URL.
  To find "starred but not yet cloned" repos, diff the two.
- `download_stars.py` (in project root) is the script that builds
  `stars-readme/` and `stars_mapping.json`. The `c-code` skill is its sibling.

## Validation

The scripts validate the JSON on read using a simple schema check (presence of
`_meta` and `repos` keys, type field in allowed values, etc.). They do **not**
use a JSON Schema validator; if you edit the file by hand, keep the structure
above and the scripts will work.

If the file is corrupted, delete it and run `scan_inventory.py` to regenerate
from the filesystem.
