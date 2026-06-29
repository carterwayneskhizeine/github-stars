#!/usr/bin/env python3
"""scan_inventory.py — walk the local code folder and regenerate
data/c-code-repos.json with one entry per subdirectory.

Usage:
    python scan_inventory.py                    # full scan, write JSON
    python scan_inventory.py --diff             # show what changed, don't write
    python scan_inventory.py --root <path>      # override root_path
    python scan_inventory.py --json <path>      # override JSON path
    python scan_inventory.py --user <username>  # override GH user detection

Classification rules (in order):
  1. If folder has no .git/                  → type = "non-git"
  2. If folder has .git/ but no remotes      → type = "no-remote-git"
  3. If origin is owned by GH_USER:
       - gh api says is_fork = true           → type = "fork"      (with upstream/parent)
       - gh api says is_fork = false         → type = "original"
       - gh api fails (private/deleted)      → type = "original"  (assume non-fork;
                                                                    or "fork" if upstream
                                                                    remote exists)
  4. Otherwise (origin is third-party)        → type = "upstream-clone"
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------- paths ----------

# Path layout: <project>/.agents/skills/c-code/scripts/scan_inventory.py
# So PROJECT_DIR is 3 levels up from this file (skip scripts/ → c-code/ → skills/ → .agents/ → <project>).
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
PROJECT_DIR = SKILL_DIR.parent.parent.parent
DEFAULT_JSON = PROJECT_DIR / "data" / "c-code-repos.json"
DEFAULT_MAPPING = PROJECT_DIR / "data" / "stars_mapping.json"
DEFAULT_ROOT_HINT = "C:\\Users\\gotmo\\Code"
DEFAULT_GH_USER = "carterwayneskhizeine"


# ---------- helpers ----------

def run(cmd: list[str], cwd: Path | None = None, timeout: int = 15) -> str:
    """Run a command, return stdout. Returns '' on failure (non-zero exit)."""
    try:
        r = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
        return r.stdout.strip() if r.returncode == 0 else ""
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def git_remote(repo: Path, name: str) -> str | None:
    """Return the URL of a git remote, or None if not set."""
    out = run(["git", "remote", "get-url", name], cwd=repo)
    return out or None


def has_git(dirpath: Path) -> bool:
    return (dirpath / ".git").exists()


def is_git_repo(dirpath: Path) -> bool:
    """More reliable than has_git: also handles worktrees and bare clones."""
    return run(["git", "rev-parse", "--git-dir"], cwd=dirpath).startswith(".")


def gh_api_fork_status(slug: str) -> dict | None:
    """Call `gh api repos/<slug>` and return {is_fork, parent} or None on failure."""
    raw = run(["gh", "api", f"repos/{slug}", "--jq",
               "{is_fork: .fork, parent: .parent.full_name}"], timeout=15)
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return {
            "is_fork": bool(data.get("is_fork")),
            "parent": data.get("parent") or None,
        }
    except json.JSONDecodeError:
        return None


def slug_from_url(url: str) -> str | None:
    """Extract owner/repo from a GitHub URL (https or ssh)."""
    import re
    m = re.search(r"github\.com[:/]([^/]+)/([^/.]+?)(?:\.git)?/?$", url)
    return f"{m.group(1)}/{m.group(2)}" if m else None


def now_iso() -> str:
    """ISO 8601 with local timezone offset (e.g. 2026-06-27T17:30:00+08:00)."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


# ---------- core ----------

