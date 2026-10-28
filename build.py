#!/usr/bin/env python3
"""Static site generator for Hounsfield Lab. Run: python3 build.py"""
import csv, json, os, re, html
from urllib.parse import quote
from datetime import date
from pathlib import Path

SITE_URL = "https://hounsfieldlab.com"
BEEHIIV_FORM = "ac9b5485-be11-4149-9a23-58c583248e6a"
ARCHIVE_URL = "https://hounsfieldlab.beehiiv.com"
FORM_ENDPOINT = "https://formsubmit.co/ajax/676d89d9edc7b8fe301931545b3a4a15"  # FormSubmit alias (activated)
SNAPSHOT = date(2026, 10, 19)  # repository metadata refreshed from the GitHub API
TODAY = date.today()
ROOT = Path(__file__).parent
E = html.escape

GROUPS = {
 "Foundation models & agents": ["Foundation model","Agent","Vision-language model","Evaluation / report labeling"],
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
 "dcm2niix": ("BSD-style (+ bundled licenses)","Permissive","license.txt is a BSD-style license (Chris Rorden). Bundled parts such as the NIfTI headers, miniz, OpenJPEG, CharLS, zlib and Jasper carry their own licenses. The file states the software is for research purposes only and is not a clinical tool."),
 "FastSurfer": ("Apache-2.0","Verify","Repo LICENSE is Apache-2.0. The surface pipeline calls FreeSurfer binaries and needs a FreeSurfer license file (free, separate terms). The README says results are for research and not for clinical decision support."),
 "TorchXRayVision": ("Apache-2.0 (library); models vary","Verify","LICENSE says the main library is Apache-2.0 and that licenses vary by subpackage; check each baseline model's license before use."),
 "RadKev": ("Apache-2.0 (code); CC BY-NC-SA 4.0 (weights)","Non-commercial","Code is Apache-2.0. Hugging Face adapters (ramu9703/radkev-27b, radkev-9b) are CC BY-NC-SA 4.0 for non-commercial research; gated access requires accepting those terms. Not a medical device."),
 "NV-Segment-CT": ("Apache-2.0 (code); NVIDIA Open Model License (weights)","Verify","Hugging Face LICENSE applies Apache-2.0 to every file except the weights. Weights (model.pt is 872 MB) are under the NVIDIA Open Model License, which says the models are commercially usable; it is a custom license, not an OSI license (https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-license/, last modified October 24, 2025). The model card limits use to research and says it is not for clinical use. Inference expects a CUDA GPU (Ampere or Hopper). NV-Segment-CTMR is a different, non-commercial model and is not this listing."),
}

SPDX = {"Apache-2.0","MIT","BSD-3-Clause","GPL-2.0","GPL-3.0","AGPL-3.0","ECL-2.0"}
def lic_url(l):
    k=l.split(' ')[0]
    if k in SPDX: return f"https://spdx.org/licenses/{k}.html"
    if l.startswith("CC BY-NC-ND 4.0"): return "https://creativecommons.org/licenses/by-nc-nd/4.0/"
    if "CC BY-NC-SA 4.0" in l: return "https://creativecommons.org/licenses/by-nc-sa/4.0/"
    return None

def pdate(d): return f"{d:%b} {d.day}, {d.year}"
SNAP_TXT = pdate(SNAPSHOT)

def jsonld(obj): return '<script type="application/ld+json">'+json.dumps(obj,ensure_ascii=False).replace("</","<\\/")+'</script>'

def card_html(t,i,prefix=""):
    return (f'<article class="card" data-i="{i}"><h2 class="ct"><a href="{prefix}tools/{t["slug"]}.html">{E(t["name"])}</a></h2><p>{E(t["what_it_does"])}</p>{badges(t)}'
            f'<button class="qv" type="button">Quick view</button></article>')

def slug(s): return re.sub(r'-+','-',re.sub(r'[^a-z0-9]+','-',s.lower())).strip('-')

def load():
    # data/catalog.json is the source of truth. A private catalog.csv is used only when
    # HL_CATALOG_CSV points at it, so a stale local copy cannot drop published tools.
    env=os.environ.get('HL_CATALOG_CSV')
    csv_path=Path(env) if env else None
    if csv_path is None:
        # Published snapshot, used when the private catalog.csv is not on this machine.
        tools=json.loads((ROOT/'data'/'catalog.json').read_text())['tools']
        for t in tools: t['urls']=list(t['urls'])
        assert len({t['slug'] for t in tools})==len(tools)
        return tools
    out=[]
    for r in csv.DictReader(open(csv_path)):
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

