---
name: code-zip-extract
description: Extract .7z archives stashed in `C:\Users\gotmo\Code\Code-zip\` into the local Code folder and keep the c-code inventory (`data/c-code-repos.json`) in sync. PRIMARY environment is Windows with 7-Zip installed at `C:\Program Files\7-Zip\7z.exe`. macOS / native Linux work by editing the `_meta.root_path` of the c-code inventory and pointing `--code-dir` / `--code-zip` to your local equivalents. Use this skill whenever the user mentions "解压 Code-zip", "把 .7z 解压到 Code 文件夹", "install from Code-zip", or has downloaded a .7z archive from a starred repo and wants it integrated into their local Code folder. Always maintains a ledger at `<code-zip>/extracted.json` recording which archives have been installed, when, and to where — so re-extracting by accident is hard. Built specifically to bridge the gap between the c-code `scan` skill and the user's habit of stashing archives in Code-zip/ before extracting.
---

# code-zip-extract — extract a .7z from `Code-zip/` and sync the inventory

This is the **archive-install** companion to the **c-code** skill. When the user downloads a `.7z` of a GitHub repo and drops it in `C:\Users\gotmo\Code\Code-zip\`, this skill extracts it into `C:\Users\gotmo\Code\` and chains the three inventory sync steps (`scan_inventory.py` → `--backfill-source-star` → `--verify`) so the new project shows up correctly in `data/c-code-repos.json` immediately.

One bundled script does the heavy lifting:

| Script | Purpose |
| --- | --- |
| `scripts/install_archive.py` | Resolve archive → inspect → extract → ledger → chain sync |

## File layout

```
github-stars/
├── .agents/skills/code-zip-extract/
│   ├── SKILL.md                       ← you are here
│   ├── scripts/
│   │   └── install_archive.py         ← main entry (extract + ledger + sync)
│   ├── references/
│   │   └── ledger-schema.md           ← `extracted.json` schema & ops
│   └── evals/
│       └── evals.json                 ← test cases for this skill
├── .agents/skills/c-code/
│   └── scripts/
│       └── scan_inventory.py          ← invoked by install_archive.py
├── data/
│   └── c-code-repos.json              ← updated by chain sync
└── …
```

## Outputs and side effects

- Writes to `C:\Users\gotmo\Code\<project>\...` (the extracted repo)
- Writes to `C:\Users\gotmo\Code\Code-zip\extracted.json` (ledger; created on first run)
- Writes to `C:\Users\gotmo\Code\github-stars\data\c-code-repos.json` (via chain sync)
- Does **not** delete the original `.7z` from `Code-zip/` (user manages their own stash)

## Environment detection — run this first

This skill writes to disk and triggers `scan_inventory.py` (which itself writes JSON). Detect the environment so you don't try to extract to a Termux path or invoke scripts under the wrong mode.

```bash
python -c "
import os, platform
sys_name = platform.system()
root = r'C:\Users\gotmo\Code'
if sys_name == 'Windows' and os.path.isdir(root):
    print(f'code-zip-extract mode: windows-local  ({sys_name} + {root})')
elif 'ANDROID_ROOT' in os.environ or 'TERMUX_VERSION' in os.environ or os.path.isdir('/data/data/com.termux'):
    print('code-zip-extract mode: termux-ubuntu  (refuse state-mutating ops)')
else:
    print(f'code-zip-extract mode: other  ({sys_name}; consider --code-dir / --ledger overrides)')
