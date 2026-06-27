#!/usr/bin/env python3
"""
Download README.md files from GitHub starred repositories.

Renames each file to {owner}-{repo}.md (e.g. Helvesec-rmux.md) and writes a
JSON mapping table `data/stars_mapping.json` so you can look
up the original URL from the local filename.

This script is **incremental**: once a repo has been processed (downloaded
successfully OR found to have no README) its `full_name` is recorded in
`data/stars_state.json`. Subsequent runs only fetch new stars. Use
`--reset-state` to start over from scratch, or `--include-known` to ignore
the state and re-process everything.

Pagination is **short-circuited**: starred repos come back newest-first, and
new stars are always prepended, so once a whole page consists of repos we've
already processed, every later page is known too and we stop fetching. In the
common case (only a few new stars since the last run) this reads 1–2 pages
instead of all of them. Pass `--full-scan` to force fetching every page.

Usage:
    python download_stars.py                   # first 10 new stars
    python download_stars.py --all             # process every new star
    python download_stars.py --limit 50        # first 50 new stars
    python download_stars.py --include-known   # re-process all 1206 from scratch
    python download_stars.py --rebuild-mapping # only rebuild data/stars_mapping.json
                                                # from files already on disk
    python download_stars.py --reset-state     # clear the state, then download
"""

import argparse
import base64
import json
import subprocess
import sys
from pathlib import Path
from time import sleep

PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_DIR / "stars-readme"
DATA_DIR = PROJECT_DIR / "data"
MAPPING_PATH = DATA_DIR / "stars_mapping.json"
STATE_PATH = DATA_DIR / "stars_state.json"
PAGE_SIZE = 100  # GitHub API max per page
README_EXTS = ("md", "rst", "txt", "adoc", "org")


def run_gh(args: list[str], retries: int = 5) -> str:
    """Run a `gh api` command and return stdout text.

    Retries on transient failures (network timeouts, 5xx, rate-limit hiccups)
    with exponential backoff, since GitHub's API occasionally drops a request.
    """
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
            wait = min(2 ** attempt, 30)  # 2, 4, 8, 16, (cap 30)s
            print(f"\n    retry {attempt}/{retries} in {wait}s "
                  f"(exit {result.returncode})...", end="", flush=True)
            sleep(wait)
    raise last_err  # type: ignore[misc]


def list_starred_repos(known: set[str] | None = None) -> list[dict]:
    """Fetch starred repos for the authenticated user (most recent first).

    The GitHub endpoint is sorted by starred_at descending, so the newest
    stars lead. If `known` (the set of already-processed full_names) is
    provided and non-empty, we stop as soon as a whole page is already
    known — every page after that point is known too, since new stars are
    always prepended to the front of the list. An empty/None `known` (e.g.
    first run, or --include-known / --rebuild-mapping) fetches every page.
    """
    known = known or set()
    do_early_stop = bool(known)
    repos: list[dict] = []
    page = 1
    while True:
        print(f"  fetching page {page}...", end="", flush=True)
        data = json.loads(run_gh([
            # sort=created&direction=desc = newest stars first (GitHub's
            # default, made explicit so the early-stop assumption holds).
            f"user/starred?per_page={PAGE_SIZE}&page={page}"
            "&sort=created&direction=desc",
        ]))
        print(" done")
        if not data:
            break
        repos.extend(data)

        if do_early_stop:
            new_in_page = sum(
                1 for r in data
                if f"{r['owner']['login']}/{r['name']}" not in known
            )
            if new_in_page == 0:
                print(f"  page {page} already known -- stopping early "
                      f"(fetched {len(repos)} repos)")
                break

        if len(data) < PAGE_SIZE:
            break
        page += 1
    return repos


