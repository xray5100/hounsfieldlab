#!/usr/bin/env python3
"""Static site generator for Hounsfield Lab. Run: python3 build.py"""
import csv, json, re, html
from urllib.parse import quote
from datetime import date
from pathlib import Path

SITE_URL = "https://hounsfieldlab.com"
BEEHIIV_FORM = "ac9b5485-be11-4149-9a23-58c583248e6a"
ARCHIVE_URL = "https://hounsfieldlab.beehiiv.com"
FORM_ENDPOINT = "https://formsubmit.co/ajax/676d89d9edc7b8fe301931545b3a4a15"  # FormSubmit alias (activated)
SNAPSHOT = date(2026, 10, 13)
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
}

SPDX = {"Apache-2.0","MIT","BSD-3-Clause","GPL-2.0","GPL-3.0","AGPL-3.0","ECL-2.0"}
def lic_url(l):
    k=l.split(' ')[0]
    if k in SPDX: return f"https://spdx.org/licenses/{k}.html"
    if l.startswith("CC BY-NC-ND 4.0"): return "https://creativecommons.org/licenses/by-nc-nd/4.0/"
    return None

def jsonld(obj): return '<script type="application/ld+json">'+json.dumps(obj,ensure_ascii=False).replace("</","<\\/")+'</script>'

def card_html(t,i,prefix=""):
    return (f'<article class="card" data-i="{i}"><h2 class="ct"><a href="{prefix}tools/{t["slug"]}.html">{E(t["name"])}</a></h2><p>{E(t["what_it_does"])}</p>{badges(t)}'
            f'<button class="qv" type="button">Quick view</button></article>')

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

def head(title, desc, path, root, og_img="assets/og.png", extra=""):
    url=f"{SITE_URL}/{path}"
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{url}">
<meta property="og:type" content="website"><meta property="og:site_name" content="Hounsfield Lab"><meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{url}"><meta property="og:image" content="{SITE_URL}/{og_img}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{E(title)}"><meta name="twitter:description" content="{E(desc)}"><meta name="twitter:image" content="{SITE_URL}/{og_img}">
<link rel="icon" href="{root}assets/logo.svg" type="image/svg+xml"><link rel="icon" href="{root}assets/favicon-32.png" sizes="32x32" type="image/png"><link rel="apple-touch-icon" href="{root}assets/apple-touch-icon.png"><meta name="theme-color" content="#0b2e6b">{extra}<link rel="stylesheet" href="{root}assets/style.css"></head><body data-root="{root}">
<header><div class="wrap nav"><a class="brand" href="{root}index.html"><img src="{root}assets/logo.svg" alt="" width="32" height="32">Hounsfield Lab</a>
<button class="menu" aria-label="Menu" onclick="document.body.classList.toggle('navopen')">☰</button>
<nav><a href="{root}directory.html">Directory</a><a href="{root}pipeline-orthanc-mercure.html">Pipeline guide</a><a href="{root}suggest.html">Suggest a tool</a><a href="{root}about.html">About</a><a href="{root}contact.html">Contact</a><a href="{root}newsletter.html">Newsletter</a></nav></div></header><main>'''

def foot(root, script=""):
    return f'''</main><footer><div class="wrap">Hounsfield Lab · Open-source medical AI, curated by a practicing neuroradiologist. Listings are for research and development reference: not medical advice, not an endorsement, not legal advice on licensing, and not a statement of regulatory clearance. Repository data snapshot: Oct 13, 2026. · <a href="{root}newsletter.html">Newsletter</a> · <a href="{root}privacy.html">Privacy</a> · <a href="{root}contact.html">Contact</a></div></footer>
