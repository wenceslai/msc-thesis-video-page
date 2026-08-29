# Rollout videos

Companion page for the thesis: closed-loop simulation rollouts, each with a
permanent link to cite from a figure caption. MP4 and GIF are both supported.

The page has two modes, chosen by the URL:

- `.../` - gallery of every video.
- `.../#some-video-id` - that video **alone**, large and centred, with an
  "All videos" button back to the gallery. This is what a thesis link opens.

Both live in `index.html`; there is no second page, so every link keeps working
whichever mode it points at.

This is a **separate repository from the research code**, deliberately: videos are
large and would permanently bloat the research repo's history. It lives inside that
project folder for convenience, but is ignored by it (`rollout-videos/` in its
`.gitignore`), so the two never interfere.

## Adding videos

1. Put files into `media/`:
   - **A file directly in `media/`** gets its own link and is shown on its own.
   - **A directory inside `media/`** becomes one link holding every video in it,
     shown with a picker underneath so the reader can step through them. This is
     what the viewpoint sweeps use.
2. Run `python3 refresh.py` — rebuilds `videos.json` and prints one link per entry.
3. `git add -A && git commit -m "add videos" && git push`

Inside a collection, items are labelled by filename without the extension and
sorted numerically — so a sweep reads `rollout`, `rollout5`, `rollout15`,
`rollout30`, not `rollout15`, `rollout30`, `rollout5`.

Spaces, `+` and parentheses in names are fine; the page URL-encodes each path
segment.

The site URL is derived from this repo's `origin` remote, so the printed links are
correct automatically once the remote is set.

The anchor comes from the filename, so **renaming a file changes its link**. Give
files their final names before putting links into a submitted PDF.

## Using a link in LaTeX

`#` is special in LaTeX and must be escaped:

```latex
\href{https://<you>.github.io/<repo>/\#can-cam35}{[video]}
```

## One-time GitHub setup

```bash
git remote add origin git@github.com:<you>/<repo>.git
git push -u origin main
```

Then: repo Settings → Pages → Build and deployment → Deploy from a branch →
branch `main`, folder `/ (root)` → Save.

The repo must be **public** on a free plan. `.nojekyll` is present so files are
served as-is without Jekyll processing.

## Size limits

`refresh.py` warns about all of these:

- **100 MB per file** — GitHub rejects the push outright.
- **50 MB per file** — GitHub warns.
- **1 GB total** — GitHub Pages site limit.

To shrink: `ffmpeg -i in.gif -vf scale=640:-2 out.mp4` (usually 10-20x smaller).
The page renders either format, so converting is optional.

## Files

| File | Role |
|---|---|
| `media/` | the videos |
| `index.html` | the page |
| `refresh.py` | regenerates `videos.json`, prints links |
| `videos.json` | generated - do not hand-edit |
| `.nojekyll` | disables Jekyll |