def fetch_readme(owner: str, repo: str) -> tuple[str, str] | None:
    """
    Fetch the default branch's README for a repo.
    Returns (content, extension) where extension is e.g. 'md' or 'rst'.
    Returns None if the repo has no README.
    """
    try:
        data = json.loads(run_gh([f"repos/{owner}/{repo}/readme"]))
    except subprocess.CalledProcessError:
        # 404 / no README
        return None
    if data.get("encoding") != "base64":
        return None
    raw = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    name = (data.get("name") or "README").lower()
    ext = "md" if name.endswith(".md") else (name.rsplit(".", 1)[-1] if "." in name else "md")
    return raw, ext


def sanitize(name: str) -> str:
    """Strip filesystem-hostile characters from a name component."""
    bad = '<>:"/\\|?*'
    return "".join("_" if c in bad else c for c in name).strip().rstrip(".")


def find_existing_file(slug: str, output_dir: Path) -> str | None:
    """Return the basename of an already-downloaded file for this slug, if any."""
    for ext in README_EXTS:
        cand = output_dir / f"{slug}.{ext}"
        if cand.exists() and cand.stat().st_size > 0:
            return cand.name
    return None


def write_mapping(mapping: dict[str, str], path: Path = MAPPING_PATH) -> None:
    """Write the {filename: url} mapping to disk as pretty JSON."""
    # Sort by filename for stable diffs.
    sorted_mapping = dict(sorted(mapping.items()))
    payload = {
        "_note": (
            "Key = local README filename in stars-readme/; "
            "value = original GitHub URL. Generated by download_stars.py. "
            "Re-run the script to refresh after new stars or new downloads."
        ),
        **sorted_mapping,
    }
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {path} ({len(sorted_mapping)} entries)")


def load_state() -> dict:
    """Load the incremental-download state. Returns a dict with a 'known' set."""
    if not STATE_PATH.exists():
        return {"version": 1, "known": []}
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "known" not in data:
            return {"version": 1, "known": []}
        return data
    except (json.JSONDecodeError, OSError):
        return {"version": 1, "known": []}