def classify_dir(dirpath: Path, gh_user: str) -> dict:
    """Return a JSON entry for one subdirectory of root."""
    name = dirpath.name
    last_scanned = now_iso()

    if not is_git_repo(dirpath):
        return {
            "name": name,
            "type": "non-git",
            "origin": None,
            "upstream": None,
            "parent": None,
            "is_fork": False,
            "source_star": None,
            "last_scanned": last_scanned,
            "notes": None,
        }

    origin = git_remote(dirpath, "origin")
    if not origin:
        return {
            "name": name,
            "type": "no-remote-git",
            "origin": None,
            "upstream": None,
            "parent": None,
            "is_fork": False,
            "source_star": None,
            "last_scanned": last_scanned,
            "notes": "本地 git init 但未配置 remote",
        }

    origin_slug = slug_from_url(origin)
    is_user_owned = bool(origin_slug and origin_slug.split("/")[0] == gh_user)

    if not is_user_owned:
        return {
            "name": name,
            "type": "upstream-clone",
            "origin": origin,
            "upstream": None,
            "parent": None,
            "is_fork": False,
            "source_star": None,
            "last_scanned": last_scanned,
            "notes": None,
        }

    # User-owned: check fork status
    upstream = git_remote(dirpath, "upstream")
    api = gh_api_fork_status(origin_slug) if origin_slug else None

    if api and api["is_fork"]:
        parent = api["parent"] or (slug_from_url(upstream) if upstream else None)
        return {
            "name": name,
            "type": "fork",
            "origin": origin,
            "upstream": upstream,
            "parent": parent,
            "is_fork": True,
            "source_star": None,
            "last_scanned": last_scanned,
            "notes": None,
        }

    if upstream and not api:
        # API failed but we have an explicit upstream remote → still a fork
        parent = slug_from_url(upstream)
        return {
            "name": name,
            "type": "fork",
            "origin": origin,
            "upstream": upstream,
            "parent": parent,
            "is_fork": True,
            "source_star": None,
            "last_scanned": last_scanned,
            "notes": "gh api 失败（私有/已删），靠 upstream remote 判定为 fork",
        }

    # Either API said is_fork=false, or API failed with no upstream
    return {
        "name": name,
        "type": "original",
        "origin": origin,
        "upstream": None,
        "parent": None,
        "is_fork": False,
        "source_star": None,
        "last_scanned": last_scanned,
        "notes": ("gh api 失败，按 original 记录；如确认是 fork 请手动改 type" if not api else None),
    }


def load_existing(json_path: Path) -> dict:
    """Load the existing JSON, returning an empty stub if missing/corrupted."""
    if not json_path.exists():
        return {"_meta": {}, "repos": []}
    try:
        with json_path.open(encoding="utf-8") as f:
            data = json.load(f)
        if "_meta" not in data or "repos" not in data:
            print(f"WARN: {json_path} missing _meta or repos; treating as empty", file=sys.stderr)
            return {"_meta": {}, "repos": []}
        return data
    except (json.JSONDecodeError, OSError) as e:
        print(f"WARN: {json_path} unreadable ({e}); treating as empty", file=sys.stderr)
        return {"_meta": {}, "repos": []}


def preserve_metadata(existing: dict, repos: list[dict]) -> dict:
    """Carry over source_star and notes from existing entries when name matches."""
    by_name = {e["name"]: e for e in existing.get("repos", [])}
    for entry in repos:
        old = by_name.get(entry["name"])
        if old:
            if old.get("source_star"):
                entry["source_star"] = old["source_star"]
            if old.get("notes") and not entry.get("notes"):
                entry["notes"] = old["notes"]
    return {"_meta": existing.get("_meta", {}), "repos": repos}


def diff_repos(old: list[dict], new: list[dict]) -> None:
    """Print a human-readable diff. Used by --diff mode."""
    old_by = {r["name"]: r for r in old}
    new_by = {r["name"]: r for r in new}
    added = sorted(set(new_by) - set(old_by))
    removed = sorted(set(old_by) - set(new_by))
    changed_types = sorted(
        n for n in set(old_by) & set(new_by)
        if old_by[n]["type"] != new_by[n]["type"]
    )

    if not (added or removed or changed_types):
        print("(no changes)")
        return
    if added:
        print(f"+ added   ({len(added)}): {', '.join(added)}")
    if removed:
        print(f"- removed ({len(removed)}): {', '.join(removed)}")
    if changed_types:
        print(f"~ retyped ({len(changed_types)}):")
        for n in changed_types:
            print(f"    {n}: {old_by[n]['type']} → {new_by[n]['type']}")


