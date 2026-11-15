from __future__ import annotations
"""Renders the owner-only review page: one self-contained HTML file (no server, $0). Edits made on the page are previewed
with the same capacity-preserving rules as review.apply_edits, kept in this browser, and exported as JSON to append to
reviews/{season}.json. Python recomputes everything from that file, so the page is a convenience, not the record."""
import json
from .review import REASONS

def render(rv: dict) -> str:
    data = json.dumps({k: v for k, v in rv.items() if k != "teams_by_key"}).replace("</", "<\\/")
    return TEMPLATE.replace("__DATA__", data).replace("__REASONS__", json.dumps(REASONS)).replace("__TITLE__", f"Bracket Review {rv['season']}")

TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title><meta name="robots" content="noindex,nofollow">
<style>
:root{--bg:#f7f7f5;--card:#fff;--ink:#1c1c1a;--muted:#6b6b66;--line:#e2e1dc;--acc:#2f5fd0;--warn:#b5651d;--good:#2e7d4f;--bad:#b23b3b;--chip:#eef1f8}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#141413;--card:#1e1e1c;--ink:#ecebe6;--muted:#9a998f;--line:#33322e;--acc:#7aa2ff;--warn:#e0a060;--good:#6cc08d;--bad:#e07a7a;--chip:#25283a}}
:root[data-theme="dark"]{--bg:#141413;--card:#1e1e1c;--ink:#ecebe6;--muted:#9a998f;--line:#33322e;--acc:#7aa2ff;--warn:#e0a060;--good:#6cc08d;--bad:#e07a7a;--chip:#25283a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,-apple-system,Segoe UI,sans-serif}
header{padding:14px 16px;border-bottom:1px solid var(--line);display:flex;flex-wrap:wrap;gap:8px 16px;align-items:baseline}
h1{font-size:18px;margin:0}h2{font-size:15px;margin:18px 0 8px}h3{font-size:13px;margin:12px 0 6px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
.muted{color:var(--muted)}main{display:grid;grid-template-columns:minmax(280px,420px) 1fr;gap:16px;padding:16px;max-width:1400px;margin:auto}
@media (max-width:860px){main{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}
nav{display:flex;gap:6px;flex-wrap:wrap;padding:0 16px 0}nav button{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:999px;padding:6px 12px;cursor:pointer}
nav button.on{background:var(--acc);color:#fff;border-color:var(--acc)}
.line{border-top:1px solid var(--line);padding:6px 0}.line b{display:inline-block;width:52px;color:var(--muted)}
.t{display:inline-flex;align-items:center;gap:4px;margin:2px;padding:3px 8px;border-radius:999px;background:var(--chip);cursor:pointer;border:1px solid transparent;font-size:13px}
.t.sel{border-color:var(--acc)}.t.edited{outline:2px dashed var(--warn)}.dot{width:8px;height:8px;border-radius:50%}
table{border-collapse:collapse;width:100%;font-size:13px}td,th{border-bottom:1px solid var(--line);padding:4px 6px;text-align:left;vertical-align:top}th{color:var(--muted);font-weight:600}
.flag{margin:4px 0;padding:6px 8px;border-left:3px solid var(--warn);background:var(--chip);border-radius:4px}
.good{color:var(--good)}.bad{color:var(--bad)}.scroll{overflow-x:auto}
select,input,textarea,button.act{font:inherit;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:6px;padding:6px}
button.act{background:var(--acc);color:#fff;border-color:var(--acc);cursor:pointer}button.sec{background:var(--card);color:var(--ink)}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:6px 0}textarea{width:100%;min-height:90px;font-family:ui-monospace,monospace;font-size:12px}
.pill{font-size:11px;padding:1px 6px;border-radius:999px;border:1px solid var(--line);color:var(--muted)}
</style></head><body>
<header><h1>__TITLE__</h1><span class="muted" id="meta"></span></header>
<nav id="tabs"></nav>
<main><section class="card" id="left"></section><section class="card" id="right"></section></main>
<script>
const D=__DATA__, REASONS=__REASONS__, LS="review-pending-"+D.season;
const LINES=D.lines, SLOTS=LINES.flatMap((n,i)=>Array(n).fill(i+1));
const T=Object.fromEntries(D.teams.map(t=>[t.key,t])), INFO=D.all_info;
let pending=[];try{pending=JSON.parse(localStorage.getItem(LS)||"[]")}catch(e){}
let tab="board", sel=D.teams[0].key;
const nm=k=>(INFO[k]||T[k]||{team:k}).team, esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const linesOf=o=>Object.fromEntries(o.map((k,i)=>[k,SLOTS[i]]));
const span=l=>[SLOTS.indexOf(l),SLOTS.lastIndexOf(l)];
const isAuto=k=>INFO[k]&&(INFO[k].champ||INFO[k].projected_auto);
function applyOne(order,rest,e){ // mirrors review.apply_edits
  const k=e.team; let o=[...order], r=[...rest];
  const ins=k2=>{let i=o.findIndex(x=>INFO[x].rank_score<INFO[k2].rank_score);if(i<0)i=o.length;o.splice(i,0,k2)};
  if(e.op==="move"){const c=o.indexOf(k);if(c<0)throw"not in field";const[a,b]=span(+e.to_line);if(a<0)throw"no such line";if(SLOTS[c]!==+e.to_line){o.splice(c,1);o.splice(+e.to_line<SLOTS[c]?a:b,0,k)}}
  else if(e.op==="swap"){const i=o.indexOf(k),j=o.indexOf(e.with);if(i<0||j<0)throw"both must be in field";[o[i],o[j]]=[o[j],o[i]]}
  else if(e.op==="add"){if(o.includes(k))throw"already in field";let x=e.remove||[...o].sort((a,b)=>INFO[a].p_in-INFO[b].p_in).find(t=>!isAuto(t));if(!o.includes(x)||isAuto(x))throw"removed team must be at-large";
    o=o.filter(t=>t!==x);r=[x,...r.filter(t=>t!==k)];if(e.to_line){o.splice(span(+e.to_line)[0],0,k)}else ins(k)}
  else if(e.op==="remove"){if(!o.includes(k)||isAuto(k))throw"only at-large teams";const y=e.add||r.find(t=>!o.includes(t));if(!y)throw"no replacement";o=o.filter(t=>t!==k);r=[k,...r.filter(t=>t!==y)];ins(y)}
  return[o,r]}
function current(){let o=[...D.model_order],r=[...D.rest_order];for(const e of D.edits){try{[o,r]=applyOne(o,r,e)}catch(x){}}
  const errs=[];for(const e of pending){try{[o,r]=applyOne(o,r,e)}catch(x){errs.push(e.id+": "+x)}}return{o,r,errs}}
function confColor(c){return c>=.7?"var(--good)":c>=.5?"var(--acc)":c>=.3?"var(--warn)":"var(--bad)"}
function board(){const{o,errs}=current(),L=linesOf(o),M=D.brackets.B1_model;let h=`<h2>Seed list <span class="pill">${D.phase.replace(/_/g," ")}</span></h2><p class="muted">Dot = model confidence. Dashed = your edit changed it. Tap a team.</p>`;
  for(let l=1;l<=16;l++){h+=`<div class="line"><b>Line ${l}</b>`+o.filter(k=>L[k]===l).map(k=>{const t=T[k]||{confidence:1};return`<span class="t ${k===sel?"sel":""} ${M[k]!==l?"edited":""}" data-k="${k}"><span class="dot" style="background:${confColor(t.confidence)}"></span>${esc(nm(k))}${t.champ?' <span class="pill">AQ</span>':''}</span>`}).join("")+"</div>"}
  h+=`<h3>First out</h3>`+D.outside.slice(0,8).map(t=>`<span class="t" data-k="${t.key}">${esc(t.team)} <span class="muted">${Math.round(t.p_in*100)}%</span></span>`).join("");
  if(errs.length)h+=`<div class="flag">${errs.map(esc).join("<br>")}</div>`;return h}
function detail(k){const t=T[k];if(!t){const x=D.outside.find(z=>z.key===k)||{};return`<h2>${esc(nm(k))}</h2><p>Outside the model field. P(in) ${Math.round((x.p_in||0)*100)}%, NET ${x.net??"?"}.</p>`+editForm(k)}
  const{o}=current(),L=linesOf(o);
  let h=`<h2>${esc(t.team)} <span class="muted">${esc(t.lg||"")}</span></h2><div class="row"><span class="pill">Model line ${t.model_line} · #${t.overall}</span><span class="pill">Your line ${L[k]??"out"}</span>${t.shadow_line?`<span class="pill">Shadow line ${t.shadow_line}</span>`:""}<span class="pill" style="color:${confColor(t.confidence)}">Confidence ${Math.round(t.confidence*100)}%</span><span class="pill">P(in) ${Math.round(t.p_in*100)}%</span>${t.champ?'<span class="pill">Automatic bid</span>':''}</div>`;
  h+=`<p class="muted">Distance to line ${t.model_line-1}: ${t.boundary_up_u??"—"} · to line ${t.model_line+1}: ${t.boundary_down_u??"—"} (positions' worth of model score)</p>`;
  h+=`<h3>Why the model might be wrong</h3>`+(t.flags.length?t.flags.map(f=>`<div class="flag">${esc(f)}</div>`).join(""):'<p class="muted">No flags.</p>');
  h+=`<h3>Résumé</h3><div class="scroll"><table>`+Object.entries(t.resume).map(([a,b])=>`<tr><th>${esc(a)}</th><td>${esc(b)}</td></tr>`).join("")+`</table></div>`;
  h+=`<p>Stronger than neighbours on: <span class="good">${t.advantages.join(", ")||"—"}</span>. Weaker on: <span class="bad">${t.disadvantages.join(", ")||"—"}</span>. Metric spread ${t.metric_spread}.</p>`;
  h+=`<h3>Neighbours (4 above, 4 below)</h3><div class="scroll"><table><tr><th>#</th><th>Team</th><th>Line</th><th>Score gap</th><th>H2H</th><th>Common opp.</th><th>NET</th><th>WAB rk</th><th>Q1</th></tr>`+
     t.neighbours.map(n=>`<tr><td>${n.overall}</td><td><a href="#" data-k="${n.key}">${esc(n.team)}</a></td><td>${n.line}</td><td>${n.gap_u>0?"+":""}${n.gap_u}</td><td>${n.h2h[0]+n.h2h[1]?n.h2h.join("-"):"—"}</td><td>${n.common.n?`${n.common.n} opp: ${n.common.a_wins}-${n.common.a_losses} vs ${n.common.b_wins}-${n.common.b_losses}`:"—"}</td><td>${n.net}</td><td>${n.rk_wab}</td><td>${n.q1}</td></tr>`).join("")+`</table></div><p class="muted">Score gap: positive = neighbour's model score is higher. H2H and common opponents are from ${esc(nm(k))}'s side.</p>`;
  return h+editForm(k)}
function editForm(k){const inField=current().o.includes(k);const opts=Object.entries(REASONS).map(([a,b])=>`<option value="${a}">${esc(b)}</option>`).join("");
  const teams=current().o.filter(x=>x!==k).map(x=>`<option value="${x}">${esc(nm(x))}</option>`).join("");
  return`<h3>Adjust</h3><div class="row"><select id="op">${inField?'<option value="move">Move to line</option><option value="swap">Swap with</option>'+(isAuto(k)?'':'<option value="remove">Remove from field</option>'):'<option value="add">Add to field</option>'}</select>
  <input id="line" type="number" min="1" max="16" placeholder="line" style="width:70px"><select id="other"><option value="">(auto)</option>${teams}</select></div>
  <div class="row"><select id="reason">${opts}</select><select id="conf"><option value="1">Confidence 1 (lean)</option><option value="2" selected>Confidence 2</option><option value="3">Confidence 3 (strong)</option></select></div>
  <div class="row"><input id="why" placeholder="Explanation (required for Other)" style="flex:1"></div><div class="row"><button class="act" id="go" data-k="${k}">Preview edit</button></div>
  <p class="muted">Line sizes stay valid: a move shifts one team across each line it passes; adding removes the lowest at-large team unless you pick one.</p>`}
function brackets(){const{o}=current(),B3=linesOf(o),B1=D.brackets.B1_model,B2=D.brackets.B2_shadow||{};const ks=[...new Set([...Object.keys(B1),...o])].sort((a,b)=>(B1[a]??99)-(B1[b]??99));
  const diff=ks.filter(k=>B1[k]!==B3[k]||(D.brackets.B2_shadow&&B1[k]!==B2[k]));
  return`<h2>Three brackets</h2><p class="muted">B1 frozen v2.0 · B2 head-to-head/common-opponent shadow · B3 v2.0 plus your edits. Teams where any differ:</p><div class="scroll"><table><tr><th>Team</th><th>B1</th><th>B2</th><th>B3</th></tr>`+
   diff.map(k=>`<tr><td>${esc(nm(k))}</td><td>${B1[k]??"out"}</td><td>${D.brackets.B2_shadow?(B2[k]??"out"):"n/a"}</td><td>${B3[k]??"out"}</td></tr>`).join("")+`</table></div>`}
function changes(){const c=D.changes;if(!c)return"<h2>Change report</h2><p class='muted'>No earlier review to compare with.</p>";
  const li=(a,f)=>a.length?"<ul>"+a.map(f).join("")+"</ul>":"<p class='muted'>None.</p>";
  return`<h2>Change report since ${esc(c.since)}</h2><h3>Seed-line changes</h3>${li(c.line_changes,m=>`<li>${esc(m.team)}: ${m.from} → ${m.to}</li>`)}
  <h3>Entered field</h3>${li(c.entered_field,x=>`<li>${esc(x)}</li>`)}<h3>Left field</h3>${li(c.left_field,x=>`<li>${esc(x)}</li>`)}
  <h3>New conference champions</h3>${li(c.new_champions,x=>`<li>${esc(x)}${c.bid_thieves.includes(x)?' <b class="bad">bid thief</b>':''}</li>`)}
  <h3>Near a seed boundary (under half a position)</h3>${li(c.near_boundary,x=>`<li>${esc(x)}</li>`)}<h3>Confidence changes (15+ points)</h3>${li(c.confidence_changes,m=>`<li>${esc(m.team)}: ${Math.round(m.from*100)}% → ${Math.round(m.to*100)}%</li>`)}`}
function log(){const rows=[...D.edits.map(e=>({...e,_s:"saved"})),...pending.map(e=>({...e,_s:"pending"}))];
  return`<h2>Edit log</h2><div class="scroll"><table><tr><th>When</th><th>Edit</th><th>Line</th><th>Reason</th><th>Conf.</th><th>Phase</th><th></th></tr>`+rows.map(e=>`<tr><td>${esc(e.at)}</td><td>${esc(e.op)} ${esc(nm(e.team||""))}${e.to_line?" → line "+e.to_line:""}${e.with?" ⇄ "+esc(nm(e.with)):""}</td><td>${e.line_before??""}${e.line_after!=null?" → "+e.line_after:""}</td><td>${esc(REASONS[e.reason_code]||e.reason_code||"")}${e.explanation?": "+esc(e.explanation):""}</td><td>${e.confidence||""}</td><td>${esc((e.phase||"").replace(/_/g," "))}</td><td>${e._s==="pending"?`<button class="act sec" data-undo="${e.id}">Discard</button>`:`<span class="pill">saved</span>`}</td></tr>`).join("")+`</table></div>
  <h3>Export</h3><p class="muted">Copy this into private/reviews/${D.season}.json (replacing it). It never goes in the public repo. The next build applies it and records every line change.</p><textarea readonly id="exp">${esc(JSON.stringify([...D.edits.map(({line_before,line_after,overall_before,overall_after,teams_changed,...e})=>e),...pending],null,1))}</textarea>
  <div class="row"><button class="act" id="copy">Copy JSON</button></div>`}
function info(){const s=D.sources||{};return`<h2>About this review</h2><table><tr><th>Inputs as of</th><td>${esc(D.asof)}</td></tr><tr><th>Generated</th><td>${esc(D.generated_at)}</td></tr><tr><th>Model</th><td>${esc(D.model_version)} (frozen)</td></tr><tr><th>NET source</th><td>${esc(s.net_source||"")} ${esc(s.net_asof||"")}</td></tr><tr><th>Phase</th><td>${esc(D.phase)}</td></tr></table>
  ${(D.edit_notes||[]).length?"<h3>Edits not applied</h3>"+D.edit_notes.map(n=>`<div class="flag">${esc(n)}</div>`).join(""):""}${(D.warnings||[]).length?"<h3>Data warnings</h3>"+D.warnings.map(n=>`<div class="flag">${esc(n)}</div>`).join(""):""}`}
function draw(){document.getElementById("meta").textContent=`Inputs through ${D.asof} · ${D.model_version} · owner-only, not published`;
  const tabs=[["board","Review"],["brackets","Three brackets"],["changes","Change report"],["log","Edit log"],["info","About"]];
  document.getElementById("tabs").innerHTML=tabs.map(([a,b])=>`<button class="${tab===a?"on":""}" data-tab="${a}">${b}${a==="log"&&pending.length?` (${pending.length})`:""}</button>`).join("");
  document.getElementById("left").innerHTML=board();
  document.getElementById("right").innerHTML=tab==="board"?detail(sel):tab==="brackets"?brackets():tab==="changes"?changes():tab==="log"?log():info()}
document.addEventListener("click",ev=>{const el=ev.target.closest("[data-k],[data-tab],[data-undo],#copy");if(!el)return;ev.preventDefault();
  if(el.dataset.tab){tab=el.dataset.tab}
  else if(el.id==="go"){const k=el.dataset.k,op=document.getElementById("op").value,line=document.getElementById("line").value,other=document.getElementById("other").value;
    const e={id:"e"+Date.now().toString(36),at:new Date().toISOString().replace(/\.\d+Z$/,"Z"),op,team:k,reason_code:document.getElementById("reason").value,confidence:+document.getElementById("conf").value,explanation:document.getElementById("why").value.trim()};
    if(op==="move"){if(!line)return alert("Pick a line");e.to_line=+line}if(op==="swap"){if(!other)return alert("Pick a team to swap with");e.with=other}
    if(op==="add"){if(other)e.remove=other;if(line)e.to_line=+line}if(op==="remove"&&other)e.add=other;
    if(e.reason_code==="other"&&!e.explanation)return alert("Explain 'Other'");
    const before=linesOf(current().o)[k];try{applyOne(current().o,current().r,e)}catch(x){return alert("Not possible: "+x)}
    pending.push(e);e.line_before=before;e.line_after=linesOf(current().o)[k];try{localStorage.setItem(LS,JSON.stringify(pending))}catch(x){}tab="board"}
  else if(el.dataset.undo){pending=pending.filter(e=>e.id!==el.dataset.undo);try{localStorage.setItem(LS,JSON.stringify(pending))}catch(x){}}
  else if(el.id==="copy"){const t=document.getElementById("exp");t.select();try{navigator.clipboard.writeText(t.value)}catch(x){document.execCommand("copy")}}
  else if(el.dataset.k){sel=el.dataset.k;tab="board"}
  draw()});
draw();
</script></body></html>"""