<div class="modal" id="modal" role="dialog" aria-modal="true"><div class="box"><button class="close" aria-label="Close">×</button><div class="content"></div></div></div>
<script src="{root}assets/app.js"></script>{script}</body></html>'''

def bh_embed():
    return f'<div class="bh-embed"><script async src="https://subscribe-forms.beehiiv.com/v3/loader.js" data-beehiiv-form="{BEEHIIV_FORM}"></script></div>'

def newsletter(root):
    return f'''<section id="newsletter"><div class="wrap"><div class="signup"><h2>The weekly open medical AI briefing</h2><p>New open models, weights and tools worth knowing, in five minutes. Free, and you can unsubscribe anytime.</p>
{bh_embed()}<p class="note">Read past issues in the <a href="{ARCHIVE_URL}" target="_blank" rel="noopener">archive</a> · <a href="{root}newsletter.html">What you get</a> · <a href="{root}privacy.html">Privacy</a></p></div></div></section>'''

def badges(t):
    m='ok' if t['maintenance']=='Maintained' else 'warn'
    c={'Permissive':'ok','Verify':'warn'}.get(t['commercial'],'bad')
    return (f'<div class="labs"><span class="lab"><b>LIC</b><span>{E(t["license"])}</span></span><span class="lab"><b>UPD</b><span>{E(t["last_push_utc"])}</span></span>'
            f'<span class="lab {m}"><b>STATUS</b><span>{t["maintenance"]}</span></span><span class="lab {c}"><b>COMM</b><span>{E(t["commercial"])}</span></span></div>')

def tool_page(t, tools):
    root="../"; desc=f'{t["name"]}: {t["what_it_does"]}. License {t["license"]}, last updated {t["last_push_utc"]}.'
    links="".join(f'<li><a href="{E(u)}" target="_blank" rel="noopener">{E(u.replace("https://",""))}</a></li>' for u in t['urls'])
    note=f'<p class="note"><strong>License review:</strong> {E(t["license_note"])}</p>' if t['license_note'] else ''
    warn='' if t['commercial']=='Permissive' else '<p class="note">Commercial use: read the project’s license (and any model-weight terms) yourself before relying on it. This isn’t legal advice.</p>'
    rel=[x for x in tools if x['group']==t['group'] and x is not t][:6]
    related="".join(f'<li><a href="{x["slug"]}.html">{E(x["name"])}</a>: {E(x["what_it_does"])}</li>' for x in rel)
    repo=next((u for u in t['urls'] if 'github.com' in u), t['urls'][0])
    ld={"@context":"https://schema.org","@type":"SoftwareSourceCode","name":t["name"],"description":t["what_it_does"],"codeRepository":repo,
        "url":f"{SITE_URL}/tools/{t['slug']}.html","dateModified":t["last_push_utc"],"applicationCategory":t["group"],"keywords":[t["category"],t["modality_specialty"]],
        "license":lic_url(t["license"]) or t["license"],"maintainer":{"@type":"Organization","name":t["maintainer"]},"sameAs":t["urls"]}
    bc={"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
        {"@type":"ListItem","position":1,"name":"Directory","item":f"{SITE_URL}/directory.html"},
        {"@type":"ListItem","position":2,"name":t["group"],"item":f"{SITE_URL}/directory.html?group={quote(t['group'])}"},
        {"@type":"ListItem","position":3,"name":t["name"],"item":f"{SITE_URL}/tools/{t['slug']}.html"}]}
    title=f'{t["name"]}: {t["category"]} for {t["modality_specialty"]} · Hounsfield Lab'
    return head(title, desc[:300], f'tools/{t["slug"]}.html', root, extra=jsonld(ld)+jsonld(bc))+f'''
