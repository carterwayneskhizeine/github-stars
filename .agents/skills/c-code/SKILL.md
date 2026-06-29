---
name: c-code
description: Manage and query the local code folder inventory. PRIMARY environment is Windows with C:\Users\gotmo\Code (full skill workflow runs here — clone, scan, sync stars, backfill, all script writes). Termux / proot-distro Ubuntu is a READ-ONLY scratch env: read any file, but do NOT invoke the bundled scripts (clone_repo.py / scan_inventory.py / download_stars.py) because they assume Windows paths and write to data/*.json. Direct `gh repo clone` / `git clone` to a Linux path IS allowed in Termux; just skip the JSON sync. macOS / native Linux can also work by editing `_meta.root_path`. Use this skill whenever the user mentions "Code文件夹", "我的Code文件夹", asks what repos are cloned locally, asks about local forks vs upstream clones, wants to clone a new GitHub repo into the Code folder (especially from a starred repo under stars-readme/), wants to scan or update the local code inventory, or asks about c-code-repos.json. Even if the user just says "我本地有什么项目" or "把 stars-readme 里的 X 克隆到我的 Code 文件夹", use this skill. Maintains a single source of truth in `data/c-code-repos.json` and uses `gh repo clone` with conflict detection so that folder names stay canonical (e.g. `MVPaint`, not `3DTopia-MVPaint`).
---

# c-code — local code folder inventory skill

This skill is bundled with the **github-stars** project. It maintains a single source of truth about what's inside the user's local `Code` folder (default: `C:\Users\gotmo\Code` on Windows; can be reconfigured in `_meta.root_path` for macOS/Linux).

Two bundled scripts do the heavy lifting:

| Script | Purpose |
| --- | --- |
| `scripts/scan_inventory.py` | Walk the root folder, classify every subdirectory, regenerate `data/c-code-repos.json` |
| `scripts/clone_repo.py` | `gh repo clone <owner>/<repo>` into the root with conflict detection |

The skill itself is just routing: it reads the JSON, runs the right script, formats the answer.

## File layout

```
github-stars/
├── .agents/skills/c-code/
│   ├── SKILL.md                   ← you are here
│   ├── references/
│   │   └── json-schema.md         ← full JSON schema docs
│   ├── scripts/
│   │   ├── scan_inventory.py      ← regenerates the JSON
│   │   └── clone_repo.py          ← clones with conflict detection
│   └── evals/
│       └── evals.json             ← test cases for this skill
├── data/
│   └── c-code-repos.json          ← the inventory (single source of truth)
├── docs/
│   └── C-Code-Repos.md            ← user manual for the JSON
└── stars-readme/                  ← 1212 README files from starred repos
```

## Environment detection — run this first

This skill mutates files in `data/`, runs `gh repo clone`, and writes JSON state. **Before doing anything that changes state, detect the environment** so you don't run Windows paths on Termux or write JSON files when you shouldn't.

### Detection snippet

```bash
python -c "
import os, platform
sys_name = platform.system()
root = r'C:\Users\gotmo\Code'
if sys_name == 'Windows' and os.path.isdir(root):
    print(f'c-code mode: windows-local  ({sys_name} + {root})')
elif 'ANDROID_ROOT' in os.environ or 'TERMUX_VERSION' in os.environ or os.path.isdir('/data/data/com.termux'):
    print('c-code mode: termux-ubuntu  (Termux / proot-distro Ubuntu detected)')
else:
    print(f'c-code mode: other  ({sys_name}, {root} not present)')
"
```

### Three modes

| Mode | When | Allowed actions |
|---|---|---|
| `windows-local` | Windows + `C:\Users\gotmo\Code` exists | Everything: clone, sync stars, backfill, scan, query. All bundled scripts safe to run. |
| `termux-ubuntu` | Termux detected (`TERMUX_VERSION` / `ANDROID_ROOT` / `/data/data/com.termux`) | Read any file; **direct `gh repo clone` / `git clone` to a Linux path is OK**; create new files under `docs/`. **Do NOT** invoke `clone_repo.py` / `scan_inventory.py` / `download_stars.py` — they hardcode `C:\Users\gotmo\Code` and write `data/*.json`. Do NOT push, do NOT edit scripts, do NOT write existing files. |
| `other` | Anything else (Linux/macOS without Termux, Windows without `C:\Users\gotmo\Code`, …) | **Stop and ask the user.** They likely need to edit `_meta.root_path`, install `gh`, or confirm a different path |

### What "core data" means (off-limits in `termux-ubuntu`)

- `data/c-code-repos.json`, `data/stars_mapping.json`, and any other JSON
- `.agents/skills/c-code/scripts/*.py`, `download_stars.py`, `SKILL.md`
- Existing files under `docs/`
- **Anything that would be rewritten by the bundled scripts** — i.e., the output of `scan_inventory.py`, `clone_repo.py`, `download_stars.py`

### What's still allowed in `termux-ubuntu`

- **Read** any file (`.md`, `.json`, `.py`, READMEs, `stars-readme/*.md`)
- Run **read-only** Python that only prints to stdout — Workflow 1 and 4 still work
- **Direct `gh repo clone` / `git clone`** to a Linux path (e.g. `/mnt/sdcard/Code/<repo>`). Just don't pipe the result through `clone_repo.py`, and don't expect `c-code-repos.json` to be updated locally — it lives on the Windows machine and gets re-synced via `scan_inventory.py` next time the user runs it there
- **Create new** files under `docs/` — e.g., `docs/clone-<owner>-<repo>-note.md` with the commands the user should run later on Windows to sync the JSON

If a user in `termux-ubuntu` mode asks to clone: **run `gh repo clone` directly to a Linux path they confirm; skip the JSON write**. If they ask to scan / sync stars / backfill, refuse and explain those need Windows. If unsure, ask.

## When to trigger

Trigger phrases (in Chinese OR English, exact wording not required):

- "我Code文件夹里有什么" / "我的Code文件夹"
- "Code文件夹" / "本地有哪些项目" / "我本地 clone 了哪些"
- "克隆到Code文件夹" / "把 stars-readme 里的 X 克隆下来"
- "扫一下本地仓库" / "更新 Code 文件夹清单" / "重新生成 c-code-repos.json"
- "c-code-repos.json 怎么用" / "data/ 那个 json"

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

User asks "我 Code 文件夹有哪些 upstream clone?" or similar.

1. Read `data/c-code-repos.json` (use the `read` tool, or `jq` via bash).
2. Filter by `type` field.
3. Format as a markdown table or short list, including `name`, `origin` (or `parent` for forks), and `source_star` if present.
4. Cite the file path and `last_full_scan` timestamp so the user knows how fresh the data is.

**Don't** re-run the scan unless the user asks. The JSON is the truth.

## Workflow 2 — clone a URL (combined: clone → sync stars → backfill source_star)

User says "把 https://github.com/X/Y 克隆到 Code 文件夹" or "clone vercel/eve 到 Code 文件夹". This workflow runs the **full chain in one shot** so the new clone is fully linked into the inventory before you finish — the user should not need to ask for `download_stars.py` and "回填" as separate follow-ups.

### Step 1: environment check

Run the detection snippet from "Environment detection" above.

| Mode | Action |
|---|---|
| `windows-local` | Proceed to Step 2 |
| `termux-ubuntu` | Don't invoke `clone_repo.py` (it writes `data/c-code-repos.json` which is Windows-machine territory). Instead: confirm the target Linux path with the user, then run `gh repo clone <owner>/<repo> <linux-path>` directly. Skip Steps 4 (`download_stars.py`) and 5 (`--backfill-source-star`) — both target the Windows JSON. Optionally write a note in `docs/clone-<owner>-<repo>-termux.md` reminding to re-sync on Windows later |
| `other` | **Stop and ask.** The user likely needs to edit `_meta.root_path` or install `gh` |

### Step 2: resolve the target owner/repo

| Input shape | Resolution |
| --- | --- |
| `stars-readme/3DTopia-MVPaint.md` | Look up `Owner-Repo` pattern in `data/stars_mapping.json`; reverse-lookup to get `https://github.com/3DTopia/MVPaint`; extract `3DTopia/MVPaint` |
| `vercel/eve` | Use directly |
| `https://github.com/a2ui-project/a2ui` | Strip URL prefix |
| Bare repo name `MVPaint` | Search `data/stars_mapping.json` values for the matching repo, then extract owner/repo |

Use the bundled scripts for the URL parsing — `scripts/clone_repo.py` accepts a URL, `owner/repo`, or a `stars-readme/Owner-Repo.md` path as input.

### Step 3: clone with conflict detection

```bash
python .agents/skills/c-code/scripts/clone_repo.py <owner/repo or URL or stars-readme path>
```

The script handles four cases:

1. **Folder does not exist** → `gh repo clone <owner>/<repo> <repo>` (canonical name, no `Owner-` prefix).
2. **Folder exists, same origin** → skip with message "已存在".
3. **Folder exists, same fork family** (target is the parent of an existing fork, or vice versa) → tell the user and ask whether to `git remote add upstream` or skip.
4. **Folder exists, totally different repo** → ask the user:
   - `[1]` cancel (don't clone)
   - `[2]` clone with a different name (default: `<owner>-<repo>` to avoid collision)
   - `[3]` delete existing folder and re-clone (requires typing the folder name as confirmation)

The script updates `data/c-code-repos.json` after a successful clone.

If the user picks `[1]` cancel or the script exits non-zero, **stop the workflow** — don't run Step 4 or 5.

### Step 4: sync stars (was previously a separate `download_stars.py` call)

After a successful clone, refresh the stars inventory so the new star is in `data/stars_mapping.json` and `stars-readme/<owner>-<repo>.md` exists:

```bash
python download_stars.py
```

This is idempotent — safe to run after every clone. If `download_stars.py` doesn't exist at the repo root, log a warning and continue to Step 5 (the clone itself still succeeded).

### Step 5: backfill source_star (was previously a separate "回填" call)

```bash
python .agents/skills/c-code/scripts/scan_inventory.py --backfill-source-star
```

This links the new clone to `stars-readme/<owner>-<repo>.md` automatically, and also reports any other upstream-clones whose `source_star` is still null.

### Step 6: verify and report

After all three steps succeed, re-read the relevant JSON entry and report:
- Folder name (canonical, no `Owner-` prefix)
- Origin URL
- `source_star` field (which stars-readme file prompted this clone, if any)
- Whether `download_stars.py` added the star (`downloaded=N skipped=M failed=K`)
- Whether `--backfill-source-star` matched it (`matched=N unmatched=M`)

If any step failed partway, report which step(s) succeeded and which didn't, so the user can decide whether to retry. Never silently swallow a step's failure.

## Workflow 3 — scan / refresh the inventory

User says "扫一下 Code 文件夹" or "更新清单".

> **Mode check first.** Only run in `windows-local` mode. In `termux-ubuntu` mode, refuse and tell the user — `scan_inventory.py` will fail because `C:\Users\gotmo\Code` doesn't exist (or isn't writable). In `other` mode, ask whether to reconfigure `_meta.root_path` first. The read-only Workflow 1 (just reading `c-code-repos.json`) is always safe.

```bash
python .agents/skills/c-code/scripts/scan_inventory.py
```

This walks `_meta.root_path`, classifies every subdirectory, and rewrites `data/c-code-repos.json`. It uses `gh api repos/<owner>/<repo>` to detect fork status for user-owned repos, and falls back to checking the `upstream` remote for unreachable APIs.

For a quick diff (what changed since last scan), use `--diff` flag.

To retroactively fill in `source_star` for upstream-clones that were cloned before this skill existed (so we can tell which ones came from a star and which are old manual clones), use `--backfill-source-star`:

```bash
python .agents/skills/c-code/scripts/scan_inventory.py --backfill-source-star
```

This reads `data/stars_mapping.json` and, for every `upstream-clone` with `source_star: null`, parses `owner/repo` from `origin` and looks up `<owner>-<repo>.md` in the mapping. If a match is found, the field is filled in. Updates `_meta.last_backfill_source_star`.

To **detect drift** without writing the file (e.g., "did anything change in the Code folder since last scan?"), use `--verify`:

```bash
python .agents/skills/c-code/scripts/scan_inventory.py --verify
echo $?  # 0 = clean, 1 = drift detected
```

This walks the disk, compares each field (`type`, `origin`, `upstream`) against the JSON, and reports drift without writing. Also catches orphan folders (on disk, not in JSON) and phantom entries (in JSON, not on disk). Exits 1 if any drift is detected — useful in pre-commit hooks or CI. Does NOT call `gh api`, so it doesn't re-check fork status (use plain `scan_inventory.py` for that).

## Workflow 4 — explain the JSON

User asks "c-code-repos.json 怎么用" or "data/ 那个 json 干嘛的".

Point them to `docs/C-Code-Repos.md` — that's the user manual. Briefly summarize:
- It's the single source of truth, regenerated by `scan_inventory.py`
- Has `_meta` (root_path, schema version, last scan time) + `repos[]` array
- Each entry has `name`, `type`, `origin`, optional `upstream`/`parent`/`source_star`/`notes`
- Cross-reference with `data/stars_mapping.json` to find "starred but not yet cloned" repos

For schema details, read `references/json-schema.md`.

## Cross-platform notes

- **Primary machine is Windows** with `C:\Users\gotmo\Code`. The skill scripts (`scan_inventory.py`, `clone_repo.py`, `download_stars.py`) assume Windows paths and write to `data/*.json`. They should be considered **Windows-only tools**.
- macOS / native Linux: works fine. Edit `_meta.root_path` in `data/c-code-repos.json` to e.g. `~/Code` or `/home/<you>/Code`, then the bundled scripts run normally.
- **Termux (Android) + proot-distro Ubuntu**: a **read-only scratch env**. The bundled scripts will misbehave (wrong path, may write to `/mnt/sdcard/...` paths that won't sync with Windows). **Don't run them.** Direct `gh repo clone` / `git clone` to `/mnt/sdcard/Code/<repo>` (or any Linux path the user picks) is fine; just skip the JSON sync. The JSON lives on the Windows machine and gets refreshed next time the user runs `scan_inventory.py` there.
- The user account detection (`is this my fork?`) hardcodes the GitHub username `carterwayneskhizeine`. Change via `--user` flag or by editing the script's `DEFAULT_GH_USER` constant.

## Things to never do

- **Don't rename a cloned folder.** If the upstream repo is named `MVPaint`, the local folder must be `MVPaint`, not `3DTopia-MVPaint`. The `Owner-Repo` naming is only for `stars-readme/` files (which need to be unique on disk), never for the actual clones.
- **Don't run `git clone` directly.** Always go through `clone_repo.py` so the JSON stays in sync.
- **Don't fabricate `parent` / `upstream` data.** If the fork status is unclear, mark the entry as `type: "upstream-clone"` with a `notes` field explaining the ambiguity.
- **Don't delete a folder without explicit user confirmation.** Even if the conflict-resolution flow recommends it, the script will require typed confirmation of the folder name.
- **Don't skip the environment check.** Always run the detection snippet before Workflow 2 or Workflow 3. Running `clone_repo.py` on Termux will silently fail or corrupt state.
- **In `termux-ubuntu` mode, don't invoke the bundled scripts.** Direct `gh repo clone` / `git clone` to a Linux path IS fine; `clone_repo.py`, `scan_inventory.py`, and `download_stars.py` are NOT, because they hardcode Windows paths and write to `data/*.json`. The JSON sync happens later on the Windows machine.
- **In `termux-ubuntu` mode, don't write to `data/`, scripts, or existing files.** Only read files, run direct `gh`/`git` clone commands to a Linux path, and create new files under `docs/`.
- **In `other` mode, don't guess.** Stop and ask the user what to do — they may need to install `gh`, change `_meta.root_path`, or move to a different machine.
- **Don't ask the user to run `download_stars.py` and "回填" as separate follow-ups.** Workflow 2 already covers both — just run them as part of the clone.

## References

- `references/json-schema.md` — full schema spec for `data/c-code-repos.json`
- `docs/C-Code-Repos.md` — user-facing manual (in the project root's `docs/`)
- `stars_mapping.json` — maps `Owner-Repo.md` filenames in `stars-readme/` to GitHub URLs (used to resolve "clone this star" requests)
