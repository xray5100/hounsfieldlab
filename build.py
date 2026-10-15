#!/usr/bin/env python3
"""Static site generator for Hounsfield Lab. Run: python3 build.py"""
import csv, json, re, html
from urllib.parse import quote
from datetime import date
from pathlib import Path

SITE_URL = "https://hounsfieldlab.com"
SNAPSHOT = date(2026, 10, 13)
ROOT = Path(__file__).parent
E = html.escape

GROUPS = {
 "Foundation models & agents": ["Foundation model","AI agent","Vision-language model","Evaluation / report labeling"],
 "Segmentation & frameworks": ["Segmentation","Framework","Annotation","Data / preprocessing","Radiomics","Registration"],
 "Neuroimaging": ["Neuro preprocessing","Neuroimaging library","Neuroimaging suite"],
 "Viewers & toolkits": ["Viewer / workstation","Viewer (web)","Image toolkit"],
 "DICOM/PACS & deployment": ["DICOM infrastructure","PACS / DICOM server","AI deployment / orchestration","AI platform"],
 "Pathology": ["Pathology","Pathology viewer / analysis"],
 "Clinical NLP": ["Clinical NLP"],
 "EHR & data": ["EHR interoperability","Synthetic data","EHR datasets/code","EHR analytics","EHR / ETL"],
}
SUB2G = {s: g for g, subs in GROUPS.items() for s in subs}
# Tools whose primary use is neuro but sub-category is generic
NEURO_OVERRIDE = {"HD-BET","BrainChop","ANTsPy"}
UNI_GROUP_OVERRIDE = {"UNI": "Pathology"}

# Manually reviewed license files (Oct 13, 2026). name -> (license, commercial, note)
LIC = {
 "Pillar-0 (finetune code + HF weights)": ("ECL-2.0","Permissive","Repo LICENSE is Educational Community License 2.0 (Apache 2.0 with a narrowed patent grant). Hugging Face weights (Pillar0-ChestCT, -AbdomenCT, -HeadCT, -BreastMRI) are tagged ecl-2.0."),
 "Pillar-0 pretraining": ("ECL-2.0","Permissive","Repo LICENSE is Educational Community License 2.0."),
 "RATE": ("ECL-2.0","Permissive","Repo LICENSE is Educational Community License 2.0."),
 "CheXagent": ("CC BY-NC-ND 4.0","Non-commercial","Repo LICENSE is Creative Commons Attribution-NonCommercial-NoDerivatives 4.0."),
 "LLaVA-Med": ("Microsoft Research License","Verify","Repo LICENSE is the Microsoft Research License Terms, covering code, models and data. Read the terms before any use beyond research."),
 "FreeSurfer": ("FreeSurfer License","Verify","Repo LICENSE.txt is the FreeSurfer Software License Agreement v1.0 (MGH), a custom license."),
 "DIPY": ("BSD-3-Clause","Permissive","Repo LICENSE is BSD 3-clause unless individual files say otherwise."),
 "3D Slicer": ("Slicer License (BSD-style)","Permissive","Repo License.txt describes a BSD-style license with Slicer-specific extensions."),
 "pydicom": ("MIT (+ noted portions)","Permissive","Repo LICENSE is MIT except for portions listed in the file."),
 "DCMTK": ("BSD-3-Clause (OFFIS)","Permissive","COPYRIGHT file is a BSD-style license from OFFIS e.V.; some bundled parts carry other notices."),
 "TIAToolbox": ("BSD-3-Clause","Verify","Code is BSD 3-clause. LICENSE says the model weights are under a different license (see TIAToolbox pretrained-model docs)."),
 "UNI": ("CC BY-NC-ND 4.0","Non-commercial","Repo LICENSE and Hugging Face weights (MahmoodLab/UNI) are CC BY-NC-ND 4.0."),
 "MedGemma": ("Apache-2.0 (code)","Verify","Code is Apache-2.0. Weights on Hugging Face are under the Health AI Developer Foundations terms: https://developers.google.com/health-ai-developer-foundations/terms"),
}