<section><div class="wrap prose"><nav class="crumb" aria-label="Breadcrumb"><a href="../directory.html">Directory</a> › <a href="../directory.html?group={quote(t["group"])}">{E(t["group"])}</a> › <span aria-current="page">{E(t["name"])}</span></nav>
<h1 class="tt">{E(t["name"])}</h1><p class="lead">{E(t["what_it_does"])}</p>{badges(t)}
<dl style="margin-top:22px"><dt>Group</dt><dd>{E(t["group"])}</dd><dt>Type</dt><dd>{E(t["category"])}</dd><dt>Modality</dt><dd>{E(t["modality_specialty"])}</dd><dt>Maintainer</dt><dd>{E(t["maintainer"])}</dd><dt>License</dt><dd>{E(t["license"])}</dd><dt>Last update</dt><dd>{E(t["last_push_utc"])} (last repository push, UTC)</dd></dl>
<h2 class="h3">Links</h2><ul class="links">{links}</ul>{note}{warn}
<h2 class="h3">Related tools in {E(t["group"])}</h2><ul class="links">{related}</ul>
<p><a class="btn ghost" href="../directory.html">← Back to directory</a></p></div></section>'''+foot(root)

def write_llms(tools):
    intro=(f"# Hounsfield Lab\n\n> A directory of open-source and downloadable software for medical AI development, curated by a practicing neuroradiologist. "
           f"Radiology-first, plus pathology, clinical NLP and EHR tooling. {len(tools)} tools. Repository data snapshot: {SNAPSHOT}.\n\n"
           "Badges: LIC = license (license files reviewed by hand where GitHub could not detect them); UPD = last repository push (UTC); "
           "STATUS = Maintained if updated within 12 months of the snapshot, else Stale; COMM = Permissive, Copyleft (GPL/AGPL), Non-commercial, or Verify (custom terms or separate model-weight terms). Not legal or medical advice.\n\n")
    pages=("## Pages\n\n"+f"- [Directory]({SITE_URL}/directory.html): filterable list of all tools\n- [Pipeline guide]({SITE_URL}/pipeline-orthanc-mercure.html): Orthanc → mercure → TotalSegmentator → OHIF\n"
           f"- [About]({SITE_URL}/about.html): curation method\n- [Full catalog for LLMs]({SITE_URL}/llms-full.txt)\n- [Catalog JSON]({SITE_URL}/data/catalog.json)\n\n")
    short=pages+"".join(f"## {g}\n\n"+"".join(f"- [{t['name']}]({SITE_URL}/tools/{t['slug']}.html): {t['what_it_does']} ({t['license']}; {t['maintenance']})\n" for t in tools if t['group']==g)+"\n" for g in GROUPS)
    (ROOT/'llms.txt').write_text(intro+short)
    full="".join(f"## {g}\n\n"+"".join(
        f"### {t['name']}\n- What it does: {t['what_it_does']}\n- Type: {t['category']}\n- Modality/specialty: {t['modality_specialty']}\n- Maintainer: {t['maintainer']}\n"
        f"- License: {t['license']}\n- Commercial use: {t['commercial']}\n"+(f"- License note: {t['license_note']}\n" if t['license_note'] else "")+
        f"- Last repository update: {t['last_push_utc']} ({t['maintenance']})\n- Links: {', '.join(t['urls'])}\n- Page: {SITE_URL}/tools/{t['slug']}.html\n\n" for t in tools if t['group']==g) for g in GROUPS)
    (ROOT/'llms-full.txt').write_text(intro+pages+full)

def main():
    tools=load(); (ROOT/'data').mkdir(exist_ok=True); (ROOT/'tools').mkdir(exist_ok=True)
    pub=[{k:t[k] for k in ('name','slug','group','category','modality_specialty','what_it_does','license','license_note','commercial','maintenance','last_push_utc','maintainer','urls')} for t in tools]
    json.dump({"groups":list(GROUPS),"tools":pub},open(ROOT/'data/catalog.json','w'),indent=1)
    for t in tools: (ROOT/f'tools/{t["slug"]}.html').write_text(tool_page(t,tools))
    counts={g:sum(t['group']==g for t in tools) for g in GROUPS}
    pillar=next(t for t in tools if t['slug']=='pillar-0')
    tiles="".join(f'<a class="card tile" href="directory.html?group={quote(g)}"><h3>{E(g)}</h3><span class="n">n = {n}</span></a>' for g,n in counts.items())
    pages={}
    pages['index.html']=head('Hounsfield Lab · Open-source medical AI directory','A neuroradiologist-curated directory of open-source medical AI models, toolkits and infrastructure, with license, update and maintenance status at a glance.','', '', extra=jsonld({'@context':'https://schema.org','@type':'WebSite','name':'Hounsfield Lab','url':SITE_URL+'/','description':'Open-source medical AI directory, curated by a practicing neuroradiologist.','potentialAction':{'@type':'SearchAction','target':{'@type':'EntryPoint','urlTemplate':SITE_URL+'/directory.html?q={search_term_string}'},'query-input':'required name=search_term_string'}}))+f'''
<div class="hero"><div class="wrap"><div class="curator">Curated by a practicing neuroradiologist</div><h1>Open-source medical AI, measured like a lab value.</h1><p>A clinician-curated directory of downloadable models, toolkits and infrastructure for building medical AI, with license, update and maintenance status at a glance.</p><p class="cta"><a class="btn" href="directory.html">Browse {len(tools)} tools</a> <a class="btn ghost" href="pipeline-orthanc-mercure.html">See a pipeline guide</a></p></div></div>
<section><div class="wrap"><h2>Featured: Pillar-0</h2><div class="feature"><div><p><strong>An open radiology foundation model from YalaLab.</strong> Pretrained on 42,990 abdomen-pelvis CTs, 86,411 chest CTs, 14,348 head CTs and 11,543 breast MRIs, with RATE, an LLM-based framework that extracts labels for 366 radiologic findings from reports. The authors release code, weights and evaluation tools.</p><p><a href="https://yalalab.github.io/pillar-0/" target="_blank" rel="noopener">Project page</a> · <a href="https://arxiv.org/abs/2511.17803" target="_blank" rel="noopener">Paper</a> · <a href="https://huggingface.co/collections/YalaLab/pillar-0" target="_blank" rel="noopener">Weights</a></p></div><div>{badges(pillar)}<p style="margin-top:16px"><a class="btn" href="tools/pillar-0.html">View details</a></p></div></div></div></section>
<section><div class="wrap"><h2>Browse by category</h2><div class="grid cats">{tiles}</div></div></section>'''+newsletter('')+foot('')
    pages['directory.html']=head('Open-source medical AI tools directory: filter by license, modality and status · Hounsfield Lab',f'Filter {len(tools)} open-source medical AI tools by category, modality, license and maintenance status.','directory.html','', extra=jsonld({'@context':'https://schema.org','@type':'ItemList','name':'Open-source medical AI tools','numberOfItems':len(tools),'itemListElement':[{'@type':'ListItem','position':i+1,'name':t['name'],'url':f"{SITE_URL}/tools/{t['slug']}.html"} for i,t in enumerate(tools)]}))+'''