# ---------- backfill source_star ----------

def backfill_source_star(json_path: Path, mapping_path: Path) -> int:
    """For each upstream-clone entry with source_star=None, try to find a matching
    entry in stars_mapping.json by parsing owner/repo from the entry's origin URL
    and looking up the key `<owner>-<repo>.md` (case-insensitive).

    Writes JSON only if at least one match was made. Updates
    `_meta.last_backfill_source_star` so you can see when the last backfill ran.

    Returns 0 on success, 1 if mapping file is missing.
    """
    if not mapping_path.exists():
        print(f"ERROR: {mapping_path} not found", file=sys.stderr)
        return 1

    with mapping_path.open(encoding="utf-8") as f:
        mapping = json.load(f)
    # Case-insensitive lookup; preserve the actual key (which is case-preserving).
    mapping_lower: dict[str, str] = {
        k.lower(): k for k in mapping.keys() if not k.startswith("_")
    }

    data = load_existing(json_path)
    repos = data.get("repos", [])
    matched: list[tuple[str, str]] = []
    unmatched: list[tuple[str, str]] = []
    skipped = 0

    for entry in repos:
        if entry.get("source_star"):
            skipped += 1
            continue
        if entry["type"] != "upstream-clone":
            skipped += 1
            continue
        origin = entry.get("origin")
        if not origin:
            skipped += 1
            continue
        slug = slug_from_url(origin)
        if not slug or "/" not in slug:
            skipped += 1
            continue
        owner, repo = slug.split("/", 1)
        star_filename = f"{owner}-{repo}.md"
        actual_key = mapping_lower.get(star_filename.lower())
        if actual_key:
            entry["source_star"] = actual_key
            matched.append((entry["name"], actual_key))
        else:
            unmatched.append((entry["name"], star_filename))

    # Persist (only if anything changed; keep the order canonical)
    if matched:
        type_order = ["original", "fork", "upstream-clone", "no-remote-git", "non-git"]
        repos.sort(key=lambda r: (type_order.index(r["type"]), r["name"].lower()))
        data["repos"] = repos
        if "_meta" not in data:
            data["_meta"] = {}
        data["_meta"]["last_backfill_source_star"] = now_iso()
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")

    print(f"Backfill source_star results:")
    print(f"  matched:   {len(matched)}")
    print(f"  unmatched: {len(unmatched)}")
    print(f"  skipped:   {skipped} (already has source_star, or not upstream-clone, or no origin)")
    if matched:
        print(f"\nMatched entries:")
        for name, star in matched:
            print(f"  {name:40s}  <- {star}")
    if unmatched:
        print(f"\nUnmatched upstream-clones (not in stars_mapping.json):")
        for name, expected in unmatched:
            print(f"  {name:40s}  (looked for {expected})")
    return 0


# ---------- verify (drift detection) ----------

