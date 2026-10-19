# Hounsfield Lab

Static site (plain HTML/CSS/JS). No build tooling is needed to serve it.

- Tool data source: `/workspace/medai/catalog.csv`, with manual license overrides in `build.py` (`LIC`). If that file is absent, `build.py` rebuilds the tool pages from `data/catalog.json`. `SNAPSHOT` in `build.py` is the date repository metadata (last push, license) was last refreshed.
- Dataset data source: `datasets.csv`. Regenerate everything with `python3 build.py`: `index.html`, `directory.html`, `datasets.html`, `datasets/*.html` (one page per dataset), `suggest.html`, `about.html`, the pipeline page, `tools/*.html`, `data/catalog.json`, `data/datasets.json`, `sitemap.xml`, `robots.txt`, `llms.txt`, `llms-full.txt`.
- The build is idempotent. A page's sitemap `lastmod` only moves to today when that page's HTML changes; unchanged pages keep the date from the previous `sitemap.xml`. Pages for tools or datasets removed from the source data are deleted.
- Related tools on dataset pages (and related datasets on tool pages) come from `AREA_TOOLS`, `FORMAT_TOOLS` and `TOOL_MODS` in `build.py`.
- Check dataset URLs: `python3 tools/check_datasets.py` (report) or `python3 tools/check_datasets.py --update` (stamp `date_last_checked`). The script does not change VERIFIED / UNVERIFIED. Reader suggestions are not auto-published; add an approved row to `datasets.csv` with status `UNVERIFIED` until the source page has been reviewed.
- Editable page bodies: `content/` (line 1 = title, line 2 = meta description; `{{SNAPSHOT}}` is replaced with the snapshot date).
- Local preview: `python3 -m http.server 8080`