<section><div class="wrap"><h1 class="h2">Open-source medical AI directory</h1><p class="note">STATUS: “Maintained” = repo updated within 12 months of the Oct 13, 2026 snapshot. COMM: “Permissive” = permissive open-source license; “Copyleft” = GPL/AGPL obligations; “Non-commercial” = license forbids commercial use; “Verify” = custom terms or separate weight terms. Always read the license yourself.</p>
<div class="filters"><input id="q" type="search" placeholder="Search tools, maintainers…" aria-label="Search"><select id="group" aria-label="Category"><option value="">All categories</option></select><select id="modality" aria-label="Modality"><option value="">All modalities</option></select><select id="commercial" aria-label="License type"><option value="">Any license type</option></select><select id="maintenance" aria-label="Status"><option value="">Any status</option></select><button class="btn ghost small" id="reset" type="button">Reset</button></div>
<div class="count" id="count" aria-live="polite">'+f'{len(tools)} of {len(tools)} tools'+'</div><div class="grid" id="list">'+''.join(card_html(t,i) for i,t in enumerate(tools))+'</div><p id="empty" class="note" hidden>No tools match these filters.</p></div></section>'''+foot('','<script>initDirectory()</script>')
    pages['suggest.html']=head('Suggest a tool · Hounsfield Lab','Suggest an open-source medical AI tool or a correction for the Hounsfield Lab directory.','suggest.html','')+'''
<section><div class="wrap prose"><h1 class="h2">Suggest a tool or a correction</h1><p>Know an open-source or downloadable medical AI tool we should list, or spotted an error? Tell us. Every submission is reviewed by hand before anything is published.</p>
<form class="live-form stack" action="'+FORM_ENDPOINT+'" method="post" data-endpoint="'+FORM_ENDPOINT+'"><input type="hidden" name="_subject" value="Hounsfield Lab: tool suggestion"><input type="hidden" name="form" value="suggest"><div class="hp" aria-hidden="true"><label>Leave this empty<input name="_honey" tabindex="-1" autocomplete="off"></label></div><input type="hidden" name="_captcha" value="false"><input type="hidden" name="_template" value="table"><label>Tool name<input name="tool_name" required maxlength="200"></label><label>Repository or download URL<input name="url" type="url" placeholder="https://github.com/…" required></label><label>Type<select name="kind"><option>New tool</option><option>Correction to a listing</option></select></label><label>Why it’s useful / what to fix<textarea name="notes" rows="5" maxlength="4000"></textarea></label><label>Your email (optional, only if you want a reply)<input name="email" type="email"></label><button class="btn" type="submit">Submit suggestion</button><p class="note">By submitting you agree to our <a href="privacy.html">privacy notice</a>.</p><p class="note formmsg" role="status" aria-live="polite"></p></form></div></section>'''+foot('')
    pages['contact.html']=head('Contact · Hounsfield Lab','Contact Hounsfield Lab with questions, partnership ideas or feedback.','contact.html','')+'''
<section><div class="wrap prose"><h1 class="h2">Contact</h1><p>Questions, feedback, or partnership ideas? Send a message and we’ll get back to you if you include an email address. To suggest a tool, use the <a href="suggest.html">suggestion form</a>.</p>
<form class="live-form stack" action="'''+FORM_ENDPOINT+'''" method="post" data-endpoint="'''+FORM_ENDPOINT+'''"><input type="hidden" name="_subject" value="Hounsfield Lab: contact message"><input type="hidden" name="form" value="contact"><div class="hp" aria-hidden="true"><label>Leave this empty<input name="_honey" tabindex="-1" autocomplete="off"></label></div><input type="hidden" name="_captcha" value="false"><input type="hidden" name="_template" value="table">
<label>Name<input name="name" required maxlength="200"></label><label>Email<input name="email" type="email" required></label><label>Message<textarea name="message" rows="6" required maxlength="5000"></textarea></label>
<button class="btn" type="submit">Send message</button><p class="note">By submitting you agree to our <a href="privacy.html">privacy notice</a>.</p><p class="note formmsg" role="status" aria-live="polite"></p></form></div></section>'''+foot('')
    pages['newsletter.html']=head('Newsletter: the weekly open medical AI briefing · Hounsfield Lab','A free weekly email on new open-source medical AI models, weights and tools, curated by a practicing neuroradiologist.','newsletter.html','')+f'''
