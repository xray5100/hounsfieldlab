const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const ROOT=document.body.dataset.root||'';
function badges(t){const m=t.maintenance==='Maintained'?'ok':'warn',c={Permissive:'ok',Verify:'warn'}[t.commercial]||'bad';
return `<div class="labs"><span class="lab"><b>LIC</b><span>${esc(t.license)}</span></span><span class="lab"><b>UPD</b><span>${esc(t.last_push_utc)}</span></span><span class="lab ${m}"><b>STATUS</b><span>${t.maintenance}</span></span><span class="lab ${c}"><b>COMM</b><span>${esc(t.commercial)}</span></span></div>`}
function card(t,i){return `<article class="card" data-i="${i}" tabindex="0" role="button" aria-label="Details for ${esc(t.name)}"><h3><a href="tools/${t.slug}.html">${esc(t.name)}</a></h3><p>${esc(t.what_it_does)}</p>${badges(t)}</article>`}
let lastFocus=null;
function openModal(t){const m=document.getElementById('modal');lastFocus=document.activeElement;
m.querySelector('.content').innerHTML=`<h2>${esc(t.name)}</h2><p>${esc(t.what_it_does)}</p>${badges(t)}<dl style="margin-top:16px"><dt>Category</dt><dd>${esc(t.group)}</dd><dt>Modality</dt><dd>${esc(t.modality_specialty)}</dd><dt>Maintainer</dt><dd>${esc(t.maintainer)}</dd><dt>License</dt><dd>${esc(t.license)}</dd><dt>Last update</dt><dd>${esc(t.last_push_utc)} (last repo push, UTC)</dd><dt>Links</dt><dd>${t.urls.map(u=>`<a href="${esc(u)}" target="_blank" rel="noopener">${esc(u.replace('https://',''))}</a>`).join('<br>')}</dd></dl>${t.license_note?`<p class="note"><strong>License review:</strong> ${esc(t.license_note)}</p>`:''}<p><a class="btn" href="tools/${t.slug}.html">Full page →</a></p>`;
m.classList.add('open');document.body.classList.add('noscroll');m.querySelector('.close').focus()}
function closeModal(){const m=document.getElementById('modal');if(!m.classList.contains('open'))return;m.classList.remove('open');document.body.classList.remove('noscroll');lastFocus&&lastFocus.focus()}
document.addEventListener('click',e=>{if(e.target.matches('.modal,.close'))closeModal()});
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal()});
document.querySelectorAll('form[data-placeholder]').forEach(f=>f.addEventListener('submit',e=>{e.preventDefault();f.querySelector('.formmsg').textContent='Thanks! This form isn’t connected yet, so nothing was sent or stored.'}));
async function initDirectory(){const {groups,tools:d}=await (await fetch('data/catalog.json')).json();
const keys=['group','modality','commercial','maintenance'],field={group:'group',modality:'modality_specialty',commercial:'commercial',maintenance:'maintenance'};
const P=new URLSearchParams(location.search),f={q:P.get('q')||''};keys.forEach(k=>f[k]=P.get(k)||'');
keys.forEach(k=>{const s=document.getElementById(k);const vals=k==='group'?groups:[...new Set(d.map(t=>t[field[k]]))].sort();vals.forEach(v=>s.add(new Option(v,v)));if(!vals.includes(f[k]))f[k]='';s.value=f[k];s.onchange=()=>{f[k]=s.value;render()}});
const q=document.getElementById('q');q.value=f.q;q.oninput=()=>{f.q=q.value;render()};
document.getElementById('reset').onclick=()=>{keys.forEach(k=>{f[k]='';document.getElementById(k).value=''});f.q='';q.value='';render()};
const list=document.getElementById('list');
list.addEventListener('click',e=>{if(e.target.closest('a'))return;const c=e.target.closest('.card[data-i]');if(c)openModal(d[c.dataset.i])});
list.addEventListener('keydown',e=>{const c=e.target.closest('.card[data-i]');if(c&&e.target===c&&(e.key==='Enter'||e.key===' ')){e.preventDefault();openModal(d[c.dataset.i])}});
function render(){const ql=f.q.trim().toLowerCase();const r=d.map((t,i)=>[t,i]).filter(([t])=>keys.every(k=>!f[k]||t[field[k]]===f[k])&&(!ql||[t.name,t.what_it_does,t.maintainer,t.modality_specialty,t.category].join(' ').toLowerCase().includes(ql)));
document.getElementById('count').textContent=`${r.length} of ${d.length} tools`;list.innerHTML=r.map(([t,i])=>card(t,i)).join('');document.getElementById('empty').hidden=r.length>0;
const u=new URLSearchParams();keys.forEach(k=>f[k]&&u.set(k,f[k]));f.q&&u.set('q',f.q);history.replaceState(null,'',u.toString()?'?'+u:location.pathname)}
render()}