def slug(s): return re.sub(r'-+','-',re.sub(r'[^a-z0-9]+','-',s.lower())).strip('-')

def load():
    out=[]
    for r in csv.DictReader(open('/workspace/medai/catalog.csv')):
        t=dict(r); t['urls']=[u.strip() for u in r['url'].split(';')]
        t['group']=UNI_GROUP_OVERRIDE.get(t['name']) or ("Neuroimaging" if t['name'] in NEURO_OVERRIDE else SUB2G[t['category']])
        d=date.fromisoformat(r['last_push_utc']); t['maintenance']='Stale' if (SNAPSHOT-d).days>365 else 'Maintained'
        if t['name'] in LIC:
            t['license'],t['commercial'],t['license_note']=LIC[t['name']]
        else:
            l=t['license']; t['license_note']=''
            t['commercial']='Copyleft' if 'GPL' in l else 'Permissive'
        t['slug']=slug(t['name'].split(' (')[0]) if t['name'] not in ("Pillar-0 pretraining",) else 'pillar-0-pretraining'
        out.append(t)
    assert len({t['slug'] for t in out})==len(out)
    return out

def head(title, desc, path, root, og_img="assets/og.png"):
    url=f"{SITE_URL}/{path}"
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{url}">
<meta property="og:type" content="website"><meta property="og:site_name" content="Hounsfield Lab"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{url}"><meta property="og:image" content="{SITE_URL}/{og_img}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{E(title)}"><meta name="twitter:description" content="{E(desc)}"><meta name="twitter:image" content="{SITE_URL}/{og_img}">
<link rel="icon" href="{root}assets/logo.svg"><link rel="stylesheet" href="{root}assets/style.css"></head><body data-root="{root}">
<header><div class="wrap nav"><a class="brand" href="{root}index.html"><img src="{root}assets/logo.svg" alt="" width="32" height="32">Hounsfield Lab</a>
<button class="menu" aria-label="Menu" onclick="document.body.classList.toggle('navopen')">☰</button>
<nav><a href="{root}directory.html">Directory</a><a href="{root}pipeline-orthanc-mercure.html">Pipeline guide</a><a href="{root}suggest.html">Suggest a tool</a><a href="{root}about.html">About</a><a href="{root}index.html#newsletter">Newsletter</a></nav></div></header><main>'''

def foot(root, script=""):
    return f'''</main><footer><div class="wrap">Hounsfield Lab · Open-source medical AI, curated by a practicing neuroradiologist. Listings are for research and development reference: not medical advice, not an endorsement, not legal advice on licensing, and not a statement of regulatory clearance. Repository data snapshot: Oct 13, 2026.</div></footer>
<div class="modal" id="modal" role="dialog" aria-modal="true"><div class="box"><button class="close" aria-label="Close">×</button><div class="content"></div></div></div>
<script src="{root}assets/app.js"></script>{script}</body></html>'''

def newsletter(root):
    return f'''<section id="newsletter"><div class="wrap"><div class="signup"><h2>The weekly open medical AI briefing</h2><p>New open models, weights and tools worth knowing, in five minutes.</p>