<section><div class="wrap prose"><div class="curator">Curated by a practicing neuroradiologist</div><h1 class="h2">The weekly open medical AI briefing</h1>
<p class="lead">A free, five-minute email for people building medical AI with open-source tools.</p>
<h2 class="h3">What you get each week</h2><ul class="links"><li><strong>New and notable releases:</strong> open models, weights, toolkits and infrastructure worth knowing, with links to the source.</li>
<li><strong>Directory updates:</strong> tools added to Hounsfield Lab, plus changes in license or maintenance status.</li><li><strong>One practical pick:</strong> a tool, workflow or pipeline tip with a short, honest verdict.</li>
<li><strong>Clear labels:</strong> any sponsored content is always marked as sponsored.</li></ul>
<div class="signup" style="margin-top:24px"><h2>Subscribe</h2>{bh_embed()}<p class="note">Unsubscribe anytime with the link in every email. See our <a href="privacy.html">privacy notice</a>.</p></div>
<p style="margin-top:22px"><a class="btn ghost" href="{ARCHIVE_URL}" target="_blank" rel="noopener">Browse the archive →</a></p></div></section>'''+foot('')
    pages['privacy.html']=head('Privacy · Hounsfield Lab','How Hounsfield Lab handles information you submit through its forms.','privacy.html','')+'''
<section><div class="wrap prose"><h1 class="h2">Privacy notice</h1><p class="note">Last updated: October 14, 2026 (newsletter added)</p>
<h3>What we collect</h3><p>This site has no accounts or analytics of its own. We only receive information you choose to send through the Contact or Suggest a tool forms or the newsletter signup: the fields you fill in (for example name, email, message, tool name and URL).</p>
<h3>How forms are processed</h3><p>Form submissions are delivered to us by email through <a href="https://formsubmit.co/" target="_blank" rel="noopener">FormSubmit</a>, a third-party form service, which processes the data to deliver it. The site itself is hosted on GitHub Pages, which may log basic technical data such as IP addresses for security and operations.</p>
<h3>How we use it</h3><p>We use form submissions only to review tool suggestions and corrections and to reply to you. We don’t sell your information, and a form submission never adds you to the newsletter.</p>\n<h3>Newsletter</h3><p>Newsletter signups are handled by <a href=\"https://www.beehiiv.com/\" target=\"_blank\" rel=\"noopener\">beehiiv</a>, which stores your email address and sends the newsletter on our behalf. The signup form is loaded from beehiiv. See <a href=\"https://www.beehiiv.com/privacy\" target=\"_blank\" rel=\"noopener\">beehiiv’s privacy policy</a>. You can unsubscribe anytime using the link at the bottom of every issue.</p>
<h3>Retention and your choices</h3><p>We keep submissions only as long as needed to handle them. To ask us to delete something you sent, use the <a href="contact.html">contact form</a>.</p>
<h3>Please don’t send patient information</h3><p>These forms aren’t for protected health information or any identifiable patient data.</p></div></section>'''+foot('')
    for p in ['pipeline-orthanc-mercure.html','about.html']:
        src=(ROOT/'content'/p).read_text()
        title,desc=src.split('\n',2)[:2]
        pages[p]=head(title,desc,p,'')+src.split('\n',2)[2]+foot('')
    for p,h in pages.items(): (ROOT/p).write_text(h)
    urls=['','directory.html','pipeline-orthanc-mercure.html','about.html','suggest.html','contact.html','privacy.html','newsletter.html']+[f'tools/{t["slug"]}.html' for t in tools]
    (ROOT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'<url><loc>{SITE_URL}/{u}</loc><lastmod>{SNAPSHOT}</lastmod></url>\n' for u in urls)+'</urlset>\n')
    bots=["GPTBot","OAI-SearchBot","ChatGPT-User","ClaudeBot","Claude-User","Claude-SearchBot","anthropic-ai","PerplexityBot","Perplexity-User","Google-Extended","Googlebot","Bingbot","Applebot","Applebot-Extended","CCBot"]
    (ROOT/'robots.txt').write_text("".join(f"User-agent: {b}\nAllow: /\n\n" for b in bots)+f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n")
    write_llms(tools)
    print(len(tools),'tools', counts)
main()
