#!/usr/bin/env python3
"""Scan media/ and regenerate videos.json, then print the link for each entry.

A file directly in media/      -> one entry, shown on its own.
A directory inside media/      -> one entry holding every video in it, shown with
                                  a picker so the reader can step through them
                                  (used for viewpoint sweeps).

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
    return f"https://{m.group(1).lower()}.github.io/{m.group(2)}/" if m else None


def aspect(path: Path):
    """w/h as a CSS aspect-ratio, so cards reserve their height before media loads."""
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


def natkey(s: str):
    """Numeric-aware sort, so a sweep orders 5, 15, 30 rather than 15, 30, 5.
    re.split alternates non-digit/digit chunks, so types always line up."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def sortkey(p: Path):
    """Sort on the stem, never the extension: with '.mp4' included, '_rollout.mp'
    compares against '_rollout' and an unsuffixed baseline sorts after '...5'."""
    return natkey(p.stem if p.is_file() else p.name)


def is_video(p: Path):
    return p.is_file() and p.suffix.lower() in EXTS


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "video"


def describe(path: Path):
    """One playable item: label is the filename without its extension."""
    return {
        "label": path.stem,
        "file": f"media/{path.relative_to(media).as_posix()}",
        "type": EXTS[path.suffix.lower()],
        "size_mb": round(path.stat().st_size / 1e6, 1),
        "aspect": aspect(path),
    }


entries, seen = [], set()


def claim(sid):
    if sid in seen:
        n = 2
        while f"{sid}-{n}" in seen:
            n += 1
        sid = f"{sid}-{n}"
    seen.add(sid)
    return sid


for path in sorted(media.iterdir(), key=sortkey):
    if is_video(path):
        item = describe(path)
        entries.append({"id": claim(slug(path.stem)), "kind": "file",
                        "name": path.name, **item})
    elif path.is_dir():
        items = [describe(p) for p in sorted(
            (q for q in path.rglob("*") if is_video(q)), key=sortkey)]
        if not items:
            print(f"  (skipping empty directory: {path.name})")
            continue
        entries.append({"id": claim(slug(path.name)), "kind": "group",
                        "name": path.name, "items": items})

(root / "videos.json").write_text(json.dumps(entries, indent=2) + "\n")

if not entries:
    print(f"No videos found in {media}. Drop .mp4 or .gif files there and rerun.")
    sys.exit(0)

flat = [i for e in entries for i in (e["items"] if e["kind"] == "group" else [e])]
total = sum(i["size_mb"] for i in flat)
groups = sum(1 for e in entries if e["kind"] == "group")
print(f"{len(entries)} entries ({len(flat)} videos, {groups} collections), "
      f"{total:.1f} MB -> videos.json\n")

base = base_url()
width = max(len(e["name"]) for e in entries)
for e in entries:
    link = f"{base}#{e['id']}" if base else f"<pages-url>#{e['id']}"
    tag = f"  [{len(e['items'])} videos]" if e["kind"] == "group" else ""
    print(f"  {e['name']:<{width}}  {link}{tag}")

if not base:
    print("\nNo GitHub origin remote yet, so the site URL is unknown.")
    print("Add one and rerun:  git remote add origin git@github.com:<you>/<repo>.git")

print("\nIn LaTeX, escape the hash:  \\href{...\\#anchor}{[video]}")

too_big = [i for i in flat if i["size_mb"] > GITHUB_FILE_LIMIT_MB]
biggish = [i for i in flat if GITHUB_WARN_MB < i["size_mb"] <= GITHUB_FILE_LIMIT_MB]
if too_big:
    print(f"\nERROR: GitHub rejects any file over {GITHUB_FILE_LIMIT_MB} MB. Shrink these before pushing:")
    for i in too_big:
        print(f"  {i['file']}  {i['size_mb']} MB")
    print("  e.g.  ffmpeg -i in.gif -vf scale=640:-2 out.mp4")
if biggish:
    print(f"\nNote: over {GITHUB_WARN_MB} MB, GitHub warns on push:")
    for i in biggish:
        print(f"  {i['file']}  {i['size_mb']} MB")
if total > PAGES_SITE_LIMIT_MB * 0.9:
    print(f"\nWARNING: {total:.0f} MB is near the {PAGES_SITE_LIMIT_MB} MB GitHub Pages site limit.")
