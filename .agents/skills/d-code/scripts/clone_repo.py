#!/usr/bin/env python3
"""clone_repo.py — clone a GitHub repo into the local code folder with
conflict detection and JSON inventory update.

Usage:
    python clone_repo.py vercel/eve
    python clone_repo.py https://github.com/a2ui-project/a2ui
    python clone_repo.py stars-readme/3DTopia-MVPaint.md
    python clone_repo.py --list-new   # show starred repos not yet cloned

The target is the FIRST positional argument. The script:
  1. Resolves the target to an owner/repo slug and a desired local folder name.
  2. Checks if the folder already exists under root_path.
  3. If it does, reads its origin and decides:
     - same origin                  → "已存在" and exits
     - same fork family             → tells user, exits
     - totally different repo       → interactive: cancel / rename / replace
  4. Otherwise runs `gh repo clone <owner>/<repo> <folder>`.
  5. On success, updates data/d-code-repos.json.

Pass --yes to skip the interactive prompt (uses "rename" as default on conflict).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Path layout: <project>/.agents/skills/d-code/scripts/clone_repo.py
# So PROJECT_DIR is 3 levels up from this file.
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
PROJECT_DIR = SKILL_DIR.parent.parent.parent
DEFAULT_JSON = PROJECT_DIR / "data" / "d-code-repos.json"
STARS_README_DIR = PROJECT_DIR / "stars-readme"
STARS_MAPPING = PROJECT_DIR / "data" / "stars_mapping.json"


# ---------- helpers ----------

def run(cmd: list[str], cwd: Path | None = None, timeout: int = 30) -> tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except FileNotFoundError as e:
        return 127, "", str(e)


def slug_from_url(url: str) -> str | None:
    m = re.search(r"github\.com[:/]([^/]+)/([^/.]+?)(?:\.git)?/?$", url)
    return f"{m.group(1)}/{m.group(2)}" if m else None


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load_json(path: Path) -> dict:
    if not path.exists():
        return {"_meta": {}, "repos": []}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ---------- input resolution ----------

def resolve_target(target: str) -> tuple[str, str, str | None]:
    """Return (owner_repo, folder_name, source_star_or_None)."""
    # Case 1: stars-readme/Owner-Repo.md
    m = re.match(r"^stars-readme/(.+)\.md$", target)
    if m:
        star_filename = target.split("/")[-1]
        if STARS_MAPPING.exists():
            mapping = load_json(STARS_MAPPING)
            url = mapping.get(star_filename)
            if url:
                slug = slug_from_url(url)
                if slug:
                    return slug, slug.split("/")[1], star_filename
        print(f"ERROR: {star_filename} not found in {STARS_MAPPING}", file=sys.stderr)
        sys.exit(1)

    # Case 2: owner/repo
    if re.match(r"^[\w.-]+/[\w.-]+$", target):
        slug = target
        return slug, slug.split("/")[1], None

    # Case 3: full URL
    slug = slug_from_url(target)
    if slug:
        return slug, slug.split("/")[1], None

    print(f"ERROR: cannot parse target '{target}' (expected owner/repo, URL, or stars-readme/Owner-Repo.md)", file=sys.stderr)
    sys.exit(1)


# ---------- conflict detection ----------

def detect_conflict(folder: Path, target_slug: str) -> dict:
    """Read the existing folder's git config and decide what kind of conflict it is.

    Returns a dict:
      {
        "status": "same" | "fork-family" | "different" | "no-git",
        "origin": str | None,
        "upstream": str | None,
        "details": str,
      }
    """
    if not folder.exists():
        return {"status": "no-git", "origin": None, "upstream": None, "details": "folder does not exist"}

    # Try to read git config
    rc, origin, _ = run(["git", "remote", "get-url", "origin"], cwd=folder)
    origin = origin.strip() or None
    rc2, upstream, _ = run(["git", "remote", "get-url", "upstream"], cwd=folder)
    upstream = upstream.strip() or None

    if not origin:
        return {"status": "no-git", "origin": None, "upstream": upstream, "details": "folder exists but is not a git repo or has no origin"}

    target_origin_candidates = {
        f"https://github.com/{target_slug}.git",
        f"git@github.com:{target_slug}.git",
        f"https://github.com/{target_slug}",
    }
    if origin in target_origin_candidates:
        return {"status": "same", "origin": origin, "upstream": upstream, "details": f"已存在（origin = {origin}）"}

    target_owner, target_repo = target_slug.split("/")
    origin_slug = slug_from_url(origin) or ""
    upstream_slug = slug_from_url(upstream) if upstream else ""

    # Fork family: same parent or same fork
    if target_slug in (origin_slug, upstream_slug) or origin_slug in (target_slug, upstream_slug):
        return {
            "status": "fork-family",
            "origin": origin,
            "upstream": upstream,
            "details": (
                f"本地 {folder.name} 的 origin={origin_slug}, upstream={upstream_slug or '—'}，"
                f"跟目标 {target_slug} 是同一 fork 家族"
            ),
        }

    return {
        "status": "different",
        "origin": origin,
        "upstream": upstream,
        "details": f"本地 {folder.name} 是完全不同的 repo（origin={origin_slug}）",
    }


def ask_user_on_conflict(folder: Path, target_slug: str, conflict: dict) -> str:
    """Print options and read choice from stdin. Returns 'cancel' | 'rename' | 'replace'."""
    print(f"\n⚠ 名称冲突：{folder} 已存在", file=sys.stderr)
    print(f"  {conflict['details']}", file=sys.stderr)
    print(f"  你想克隆的是: {target_slug}", file=sys.stderr)
    print(file=sys.stderr)
    print("  [1] 取消（不克隆）", file=sys.stderr)
    print(f"  [2] 用不同名字克隆（建议: {target_slug.replace('/', '-')}）", file=sys.stderr)
    print(f"  [3] 删除 {folder} 后重新克隆（需要输入文件夹名确认）", file=sys.stderr)
    print(file=sys.stderr)

    while True:
        try:
            choice = input("选 [1/2/3] (默认 1): ").strip()
        except EOFError:
            return "cancel"
        if choice in ("", "1"):
            return "cancel"
        if choice == "2":
            return "rename"
        if choice == "3":
            typed = input(f"输入文件夹名 '{folder.name}' 确认删除: ").strip()
            if typed == folder.name:
                return "replace"
            print("  输入不匹配，已取消", file=sys.stderr)
            return "cancel"
        print("  无效输入，重试", file=sys.stderr)


# ---------- JSON update ----------

def update_json_after_clone(
    json_path: Path,
    folder: Path,
    target_slug: str,
    source_star: str | None,
) -> None:
    """Reclassify the newly-cloned folder and update the JSON."""
    # Use the scan script's classifier by re-classifying in-place
    sys.path.insert(0, str(SCRIPT_DIR))
    from scan_inventory import classify_dir, slug_from_url  # type: ignore

    entry = classify_dir(folder, gh_user_default(json_path))
    if source_star:
        entry["source_star"] = source_star
    if not entry.get("origin"):
        entry["origin"] = f"https://github.com/{target_slug}"

    data = load_json(json_path)
    repos = [r for r in data.get("repos", []) if r["name"] != folder.name]
    repos.append(entry)
    repos.sort(key=lambda r: (r["type"], r["name"].lower()))
    data["repos"] = repos
    if "last_full_scan" in data.get("_meta", {}):
        data["_meta"]["last_full_scan"] = now_iso()
    save_json(json_path, data)


def gh_user_default(json_path: Path) -> str:
    data = load_json(json_path)
    return data.get("_meta", {}).get("gh_user", "carterwayneskhizeine")


# ---------- list-new ----------

def list_uncloned_stars(json_path: Path) -> list[tuple[str, str]]:
    """Return [(owner/repo, stars-readme filename), ...] for starred repos not yet cloned."""
    if not STARS_MAPPING.exists():
        print(f"ERROR: {STARS_MAPPING} not found", file=sys.stderr)
        return []
    mapping = load_json(STARS_MAPPING)
    data = load_json(json_path)
    cloned_slugs = set()
    for r in data.get("repos", []):
        if r.get("origin"):
            slug = slug_from_url(r["origin"])
            if slug:
                cloned_slugs.add(slug)
        if r.get("parent"):
            cloned_slugs.add(r["parent"])

    uncloned = []
    for filename, url in mapping.items():
        if filename.startswith("_"):
            continue
        slug = slug_from_url(url) if isinstance(url, str) else None
        if slug and slug not in cloned_slugs:
            uncloned.append((slug, filename))
    return uncloned


# ---------- entry point ----------

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("target", nargs="?", help="owner/repo, GitHub URL, or stars-readme/Owner-Repo.md")
    p.add_argument("--json", help=f"Override JSON path (default: {DEFAULT_JSON})")
    p.add_argument("--root", help="Override root path (else read from JSON)")
    p.add_argument("--yes", action="store_true", help="Non-interactive: on conflict, use 'rename' as default")
    p.add_argument("--list-new", action="store_true", help="List starred repos not yet cloned, then exit")
    args = p.parse_args()

    json_path = Path(args.json) if args.json else DEFAULT_JSON
    data = load_json(json_path)
    root = Path(args.root or data.get("_meta", {}).get("root_path") or "D:\\Code")

    if args.list_new:
        uncloned = list_uncloned_stars(json_path)
        if not uncloned:
            print("All starred repos are already cloned. ✓")
            return 0
        print(f"{len(uncloned)} starred repos not yet cloned:")
        for slug, fname in uncloned:
            print(f"  {slug:45s}  ← stars-readme/{fname}")
        return 0

    if not args.target:
        p.error("target is required (or use --list-new)")

    target_slug, folder_name, source_star = resolve_target(args.target)
    target_folder = root / folder_name

    # Safety: if --root differs from the JSON's _meta.root_path, the user is
    # probably testing in a sandbox. Refuse to pollute the production JSON.
    json_root = data.get("_meta", {}).get("root_path")
    if json_root and str(root).lower() != str(Path(json_root)).lower():
        print(
            f"WARNING: --root '{root}' differs from JSON's _meta.root_path "
            f"'{json_root}'. Skipping JSON update so the production inventory "
            f"stays in sync with the real D:\\Code. Pass --json to point at a "
            f"sandbox JSON if you want to test there.",
            file=sys.stderr,
        )
        skip_json_update = True
    else:
        skip_json_update = False
    print(f"Target: {target_slug} → {target_folder}", file=sys.stderr)
    if source_star:
        print(f"  (from {source_star})", file=sys.stderr)

    # Conflict check
    conflict = detect_conflict(target_folder, target_slug)
    if conflict["status"] == "same":
        print(f"✓ 已经在本地: {target_folder} (origin matches)", file=sys.stderr)
        return 0
    if conflict["status"] == "fork-family":
        print(f"ℹ {conflict['details']}", file=sys.stderr)
        print(f"  提示：如果要把 {target_slug} 加为 upstream，cd 进去后跑：", file=sys.stderr)
        print(f"    git remote add upstream https://github.com/{target_slug}.git", file=sys.stderr)
        return 0
    if conflict["status"] == "different":
        if args.yes:
            action = "rename"
        else:
            action = ask_user_on_conflict(target_folder, target_slug, conflict)
        if action == "cancel":
            print("已取消。", file=sys.stderr)
            return 0
        if action == "rename":
            alt_name = target_slug.replace("/", "-")
            target_folder = root / alt_name
            print(f"  → 改用名字: {alt_name}", file=sys.stderr)
        elif action == "replace":
            print(f"  → 删除 {target_folder} ...", file=sys.stderr)
            import shutil
            shutil.rmtree(target_folder)
        if target_folder.exists():
            print(f"ERROR: {target_folder} still exists after conflict resolution", file=sys.stderr)
            return 1

    # Clone
    print(f"Cloning gh repo clone {target_slug} → {target_folder} ...", file=sys.stderr)
    rc, _, err = run(["gh", "repo", "clone", target_slug, str(target_folder)], timeout=180)
    if rc != 0:
        print(f"ERROR: gh repo clone failed: {err}", file=sys.stderr)
        return rc or 1

    # Update JSON (unless we're in sandbox mode with a different --root)
    if not skip_json_update:
        update_json_after_clone(json_path, target_folder, target_slug, source_star)
        print(f"✓ 克隆完成：{target_folder}", file=sys.stderr)
        print(f"✓ 清单已更新：{json_path}", file=sys.stderr)
    else:
        print(f"✓ 克隆完成：{target_folder}", file=sys.stderr)
        print(f"  (skipped JSON update because --root ≠ _meta.root_path)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