<!-- TODO(launch): set action to your newsletter provider's form endpoint (e.g. Buttondown/ConvertKit/Beehiiv) and remove data-placeholder. -->
<form class="ph-form" action="#" method="post" data-placeholder="newsletter"><label class="sr" for="nl-email">Email</label><input id="nl-email" name="email" type="email" placeholder="you@hospital.org" required><button class="btn" type="submit">Notify me</button><p class="note formmsg" aria-live="polite">Signup isn’t live yet. Nothing is sent or stored.</p></form></div></div></section>'''

def badges(t):
    m='ok' if t['maintenance']=='Maintained' else 'warn'
    c={'Permissive':'ok','Verify':'warn'}.get(t['commercial'],'bad')
    return (f'<div class="labs"><span class="lab"><b>LIC</b><span>{E(t["license"])}</span></span><span class="lab"><b>UPD</b><span>{E(t["last_push_utc"])}</span></span>'
            f'<span class="lab {m}"><b>STATUS</b><span>{t["maintenance"]}</span></span><span class="lab {c}"><b>COMM</b><span>{E(t["commercial"])}</span></span></div>')

def tool_page(t):
    root="../"; desc=f'{t["name"]}: {t["what_it_does"]}. License {t["license"]}, last updated {t["last_push_utc"]}.'
    links="".join(f'<li><a href="{E(u)}" target="_blank" rel="noopener">{E(u.replace("https://",""))}</a></li>' for u in t['urls'])
    note=f'<p class="note"><strong>License review:</strong> {E(t["license_note"])}</p>' if t['license_note'] else ''
    warn='' if t['commercial']=='Permissive' else '<p class="note">Commercial use: read the project’s license (and any model-weight terms) yourself before relying on it. This isn’t legal advice.</p>'
    return head(f'{t["name"]} · Hounsfield Lab', desc[:300], f'tools/{t["slug"]}.html', root)+f'''
<section><div class="wrap prose"><p class="crumb"><a href="../directory.html">Directory</a> › <a href="../directory.html?group={quote(t["group"])}">{E(t["group"])}</a></p>
<h1 class="tt">{E(t["name"])}</h1><p class="lead">{E(t["what_it_does"])}</p>{badges(t)}
<dl style="margin-top:22px"><dt>Group</dt><dd>{E(t["group"])}</dd><dt>Type</dt><dd>{E(t["category"])}</dd><dt>Modality</dt><dd>{E(t["modality_specialty"])}</dd><dt>Maintainer</dt><dd>{E(t["maintainer"])}</dd><dt>License</dt><dd>{E(t["license"])}</dd><dt>Last update</dt><dd>{E(t["last_push_utc"])} (last repository push, UTC)</dd></dl>
<h3>Links</h3><ul>{links}</ul>{note}{warn}<p><a class="btn ghost" href="../directory.html">← Back to directory</a></p></div></section>'''+foot(root)

def main():
    tools=load(); (ROOT/'data').mkdir(exist_ok=True); (ROOT/'tools').mkdir(exist_ok=True)
    pub=[{k:t[k] for k in ('name','slug','group','category','modality_specialty','what_it_does','license','license_note','commercial','maintenance','last_push_utc','maintainer','urls')} for t in tools]
    json.dump({"groups":list(GROUPS),"tools":pub},open(ROOT/'data/catalog.json','w'),indent=1)
    for t in tools: (ROOT/f'tools/{t["slug"]}.html').write_text(tool_page(t))
    counts={g:sum(t['group']==g for t in tools) for g in GROUPS}
    pillar=next(t for t in tools if t['slug']=='pillar-0')
    tiles="".join(f'<a class="card tile" href="directory.html?group={quote(g)}"><h3>{E(g)}</h3><span class="n">n = {n}</span></a>' for g,n in counts.items())
    pages={}
    pages['index.html']=head('Hounsfield Lab · Open-source medical AI directory','A neuroradiologist-curated directory of open-source medical AI models, toolkits and infrastructure, with license, update and maintenance status at a glance.','', '')+f'''
