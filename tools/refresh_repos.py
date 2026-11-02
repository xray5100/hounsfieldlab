#!/usr/bin/env python3
"""Refresh last_push_utc and maintenance in data/catalog.json from the GitHub API.
Usage: python3 tools/refresh_repos.py YYYY-MM-DD   (snapshot date; then set SNAPSHOT in build.py)
Needs `gh` signed in. Licenses are hand-reviewed, so mismatches are only reported."""
import json, subprocess, sys, re
from datetime import date
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
snap = date.fromisoformat(sys.argv[1])
p = ROOT/'data'/'catalog.json'
c = json.loads(p.read_text())
for t in c['tools']:
    gh = next((u for u in t['urls'] if re.match(r'https://github\.com/[^/]+/[^/#?]+', u)), None)
    if not gh:
        print('no github url:', t['name']); continue
    owner, repo = gh.split('/')[3:5]
    r = subprocess.run(['gh','api',f'repos/{owner}/{repo}'], capture_output=True, text=True)
    if r.returncode:
        print('API error:', t['name'], r.stderr.strip()[:120]); continue
    j = json.loads(r.stdout)
    pushed = j['pushed_at'][:10]
    old = t['last_push_utc']
    if pushed < old:
        pushed = old  # never move backwards
    t['last_push_utc'] = pushed
    t['maintenance'] = 'Stale' if (snap - date.fromisoformat(pushed)).days > 365 else 'Maintained'
    if j.get('archived'): print('ARCHIVED:', t['name'])
    spdx = (j.get('license') or {}).get('spdx_id')
    if spdx and spdx not in ('NOASSERTION',) and spdx not in t['license']:
        print(f"license differs: {t['name']}: listed {t['license']!r}, GitHub {spdx}")
    if old != pushed: print(f"{t['name']}: {old} -> {pushed} ({t['maintenance']})")
p.write_text(json.dumps(c, indent=1, ensure_ascii=False) + '\n')
