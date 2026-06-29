#!/usr/bin/env python3
"""install_archive.py — extract a .7z archive from Code-zip/ into the local Code
folder and sync the inventory via the c-code skill.

This is the main entry point for the `code-zip-extract` skill.

Usage:
    python install_archive.py <archive-or-basename>
    python install_archive.py C:\\Users\\gotmo\\Code\\Code-zip\\memorix.7z
    python install_archive.py memorix                         # bare name search
    python install_archive.py memorix --force                # re-extract over existing
    python install_archive.py memorix --no-sync              # skip inventory sync
    python install_archive.py --dry-run                      # show what would happen
    python install_archive.py --ledger <path>                # override ledger path
    python install_archive.py --list                         # show ledger contents

What it does (default, no flags):
  1. Resolves the .7z path. If you pass a bare name, searches `<code-zip>/<name>.7z`.
  2. Pre-flight checks:
     - file exists and is .7z
     - 7-Zip CLI (`7z.exe`) is available
     - target folder doesn't already exist  → otherwise refuse, exit 2
     - not already in the ledger             → otherwise refuse with hint, exit 3
  3. Inspects the archive (`7z l`) and detects the top-level project folder:
       - single top-level `foo\\`          → target = `foo` (normal case)
       - single top-level `foo\\foo\\` …    → target = `foo` (nested case)
       - multiple top-level entries       → abort ("复杂归档，未自动处理")
  4. Extracts via `7z x` to the parent of the target.
  5. Re-points the target (handles nested case by promoting inner folder).
  6. Chains c-code sync:
       - `scan_inventory.py`                (full scan, writes JSON)
       - `scan_inventory.py --backfill-source-star`
       - `scan_inventory.py --verify`       (catches drift; exits 0/1)
  7. Appends an entry to `<code-zip>/extracted.json` (idempotent on `archive` name:
     re-running without --force appends nothing).
  8. Prints a one-line summary plus the matched inventory entry.

Path layout (this script is at):
  <github-stars>/.agents/skills/code-zip-extract/scripts/install_archive.py
PROJECT_DIR (3 levels up from here) = <github-stars>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Force UTF-8 stdout/stderr on Windows so emoji + Chinese print cleanly when
# the script is invoked from a GBK-encoded shell (default for `cmd.exe` /
# PowerShell without `chcp 65001`).  Reconfiguring is a no-op on macOS/Linux.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        pass

# ---------- paths (relative to this script) ----------

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
PROJECT_DIR = SKILL_DIR.parent.parent.parent  # .agents/ -> github-stars/

# Sibling skill — we drive its scan_inventory.py after each extract.
C_CODE_SCRIPTS = PROJECT_DIR / ".agents" / "skills" / "c-code" / "scripts"
SCAN_INVENTORY = C_CODE_SCRIPTS / "scan_inventory.py"

# Hardcoded for the user's primary Windows machine; mirrors c-code's defaults.
DEFAULT_CODE_DIR = Path(r"C:\Users\gotmo\Code")
DEFAULT_CODE_ZIP = DEFAULT_CODE_DIR / "Code-zip"
DEFAULT_LEDGER = DEFAULT_CODE_ZIP / "extracted.json"

LEDGER_SCHEMA_VERSION = 1


# ---------- helpers ----------

def run(cmd: list[str], cwd: Path | None = None, timeout: int = 60) -> tuple[int, str, str]:
    """Run a command, return (returncode, stdout, stderr). Always returns a tuple."""
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except FileNotFoundError as e:
        return 127, "", str(e)


def now_iso() -> str:
    """ISO 8601 with local timezone offset."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def find_7z() -> Optional[Path]:
    """Locate the 7-Zip CLI. Returns the path or None.

    Search order:
      1. %ProgramFiles%\\7-Zip\\7z.exe
      2. %ProgramFiles(x86)%\\7-Zip\\7z.exe
      3. `which 7z` / `where 7z` (PATH lookup)
    """
    candidates = []
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pfx86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    candidates.append(Path(pf) / "7-Zip" / "7z.exe")
    candidates.append(Path(pfx86) / "7-Zip" / "7z.exe")

    for c in candidates:
        if c.is_file():
            return c

    # PATH lookup
    rc, out, _ = run(["where", "7z"], timeout=5) if sys.platform == "win32" \
        else run(["which", "7z"], timeout=5)
    if rc == 0 and out.strip():
        for line in out.splitlines():
            p = Path(line.strip())
            if p.is_file():
                return p
    return None


