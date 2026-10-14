# Hounsfield Lab

Static site (plain HTML/CSS/JS). No build tooling is needed to serve it.

- Data source: `/workspace/medai/catalog.csv`, with manual license overrides in `build.py` (`LIC`).
- Regenerate: `python3 build.py` (writes `index.html`, `directory.html`, `suggest.html`, `about.html`, the pipeline page, `tools/*.html`, `data/catalog.json`, `sitemap.xml`, `robots.txt`).
- Editable page bodies: `content/` (line 1 = title, line 2 = meta description).
- Local preview: `python3 -m http.server 8080`

## Launch TODOs
- Set `SITE_URL` in build.py to the real domain (it's currently a placeholder; hounsfieldlab.com isn't registered yet).
- Wire the newsletter form (index.html) and the suggest form (suggest.html) to a provider; see the `TODO(launch)` comments.
