# Hounsfield Lab

Static site (plain HTML/CSS/JS). No build tooling is needed to serve it.

- Tool data source: `/workspace/medai/catalog.csv`, with manual license overrides in `build.py` (`LIC`). If that file is absent, `build.py` rebuilds the tool pages from `data/catalog.json`.
- Dataset data source: `datasets.csv`. Regenerate with `python3 build.py` (writes `index.html`, `directory.html`, `datasets.html`, `suggest.html`, `about.html`, the pipeline page, `tools/*.html`, `data/catalog.json`, `data/datasets.json`, `sitemap.xml`, `robots.txt`).
- Check dataset URLs: `python3 tools/check_datasets.py` (report) or `python3 tools/check_datasets.py --update` (stamp `date_last_checked`). The script does not change VERIFIED / UNVERIFIED. Reader suggestions are not auto-published; add an approved row to `datasets.csv` with status `UNVERIFIED` until the source page has been reviewed.
- Editable page bodies: `content/` (line 1 = title, line 2 = meta description).
- Local preview: `python3 -m http.server 8080`

## Launch TODOs
- Set `SITE_URL` in build.py to the real domain (it's currently a placeholder; hounsfieldlab.com isn't registered yet).
- Wire the newsletter form (index.html) and the suggest form (suggest.html) to a provider; see the `TODO(launch)` comments.
