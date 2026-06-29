# Ledger schema — `Code-zip/extracted.json`

The ledger is the durable record of "this `.7z` from `Code-zip/` was installed into `C:\Users\gotmo\Code\<project>\` on <date>". It lives **inside** the user's own `Code-zip/` folder so that:

- It stays on the user's machine, not in this skill's repo (no JSON in github-stars to commit).
- The user can open it, scan it, hand-edit it.
- Each extraction is atomic and idempotent on `archive` filename.

## Location

Default: `C:\Users\gotmo\Code\Code-zip\extracted.json`
Override: `python install_archive.py --ledger <path>`

The skill creates the file with `_meta` + empty `extractions` on first successful run.

## Top-level shape

```json
{
  "_meta": {
    "schema_version": 1,
    "last_updated": "2026-06-29T22:46:00+08:00"
  },
  "extractions": [
    { /* one entry per archive */ }
  ]
}
```

`_meta.last_updated` is rewritten on every save (atomic write via `.tmp` + rename).
`_meta.schema_version` is preserved (and reset to 1 if missing).

## Entry shape

```jsonc
{
  "archive": "memorix.7z",
  "archive_path": "C:\\Users\\gotmo\\Code\\Code-zip\\memorix.7z",
  "archive_sha256": "5b8a...c3d",
  "extracted_at": "2026-06-29T22:46:00+08:00",
  "target_dir": "C:\\Users\\gotmo\\Code\\memorix",
  "project_name": "memorix",
  "size_bytes_archived": 14140576,
  "inventory_type": "upstream-clone",
  "source_star": "AVIDS2-memorix.md",
  "is_fork": false,
  "synced": true,
  "sync_results": {
    "scan": 0,
    "backfill": 0,
    "verify": 0
  }
}
```

| Field | Type | Notes |
|---|---|---|
| `archive` | string | Just the filename (`memorix.7z`). This is the natural key used to detect re-runs. |
| `archive_path` | string | Absolute path at extraction time. The file may have moved since. |
| `archive_sha256` | hex string | Snapshot of the archive contents at extract time. Lets you detect "same name, different bytes". |
| `extracted_at` | ISO 8601 | Local timezone (`+08:00` for this user). |
| `target_dir` | string | Where it landed. If `project_name/memorix/.git` etc. got nested, the script promoted it here. |
| `project_name` | string | The folder name used (`memorix` here, even if the archive's top-level was `memorix/memorix/`). |
| `size_bytes_archived` | int | The .7z's size, in bytes. |
| `inventory_type` | string \| null | What `c-code-repos.json` recorded for this repo: `original`, `fork`, `upstream-clone`, `no-remote-git`, `non-git`. `null` if the chain sync didn't run (`--no-sync`). |
| `source_star` | string \| null | `stars-readme/<owner>-<repo>.md` filename, if `--backfill-source-star` matched. |
| `is_fork` | bool \| null | Mirrors `c-code-repos.json`'s `is_fork` for this entry. |
| `synced` | bool | `false` only if you ran with `--no-sync`. |
| `sync_results` | object \| null | Map of `{scan, backfill, verify}` → exit code (`0` = ok, non-zero = drift/error). `null` if `synced=false`. |

## Operations

### Append (default)

```bash
python install_archive.py memorix
```

If `extractions` already contains an `archive: "memorix.7z"`, the script refuses with exit 3 (use `--force` to replace).

### Replace with `--force`

```bash
python install_archive.py memorix --force
```

Removes any prior entry with `archive: "memorix.7z"`, then appends the new one. Also allows overwriting an existing target directory.

### Atomic write

Every save goes through a temp-file dance:

```python
tmp = path.with_suffix(path.suffix + ".tmp")
tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
tmp.replace(path)
```

So an interrupted extraction won't leave a partial JSON. If you ever see a stray `extracted.json.tmp`, it's safe to delete.

### Querying by ad-hoc Python

```python
import json
ledger = json.load(open(r"C:\Users\gotmo\Code\Code-zip\extracted.json", encoding="utf-8"))
for entry in ledger["extractions"]:
    print(entry["archive"], entry["inventory_type"], entry["source_star"])
```

The skill also provides a `--list` table renderer that does this for you.

### Hand edits

The format is stable enough that hand-edits are safe — the script will:

- Read whatever's there on next invocation
- Accept missing `extractions` (treats as empty)
- Accept missing `_meta` (rewrites with defaults)
- Refuse with exit 3 if `archive` already exists in `extractions` for the new run, so you can manually de-duplicate by deleting entries before re-running.

## Why a ledger, not a flag

Two reasons:

1. **The user offloads the decision from "did I extract this?" to a queryable source.** Want to know what's installed? `python install_archive.py --list` or read the JSON. No memory of filenames required.
2. **`.7z` and the resulting folder are in different trees** (`Code-zip/` vs `Code/`). A flag on the folder wouldn't catch "I deleted the folder and want to re-extract". A ledger in `Code-zip/` (where the archive physically is) is naturally co-located with the artifact.

If the user wants the ledger somewhere else (`docs/` of github-stars, a database, etc.), pass `--ledger` and they can move it.