"
```

### Three modes

| Mode | When | Allowed actions |
|---|---|---|
| `windows-local` | Windows + `C:\Users\gotmo\Code` exists | Everything. The default path. `7-Zip` is expected at `C:\Program Files\7-Zip\7z.exe` |
| `termux-ubuntu` | Termux detected | **Refuse** the main workflow (script writes to Windows-locked paths). Direct 7-Zip extraction to a Linux path IS OK if the user explicitly asks, but skip the inventory sync and ledger updates. |
| `other` | Anything else (macOS, native Linux, weird Windows) | Allow main workflow if the user supplies `--code-dir` / `--code-zip` / `--ledger` overrides AND a 7-Zip binary is on PATH. Otherwise stop and ask. |

### What "core data" means (off-limits in `termux-ubuntu`)

Same as the c-code skill. This skill additionally considers:

- `extracted.json` ledger — Windows-machine territory
- The extracted repo directory itself

## When to trigger

Trigger phrases (Chinese OR English, exact wording not required):

- "解压 Code-zip 里的 X" / "把 X.7z 解压到 Code 文件夹"
- "install memorix.7z" / "install that 7z"
- "我下载了一个 .7z，怎么装到 Code 里"
- "从 Code-zip 安装到 Code 文件夹"
- "ledger 里有没有 memorix" / "哪些 7z 已经装过了"

**Do NOT trigger** for:

- General .7z / .zip extraction in unrelated paths (this skill assumes `Code-zip/` and `Code/`)
- Cloning a fresh repo from GitHub (that's c-code's Workflow 2 / `clone_repo.py`)
- Modifying or reading the extracted repo's contents

## The 5 workflows

### Workflow 1 — install an archive (default)

User says "解压 memorix.7z" or "install that one in Code-zip".

1. **Environment check.** Run the detection snippet above. Stop if `termux-ubuntu`. In `other` mode, confirm overrides.
2. **Resolve the archive path.** Accept either:
   - Full path: `C:\Users\gotmo\Code\Code-zip\memorix.7z`
   - Bare name: `memorix` → script appends `.7z` and searches `<code-zip>/`
3. **Pre-flight** (handled by the script):
   - File exists, has `.7z` extension
   - 7-Zip CLI is found (default Windows install path)
   - **Target directory doesn't exist** — otherwise refuse and ask the user to clean up first. To override, pass `--force` (this also wipes the prior ledger entry).
   - **Not already in the ledger** — otherwise refuse and tell them when it was extracted. Use `--force` to re-run.
4. **Inspect the archive** via `7z l` to detect top-level structure:
   - Single top-level `memorix\\…` → normal case, target = `memorix`
   - Single top-level `memorix\\memorix\\…` (and `memorix\\.git\\…` printed as another top entry) → **nested case**, target still = `memorix`. After extraction the script promotes the inner folder up one level so the path matches the normal case.
   - Multiple unrelated top-level folders → abort with "复杂归档，未自动处理"
5. **Extract** via `7z x -o<code_dir> -y` with a 5-minute timeout.
6. **Chain sync** (`--no-sync` to opt out):
   ```
   python <c-code-skill>/scripts/scan_inventory.py            # full scan
   python <c-code-skill>/scripts/scan_inventory.py --backfill-source-star
   python <c-code-skill>/scripts/scan_inventory.py --verify   # exit 0 = clean, 1 = drift
   ```
7. **Update the ledger**: append `<code-zip>/extracted.json` entry with archive path, sha256, timestamp, target, inventory type, source star if known, and the three sync exit codes.
8. **Report**: one success block with archive, target, ledger diff, sync exit codes, and the matched inventory entry (so the user immediately sees what the JSON now contains).

```bash
python .agents/skills/code-zip-extract/scripts/install_archive.py memorix
```

### Workflow 2 — query the ledger

User says "哪些 7z 已经解压过了" or "ledger 里有没有 memorix".

```bash
python .agents/skills/code-zip-extract/scripts/install_archive.py --list
```

The script prints a table with archive name, project name, extracted-at, inventory type, and source star. Empty ledger prints a friendly hint instead of an empty table.

For ad-hoc checks (e.g., from a parent agent), reading `extracted.json` directly is fine — see `references/ledger-schema.md` for the schema.

### Workflow 3 — re-extract / replace

User says "我想重装 memorix" or "the target got corrupted, redo it".

Two failure modes that `--force` resets:

1. **Target folder still on disk** — most common. Cause: previous run, then user deleted only some files. `--force` lets the script wipe and re-extract.
2. **Ledger still says "extracted"** but the target is gone — rare. `--force` lets the script write a fresh ledger entry (replacing the prior one).

```bash
python .agents/skills/code-zip-extract/scripts/install_archive.py memorix --force
```

Warning: `--force` does **not** snapshot or diff your files first. If the target contains uncommitted work, commit, stash, or back it up before re-extracting.

### Workflow 4 — dry-run / preview

User wants to know what would happen before committing.

```bash
python .agents/skills/code-zip-extract/scripts/install_archive.py memorix --dry-run
```

Prints resolved archive path, target, ledger state, and exits 0 without touching anything. Useful for sanity-check before a 14-MiB extract on a slow disk.

### Workflow 5 — non-default locations (macOS, Linux, weird Windows)

User points the skill at different paths.

```bash
python .agents/skills/code-zip-extract/scripts/install_archive.py \
    /Users/zhang/Downloads/foo.7z \
    --code-dir /Users/zhang/Code \
    --code-zip /Users/zhang/Downloads \
    --ledger   /Users/zhang/Downloads/extracted.json