def verify_drift(root: Path, existing: dict, gh_user: str) -> tuple[dict, int]:
    """Compare the on-disk state with the existing JSON, field by field.

    What this catches (without calling `gh api`):
      - type drift: non-git ↔ no-remote-git ↔ git-with-origin mismatches
        (for git-with-origin, also flags "upstream-clone but origin is now
        user-owned" and vice versa)
      - origin URL drift
      - upstream URL drift
      - orphan folders (on disk, not in JSON)
      - phantom entries (in JSON, not on disk)

    What this does NOT catch (need full re-scan):
      - is_fork / parent changes (requires `gh api`)
      - is_user_owned mis-classification when origin URL stayed the same

    Returns (drift_dict, total_drift_count).
    """
    by_name = {r["name"]: r for r in existing.get("repos", [])}
    disk_names: set[str] = set()
    drift: dict = {
        "type": [],
        "origin": [],
        "upstream": [],
        "orphan_folders": [],
        "phantom_entries": [],
    }

    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        disk_names.add(child.name)
        name = child.name
        is_git = is_git_repo(child)
        origin = git_remote(child, "origin") if is_git else None
        upstream = git_remote(child, "upstream") if is_git else None

        # What the disk "should" look like, ignoring gh_api classification
        if not is_git:
            disk_type = "non-git"
        elif not origin:
            disk_type = "no-remote-git"
        else:
            disk_type = "git-with-origin"

        if name not in by_name:
            drift["orphan_folders"].append(name)
            continue

        entry = by_name[name]
        actual_type = entry["type"]

        # Type drift
        if disk_type in ("non-git", "no-remote-git"):
            if actual_type != disk_type:
                drift["type"].append((name, actual_type, disk_type))
        else:  # git-with-origin
            slug = slug_from_url(origin) if origin else None
            owner = slug.split("/")[0] if slug else None
            is_user_owned_now = owner == gh_user
            if actual_type == "upstream-clone" and is_user_owned_now:
                drift["type"].append((name, actual_type, f"user-owned (origin={owner})"))
            elif actual_type in ("original", "fork") and not is_user_owned_now:
                drift["type"].append((name, actual_type, f"third-party origin ({owner})"))

        # origin drift (skip if both are None/empty)
        json_origin = entry.get("origin")
        if (origin or json_origin) and origin != json_origin:
            drift["origin"].append((name, json_origin, origin))

        # upstream drift (skip if both are None/empty)
        json_upstream = entry.get("upstream")
        if (upstream or json_upstream) and upstream != json_upstream:
            drift["upstream"].append((name, json_upstream, upstream))

    for name in by_name:
        if name not in disk_names:
            drift["phantom_entries"].append(name)

    total = sum(len(v) for v in drift.values())
    return drift, total


def print_drift_report(drift: dict, root: Path, existing: dict) -> None:
    """Pretty-print the drift result. Goes to stdout."""
    print("=" * 60)
    print("Drift report (--verify)")
    print("=" * 60)
    print(f"  root:           {root}")
    print(f"  JSON:           {len(existing.get('repos', []))} entries")
    last = existing.get("_meta", {}).get("last_full_scan", "—")
    print(f"  last_full_scan: {last}")
    print()
    print("  Summary:")
    print(f"    type drift:      {len(drift['type'])}")
    print(f"    origin drift:    {len(drift['origin'])}")
    print(f"    upstream drift:  {len(drift['upstream'])}")
    print(f"    orphan folders:  {len(drift['orphan_folders'])}")
    print(f"    phantom entries: {len(drift['phantom_entries'])}")
    print()

    if drift["type"]:
        print("Type drift:")
        for name, j, d in drift["type"]:
            print(f"  {name}:")
            print(f"    json says:  {j}")
            print(f"    disk says:  {d}")
        print()

    if drift["origin"]:
        print("Origin URL drift:")
        for name, j, d in drift["origin"]:
            print(f"  {name}:")
            print(f"    json:  {j}")
            print(f"    disk:  {d}")
        print()

    if drift["upstream"]:
        print("Upstream URL drift:")
        for name, j, d in drift["upstream"]:
            print(f"  {name}:")
            print(f"    json:  {j}")
            print(f"    disk:  {d}")
        print()

    if drift["orphan_folders"]:
        print("Orphan folders (on disk, not in JSON):")
        for n in sorted(drift["orphan_folders"]):
            print(f"  + {n}")
        print()

    if drift["phantom_entries"]:
        print("Phantom entries (in JSON, not on disk):")
        for n in sorted(drift["phantom_entries"]):
            print(f"  - {n}")
        print()

    total = sum(len(v) for v in drift.values())
    if total == 0:
        print("Verdict: clean (no drift)")
    else:
        print(f"Verdict: {total} drift item(s) detected")