def head(title, desc, path, root, og_img="assets/og.png", extra=""):
    url=f"{SITE_URL}/{path}"
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="google-site-verification" content="LpZ3OvHdRFVQAlJ5GIwsO6LPgXwDeOhBBG9iZz2kFro" />
<title>{E(title)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{url}">
<meta property="og:type" content="website"><meta property="og:site_name" content="Hounsfield Lab"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{url}"><meta property="og:image" content="{SITE_URL}/{og_img}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{E(title)}"><meta name="twitter:description" content="{E(desc)}"><meta name="twitter:image" content="{SITE_URL}/{og_img}">
<link rel="icon" href="{root}assets/logo.svg" type="image/svg+xml"><link rel="icon" href="{root}assets/favicon-32.png" sizes="32x32" type="image/png"><link rel="apple-touch-icon" href="{root}assets/apple-touch-icon.png"><meta name="theme-color" content="#0b2e6b">{extra}<link rel="stylesheet" href="{root}assets/style.css"></head><body data-root="{root}">
<a class="skip" href="#main">Skip to content</a>
<header><div class="wrap nav"><a class="brand" href="{root}index.html"><img src="{root}assets/logo.svg" alt="" width="32" height="32">Hounsfield Lab</a>
<button class="menu" type="button" aria-label="Menu" aria-expanded="false" aria-controls="sitenav" onclick="this.setAttribute('aria-expanded',document.body.classList.toggle('navopen'))">☰</button>
<nav id="sitenav" aria-label="Main">{nav_links(root, path)}</nav></div></header><main id="main">'''

NAV = [("directory.html","Directory"),("datasets.html","DICOM datasets"),("pipeline-orthanc-mercure.html","Pipeline guide"),("suggest.html","Suggest a tool"),("about.html","About"),("contact.html","Contact"),("newsletter.html","Newsletter")]
def nav_links(root, path):
    sec = "directory.html" if path.startswith("tools/") else "datasets.html" if path.startswith("datasets/") else path
    return "".join(f'<a href="{root}{h}"'+(' aria-current="page"' if h==path else ' class="here"' if h==sec else '')+f'>{t}</a>' for h,t in NAV)

def foot(root, script=""):
    return f'''</main><footer><div class="wrap">Hounsfield Lab · Open-source medical AI, curated by a practicing neuroradiologist. Listings are for research and development reference: not medical advice, not an endorsement, not legal advice on licensing, and not a statement of regulatory clearance. Repository data snapshot: {SNAP_TXT}. · <a href="{root}newsletter.html">Newsletter</a> · <a href="{root}privacy.html">Privacy</a> · <a href="{root}contact.html">Contact</a></div></footer>
<div class="modal" id="modal" role="dialog" aria-modal="true" aria-label="Tool details"><div class="box"><button class="close" type="button" aria-label="Close">×</button><div class="content"></div></div></div>
<script src="{root}assets/app.js"></script>{script}</body></html>'''

def bh_embed(lazy=False):
    if lazy:  # loaded by app.js when the section scrolls near the viewport
        return f'<div class="bh-embed" data-bh-lazy="{BEEHIIV_FORM}"><noscript><a href="{ARCHIVE_URL}">Subscribe on our newsletter page</a></noscript></div>'
    return f'<div class="bh-embed"><script async src="https://subscribe-forms.beehiiv.com/v3/loader.js" data-beehiiv-form="{BEEHIIV_FORM}"></script></div>'

def newsletter(root):
    return f'''<section id="newsletter"><div class="wrap"><div class="signup"><h2>The weekly open medical AI briefing</h2><p>New open models, weights and tools worth knowing, in five minutes. Free, and you can unsubscribe anytime.</p>
{bh_embed(lazy=True)}<p class="note">Read past issues in the <a href="{ARCHIVE_URL}" target="_blank" rel="noopener">archive</a> · <a href="{root}newsletter.html">What you get</a> · <a href="{root}privacy.html">Privacy</a></p></div></div></section>'''

def badges(t):
    m='ok' if t['maintenance']=='Maintained' else 'warn'
    c={'Permissive':'ok','Verify':'warn'}.get(t['commercial'],'bad')
    return (f'<div class="labs"><span class="lab"><b>LIC</b><span>{E(t["license"])}</span></span><span class="lab"><b>UPD</b><span>{E(t["last_push_utc"])}</span></span>'
            f'<span class="lab {m}"><b>STATUS</b><span>{t["maintenance"]}</span></span><span class="lab {c}"><b>COMM</b><span>{E(t["commercial"])}</span></span></div>')

def tool_page(t, tools, datasets):
    root="../"; desc=f'{t["name"]}: {t["what_it_does"]}. License {t["license"]}, last updated {t["last_push_utc"]}.'
    links="".join(f'<li><a href="{E(u)}" target="_blank" rel="noopener">{E(u.replace("https://",""))}</a></li>' for u in t['urls'])
    note=f'<p class="note"><strong>License review:</strong> {E(t["license_note"])}</p>' if t['license_note'] else ''
    warn='' if t['commercial']=='Permissive' else '<p class="note">Commercial use: read the project’s license (and any model-weight terms) yourself before relying on it. This isn’t legal advice.</p>'
    rel=[x for x in tools if x['group']==t['group'] and x is not t][:6]
    related="".join(f'<li><a href="{x["slug"]}.html">{E(x["name"])}</a>: {E(x["what_it_does"])}</li>' for x in rel)
    rds=datasets_for_tool(t['slug'], datasets)
    ds_html=('' if not rds else f'<h2 class="h3">Related public imaging datasets</h2><ul class="links">'+"".join(
        f'<li><a href="../datasets/{d["slug"]}.html">{E(d["name"])}</a>: {E(", ".join(d["modalities"]))}, {E(", ".join(AREA_LABEL[a] for a in d["areas"]))} · {E(d["license"])}</li>' for d in rds)
        +'</ul><p class="note">Browse all <a href="../datasets.html">DICOM datasets</a> with license and access details.</p>')
    repo=next((u for u in t['urls'] if 'github.com' in u), t['urls'][0])
    ld={"@context":"https://schema.org","@type":["SoftwareSourceCode","SoftwareApplication"],"name":t["name"],"description":t["what_it_does"],"codeRepository":repo,
        "url":f"{SITE_URL}/tools/{t['slug']}.html","dateModified":t["last_push_utc"],"applicationCategory":"HealthApplication","applicationSubCategory":t["group"],
        "keywords":[t["category"],t["modality_specialty"]],"isAccessibleForFree":True,"offers":{"@type":"Offer","price":"0","priceCurrency":"USD"},
        "license":lic_url(t["license"]) or t["license"],"maintainer":{"@type":"Organization","name":t["maintainer"]},"sameAs":t["urls"]}
    bc={"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
        {"@type":"ListItem","position":1,"name":"Home","item":SITE_URL+"/"},
        {"@type":"ListItem","position":2,"name":"Directory","item":f"{SITE_URL}/directory.html"},
        {"@type":"ListItem","position":3,"name":t["group"],"item":f"{SITE_URL}/directory.html?group={quote(t['group'])}"},
        {"@type":"ListItem","position":4,"name":t["name"],"item":f"{SITE_URL}/tools/{t['slug']}.html"}]}
    tn=t["name"].split(" (")[0]
    title=fit_title(f'{t["name"]}: {t["category"]} for {t["modality_specialty"]}', f'{tn}: {t["category"]} for {t["modality_specialty"]}', f'{tn}: open-source {t["category"].lower()}', tn)
    desc=fit_desc(desc, f'{t["name"]}: {t["what_it_does"]}. License {t["license"]}.', f'{tn}: {t["what_it_does"]}.')
    return head(title, desc, f'tools/{t["slug"]}.html', root, extra=jsonld(ld)+jsonld(bc))+f'''
<section><div class="wrap prose"><nav class="crumb" aria-label="Breadcrumb"><a href="../directory.html">Directory</a> › <a href="../directory.html?group={quote(t["group"])}">{E(t["group"])}</a> › <span aria-current="page">{E(t["name"])}</span></nav>
<h1 class="tt">{E(t["name"])}</h1><p class="lead">{E(t["what_it_does"])}</p>{badges(t)}
<dl style="margin-top:22px"><dt>What it is</dt><dd>{E(t["category"])} ({E(t["group"])})</dd><dt>Modality</dt><dd>{E(t["modality_specialty"])}</dd><dt>Maintainer</dt><dd>{E(t["maintainer"])}</dd><dt>License</dt><dd>{E(t["license"])}</dd><dt>Commercial use</dt><dd>{E(t["commercial"])}</dd><dt>Access</dt><dd>Free, public source repository (see links below)</dd><dt>Last update</dt><dd>{E(t["last_push_utc"])} (last repository push, UTC; {t["maintenance"]})</dd><dt>Last checked</dt><dd>{SNAPSHOT.isoformat()}</dd><dt>Limitations</dt><dd>Listed for research and development reference. Hounsfield Lab has not tested its clinical performance; check the project’s own documentation for intended use and regulatory status.</dd></dl>
<h2 class="h3">Links</h2><ul class="links">{links}</ul>{note}{warn}
<h2 class="h3">Related tools in {E(t["group"])}</h2><ul class="links">{related}</ul>{ds_html}
<p><a class="btn ghost" href="../directory.html">← Back to directory</a></p></div></section>'''+foot(root)

def write_llms(tools, datasets):
    updated=max(max(d["date_added"],d["date_last_checked"]) for d in datasets)
    ds_sorted=sorted(datasets, key=lambda d: d["name"].lower())
    intro=(f"# Hounsfield Lab\n\n> Hounsfield Lab is a directory of {len(tools)} open-source medical AI software tools and {len(datasets)} public DICOM and NIfTI imaging datasets, "
           f"curated by a practicing neuroradiologist. Radiology first, plus pathology, clinical NLP and EHR tooling. "
           f"Tool repository metadata last refreshed {SNAPSHOT}; dataset list last updated {updated}.\n\n"
           "Key facts:\n"
           "- Tool entries record license, commercial-use class, last repository push (UTC) and maintenance status.\n"
           "- Dataset entries record area, modality, format, size, license, commercial use, access route, whether normals are included, limitations, citation, and the date the source page was last checked.\n"
           "- Hounsfield Lab links to original sources and does not host code, weights or images.\n"
           "- Reader-suggested datasets are marked UNVERIFIED until the source page is reviewed.\n"
           "- Listings are research and development references, not medical, legal or regulatory advice.\n\n"
           "Badges: LIC = license (license files reviewed by hand where GitHub could not detect them); UPD = last repository push (UTC); "
           "STATUS = Maintained if updated within 12 months of the snapshot, else Stale; COMM = Permissive, Copyleft (GPL/AGPL), Non-commercial, or Verify (custom terms or separate model-weight terms).\n\n")
    pages=("## Pages\n\n"+f"- [Tool directory]({SITE_URL}/directory.html): filterable list of all tools\n"
           f"- [DICOM datasets]({SITE_URL}/datasets.html): public imaging datasets with license, access and normals; each has its own page under /datasets/\n"
           f"- [Pipeline guide]({SITE_URL}/pipeline-orthanc-mercure.html): Orthanc → mercure → TotalSegmentator → OHIF\n"
           f"- [About]({SITE_URL}/about.html): curation method\n- [Full catalog for LLMs]({SITE_URL}/llms-full.txt)\n- [Tool catalog JSON]({SITE_URL}/data/catalog.json)\n- [Dataset JSON]({SITE_URL}/data/datasets.json)\n\n")
    short=pages+"".join(f"## Tools: {g}\n\n"+"".join(f"- [{t['name']}]({SITE_URL}/tools/{t['slug']}.html): {t['what_it_does']} ({t['license']}; {t['maintenance']}; updated {t['last_push_utc']})\n" for t in tools if t['group']==g)+"\n" for g in GROUPS)
    ds_lines="".join(
        f"- [{d['name']}]({ds_url(d)}): {d['pathology']}. {', '.join(d['modalities'])}; {', '.join(d['formats'])}; license {d['license']}; access {d['access']}; normals {d['normals']}; {d['status']}. Source: {d['url']}\n"
        for d in ds_sorted)
    (ROOT/'llms.txt').write_text(intro+short+f"## DICOM datasets\n\n{ds_lines}")
    full="".join(f"## Tools: {g}\n\n"+"".join(
        f"### {t['name']}\n- What it is: {t['what_it_does']}\n- Type: {t['category']}\n- Modality/specialty: {t['modality_specialty']}\n- Maintainer: {t['maintainer']}\n"
        f"- License: {t['license']}\n- Commercial use: {t['commercial']}\n"+(f"- License note: {t['license_note']}\n" if t['license_note'] else "")+
        f"- Access: free public source repository\n- Last repository update: {t['last_push_utc']} ({t['maintenance']})\n- Last checked: {SNAPSHOT}\n- Links: {', '.join(t['urls'])}\n- Page: {SITE_URL}/tools/{t['slug']}.html\n"
        +("- Related datasets: "+", ".join(d['name'] for d in datasets_for_tool(t['slug'],datasets))+"\n" if datasets_for_tool(t['slug'],datasets) else "")+"\n" for t in tools if t['group']==g) for g in GROUPS)
    ds_full="".join(
        f"### {d['name']}\n- What it is: {d['pathology']}\n- Source: {d['url']}\n- Area: {d['area']}\n- Modality: {d['modality']}\n"
        f"- Normals included: {d['normals']}\n- Format: {d['format']}\n- Size: {d['size']}\n- License: {d['license']}\n"
        f"- Commercial use allowed: {d['commercial']}\n- Access: {d['access']}\n- How to access: {d['how_to_access']}\n"
        f"- Limitations: {d['limitations']}\n- Citation: {d['citation']}\n- Status: {d['status']}\n"
        f"- Added: {d['date_added']}\n- Last checked: {d['date_last_checked']}\n- Page: {ds_url(d)}\n\n"
        for d in ds_sorted)
    (ROOT/'llms-full.txt').write_text(intro+pages+full+f"## DICOM datasets\n\n{ds_full}")

DATASET_FIELDS = ["name","url","area","modality","pathology","normals","format","size","license","commercial","access","how_to_access","limitations","citation","status","date_added","date_last_checked"]
AREAS = ["neuro","chest","body","msk","breast","nuclear medicine","ultrasound","cardiac"]
AREA_LABEL = {"neuro":"Neuro","chest":"Chest","body":"Body","msk":"MSK","breast":"Breast","nuclear medicine":"Nuclear medicine","ultrasound":"Ultrasound","cardiac":"Cardiac"}
UNVERIFIED_WARNING = "UNVERIFIED — community-submitted, not reviewed by Hounsfield Lab; verify license and de-identification yourself"

def pretty_date(iso):
    y,m,d = iso.split("-")
    mon = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    return f"{int(d)} {mon[int(m)-1]} {y}"

def load_datasets():
    rows=list(csv.DictReader(open(ROOT/"datasets.csv")))
    if not rows: raise SystemExit("datasets.csv is empty")
    missing=[k for k in DATASET_FIELDS if k not in rows[0]]
    if missing: raise SystemExit("datasets.csv missing columns: "+", ".join(missing))
    enums={"normals":{"yes","no","partial"},"commercial":{"yes","no","check"},"access":{"open","account","credentialed"},"status":{"VERIFIED","UNVERIFIED"}}
    for r in rows:
        for k,ok in enums.items():
            if r[k] not in ok: raise SystemExit(f"{r['name']}: bad {k}={r[k]!r}")
        r["areas"]=[x.strip() for x in r["area"].split(";") if x.strip()]
        r["modalities"]=[x.strip() for x in r["modality"].split(";") if x.strip()]
        r["formats"]=[x.strip() for x in r["format"].split(";") if x.strip()]
        if not r["areas"] or not r["url"].startswith("https://"): raise SystemExit(f"{r['name']}: need an area and an https URL")
        for a in r["areas"]:
            if a not in AREAS: raise SystemExit(f"{r['name']}: unknown area {a}")
        r["slug"]=slug(r["name"])
        date.fromisoformat(r["date_added"]); date.fromisoformat(r["date_last_checked"])
    if len({r["slug"] for r in rows})!=len(rows): raise SystemExit("duplicate dataset slug")
    return rows

def ds_pills(d):
    comm={"yes":("ok","Commercial OK"),"no":("bad","Non-commercial"),"check":("warn","Check license")}[d["commercial"]]
    acc={"open":"Open download","account":"Account required","credentialed":"Credentialed DUA"}[d["access"]]
    status=("ok","Verified") if d["status"]=="VERIFIED" else ("warn","UNVERIFIED")
    return (f'<div class="pills"><span class="pill {comm[0]}">{comm[1]}</span><span class="pill {status[0]}">{status[1]}</span>'
            f'<span class="pill neutral">{acc}</span></div>')

def ds_labs(d):
    norm={"yes":"Yes","no":"No","partial":"Partial"}[d["normals"]]
    st="ok" if d["status"]=="VERIFIED" else "warn"
    return (f'<div class="labs"><span class="lab"><b>AREA</b><span>{E(", ".join(AREA_LABEL[a] for a in d["areas"]))}</span></span>'
            f'<span class="lab"><b>MOD</b><span>{E(", ".join(d["modalities"]))}</span></span>'
            f'<span class="lab"><b>FORMAT</b><span>{E(", ".join(d["formats"]))}</span></span>'
            f'<span class="lab"><b>NORMALS</b><span>{norm}</span></span>'
            f'<span class="lab"><b>LIC</b><span>{E(d["license"])}</span></span>'
            f'<span class="lab {st}"><b>CHECKED</b><span>{E(d["date_last_checked"])}</span></span></div>')

def ds_card(d):
    warn="" if d["status"]=="VERIFIED" else f'<p class="warnbox">{E(UNVERIFIED_WARNING)}</p>'
    cls="dcard unverified" if d["status"]!="VERIFIED" else "dcard"
    data=(f'data-area="{E(";".join(d["areas"]))}" data-modality="{E(";".join(d["modalities"]))}" '
          f'data-commercial="{d["commercial"]}" data-access="{d["access"]}" data-normals="{d["normals"]}" '
          f'data-format="{E(";".join(d["formats"]))}" data-status="{d["status"]}"')
    return (f'<article class="{cls}" id="ds-{d["slug"]}" {data}><h2><a href="datasets/{d["slug"]}.html">{E(d["name"])}</a></h2>'
            f'{warn}{ds_pills(d)}<p class="meta">{E(d["pathology"])}</p><p class="meta"><strong>Size.</strong> {E(d["size"])}</p>{ds_labs(d)}'
            f'<h3>How to access</h3><p>{E(d["how_to_access"])}</p><h3>Limitations</h3><p>{E(d["limitations"])}</p>'
            f'<p class="note" style="margin-top:10px"><strong>Citation.</strong> {E(d["citation"])} Added {pretty_date(d["date_added"])}.</p>'
            f'<p class="dlinks"><a href="datasets/{d["slug"]}.html">Details</a> · <a href="{E(d["url"])}" target="_blank" rel="noopener">Source page ↗</a></p></article>')

# Related tools for a dataset, by area and file format. A tool with a modality set only
# relates to datasets that include one of those modalities.
AREA_TOOLS = {"neuro":["hd-bet","fastsurfer","freesurfer","brainchop","dcm2niix"],
 "chest":["torchxrayvision","chexagent","medrax","pillar-0","totalsegmentator","nv-segment-ct"],
 "body":["totalsegmentator","nv-segment-ct","merlin","pillar-0","nnu-net"],
 "msk":["totalsegmentator","nv-segment-ct","nnu-net","3d-slicer"],
 "breast":["pillar-0","nnu-net","3d-slicer"],
 "nuclear medicine":["totalsegmentator","nv-segment-ct","nnu-net","3d-slicer"],
 "ultrasound":["monai","monai-label","3d-slicer"],
 "cardiac":["monai","nnu-net","3d-slicer"]}
FORMAT_TOOLS = {"DICOM":["pydicom","highdicom","ohif-viewer","orthanc"],"NIfTI":["torchio","simpleitk","itk"]}
TOOL_MODS = {"hd-bet":{"MR"},"fastsurfer":{"MR"},"freesurfer":{"MR"},"brainchop":{"MR"},"dcm2niix":{"MR","CT"},
 "torchxrayvision":{"DX","CR"},"chexagent":{"DX","CR"},"medrax":{"DX","CR"},"pillar-0":{"CT","MR"},"merlin":{"CT"},"totalsegmentator":{"CT","MR"},"nv-segment-ct":{"CT"}}
TOOL_SLUGS = set()

def tools_for_dataset(d):
    out=[]
    for a in d["areas"]: out+=AREA_TOOLS.get(a,[])
    for f in d["formats"]: out+=FORMAT_TOOLS.get(f,[])
    mods=set(d["modalities"]); seen=[]
    for s_ in out:
        if s_ in TOOL_SLUGS and s_ not in seen and (s_ not in TOOL_MODS or TOOL_MODS[s_]&mods): seen.append(s_)
    return seen[:7]

def datasets_for_tool(slug_, datasets, n=6):
    rel=[d for d in datasets if slug_ in tools_for_dataset(d)]
    rel.sort(key=lambda d:({"open":0,"account":1,"credentialed":2}[d["access"]], d["name"].lower()))
    return rel[:n]

DS_LIC_URL = {"CC BY 4.0":"https://creativecommons.org/licenses/by/4.0/","CC BY 3.0":"https://creativecommons.org/licenses/by/3.0/",
 "CC BY-NC 4.0":"https://creativecommons.org/licenses/by-nc/4.0/","CC BY-NC-SA 4.0":"https://creativecommons.org/licenses/by-nc-sa/4.0/",
 "CC BY-SA 3.0":"https://creativecommons.org/licenses/by-sa/3.0/","CC BY-SA 4.0":"https://creativecommons.org/licenses/by-sa/4.0/","CC0 1.0":"https://creativecommons.org/publicdomain/zero/1.0/"}
def ds_lic_url(l):
    for k,u in DS_LIC_URL.items():
        if l==k or l.startswith(k+" ("): return u
    return None
ACCESS_LABEL = {"open":"Open download, no account","account":"Free account and data-use terms required","credentialed":"Credentialed access under a data-use agreement"}
COMM_LABEL = {"yes":"Allowed by the license, with its attribution terms","no":"Not allowed under the free terms","check":"Mixed or unclear; check the source"}

SUFFIX = " · Hounsfield Lab"
def fit_title(*cands, n=65):
    """First candidate that fits in n characters with the site suffix; else the shortest, bare."""
    for c in cands:
        if len(c+SUFFIX)<=n: return c+SUFFIX
    return min(cands, key=len) if len(min(cands, key=len))<=n else trim(min(cands, key=len), n)

def fit_desc(*cands, n=160):
    for c in cands:
        if len(c)<=n: return c
    return trim(cands[-1], n)

def trim(t, n=200):
    return t if len(t)<=n else t[:n].rsplit(" ",1)[0].rstrip(",;:.")+"…"

def ds_url(d): return f"{SITE_URL}/datasets/{d['slug']}.html"

def dataset_page(d, datasets, tools_by_slug):
    root="../"; areas=", ".join(AREA_LABEL[a] for a in d["areas"]); mods=", ".join(d["modalities"])
    nm=d["name"]; short=nm.split(" (")[0]; m3=", ".join(d["modalities"][:3]); a1=AREA_LABEL[d["areas"][0]].lower()
    title=fit_title(f'{nm}: {m3} {a1} imaging dataset', f'{nm}: {m3} imaging dataset', f'{short}: {m3} imaging dataset', f'{short} imaging dataset', short)
    lic_short=re.split(r' \(|; ', d["license"])[0]; fm=", ".join(d["formats"])
    if d["commercial"]=="no" and "NC" not in lic_short and "non-commercial" not in lic_short.lower(): lic_short+=" (non-commercial)"
    desc=fit_desc(f'{nm}: {d["pathology"]}. {fm}. License: {d["license"]}. {ACCESS_LABEL[d["access"]]}.',
                  f'{nm}: {d["pathology"]}. {fm}. License: {lic_short}. {ACCESS_LABEL[d["access"]]}.',
                  f'{nm}: {d["pathology"]}. License: {lic_short}.',
                  f'{nm}: {d["pathology"]}.')
    norm={"yes":"Yes","no":"No","partial":"Partial (mixed or unlabeled)"}[d["normals"]]
    status=("Verified: source page reviewed by Hounsfield Lab" if d["status"]=="VERIFIED" else UNVERIFIED_WARNING)
    warn="" if d["status"]=="VERIFIED" else f'<p class="warnbox">{E(UNVERIFIED_WARNING)}</p>'
    rel_tools="".join(f'<li><a href="../tools/{t}.html">{E(tools_by_slug[t]["name"])}</a>: {E(tools_by_slug[t]["what_it_does"])}</li>' for t in tools_for_dataset(d))
    same=[x for x in sorted(datasets,key=lambda x:x["name"].lower()) if x is not d and set(x["areas"])&set(d["areas"][:1])][:6]
    same_li="".join(f'<li><a href="{x["slug"]}.html">{E(x["name"])}</a>: {E(", ".join(x["modalities"]))} · {E(x["license"])}</li>' for x in same)
    lic=ds_lic_url(d["license"])
    ld={"@context":"https://schema.org","@type":"Dataset","name":d["name"],
        "description":trim(f'{d["pathology"]}. Modality: {mods}. Format: {", ".join(d["formats"])}. Size: {d["size"]}. Access: {ACCESS_LABEL[d["access"]]}.',4900),
        "url":ds_url(d),"sameAs":d["url"],"license":lic or d["license"],"keywords":[*(AREA_LABEL[a] for a in d["areas"]),*d["modalities"],"medical imaging","radiology AI"],
        "measurementTechnique":d["modalities"],"dateModified":d["date_last_checked"],"citation":d["citation"],
        "includedInDataCatalog":{"@type":"DataCatalog","name":"Hounsfield Lab DICOM datasets","url":f"{SITE_URL}/datasets.html"}}
    if d["access"]=="open": ld["isAccessibleForFree"]=True
    bc={"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
        {"@type":"ListItem","position":1,"name":"Home","item":SITE_URL+"/"},
        {"@type":"ListItem","position":2,"name":"DICOM datasets","item":f"{SITE_URL}/datasets.html"},
        {"@type":"ListItem","position":3,"name":d["name"],"item":ds_url(d)}]}
    lic_html=f'<a href="{lic}" target="_blank" rel="noopener">{E(d["license"])}</a>' if lic else E(d["license"])
    return head(title, desc, f'datasets/{d["slug"]}.html', root, extra=jsonld(ld)+jsonld(bc))+f'''
<section><div class="wrap prose"><nav class="crumb" aria-label="Breadcrumb"><a href="../index.html">Home</a> › <a href="../datasets.html">DICOM datasets</a> › <span aria-current="page">{E(d["name"])}</span></nav>
<h1 class="tt">{E(d["name"])}</h1>{warn}<p class="lead">{E(d["pathology"])}</p>{ds_pills(d)}{ds_labs(d)}
<p class="cta" style="margin-top:18px"><a class="btn" href="{E(d["url"])}" target="_blank" rel="noopener">Open the source page ↗</a> <a class="btn ghost" href="../datasets.html#ds-{d["slug"]}">See it in the directory</a></p>
<h2 class="h3">At a glance</h2>
<dl><dt>What it is</dt><dd>{E(d["pathology"])}</dd><dt>Area</dt><dd>{E(areas)}</dd><dt>Modality</dt><dd>{E(mods)}</dd><dt>Format</dt><dd>{E(", ".join(d["formats"]))}</dd><dt>Size</dt><dd>{E(d["size"])}</dd><dt>Normals included</dt><dd>{norm}</dd><dt>License</dt><dd>{lic_html}</dd><dt>Commercial use</dt><dd>{COMM_LABEL[d["commercial"]]}</dd><dt>Access</dt><dd>{ACCESS_LABEL[d["access"]]}</dd><dt>Status</dt><dd>{E(status)}</dd><dt>Added</dt><dd>{d["date_added"]}</dd><dt>Last checked</dt><dd>{d["date_last_checked"]}</dd><dt>Source</dt><dd><a href="{E(d["url"])}" target="_blank" rel="noopener">{E(d["url"].replace("https://",""))}</a></dd></dl>
<h2 class="h3">How to access</h2><p>{E(d["how_to_access"])}</p>
<h2 class="h3">Limitations</h2><p>{E(d["limitations"])}</p>
<h2 class="h3">Citation required?</h2><p>{E(d["citation"])}</p>
{f'<h2 class="h3">Related open-source tools</h2><ul class="links">{rel_tools}</ul>' if rel_tools else ''}
{f'<h2 class="h3">More {E(AREA_LABEL[d["areas"][0]].lower())} datasets</h2><ul class="links">{same_li}</ul>' if same_li else ''}
<p class="note">Hounsfield Lab links to the source and does not host images. The license and access summary reflects the source page on the last-checked date; terms can change, so read the source before you download. Not legal advice.</p>
<p><a class="btn ghost" href="../datasets.html">← All DICOM datasets</a></p></div></section>'''+foot(root)

def datasets_page(datasets):
    ordered=sorted(datasets, key=lambda d: d["name"].lower())
    ordered=sorted(ordered, key=lambda d: d["date_added"], reverse=True)
    recent=ordered[:8]
    recent_li="".join(
        f'<li><a href="datasets/{d["slug"]}.html">{E(d["name"])}</a> <span class="note">· {E(", ".join(AREA_LABEL[a] for a in d["areas"]))} · added {pretty_date(d["date_added"])}</span></li>'
        for d in recent)
    newest=ordered[0]["date_added"]
    n_new=sum(d["date_added"]==newest for d in datasets)
    recent_note=(f'<p class="note">{n_new} datasets were added on {pretty_date(newest)}. Showing {len(recent)} below; the full list follows.</p>'
                 if n_new>len(recent) else f'<p class="note">Newest entries, by the date they were added to this directory.</p>')
    desc="Curated directory of public DICOM and NIfTI imaging datasets for radiology AI, with license, access, and whether normals are included."
    ld={"@context":"https://schema.org","@type":"CollectionPage","name":"DICOM datasets","url":f"{SITE_URL}/datasets.html",
        "description":desc,"isPartOf":{"@type":"WebSite","name":"Hounsfield Lab","url":SITE_URL+"/"},
        "mainEntity":{"@type":"ItemList","name":"Public DICOM and NIfTI datasets","numberOfItems":len(datasets),
                      "itemListElement":[{"@type":"ListItem","position":i+1,"name":d["name"],"url":ds_url(d)} for i,d in enumerate(sorted(datasets, key=lambda d: d["name"].lower()))]}}
    bc={"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
        {"@type":"ListItem","position":1,"name":"Home","item":SITE_URL+"/"},
        {"@type":"ListItem","position":2,"name":"DICOM datasets","item":f"{SITE_URL}/datasets.html"}]}
    cards="".join(ds_card(d) for d in sorted(datasets, key=lambda d: d["name"].lower()))
    updated=max(max(d["date_added"],d["date_last_checked"]) for d in datasets)
    n_open=sum(d["access"]=="open" for d in datasets); n_comm=sum(d["commercial"]=="yes" for d in datasets)
    return head("Public DICOM and NIfTI datasets for radiology AI · Hounsfield Lab", desc, "datasets.html", "", extra=jsonld(ld)+jsonld(bc))+f'''
<section><div class="wrap prose"><h1 class="h2">DICOM datasets</h1>
<p class="note updated">{len(datasets)} datasets · {n_open} open download · {n_comm} with commercial-use licenses · Last updated {pretty_date(updated)}</p>
<p class="lead">A directory of public DICOM, and a few closely related NIfTI, collections for radiologists and researchers training imaging models.</p>
<p>Each card is a link to the source download, plus the license, who can get in, and whether the set includes normals. Hounsfield Lab does not host images. The checked date is the day we loaded the source page. Files and terms change after that. <strong>This is not legal advice.</strong></p>
<h2 class="h3">How to read a license</h2>
<ul class="links">
<li><strong>CC BY</strong> (3.0 or 4.0) lets you copy, adapt, and use the data commercially if you give the credit the license asks for.</li>
<li><strong>CC BY-SA</strong> adds share-alike. If you redistribute an adaptation of the dataset, that adaptation stays under the same license.</li>
<li><strong>CC BY-NC</strong> and <strong>CC BY-NC-SA</strong> are non-commercial. Those cards carry a red Non-commercial badge. Training a product, or using the data inside a paid service, is usually outside the grant even when the work happens in a lab. Read the deed.</li>
<li><strong>Data-use agreements</strong> (PhysioNet, MIDRC, Stanford AIMI, NIH controlled access, Kaggle competition rules) are contracts. They often require an account, forbid redistribution, forbid re-identification, and limit you to research or education. Some hosts sell a separate commercial license. A DUA is not a Creative Commons license.</li>
<li><strong>De-identification is not permission.</strong> A dataset can be de-identified and still be off limits for your use. Head CT and MRI can sometimes be turned back into a face; several brain collections are controlled for that reason. Do not try to re-identify anyone.</li>
<li>Rows marked <strong>Check license</strong> or <strong>Check source</strong> are ones where the public page did not give a single clear grant. Use the source text, not this summary.</li>
</ul>
<h2 class="h3">Unverified suggestions</h2>
<p>Ideas sent through the form are not published by themselves. If we add one before checking the source, the card gets an orange badge and this warning: “{E(UNVERIFIED_WARNING)}.” We never host DICOM files or protected health information. Please don’t send either.</p>
</div></section>
<section><div class="wrap"><h2>Recently added</h2>{recent_note}<ul class="links recent">{recent_li}</ul></div></section>
<section><div class="wrap"><h2>All datasets</h2>
<div class="filters"><input id="q" type="search" placeholder="Search name, pathology, license…" aria-label="Search datasets"><select id="area" aria-label="Area"><option value="">All areas</option></select><select id="modality" aria-label="Modality"><option value="">All modalities</option></select><select id="commercial" aria-label="License"><option value="">Any license</option></select><select id="access" aria-label="Access"><option value="">Any access</option></select><select id="normals" aria-label="Normals"><option value="">Normals, any</option></select><select id="format" aria-label="Format"><option value="">Any format</option></select><button class="btn ghost small" id="reset" type="button">Reset</button></div>
<div class="count" id="count" aria-live="polite">{len(datasets)} of {len(datasets)} datasets</div>
<div class="dgrid" id="list">{cards}</div>
<p id="empty" class="note" hidden>No datasets match these filters.</p>
</div></section>
<section id="suggest"><div class="wrap prose"><h2>Suggest a dataset</h2>
<p>Know a public DICOM or NIfTI collection we should list? Send the link. A person reviews every note before anything is added. Nothing is published automatically. If we list it before that review is finished, it is marked UNVERIFIED.</p>
<form class="live-form stack" action="{FORM_ENDPOINT}" method="post" data-endpoint="{FORM_ENDPOINT}"><input type="hidden" name="_subject" value="Hounsfield Lab: dataset suggestion"><input type="hidden" name="form" value="dataset"><div class="hp" aria-hidden="true"><label>Leave this empty<input type="text" name="_honey" tabindex="-1" autocomplete="off"></label></div><input type="hidden" name="_captcha" value="false"><input type="hidden" name="_template" value="table">
<label>Dataset name<input type="text" name="dataset_name" required maxlength="200"></label>
<label>URL<input name="url" type="url" placeholder="https://…" required></label>
<label>Type<select name="kind"><option>DICOM files</option><option>Reports</option><option>Both</option><option>Other</option></select></label>
<label>Area<select name="area"><option>Neuro</option><option>Chest</option><option>Body</option><option>MSK</option><option>Breast</option><option>Nuclear medicine</option><option>Ultrasound</option><option>Cardiac</option><option>Other</option></select></label>
<label>Modality<input type="text" name="modality" maxlength="120" placeholder="CT, MR, MG, US…"></label>
<label>License, if you know it<input type="text" name="license" maxlength="200" placeholder="CC BY 4.0, DUA, unsure…"></label>
<label>Access notes<textarea name="access_notes" rows="4" maxlength="2000" placeholder="Open download, account, credentialed DUA…"></textarea></label>
<label>Your name (optional)<input type="text" name="name" autocomplete="name" maxlength="200"></label>
<label>Your email (optional, only if you want a reply)<input name="email" type="email" autocomplete="email"></label>
<label class="check"><input type="checkbox" name="deidentified_ok" value="yes" required> <span>I confirm this dataset is de-identified and lawfully shareable. I am not sending images or protected health information.</span></label>
<button class="btn" type="submit">Submit dataset</button>
<p class="note">Submissions are not added to the directory by this form. Approved links are entered by hand. Until we review them they are listed as UNVERIFIED. We never host PHI. By submitting you agree to our <a href="privacy.html">privacy notice</a>.</p>
<p class="note formmsg" role="status" aria-live="polite"></p></form></div></section>'''+foot("", "<script>initDatasets()</script>")

def old_lastmods():
    sm=ROOT/'sitemap.xml'
    if not sm.exists(): return {}
    return {loc[len(SITE_URL)+1:]:mod for loc,mod in re.findall(r'<loc>([^<]+)</loc><lastmod>([^<]+)</lastmod>', sm.read_text())}

LASTMOD={}
def emit(rel, text):
    """Write a page; its sitemap lastmod moves to today only when its bytes change."""
    f=ROOT/rel; key='' if rel=='index.html' else rel
    same=f.exists() and f.read_text()==text
    LASTMOD[key]=OLD_MOD.get(key, TODAY.isoformat()) if same else TODAY.isoformat()
    if not same: f.write_text(text)

def main():
    global OLD_MOD
    OLD_MOD=old_lastmods()
    tools=load(); (ROOT/'data').mkdir(exist_ok=True); (ROOT/'tools').mkdir(exist_ok=True); (ROOT/'datasets').mkdir(exist_ok=True)
    TOOL_SLUGS.update(t['slug'] for t in tools); tools_by_slug={t['slug']:t for t in tools}
    datasets=load_datasets()
    pub=[{k:t[k] for k in ('name','slug','group','category','modality_specialty','what_it_does','license','license_note','commercial','maintenance','last_push_utc','maintainer','urls')} for t in tools]
    json.dump({"groups":list(GROUPS),"tools":pub},open(ROOT/'data/catalog.json','w'),indent=1)
    for t in tools: emit(f'tools/{t["slug"]}.html', tool_page(t,tools,datasets))
    for d in datasets: emit(f'datasets/{d["slug"]}.html', dataset_page(d,datasets,tools_by_slug))
    # Remove generated pages whose tool or dataset was dropped from the source data.
    keep={f'{t["slug"]}.html' for t in tools}
    for f in (ROOT/'tools').glob('*.html'):
        if f.name not in keep: f.unlink()
    keep={f'{d["slug"]}.html' for d in datasets}
    for f in (ROOT/'datasets').glob('*.html'):
        if f.name not in keep: f.unlink()
    recent_ds=sorted(sorted(datasets,key=lambda d:d["name"].lower()),key=lambda d:d["date_added"],reverse=True)[:5]
    recent_ds_li="".join(f'<li><a href="datasets/{d["slug"]}.html">{E(d["name"])}</a> <span class="note">· {E(", ".join(AREA_LABEL[a] for a in d["areas"]))} · {E(", ".join(d["modalities"]))} · added {pretty_date(d["date_added"])}</span></li>' for d in recent_ds)
    counts={g:sum(t['group']==g for t in tools) for g in GROUPS}
    pillar=next(t for t in tools if t['slug']=='pillar-0')
    tiles="".join(f'<a class="card tile" href="directory.html?group={quote(g)}"><h3>{E(g)}</h3><span class="n">n = {n}</span></a>' for g,n in counts.items())
    pages={}
    org={'@context':'https://schema.org','@type':'Organization','name':'Hounsfield Lab','url':SITE_URL+'/','logo':SITE_URL+'/assets/icon-512.png','description':'Open-source medical AI directory, curated by a practicing neuroradiologist.'}
    pages['index.html']=head('Hounsfield Lab: open-source medical AI tools and DICOM datasets',f'A neuroradiologist-curated directory of {len(tools)} open-source medical AI tools and {len(datasets)} public DICOM imaging datasets, with license, access and maintenance status.','', '', extra=jsonld(org)+jsonld({'@context':'https://schema.org','@type':'WebSite','name':'Hounsfield Lab','url':SITE_URL+'/','description':'Open-source medical AI directory, curated by a practicing neuroradiologist.','potentialAction':{'@type':'SearchAction','target':{'@type':'EntryPoint','urlTemplate':SITE_URL+'/directory.html?q={search_term_string}'},'query-input':'required name=search_term_string'}}))+f'''
<div class="hero"><div class="wrap"><div class="curator">Curated by a practicing neuroradiologist</div><h1>Open-source medical AI, measured like a lab value.</h1><p>A clinician-curated directory of downloadable models, toolkits and infrastructure for building medical AI, with license, update and maintenance status at a glance.</p><p class="cta"><a class="btn" href="directory.html">Browse {len(tools)} tools</a> <a class="btn ghost" href="datasets.html">DICOM datasets</a> <a class="btn ghost" href="pipeline-orthanc-mercure.html">See a pipeline guide</a></p></div></div>
<section><div class="wrap"><h2>Featured: Pillar-0</h2><div class="feature"><div><p><strong>An open radiology foundation model from YalaLab.</strong> Pretrained on 42,990 abdomen-pelvis CTs, 86,411 chest CTs, 14,348 head CTs and 11,543 breast MRIs, with RATE, an LLM-based framework that extracts labels for 366 radiologic findings from reports. The authors release code, weights and evaluation tools.</p><p><a href="https://yalalab.github.io/pillar-0/" target="_blank" rel="noopener">Project page</a> · <a href="https://arxiv.org/abs/2511.17803" target="_blank" rel="noopener">Paper</a> · <a href="https://huggingface.co/collections/YalaLab/pillar-0" target="_blank" rel="noopener">Weights</a></p></div><div>{badges(pillar)}<p style="margin-top:16px"><a class="btn" href="tools/pillar-0.html">View details</a></p></div></div></div></section>
<section><div class="wrap"><h2>Browse by category</h2><div class="grid cats">{tiles}</div></div></section>
<section><div class="wrap"><h2>DICOM datasets</h2><p>{len(datasets)} public DICOM and NIfTI collections for training and evaluation, with the license, who can download, and whether normals are included. Recently added:</p><ul class="links recent">{recent_ds_li}</ul><p class="cta"><a class="btn" href="datasets.html">Browse {len(datasets)} DICOM datasets</a></p></div></section>'''+newsletter('')+foot('')
    pages['directory.html']=head('Open-source medical AI tools directory · Hounsfield Lab',f'Filter {len(tools)} open-source medical AI tools by category, modality, license and maintenance status.','directory.html','', extra=jsonld({'@context':'https://schema.org','@type':'ItemList','name':'Open-source medical AI tools','numberOfItems':len(tools),'itemListElement':[{'@type':'ListItem','position':i+1,'name':t['name'],'url':f"{SITE_URL}/tools/{t['slug']}.html"} for i,t in enumerate(tools)]}))+'''
<section><div class="wrap"><h1 class="h2">Open-source medical AI directory</h1><p class="note">STATUS: “Maintained” = repo updated within 12 months of the '''+SNAP_TXT+''' snapshot. COMM: “Permissive” = permissive open-source license; “Copyleft” = GPL/AGPL obligations; “Non-commercial” = license forbids commercial use; “Verify” = custom terms or separate weight terms. Always read the license yourself. Imaging datasets are listed on the <a href="datasets.html">DICOM datasets</a> page.</p>
<div class="filters"><input id="q" type="search" placeholder="Search tools, maintainers…" aria-label="Search"><select id="group" aria-label="Category"><option value="">All categories</option></select><select id="modality" aria-label="Modality"><option value="">All modalities</option></select><select id="commercial" aria-label="License type"><option value="">Any license type</option></select><select id="maintenance" aria-label="Status"><option value="">Any status</option></select><button class="btn ghost small" id="reset" type="button">Reset</button></div>
<div class="count" id="count" aria-live="polite">'''+f'{len(tools)} of {len(tools)} tools'+'''</div><div class="grid" id="list">'''+''.join(card_html(t,i) for i,t in enumerate(tools))+'''</div><p id="empty" class="note" hidden>No tools match these filters.</p></div></section>'''+foot('','<script>initDirectory()</script>')
    pages['suggest.html']=head('Suggest a tool · Hounsfield Lab','Suggest an open-source medical AI tool or a correction for the Hounsfield Lab directory.','suggest.html','')+'''
<section><div class="wrap prose"><h1 class="h2">Suggest a tool or a correction</h1><p>Know an open-source or downloadable medical AI tool we should list, or spotted an error? Tell us. Every submission is reviewed by hand before anything is published. For an imaging dataset, use the <a href="datasets.html#suggest">dataset form</a>.</p>
<form class="live-form stack" action="'''+FORM_ENDPOINT+'''" method="post" data-endpoint="'''+FORM_ENDPOINT+'''"><input type="hidden" name="_subject" value="Hounsfield Lab: tool suggestion"><input type="hidden" name="form" value="suggest"><div class="hp" aria-hidden="true"><label>Leave this empty<input type="text" name="_honey" tabindex="-1" autocomplete="off"></label></div><input type="hidden" name="_captcha" value="false"><input type="hidden" name="_template" value="table"><label>Tool name<input type="text" name="tool_name" required maxlength="200"></label><label>Repository or download URL<input name="url" type="url" placeholder="https://github.com/…" required></label><label>Type<select name="kind"><option>New tool</option><option>Correction to a listing</option></select></label><label>Why it’s useful / what to fix<textarea name="notes" rows="5" maxlength="4000"></textarea></label><label>Your email (optional, only if you want a reply)<input name="email" type="email" autocomplete="email"></label><button class="btn" type="submit">Submit suggestion</button><p class="note">By submitting you agree to our <a href="privacy.html">privacy notice</a>.</p><p class="note formmsg" role="status" aria-live="polite"></p></form></div></section>'''+foot('')
    pages['contact.html']=head('Contact · Hounsfield Lab','Contact Hounsfield Lab with questions, corrections, partnership ideas or feedback about the open-source medical AI tool and dataset directory.','contact.html','')+'''
<section><div class="wrap prose"><h1 class="h2">Contact</h1><p>Questions, feedback, or partnership ideas? Send a message and we’ll get back to you if you include an email address. To suggest a tool, use the <a href="suggest.html">suggestion form</a>. To suggest a dataset, use the <a href="datasets.html#suggest">dataset form</a>.</p>
<form class="live-form stack" action="'''+FORM_ENDPOINT+'''" method="post" data-endpoint="'''+FORM_ENDPOINT+'''"><input type="hidden" name="_subject" value="Hounsfield Lab: contact message"><input type="hidden" name="form" value="contact"><div class="hp" aria-hidden="true"><label>Leave this empty<input type="text" name="_honey" tabindex="-1" autocomplete="off"></label></div><input type="hidden" name="_captcha" value="false"><input type="hidden" name="_template" value="table">
<label>Name<input type="text" name="name" autocomplete="name" required maxlength="200"></label><label>Email<input name="email" type="email" autocomplete="email" required></label><label>Message<textarea name="message" rows="6" required maxlength="5000"></textarea></label>
<button class="btn" type="submit">Send message</button><p class="note">By submitting you agree to our <a href="privacy.html">privacy notice</a>.</p><p class="note formmsg" role="status" aria-live="polite"></p></form></div></section>'''+foot('')
    pages['newsletter.html']=head('Newsletter: the weekly open medical AI briefing · Hounsfield Lab','A free weekly email on new open-source medical AI models, weights and tools, curated by a practicing neuroradiologist.','newsletter.html','')+f'''
<section><div class="wrap prose"><div class="curator">Curated by a practicing neuroradiologist</div><h1 class="h2">The weekly open medical AI briefing</h1>
<p class="lead">A free, five-minute email for people building medical AI with open-source tools.</p>
<h2 class="h3">What you get each week</h2><ul class="links"><li><strong>New and notable releases:</strong> open models, weights, toolkits and infrastructure worth knowing, with links to the source.</li>
<li><strong>Directory updates:</strong> tools added to Hounsfield Lab, plus changes in license or maintenance status.</li><li><strong>One practical pick:</strong> a tool, workflow or pipeline tip with a short, honest verdict.</li>
<li><strong>Clear labels:</strong> any sponsored content is always marked as sponsored.</li></ul>
<div class="signup" style="margin-top:24px"><h2>Subscribe</h2>{bh_embed()}<p class="note">Unsubscribe anytime with the link in every email. See our <a href="privacy.html">privacy notice</a>.</p></div>
<p style="margin-top:22px"><a class="btn ghost" href="{ARCHIVE_URL}" target="_blank" rel="noopener">Browse the archive →</a></p></div></section>'''+foot('')
    pages['privacy.html']=head('Privacy · Hounsfield Lab','How Hounsfield Lab handles information you submit through its contact, suggestion and newsletter forms, and which third-party services process it.','privacy.html','')+'''
<section><div class="wrap prose"><h1 class="h2">Privacy notice</h1><p class="note">Last updated: October 18, 2026 (dataset directory added)</p>
<h2 class="h3">What we collect</h2><p>This site has no accounts or analytics of its own. We only receive information you choose to send through the Contact, Suggest a tool, or Suggest a dataset forms, or the newsletter signup: the fields you fill in (for example name, email, message, tool or dataset name, and URL).</p>
<h2 class="h3">How forms are processed</h2><p>Form submissions are delivered to us by email through <a href="https://formsubmit.co/" target="_blank" rel="noopener">FormSubmit</a>, a third-party form service, which processes the data to deliver it. The site itself is hosted on GitHub Pages, which may log basic technical data such as IP addresses for security and operations.</p>
<h2 class="h3">How we use it</h2><p>We use form submissions only to review tool and dataset suggestions and corrections and to reply to you. A dataset suggestion is not published automatically. We don’t sell your information, and a form submission never adds you to the newsletter.</p>\n<h2 class="h3">Newsletter</h2><p>Newsletter signups are handled by <a href=\"https://www.beehiiv.com/\" target=\"_blank\" rel=\"noopener\">beehiiv</a>, which stores your email address and sends the newsletter on our behalf. The signup form is loaded from beehiiv. See <a href=\"https://www.beehiiv.com/privacy\" target=\"_blank\" rel=\"noopener\">beehiiv’s privacy policy</a>. You can unsubscribe anytime using the link at the bottom of every issue.</p>
<h2 class="h3">Retention and your choices</h2><p>We keep submissions only as long as needed to handle them. To ask us to delete something you sent, use the <a href="contact.html">contact form</a>.</p>
<h2 class="h3">Please don’t send patient information</h2><p>These forms aren’t for protected health information, images, or any identifiable patient data. Don’t send DICOM files.</p></div></section>'''+foot('')
    for p in ['pipeline-orthanc-mercure.html','about.html']:
        src=(ROOT/'content'/p).read_text()
        title,desc=src.split('\n',2)[:2]
        pages[p]=head(title,desc,p,'')+src.split('\n',2)[2].replace('{{SNAPSHOT}}',SNAP_TXT)+foot('')
    pub_ds=[{**{k:d[k] for k in DATASET_FIELDS}, "slug":d["slug"]} for d in datasets]
    json.dump({"areas":AREAS,"datasets":pub_ds}, open(ROOT/'data'/'datasets.json','w'), indent=1, ensure_ascii=False)
    pages['datasets.html']=datasets_page(datasets)
    PAGE_TYPES={'about.html':('AboutPage','About'),'contact.html':('ContactPage','Contact'),'suggest.html':('WebPage','Suggest a tool'),
        'newsletter.html':('WebPage','Newsletter'),'privacy.html':('WebPage','Privacy'),'pipeline-orthanc-mercure.html':('TechArticle','Pipeline guide')}
    for p,(typ,crumb) in PAGE_TYPES.items():
        t_=re.search(r'<title>(.*?)</title>',pages[p]).group(1); d_=re.search(r'<meta name="description" content="(.*?)"',pages[p]).group(1)
        ld={'@context':'https://schema.org','@type':typ,'name':html.unescape(t_).replace(SUFFIX,''),'description':html.unescape(d_),'url':f'{SITE_URL}/{p}',
            'isPartOf':{'@type':'WebSite','name':'Hounsfield Lab','url':SITE_URL+'/'}}
        if typ=='TechArticle': ld['headline']=ld['name']
        bc={'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'Home','item':SITE_URL+'/'},
            {'@type':'ListItem','position':2,'name':crumb,'item':f'{SITE_URL}/{p}'}]}
        pages[p]=pages[p].replace('<link rel="stylesheet"',jsonld(ld)+jsonld(bc)+'<link rel="stylesheet"',1)
    for p,h in pages.items(): emit(p,h)
    urls=['','directory.html','datasets.html','pipeline-orthanc-mercure.html','about.html','suggest.html','contact.html','privacy.html','newsletter.html']+[f'tools/{t["slug"]}.html' for t in tools]+[f'datasets/{d["slug"]}.html' for d in sorted(datasets,key=lambda d:d["name"].lower())]
    (ROOT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>{SITE_URL}/{u}</loc><lastmod>{LASTMOD[u]}</lastmod></url>\n' for u in urls)+'</urlset>\n')
    bots=["GPTBot","OAI-SearchBot","ChatGPT-User","ClaudeBot","Claude-User","Claude-SearchBot","anthropic-ai","PerplexityBot","Perplexity-User","Google-Extended","Googlebot","Bingbot","Applebot","Applebot-Extended","CCBot","Amazonbot","DuckAssistBot","Meta-ExternalAgent","MistralAI-User","cohere-ai"]
    (ROOT/'robots.txt').write_text("".join(f"User-agent: {b}\nAllow: /\n\n" for b in bots)+f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n")
    write_llms(tools, datasets)
    print(len(tools),'tools', counts, len(datasets), 'datasets')
main()