<div class="hero"><div class="wrap"><div class="curator">Curated by a practicing neuroradiologist</div><h1>Open-source medical AI, measured like a lab value.</h1><p>A clinician-curated directory of downloadable models, toolkits and infrastructure for building medical AI, with license, update and maintenance status at a glance.</p><p class="cta"><a class="btn" href="directory.html">Browse {len(tools)} tools</a> <a class="btn ghost" href="pipeline-orthanc-mercure.html">See a pipeline guide</a></p></div></div>
<section><div class="wrap"><h2>Featured: Pillar-0</h2><div class="feature"><div><p><strong>An open radiology foundation model from YalaLab.</strong> Pretrained on 42,990 abdomen-pelvis CTs, 86,411 chest CTs, 14,348 head CTs and 11,543 breast MRIs, with RATE, an LLM-based framework that extracts labels for 366 radiologic findings from reports. The authors release code, weights and evaluation tools.</p><p><a href="https://yalalab.github.io/pillar-0/" target="_blank" rel="noopener">Project page</a> · <a href="https://arxiv.org/abs/2511.17803" target="_blank" rel="noopener">Paper</a> · <a href="https://huggingface.co/collections/YalaLab/pillar-0" target="_blank" rel="noopener">Weights</a></p></div><div>{badges(pillar)}<p style="margin-top:16px"><a class="btn" href="tools/pillar-0.html">View details</a></p></div></div></div></section>
<section><div class="wrap"><h2>Browse by category</h2><div class="grid cats">{tiles}</div></div></section>'''+newsletter('')+foot('')
    pages['directory.html']=head('Directory · Hounsfield Lab',f'Filter {len(tools)} open-source medical AI tools by category, modality, license and maintenance status.','directory.html','')+'''
<section><div class="wrap"><h1 class="h2">Directory</h1><p class="note">STATUS: “Maintained” = repo updated within 12 months of the Oct 13, 2026 snapshot. COMM: “Permissive” = permissive open-source license; “Copyleft” = GPL/AGPL obligations; “Non-commercial” = license forbids commercial use; “Verify” = custom terms or separate weight terms. Always read the license yourself.</p>
<div class="filters"><input id="q" type="search" placeholder="Search tools, maintainers…" aria-label="Search"><select id="group" aria-label="Category"><option value="">All categories</option></select><select id="modality" aria-label="Modality"><option value="">All modalities</option></select><select id="commercial" aria-label="License type"><option value="">Any license type</option></select><select id="maintenance" aria-label="Status"><option value="">Any status</option></select><button class="btn ghost small" id="reset" type="button">Reset</button></div>
<div class="count" id="count" aria-live="polite"></div><div class="grid" id="list"></div><p id="empty" class="note" hidden>No tools match these filters.</p></div></section>'''+foot('','<script>initDirectory()</script>')
    pages['suggest.html']=head('Suggest a tool · Hounsfield Lab','Suggest an open-source medical AI tool or a correction for the Hounsfield Lab directory.','suggest.html','')+'''
<section><div class="wrap prose"><h1 class="h2">Suggest a tool or a correction</h1><p>Know an open-source or downloadable medical AI tool we should list, or spotted an error? Tell us. Every submission is reviewed by hand before anything is published.</p>
<!-- TODO(launch): point action at a form backend (e.g. Formspree / Netlify Forms / a GitHub issue template) and remove data-placeholder. -->
<form class="ph-form stack" action="#" method="post" data-placeholder="suggest">
<label>Tool name<input name="name" required></label><label>Repository or download URL<input name="url" type="url" placeholder="https://github.com/…" required></label>
<label>Type<select name="kind"><option>New tool</option><option>Correction to a listing</option></select></label>
<label>Why it’s useful / what to fix<textarea name="notes" rows="5"></textarea></label><label>Your email (optional)<input name="email" type="email"></label>
<button class="btn" type="submit">Submit suggestion</button><p class="note formmsg" aria-live="polite">Submissions aren’t live yet. Nothing is sent or stored.</p></form></div></section>'''+foot('')
    for p in ['pipeline-orthanc-mercure.html','about.html']:
        src=(ROOT/'content'/p).read_text()
        title,desc=src.split('\n',2)[:2]
        pages[p]=head(title,desc,p,'')+src.split('\n',2)[2]+foot('')
    for p,h in pages.items(): (ROOT/p).write_text(h)
    urls=['','directory.html','pipeline-orthanc-mercure.html','about.html','suggest.html']+[f'tools/{t["slug"]}.html' for t in tools]
    (ROOT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>{SITE_URL}/{u}</loc><lastmod>{SNAPSHOT}</lastmod></url>\n' for u in urls)+'</urlset>\n')
    (ROOT/'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n')
    print(len(tools),'tools', counts)
main()
