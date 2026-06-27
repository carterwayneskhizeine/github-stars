---
name: d-code
description: Manage and query the local code folder inventory (D:\Code on Windows, or any user-configured root_path). Use this skill whenever the user mentions "D盘Code文件夹", "我的D盘Code", "Code文件夹", asks what repos are cloned locally, asks about local forks vs upstream clones, wants to clone a new GitHub repo into the Code folder (especially from a starred repo under stars-readme/), wants to scan or update the local code inventory, or asks about d-code-repos.json. Even if the user just says "我D盘里有什么项目" or "把 stars-readme 里的 X 克隆到我的 Code 文件夹", use this skill. Maintains a single source of truth in `data/d-code-repos.json` and uses `gh repo clone` with conflict detection so that folder names stay canonical (e.g. `MVPaint`, not `3DTopia-MVPaint`).
---

# d-code — local code folder inventory skill

This skill is bundled with the **github-stars** project. It maintains a single source of truth about what's inside the user's local `Code` folder (default: `D:\Code` on Windows; can be reconfigured in `_meta.root_path` for macOS/Linux).

Two bundled scripts do the heavy lifting:

| Script | Purpose |
| --- | --- |
| `scripts/scan_inventory.py` | Walk the root folder, classify every subdirectory, regenerate `data/d-code-repos.json` |
| `scripts/clone_repo.py` | `gh repo clone <owner>/<repo>` into the root with conflict detection |

The skill itself is just routing: it reads the JSON, runs the right script, formats the answer.

## File layout

```
github-stars/
├── .agents/skills/d-code/
│   ├── SKILL.md                   ← you are here
│   ├── references/
│   │   └── json-schema.md         ← full JSON schema docs
│   ├── scripts/
│   │   ├── scan_inventory.py      ← regenerates the JSON
│   │   └── clone_repo.py          ← clones with conflict detection
│   └── evals/
│       └── evals.json             ← test cases for this skill
├── data/
│   └── d-code-repos.json          ← the inventory (single source of truth)
├── docs/
│   └── D-Code-Repos.md            ← user manual for the JSON
└── stars-readme/                  ← 1212 README files from starred repos
```

## When to trigger

Trigger phrases (in Chinese OR English, exact wording not required):

- "我D盘Code文件夹里有什么" / "我的D盘" / "D盘Code"
- "Code文件夹" / "本地有哪些项目" / "我本地 clone 了哪些"
- "克隆到Code文件夹" / "把 stars-readme 里的 X 克隆下来"
- "扫一下本地仓库" / "更新 D 盘清单" / "重新生成 d-code-repos.json"
- "d-code-repos.json 怎么用" / "data/ 那个 json"

**Do NOT trigger** for general git/GitHub questions, `gh` CLI usage tutorials, or repo management that's not about the local `Code` folder.

## The 5 repo types

The JSON classifies every subdirectory under the root into exactly one of:

| Type | Meaning | Has origin remote? | Has upstream remote? |
| --- | ---: | ---: | ---: |
| `original` | User's own non-fork repo on GitHub | yes (carterwayneskhizeine/*) | no |
| `fork` | User's fork of someone else's repo | yes (carterwayneskhizeine/*) | yes (parent) |
| `upstream-clone` | Direct `git clone` of a third-party repo | yes (third party) | no |
| `no-remote-git` | Local `git init` with no remote | no | no |
| `non-git` | Plain folder, no `.git` | n/a | n/a |

## Workflow 1 — query the inventory

User asks "我 D 盘有哪些 upstream clone?" or similar.

1. Read `data/d-code-repos.json` (use the `read` tool, or `jq` via bash).
2. Filter by `type` field.
3. Format as a markdown table or short list, including `name`, `origin` (or `parent` for forks), and `source_star` if present.
4. Cite the file path and `last_full_scan` timestamp so the user knows how fresh the data is.

**Don't** re-run the scan unless the user asks. The JSON is the truth.

## Workflow 2 — clone a starred repo to the local Code folder

User says "把 stars-readme/3DTopia-MVPaint.md 那个 clone 到我 D 盘" or "clone vercel/eve 到 Code 文件夹".

### Step 1: resolve the target owner/repo

| Input shape | Resolution |
| --- | --- |
| `stars-readme/3DTopia-MVPaint.md` | Look up `Owner-Repo` pattern in `data/stars_mapping.json`; reverse-lookup to get `https://github.com/3DTopia/MVPaint`; extract `3DTopia/MVPaint` |
| `vercel/eve` | Use directly |
| `https://github.com/a2ui-project/a2ui` | Strip URL prefix |
| Bare repo name `MVPaint` | Search `data/stars_mapping.json` values for the matching repo, then extract owner/repo |

Use the bundled scripts for the URL parsing — `scripts/clone_repo.py` accepts a URL, `owner/repo`, or a `stars-readme/Owner-Repo.md` path as input.

### Step 2: run the clone script with conflict detection

```bash
python .agents/skills/d-code/scripts/clone_repo.py <owner/repo or URL or stars-readme path>
```

The script handles four cases:

1. **Folder does not exist** → `gh repo clone <owner>/<repo> <repo>` (canonical name, no `Owner-` prefix).
2. **Folder exists, same origin** → skip with message "已存在".
3. **Folder exists, same fork family** (target is the parent of an existing fork, or vice versa) → tell the user and ask whether to `git remote add upstream` or skip.
4. **Folder exists, totally different repo** → ask the user:
   - `[1]` cancel (don't clone)
   - `[2]` clone with a different name (default: `<owner>-<repo>` to avoid collision)
   - `[3]` delete existing folder and re-clone (requires typing the folder name as confirmation)

The script updates `data/d-code-repos.json` after a successful clone.

### Step 3: verify and report

After cloning, re-read the relevant JSON entry and report:
- Folder name (canonical, no `Owner-` prefix)
- Origin URL
- `source_star` field (which stars-readme file prompted this clone, if any)

## Workflow 3 — scan / refresh the inventory

User says "扫一下 D 盘" or "更新清单".

```bash
python .agents/skills/d-code/scripts/scan_inventory.py
```

This walks `_meta.root_path`, classifies every subdirectory, and rewrites `data/d-code-repos.json`. It uses `gh api repos/<owner>/<repo>` to detect fork status for user-owned repos, and falls back to checking the `upstream` remote for unreachable APIs.

For a quick diff (what changed since last scan), use `--diff` flag.

To retroactively fill in `source_star` for upstream-clones that were cloned before this skill existed (so we can tell which ones came from a star and which are old manual clones), use `--backfill-source-star`:

```bash
python .agents/skills/d-code/scripts/scan_inventory.py --backfill-source-star
```

This reads `data/stars_mapping.json` and, for every `upstream-clone` with `source_star: null`, parses `owner/repo` from `origin` and looks up `<owner>-<repo>.md` in the mapping. If a match is found, the field is filled in. Updates `_meta.last_backfill_source_star`.

To **detect drift** without writing the file (e.g., "did anything change in D:\Code since last scan?"), use `--verify`:

```bash
python .agents/skills/d-code/scripts/scan_inventory.py --verify
echo $?  # 0 = clean, 1 = drift detected
```

This walks the disk, compares each field (`type`, `origin`, `upstream`) against the JSON, and reports drift without writing. Also catches orphan folders (on disk, not in JSON) and phantom entries (in JSON, not on disk). Exits 1 if any drift is detected — useful in pre-commit hooks or CI. Does NOT call `gh api`, so it doesn't re-check fork status (use plain `scan_inventory.py` for that).

## Workflow 4 — explain the JSON

User asks "d-code-repos.json 怎么用" or "data/ 那个 json 干嘛的".

Point them to `docs/D-Code-Repos.md` — that's the user manual. Briefly summarize:
- It's the single source of truth, regenerated by `scan_inventory.py`
- Has `_meta` (root_path, schema version, last scan time) + `repos[]` array
- Each entry has `name`, `type`, `origin`, optional `upstream`/`parent`/`source_star`/`notes`
- Cross-reference with `data/stars_mapping.json` to find "starred but not yet cloned" repos

For schema details, read `references/json-schema.md`.

## Cross-platform notes

- The skill scripts use `pathlib` and handle Windows/Unix paths.
- `_meta.root_path` is the only platform-specific value; everything else is portable.
- On macOS/Linux, edit the JSON's `_meta.root_path` to e.g. `~/Code` and re-run `scan_inventory.py`.
- The user account detection (`is this my fork?`) hardcodes the GitHub username `carterwayneskhizeine`. Change via `--user` flag or by editing the script's `DEFAULT_GH_USER` constant.

## Things to never do

- **Don't rename a cloned folder.** If the upstream repo is named `MVPaint`, the local folder must be `MVPaint`, not `3DTopia-MVPaint`. The `Owner-Repo` naming is only for `stars-readme/` files (which need to be unique on disk), never for the actual clones.
- **Don't run `git clone` directly.** Always go through `clone_repo.py` so the JSON stays in sync.
- **Don't fabricate `parent` / `upstream` data.** If the fork status is unclear, mark the entry as `type: "upstream-clone"` with a `notes` field explaining the ambiguity.
- **Don't delete a folder without explicit user confirmation.** Even if the conflict-resolution flow recommends it, the script will require typed confirmation of the folder name.

## References

- `references/json-schema.md` — full schema spec for `data/d-code-repos.json`
- `docs/D-Code-Repos.md` — user-facing manual (in the project root's `docs/`)
- `stars_mapping.json` — maps `Owner-Repo.md` filenames in `stars-readme/` to GitHub URLs (used to resolve "clone this star" requests)