def save_state(state: dict) -> None:
    """Persist the state. 'known' is stored as a sorted list for diff stability."""
    payload = {
        "version": 1,
        "known": sorted(set(state.get("known", []))),
    }
    STATE_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def rebuild_mapping(repos: list[dict], output_dir: Path) -> None:
    """Build the mapping from files already on disk + the starred list."""
    mapping: dict[str, str] = {}
    missing = 0
    for repo in repos:
        owner = repo["owner"]["login"]
        name = repo["name"]
        slug = f"{sanitize(owner)}-{sanitize(name)}"
        url = f"https://github.com/{owner}/{name}"
        existing = find_existing_file(slug, output_dir)
        if existing is not None:
            mapping[existing] = url
        else:
            missing += 1
    write_mapping(mapping)
    print(f"  on disk: {len(mapping)}    not yet downloaded: {missing}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=10,
                        help="Max number of *new* repos to download (default 10). "
                             "Use --all to remove the cap.")
    parser.add_argument("--all", action="store_true",
                        help="Download all *new* starred repos (overrides --limit).")
    parser.add_argument("--delay", type=float, default=0.5,
                        help="Seconds to sleep between requests (default 0.5).")
    parser.add_argument("--include-known", action="store_true",
                        help="Ignore data/stars_state.json and re-process every "
                             "starred repo from scratch.")
    parser.add_argument("--full-scan", action="store_true",
                        help="Fetch every page instead of stopping once a page "
                             "is fully known. Use if you suspect the state is "
                             "out of sync with GitHub.")
    parser.add_argument("--reset-state", action="store_true",
                        help="Delete data/stars_state.json before running, so every "
                             "star is treated as new.")
    parser.add_argument("--rebuild-mapping", action="store_true",
                        help="Don't download anything; rebuild data/stars_mapping.json "
                             "from files already on disk + the starred list.")
    args = parser.parse_args()

    # Resolve the incremental state BEFORE fetching, so we can stop paginating
    # early once we reach repos we've already processed.
    if args.reset_state:
        if STATE_PATH.exists():
            STATE_PATH.unlink()
            print("Cleared data/stars_state.json")
    state = load_state()
    known = set(state.get("known", []))

    # Convenience: on the very first run, seed the state from any pre-existing
    # mapping so files already on disk aren't re-downloaded.
    if not STATE_PATH.exists() and MAPPING_PATH.exists() and not args.reset_state:
        try:
            existing = json.loads(MAPPING_PATH.read_text(encoding="utf-8"))
            seeded = set()
            for fname, url in existing.items():
                if fname.startswith("_"):
                    continue
                # url looks like https://github.com/Owner/Repo
                if url.startswith("https://github.com/"):
                    seeded.add(url[len("https://github.com/"):].rstrip("/"))
            if seeded:
                known |= seeded
                state["known"] = sorted(known)
                print(f"  seeded state from {MAPPING_PATH.name}: {len(seeded)} entries")
        except (json.JSONDecodeError, OSError):
            pass

    print(f"  already processed (from state): {len(known)}")

    # These modes need the complete starred list (every page); a normal run
    # passes `known` so pagination short-circuits at the first fully-known page.
    fetch_all = args.rebuild_mapping or args.include_known or args.full_scan
    print("Fetching list of starred repos...")
    repos = list_starred_repos(known=set() if fetch_all else known)
    print(f"  total starred: {len(repos)}")

    if args.rebuild_mapping:
        print()
        rebuild_mapping(repos, OUTPUT_DIR)
        return 0

    # Filter out already-known stars unless --include-known was passed.
    if args.include_known:
        targets = repos
        print(f"  --include-known: processing all {len(targets)} stars")
    else:
        targets = [r for r in repos if f"{r['owner']['login']}/{r['name']}" not in known]
        print(f"  new stars to process: {len(targets)}")

    if args.all:
        cap = len(targets)
    else:
        cap = min(args.limit, len(targets))
        if cap < len(targets):
            print(f"  --limit {args.limit}: capping at {cap} of {len(targets)} new stars")
    targets = targets[:cap]
    print()

    # Start from any existing mapping so partial runs accumulate rather than wipe.
    mapping: dict[str, str] = {}
    if MAPPING_PATH.exists():
        try:
            mapping = {
                k: v for k, v in json.loads(MAPPING_PATH.read_text(encoding="utf-8")).items()
                if not k.startswith("_")
            }
        except (json.JSONDecodeError, OSError):
            mapping = {}

    # Ensure the output directory exists.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    ok = 0
    no_readme = 0
    failed = 0
    for i, repo in enumerate(targets, 1):
        owner = repo["owner"]["login"]
        name = repo["name"]
        full = f"{owner}/{name}"
        slug = f"{sanitize(owner)}-{sanitize(name)}"
        url = f"https://github.com/{owner}/{name}"

        try:
            result = fetch_readme(owner, name)
        except Exception as e:  # noqa: BLE001
            print(f"[{i:>4}/{len(targets)}] {full} -- ERROR: {e}")
            failed += 1
            known.add(full)  # don't hammer a repo that's misbehaving
            sleep(args.delay)
            continue

        if result is None:
            print(f"[{i:>4}/{len(targets)}] {full} -- no README, skipping")
            no_readme += 1
            known.add(full)  # remember we tried, so we don't re-query later
            sleep(args.delay)
            continue

        content, ext = result
        out_path = OUTPUT_DIR / f"{slug}.{ext}"
        out_path.write_text(content, encoding="utf-8")
        mapping[out_path.name] = url
        known.add(full)
        size_kb = len(content.encode("utf-8")) / 1024
        print(f"[{i:>4}/{len(targets)}] {full} -> {out_path.name} ({size_kb:.1f} KB)")
        ok += 1
        sleep(args.delay)

    state["known"] = sorted(known)
    save_state(state)
    print()
    print(f"Done. downloaded={ok} skipped(no-readme)={no_readme} failed={failed} "
          f"known_total={len(known)}")
    write_mapping(mapping)
    return 0


if __name__ == "__main__":
    sys.exit(main())