# ---------- archive inspection ----------

# 7z l body lines look like:
#   2026-06-29 14:36:45 D....            0            0  memorix\.git\hooks
# Columns are separated by 2+ spaces; the LAST column is the path.
# We don't try to parse the full column structure (size fields vary in width)
# — we just split on 2+ spaces, take the last field as the path.

# Footer lines we explicitly ignore (they look almost-but-not-quite like listings).
FOOTER_PATTERNS = [
    re.compile(r"\b\d+\s+files?\b"),
    re.compile(r"\b\d+\s+folders?\b"),
    re.compile(r"^Size:"),
    re.compile(r"^Method:"),
    re.compile(r"^Blocks:"),
    re.compile(r"^Physical"),
    re.compile(r"^Headers"),
]


def top_level_entries(sevenz: Path, archive: Path) -> list[str]:
    """Return the set of top-level entries inside the archive (single segment names).

    Example: ['memorix', 'memorix'] if everything is under memorix\\memorix\\...;
             ['memorix'] if everything is under memorix\\...;
             ['a', 'b']   if there are two top-level folders a\\ and b\\ at root.
    """
    rc, out, err = run([str(sevenz), "l", str(archive)], timeout=30)
    if rc != 0:
        raise RuntimeError(f"7z l failed: {err or out}")

    tops: list[str] = []
    seen: set[str] = set()

    body_started = False
    for raw in out.splitlines():
        stripped = raw.strip()
        if not stripped:
            continue

        # 7z prints a dashed separator ("------ -----...") just before
        # the file table. Use it as the body start marker.
        if not body_started:
            if stripped.startswith("---") and "Date" not in stripped:
                # Either the dashed separator or the column header. The
                # dashed separator is "----- ----- ..."; the column header is
                # "Date Time Attr Size Compressed Name". Skip both.
                body_started = True
            continue

        # Inside body: ignore footer summary lines ("1508 files, 317 folders")
        # and metadata lines ("Size:", "Method:"). These appear AFTER the
        # body in the 7z output, but we filter them defensively.
        if any(p.search(stripped) for p in FOOTER_PATTERNS):
            continue

        # Split on 2+ spaces (column separator). Last field is the path.
        # 7z l body row shape: "Date Time Attr" merged (because Date/Time are
        # single-space separated, not 2+) + Size + Compressed + Name = 4 cols.
        # A path containing spaces (rare) still splits correctly because the
        # internal space isn't 2+.
        parts = re.split(r"\s{2,}", raw.rstrip())
        if len(parts) < 4:
            continue

        path = parts[-1].strip()
        if not path:
            continue

        # Path separator in 7z output is backslash; collapse to first segment.
        first = path.replace("/", "\\").split("\\", 1)[0]
        if first and first not in seen:
            seen.add(first)
            tops.append(first)
    return tops


def detect_project_name(sevenz: Path, archive: Path) -> str:
    """Decide what the target folder name should be.

    Rules:
      - exactly one top-level entry, name X                  → project = X
      - anything else                                        → raise

    Note: nested-case detection (X\\X\\… inside the archive itself) is NOT
    done here — 7z l output collapses `memorix\\memorix\\...` to top-level
    "memorix" the same as the normal `memorix\\...`. Instead, after extract,
    `promote_nested()` walks the on-disk tree and promotes an inner
    `<project>/<project>/` if found.
    """
    tops = top_level_entries(sevenz, archive)
    unique = list(dict.fromkeys(tops))  # de-dup, preserve order

    if len(unique) == 1:
        return unique[0]

    raise RuntimeError(
        f"复杂归档：检测到多个顶层条目 {unique}。"
        f"这个 skill 只处理单个项目归档，请手动解压。"
    )


