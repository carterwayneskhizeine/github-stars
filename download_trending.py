#!/usr/bin/env python3
"""
Download README files from GitHub repos mentioned in a WhiteNote share post
(GitHub Trending monthly collections).

Same download method as download_stars.py — `gh api repos/{owner}/{repo}/readme`,
base64-decoded, saved as `{Owner}-{Repo}.{ext}` — but a different save path:
files go to `trending-readme/` instead of `stars-readme/`, with their own
mapping (`data/trending_mapping.json`) and state (`data/trending_state.json`).

The repo list is extracted from the share post's markdown (every
`https://github.com/{owner}/{repo}` link, deduplicated) and cached in
`data/trending_urls.json`, so later incremental runs work offline.

Usage:
    python download_trending.py                  # first 10 new repos
    python download_trending.py --all            # process every new repo
    python download_trending.py --limit 50       # first 50 new repos
    python download_trending.py --refresh-list   # re-fetch the share post first
    python download_trending.py --include-known  # re-download everything on the list
"""

import argparse
import base64
import json
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from time import sleep

PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "trending-readme"
DATA_DIR = PROJECT_DIR / "data"
LIST_PATH = DATA_DIR / "trending_urls.json"
MAPPING_PATH = DATA_DIR / "trending_mapping.json"
STATE_PATH = DATA_DIR / "trending_state.json"

DEFAULT_SHARE_URL = (
    "https://whitenote.goldierill.com/share/cmwdu4f980000lfkme9o6zwzt/markdown"
)
GITHUB_RE = re.compile(r"https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)")
README_EXTS = ("md", "rst", "txt", "adoc", "org")


def fetch_share_markdown(url: str) -> str:
    """Fetch the share post's markdown over HTTPS (public share link)."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def extract_repos(markdown: str) -> list[tuple[str, str]]:
    """Extract unique owner/repo pairs from the markdown, keeping first order."""
    seen: set[str] = set()
    repos: list[tuple[str, str]] = []
    for owner, name in GITHUB_RE.findall(markdown):
        name = name.rstrip(".")  # trailing dot would be a sentence period
        slug = f"{owner}/{name}"
        if slug.lower() in seen:
            continue
        seen.add(slug.lower())
        repos.append((owner, name))
    return repos


def load_url_list(refresh: bool) -> list[tuple[str, str]]:
    """Load the cached repo list, or (re)build it from the share post."""
    if not refresh and LIST_PATH.exists():
        try:
            data = json.loads(LIST_PATH.read_text(encoding="utf-8"))
            repos = [tuple(r.split("/", 1)) for r in data.get("repos", [])]
            print(f"  repo list from cache: {LIST_PATH.name} ({len(repos)} repos)")
            return repos
        except (json.JSONDecodeError, OSError, ValueError):
            pass  # fall through and re-fetch

    print(f"  fetching share post: {DEFAULT_SHARE_URL}")
    markdown = fetch_share_markdown(DEFAULT_SHARE_URL)
    repos = extract_repos(markdown)
    print(f"  extracted {len(repos)} unique repos from the share post")

    payload = {
        "_note": (
            "owner/repo list extracted from the WhiteNote share post "
            "(GitHub Trending monthly collections). Used by download_trending.py."
        ),
        "_source": DEFAULT_SHARE_URL,
        "_extracted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repos": [f"{o}/{n}" for o, n in repos],
    }
    LIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    LIST_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"  wrote {LIST_PATH}")
    return repos


def run_gh(args: list[str], retries: int = 5) -> str:
    """Run a `gh api` command and return stdout text (same as download_stars.py)."""
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        result = subprocess.run(
            ["gh", "api", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode == 0:
            return result.stdout

        last_err = subprocess.CalledProcessError(
            result.returncode, ["gh", "api", *args],
            output=result.stdout, stderr=result.stderr,
        )
        stderr = (result.stderr or "").lower()

        # Don't retry on hard 4xx errors like 404 (no README) or 401 (bad auth).
        if any(sig in stderr for sig in ("404", "401", "403 forbidden")):
            raise last_err

        if attempt < retries:
            wait = min(2 ** attempt, 30)
            print(f"\n    retry {attempt}/{retries} in {wait}s "
                  f"(exit {result.returncode})...", end="", flush=True)
            sleep(wait)
    raise last_err  # type: ignore[misc]


def fetch_readme(owner: str, repo: str) -> tuple[str, str] | None:
    """Fetch the default branch's README. Returns (content, ext) or None."""
    try:
        data = json.loads(run_gh([f"repos/{owner}/{repo}/readme"]))
    except subprocess.CalledProcessError:
        return None  # 404 / no README
    if data.get("encoding") != "base64":
        return None
    raw = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    name = (data.get("name") or "README").lower()
    ext = "md" if name.endswith(".md") else (
        name.rsplit(".", 1)[-1] if "." in name else "md"
    )
    return raw, ext