```

The script uses these CLI overrides throughout — no need to edit the file. The c-code companion on a non-Windows machine must also have its `_meta.root_path` updated; the script does **not** rewrite that automatically.

## Acceptance criteria

A successful run:

1. The `.7z` file is still in `Code-zip/` (untouched).
2. `C:\Users\gotmo\Code\<project>\` exists with all files extracted.
3. `C:\Users\gotmo\Code\Code-zip\extracted.json` has a new entry at the end of `extractions[]`.
4. `C:\Users\gotmo\Code\github-stars\data\c-code-repos.json` contains a new entry for the project, with `type` correctly set (likely `upstream-clone` for a third-party `origin`).
5. `scan_inventory.py --verify` returns exit 0.
6. For archives whose origin matches a `stars-readme/<owner>-<repo>.md`, `--backfill-source-star` populated the `source_star` field.

If any of these fail, the script exits non-zero and prints which step broke. Don't claim success unless all six hold.

## Cross-platform notes

- **Primary machine is Windows** with `C:\Users\gotmo\Code` and 7-Zip installed at the default path. The script searches both `%ProgramFiles%` and `%ProgramFiles(x86)%`.
- **macOS** users should `brew install 7zip p7zip` and either symlink `7z` onto PATH or pre-set env vars. Override `--code-dir`, `--code-zip`, `--ledger` as needed.
- **Native Linux** same as macOS — package manager should provide `p7zip-full`.
- **Termux (Android) + proot-distro Ubuntu**: this skill is **read-mostly**. The default ledger path won't be writeable, and the inventory sync hardcodes `C:\Users\gotmo\Code`. Refuse the main workflow. Users should extract locally then sync the JSON later on Windows by hand.
- The c-code companion script `scan_inventory.py` has the same hardcoded Windows path assumption; this skill does **not** patch it. If the user wants the chain to work on macOS/Linux, edit `c-code/scripts/scan_inventory.py`'s `DEFAULT_ROOT_HINT` first.

## Things to never do

- **Don't silently overwrite an existing target.** Default behavior is refuse. `--force` is opt-in.
- **Don't silently re-extract a ledger-known archive.** Same default-refuse policy.
- **Don't auto-delete the `.7z` from `Code-zip/`.** The user may want to keep archives (for re-cloning elsewhere, transfer, etc.). Ledger records that it was extracted; that's enough.
- **Don't run on Termux without explicit override.** The default Windows path will silently fail.
- **Don't trust `os.path.exists()` to detect "is this really a fresh archive?"** — that's what the ledger is for. Two archives with the same basename but different content should appear as separate entries (`archive_sha256` will differ).
- **Don't fabricate inventory data.** If `scan_inventory.py` couldn't classify (e.g., the extracted folder isn't a git repo), the ledger stores `inventory_type=null`. Don't guess.
- **Don't chain `scan_inventory.py` under `--no-sync`** — that flag means "skip the chain". `--no-sync` and ledger updates are still both on by default.
- **Don't write to `Code/` for archives the user didn't ask you to handle.** Every CLI invocation processes exactly one archive.

## References

- `references/ledger-schema.md` — full schema spec for `<code-zip>/extracted.json`
- `data/c-code-repos.json` — what the chain sync updates
- `data/stars_mapping.json` — what `--backfill-source-star` cross-references (so source_star can auto-fill)
