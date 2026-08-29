#!/usr/bin/env python3
"""Scan media/ and regenerate videos.json, then print the link for each video.

Usage:  python3 refresh.py
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

EXTS = {".mp4": "mp4", ".gif": "gif", ".webm": "webm", ".mov": "mp4"}
GITHUB_FILE_LIMIT_MB = 100      # hard: push is rejected above this
GITHUB_WARN_MB = 50             # GitHub warns above this
PAGES_SITE_LIMIT_MB = 1000

root = Path(__file__).resolve().parent
media = root / "media"

if not media.is_dir():
    sys.exit(f"no media directory at {media}")

FFPROBE = shutil.which("ffprobe")


def base_url():
    """Derive the Pages URL from this repo's origin remote, so the printed links
    are always correct for wherever it is actually pushed."""
    try:
        url = subprocess.run(["git", "-C", str(root), "remote", "get-url", "origin"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return None
    m = re.match(r"(?:git@github\.com:|https://github\.com/)([^/]+)/(.+?)(?:\.git)?$", url)
    if not m:
        return None
    owner, repo = m.group(1), m.group(2)
    return f"https://{owner.lower()}.github.io/{repo}/"


def aspect(path: Path):
    """w/h as a CSS aspect-ratio, so cards reserve their height before media loads
    and a #anchor link lands on the right card. None if ffprobe is unavailable."""
    if not FFPROBE:
        return None
    try:
        out = subprocess.run(
            [FFPROBE, "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0:s=/", str(path)],
            capture_output=True, text=True, timeout=20,
        ).stdout.strip().splitlines()
        w, h = out[0].split("/")[:2]
        return f"{int(w)}/{int(h)}" if int(w) > 0 and int(h) > 0 else None
    except Exception:
        return None


def slug(rel: Path) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(rel.with_suffix("")).lower()).strip("-")
    return s or "video"


entries, seen = [], set()
for path in sorted(p for p in media.rglob("*") if p.suffix.lower() in EXTS):
    rel = path.relative_to(media)
    sid = slug(rel)
    if sid in seen:                       # distinct files must not share an anchor
        n = 2
        while f"{sid}-{n}" in seen:
            n += 1
        sid = f"{sid}-{n}"
    seen.add(sid)
    entries.append({
        "id": sid,
        "file": f"media/{rel.as_posix()}",
        "name": rel.as_posix(),
        "type": EXTS[path.suffix.lower()],
        "size_mb": round(path.stat().st_size / 1e6, 1),
        "aspect": aspect(path),
    })

(root / "videos.json").write_text(json.dumps(entries, indent=2) + "\n")

if not entries:
    print(f"No videos found in {media}. Drop .mp4 or .gif files there and rerun.")
    sys.exit(0)

total = sum(e["size_mb"] for e in entries)
print(f"{len(entries)} video(s), {total:.1f} MB total -> videos.json\n")

base = base_url()
width = max(len(e["name"]) for e in entries)
for e in entries:
    link = f"{base}#{e['id']}" if base else f"<pages-url>#{e['id']}"
    print(f"  {e['name']:<{width}}  {link}")

if not base:
    print("\nNo GitHub origin remote yet, so the site URL is unknown.")
    print("Add one and rerun to get real links:")
    print("  git remote add origin git@github.com:<you>/<repo>.git")

print("\nIn LaTeX, escape the hash:  \\href{...\\#anchor}{[video]}")

too_big = [e for e in entries if e["size_mb"] > GITHUB_FILE_LIMIT_MB]
biggish = [e for e in entries if GITHUB_WARN_MB < e["size_mb"] <= GITHUB_FILE_LIMIT_MB]
if too_big:
    print(f"\nERROR: GitHub rejects any file over {GITHUB_FILE_LIMIT_MB} MB. Shrink these before pushing:")
    for e in too_big:
        print(f"  {e['name']}  {e['size_mb']} MB")
    print("  e.g.  ffmpeg -i in.gif -vf scale=640:-2 out.mp4")
if biggish:
    print(f"\nNote: over {GITHUB_WARN_MB} MB, GitHub warns on push:")
    for e in biggish:
        print(f"  {e['name']}  {e['size_mb']} MB")
if total > PAGES_SITE_LIMIT_MB * 0.9:
    print(f"\nWARNING: {total:.0f} MB is near the {PAGES_SITE_LIMIT_MB} MB GitHub Pages site limit.")