def sanitize(name: str) -> str:
    """Strip filesystem-hostile characters from a name component."""
    bad = '<>:"/\\|?*'
    return "".join("_" if c in bad else c for c in name).strip().rstrip(".")


def find_existing_file(slug: str) -> str | None:
    """Return the basename of an already-downloaded file for this slug, if any."""
    for ext in README_EXTS:
        cand = OUTPUT_DIR / f"{slug}.{ext}"
        if cand.exists() and cand.stat().st_size > 0:
            return cand.name
    return None


def load_state() -> set[str]:
    """Load the set of repos known to have no README (or that errored)."""
    if not STATE_PATH.exists():
        return set()
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return set(data.get("skip", []))
    except (json.JSONDecodeError, OSError):
        return set()


def save_state(skip: set[str]) -> None:
    STATE_PATH.write_text(
        json.dumps({"version": 1, "skip": sorted(skip)}, indent=2) + "\n",
        encoding="utf-8",
    )


def load_mapping() -> dict[str, str]:
    if not MAPPING_PATH.exists():
        return {}
    try:
        return {
            k: v
            for k, v in json.loads(MAPPING_PATH.read_text(encoding="utf-8")).items()
            if not k.startswith("_")
        }
    except (json.JSONDecodeError, OSError):
        return {}


def write_mapping(mapping: dict[str, str]) -> None:
    payload = {
        "_note": (
            "Key = local README filename in trending-readme/; "
            "value = original GitHub URL. Generated by download_trending.py."
        ),
        **dict(sorted(mapping.items())),
    }
    MAPPING_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {MAPPING_PATH} ({len(mapping)} entries)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=10,
                        help="Max number of new repos to download (default 10).")
    parser.add_argument("--all", action="store_true",
                        help="Download all new repos on the list (overrides --limit).")
    parser.add_argument("--delay", type=float, default=0.5,
                        help="Seconds to sleep between requests (default 0.5).")
    parser.add_argument("--refresh-list", action="store_true",
                        help="Re-fetch the share post and rebuild the repo list "
                             "before downloading.")
    parser.add_argument("--include-known", action="store_true",
                        help="Re-download every repo on the list, even those "
                             "already on disk or known to have no README.")
    args = parser.parse_args()

    print("Building repo list...")
    repos = load_url_list(refresh=args.refresh_list)

    mapping = load_mapping()
    skip = set() if args.include_known else load_state()

    targets = []
    already = 0
    for owner, name in repos:
        slug = f"{sanitize(owner)}-{sanitize(name)}"
        full = f"{owner}/{name}"
        if not args.include_known:
            if full in skip:
                continue
            if find_existing_file(slug) is not None:
                already += 1
                continue
        targets.append((owner, name, slug, full))

    skip_in_list = len(skip & {f"{o}/{n}" for o, n in repos})
    print(f"  already downloaded: {already}    previously skipped(no-readme/failed): {skip_in_list}")
    print(f"  new repos to process: {len(targets)}")

    cap = len(targets) if args.all else min(args.limit, len(targets))
    if cap < len(targets):
        print(f"  --limit {args.limit}: capping at {cap} of {len(targets)}")
    targets = targets[:cap]
    print()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    ok = 0
    no_readme = 0
    failed = 0
    for i, (owner, name, slug, full) in enumerate(targets, 1):
        url = f"https://github.com/{owner}/{name}"
        try:
            result = fetch_readme(owner, name)
        except Exception as e:  # noqa: BLE001
            print(f"[{i:>4}/{len(targets)}] {full} -- ERROR: {e}")
            failed += 1
            skip.add(full)
            sleep(args.delay)
            continue

        if result is None:
            print(f"[{i:>4}/{len(targets)}] {full} -- no README, skipping")
            no_readme += 1
            skip.add(full)
            sleep(args.delay)
            continue

        content, ext = result
        out_path = OUTPUT_DIR / f"{slug}.{ext}"
        out_path.write_text(content, encoding="utf-8")
        mapping[out_path.name] = url
        size_kb = len(content.encode("utf-8")) / 1024
        print(f"[{i:>4}/{len(targets)}] {full} -> {out_path.name} ({size_kb:.1f} KB)")
        ok += 1
        sleep(args.delay)

    save_state(skip)
    print()
    print(f"Done. downloaded={ok} skipped(no-readme)={no_readme} failed={failed} "
          f"already_on_disk={already} list_total={len(repos)}")
    write_mapping(mapping)
    return 0


if __name__ == "__main__":
    sys.exit(main())