# ---------- entry point ----------

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--root", help="Override root path (else read from JSON's _meta.root_path, then default C:\\Users\\gotmo\\Code)")
    p.add_argument("--json", help=f"Override JSON path (default: {DEFAULT_JSON})")
    p.add_argument("--user", default=DEFAULT_GH_USER, help=f"GitHub username (default: {DEFAULT_GH_USER})")
    p.add_argument("--diff", action="store_true", help="Show diff vs existing JSON, don't write")
    p.add_argument("--backfill-source-star", action="store_true",
                   help="For each upstream-clone with null source_star, match against stars_mapping.json (parsed from origin) and fill it in. Writes JSON.")
    p.add_argument("--mapping", help=f"Override stars_mapping path for --backfill-source-star (default: {DEFAULT_MAPPING})")
    p.add_argument("--verify", action="store_true",
                   help="Walk the disk and compare against the existing JSON field-by-field "
                        "(type, origin, upstream, orphan, phantom). Reports drift but does NOT write. "
                        "Exits 1 if drift is detected (useful in CI/pre-commit). "
                        "Does not call gh api — for full re-classification use scan_inventory.py without --verify.")
    args = p.parse_args()

    json_path = Path(args.json) if args.json else DEFAULT_JSON

    # Backfill is its own mode: doesn't need a root scan, works on the existing JSON.
    if args.backfill_source_star:
        mapping_path = Path(args.mapping) if args.mapping else DEFAULT_MAPPING
        return backfill_source_star(json_path, mapping_path)

    existing = load_existing(json_path)

    root_str = args.root or existing.get("_meta", {}).get("root_path") or DEFAULT_ROOT_HINT
    root = Path(root_str)
    if not root.is_dir():
        print(f"ERROR: root_path '{root}' is not a directory", file=sys.stderr)
        return 1

    # Verify mode: walk disk, compare field-by-field to existing JSON, no write.
    if args.verify:
        drift, total = verify_drift(root, existing, args.user)
        print_drift_report(drift, root, existing)
        return 1 if total else 0

    print(f"Scanning {root} (gh_user={args.user}) ...", file=sys.stderr)

    entries: list[dict] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        try:
            entry = classify_dir(child, args.user)
        except Exception as e:
            print(f"WARN: failed to classify {child}: {e}", file=sys.stderr)
            entry = {
                "name": child.name,
                "type": "non-git",
                "origin": None,
                "upstream": None,
                "parent": None,
                "is_fork": False,
                "source_star": None,
                "last_scanned": now_iso(),
                "notes": f"scan error: {e}",
            }
        entries.append(entry)

    if args.diff:
        diff_repos(existing.get("repos", []), entries)
        return 0

    # Preserve source_star and notes from existing JSON
    merged = preserve_metadata(existing, entries)
    # Preserve any unknown _meta fields the user may have added (e.g.
    # last_backfill_source_star set by --backfill-source-star), then
    # overwrite the ones we manage.
    new_meta = {
        "description": "本地 Code 文件夹的仓库清单（单一数据源）",
        "root_path": str(root),
        "schema_version": 1,
        "last_full_scan": now_iso(),
        "gh_user": args.user,
    }
    old_meta = existing.get("_meta", {})
    # Carry over unknown keys (anything not in new_meta) so future fields
    # we add won't get silently dropped.
    for k, v in old_meta.items():
        if k not in new_meta:
            new_meta[k] = v
    merged["_meta"] = new_meta

    json_path.parent.mkdir(parents=True, exist_ok=True)
    # Sort by type (canonical order) then by case-insensitive name
    type_order = ["original", "fork", "upstream-clone", "no-remote-git", "non-git"]
    merged["repos"].sort(key=lambda r: (type_order.index(r["type"]), r["name"].lower()))
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
        f.write("\n")

    by_type: dict[str, int] = {}
    for e in entries:
        by_type[e["type"]] = by_type.get(e["type"], 0) + 1
    print(f"Wrote {len(entries)} entries to {json_path}", file=sys.stderr)
    for t in ("original", "fork", "upstream-clone", "no-remote-git", "non-git"):
        if t in by_type:
            print(f"  {t:18s} {by_type[t]}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