def promote_nested(target: Path, project_name: str) -> bool:
    """If extracting produced <target>\\<project_name>\\... (i.e., a doubled
    top-level folder), collapse the extra nesting by moving everything up one
    level and removing the now-empty inner folder.

    Returns True if promotion happened, False otherwise (normal case, or
    "other stuff in target, won't auto-promote").
    """
    inner = target / project_name  # .../memorix/memorix
    if not inner.is_dir():
        return False

    siblings = [p for p in target.iterdir() if p != inner]
    if siblings:
        return False  # other files in target; don't auto-collapse

    for child in inner.iterdir():
        dest = target / child.name
        if dest.exists():
            continue
        child.rename(dest)
    try:
        inner.rmdir()
    except OSError:
        pass
    return True


# ---------- ledger ----------

def load_ledger(path: Path) -> dict:
    """Load ledger JSON; return empty stub if missing or corrupted."""
    if not path.exists():
        return {"_meta": {"schema_version": LEDGER_SCHEMA_VERSION}, "extractions": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "extractions" not in data:
            return {"_meta": {"schema_version": LEDGER_SCHEMA_VERSION}, "extractions": []}
        return data
    except (json.JSONDecodeError, OSError):
        return {"_meta": {"schema_version": LEDGER_SCHEMA_VERSION}, "extractions": []}


def save_ledger(path: Path, data: dict) -> None:
    """Atomic write: write to .tmp then rename."""
    data.setdefault("_meta", {})
    data["_meta"]["last_updated"] = now_iso()
    data["_meta"]["schema_version"] = LEDGER_SCHEMA_VERSION
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def find_ledger_entry(ledger: dict, archive_filename: str) -> Optional[dict]:
    for entry in ledger.get("extractions", []):
        if entry.get("archive") == archive_filename:
            return entry
    return None


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------- inventory chain ----------

def chain_sync(project_dir: Path) -> dict:
    """Run scan_inventory.py in three modes. Returns parsed stdout of each."""
    if not SCAN_INVENTORY.is_file():
        return {"error": f"scan_inventory.py not found at {SCAN_INVENTORY}"}

    results = {}
    for mode, flag in [("scan", []), ("backfill", ["--backfill-source-star"]), ("verify", ["--verify"])]:
        rc, out, err = run([sys.executable, str(SCAN_INVENTORY), *flag], timeout=120)
        results[mode] = {"rc": rc, "stdout": out.strip(), "stderr": err.strip()}
    return results


# ---------- argument resolution ----------

def resolve_archive_path(arg: str, code_zip: Path) -> Path:
    """Accept either a full path to a .7z or a bare basename (with or without .7z).

    Looks in <code_zip> first; falls back to treating `arg` as a path directly.
    """
    p = Path(arg)
    if p.is_file():
        return p.resolve()

    # Try with and without .7z suffix inside code_zip.
    candidates = []
    name = arg if arg.lower().endswith(".7z") else arg + ".7z"
    candidates.append(code_zip / name)
    candidates.append(code_zip / arg)
    for c in candidates:
        if c.is_file():
            return c.resolve()

    raise FileNotFoundError(
        f"找不到归档 {arg!r}（在 {code_zip} 里找 .7z 也找不到）。"
        f"给出完整路径或先放一份到 Code-zip/。"
    )


# ---------- main pipeline ----------

def install(
    archive_path: Path,
    code_zip: Path,
    code_dir: Path,
    ledger_path: Path,
    *,
    force: bool,
    no_sync: bool,
    dry_run: bool,
) -> int:
    # 1. sanity on archive
    if not archive_path.is_file():
        print(f"❌ 归档不存在: {archive_path}", file=sys.stderr)
        return 2
    if archive_path.suffix.lower() != ".7z":
        print(f"❌ 只支持 .7z 归档（你给的是 {archive_path.suffix}）", file=sys.stderr)
        return 2

    # 2. find 7z
    sevenz = find_7z()
    if not sevenz:
        print("❌ 找不到 7-Zip CLI。安装 7-Zip 到默认路径 C:\\Program Files\\7-Zip\\。", file=sys.stderr)
        return 2

    # 3. inspect
    try:
        project_name = detect_project_name(sevenz, archive_path)
    except RuntimeError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 2

    target = code_dir / project_name
    ledger = load_ledger(ledger_path)
    prior = find_ledger_entry(ledger, archive_path.name)

    print(f"📦 归档      : {archive_path}")
    print(f"📁 目标目录  : {target}")
    print(f"📐 形态      : 单一项目，提取后会自检嵌套折叠")
    print(f"🗂  ledger   : {ledger_path}")
    # Flush so the info block appears above any subsequent stderr error.
    sys.stdout.flush()
    sys.stderr.flush()

    # 4. collect ALL pre-flight blockers, then report + exit (don't bail early
    # on the first one — the user benefits from seeing every reason).
    blockers: list[tuple[str, str]] = []
    if target.exists():
        blockers.append((
            "target",
            f"❌ 目标目录已存在: {target}\n"
            f"   按当前 skill 设置，冲突时拒绝自动处理。\n"
            f"   - 想重新解压：先手动删除或改名 target，再重跑\n"
            f"   - 想强制覆盖：加 --force（ledger 也会更新）",
        ))
    if prior and not force:
        blockers.append((
            "ledger",
            f"❌ ledger 已记录 {archive_path.name}（{prior.get('extracted_at')}）。\n"
            f"   想重跑用 --force（也会重新解压并刷新 ledger）。",
        ))

    if blockers and not force:
        # If BOTH apply, prefix with a clear "既已解压过，又换了目录..." so the
        # user understands the two conditions are related.
        if len(blockers) == 2:
            print(
                f"\n⚠️  这个归档已经装过了（ledger 有记录，且目标目录还在磁盘上）。",
                file=sys.stderr,
            )
        for _label, msg in blockers:
            print(f"\n{msg}", file=sys.stderr)
        print("\n   任意一条用 --force 都会既重新解压，又刷新 ledger。", file=sys.stderr)
        # Exit code distinguishes: 2 = target conflict dominates (and ledger probably matches);
        # 3 = ledger-only. We only hit "ledger-only" in practice when target was deleted
        # between scans — an edge case. The user mostly cares that we refused.
        return 2 if any(label == "target" for label, _ in blockers) else 3

    if force and (target.exists() or prior):
        if target.exists():
            print(f"⚠️  --force 模式：目标目录已存在，将被覆盖")
        if prior:
            print(f"⚠️  --force 模式：ledger 已有记录，将被替换")

    if dry_run:
        print("\n[dry-run] 上面就是要执行的动作，未实际操作。")
        return 0

    # 6. extract
    rc, out, err = run(
        [str(sevenz), "x", str(archive_path),
         f"-o{code_dir}", "-y"],
        timeout=300,
    )
    if rc != 0:
        print(f"❌ 7z x 失败:\n{err or out}", file=sys.stderr)
        return 2

    # 7. collapse nested case if it occurred (always run — it's a no-op
    # in the normal case and self-determines for nested case).
    promoted = promote_nested(target, project_name)

    if not target.is_dir():
        print(
            f"❌ 解压完成但目标目录不存在: {target}\n"
            f"   7z 输出里有，但磁盘上看不到？",
            file=sys.stderr,
        )
        return 2

    # 8. chain sync (scan + backfill + verify)
    sync_results = {}
    if not no_sync:
        sync_results = chain_sync(target)
        scan_rc = sync_results.get("scan", {}).get("rc", -1)
        if scan_rc != 0:
            print(f"⚠️  scan_inventory.py 退出码非零: {scan_rc}", file=sys.stderr)

    # 9. figure out the new inventory entry by reading the JSON
    new_entry = None
    try:
        full = json.loads((PROJECT_DIR / "data" / "c-code-repos.json").read_text(encoding="utf-8"))
        for r in full.get("repos", []):
            if r.get("name") == project_name:
                new_entry = r
                break
    except Exception:
        pass

    # 10. update ledger
    entry = {
        "archive": archive_path.name,
        "archive_path": str(archive_path),
        "archive_sha256": sha256_of(archive_path),
        "extracted_at": now_iso(),
        "target_dir": str(target),
        "project_name": project_name,
        "size_bytes_archived": archive_path.stat().st_size,
        "inventory_type": new_entry.get("type") if new_entry else None,
        "source_star": new_entry.get("source_star") if new_entry else None,
        "is_fork": new_entry.get("is_fork") if new_entry else None,
        "synced": not no_sync,
        "sync_results": {k: v.get("rc") for k, v in sync_results.items()} if sync_results else None,
    }
    # Replace prior entry if --force, else append.
    if prior and force:
        ledger["extractions"] = [e for e in ledger["extractions"] if e.get("archive") != archive_path.name]
    ledger["extractions"].append(entry)
    save_ledger(ledger_path, ledger)

    # 11. report
    print()
    print("✅ 解压完成")
    print(f"   archive  : {archive_path.name}")
    print(f"   target   : {target}")
    if promoted:
        print(f"   shape    : 7z 是嵌套 X\\X\\…，已自动折叠为 {project_name}/")
    print(f"   ledger   : 新增 1 条 → {ledger_path}")
    if not no_sync:
        verify_rc = sync_results.get("verify", {}).get("rc")
        print(f"   sync     : scan={sync_results.get('scan', {}).get('rc')} "
              f"backfill={sync_results.get('backfill', {}).get('rc')} "
              f"verify={verify_rc} ({'clean' if verify_rc == 0 else 'drift detected'})")
    if new_entry:
        print(f"   inventory: {new_entry['type']:18s} source_star={new_entry.get('source_star')!r}")

    # Friendly hint for off-target use
    if code_dir != DEFAULT_CODE_DIR:
        print(f"\n（注意：code_dir 不是默认 {DEFAULT_CODE_DIR}，ledger 也写到自定义路径。）")

    return 0


# ---------- CLI ----------

def main() -> int:
    p = argparse.ArgumentParser(
        description="解压 Code-zip 里的 .7z 归档到 Code 文件夹，并同步 c-code inventory。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("archive", nargs="?", help="归档路径或裸文件名（在 Code-zip 里找 .7z）")
    p.add_argument("--force", action="store_true",
                   help="目标目录已存在或 ledger 已有记录时仍然重跑")
    p.add_argument("--no-sync", action="store_true",
                   help="不调用 scan_inventory.py — 只解压 + 更新 ledger")
    p.add_argument("--dry-run", action="store_true",
                   help="只打印将要做什么，不实际操作")
    p.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER,
                   help=f"ledger JSON 路径（默认 {DEFAULT_LEDGER}）")
    p.add_argument("--code-dir", type=Path, default=DEFAULT_CODE_DIR,
                   help=f"Code 根目录（默认 {DEFAULT_CODE_DIR}）")
    p.add_argument("--code-zip", type=Path, default=DEFAULT_CODE_ZIP,
                   help=f"归档暂存目录（默认 {DEFAULT_CODE_ZIP}）")
    p.add_argument("--list", action="store_true",
                   help="列出 ledger 内容后退出")

    args = p.parse_args()

    if args.list:
        ledger = load_ledger(args.ledger)
        items = ledger.get("extractions", [])
        if not items:
            print(f"(ledger 是空的: {args.ledger})")
            return 0
        print(f"ledger: {args.ledger}  ({len(items)} 条)\n")
        print(f"{'archive':25s} {'project':18s} {'extracted_at':22s} {'type':18s} source_star")
        print("-" * 110)
        for e in items:
            print(f"{e.get('archive',''):25s} "
                  f"{e.get('project_name',''):18s} "
                  f"{e.get('extracted_at',''):22s} "
                  f"{e.get('inventory_type') or '?':18s} "
                  f"{e.get('source_star') or ''}")
        return 0

    if not args.archive:
        p.print_help()
        return 1

    try:
        archive_path = resolve_archive_path(args.archive, args.code_zip)
    except FileNotFoundError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 2

    return install(
        archive_path=archive_path,
        code_zip=args.code_zip,
        code_dir=args.code_dir,
        ledger_path=args.ledger,
        force=args.force,
        no_sync=args.no_sync,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
