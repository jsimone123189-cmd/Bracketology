// One-file, offline preview of the review page for trying it on a phone: the real page, with the Worker replaced by an
// in-memory stand-in that runs the same edit engine. Nothing is sent anywhere; edits vanish on reload. Output: private/review_preview.html
import { readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { realReview, REPO } from "./helpers.mjs";
const dir = path.join(REPO, "review-worker/src");
const engine = readFileSync(path.join(dir, "engine.js"), "utf8").replace(/^export /gm, "");
const page = readFileSync(path.join(dir, "page.html"), "utf8");
const rv = realReview(); delete rv.teams_by_key; rv.edits = []; rv.edit_notes = [];
const data = JSON.stringify(rv).replace(/</g, "\\u003c");
const stub = `<script>
${engine}
(function(){
const RV=${data}, LINES=RV.lines, SL=slotsOf(LINES), SS="2027-03-14", edits=[];
const iso=()=>new Date().toISOString().replace(/\\.\\d{3}Z$/,"Z");
const b3=(E)=>applyEdits(RV.model_order,RV.rest_order,E,SL,RV.all_info,SS);
const resp=(o,s=200)=>Promise.resolve(new Response(JSON.stringify(o),{status:s,headers:{"Content-Type":"application/json"}}));
function state(){const B=b3(edits);return{season:2027,server_time:iso(),review:RV,edits,b3_order:B.order,b3:linesOf(B.order,SL),applied:B.applied,notes:B.notes,
  freezes:[{kind:"research",cutoff:"2027-03-14T16:00:00Z",earliest:"2027-03-14T15:30:00Z",frozen:false},{kind:"final",cutoff:null,earliest:null,frozen:false}],
  window:{open:true,note:null},reasons:REASONS}}
window.fetch=async(url,opt)=>{const p=new URL(url,"https://preview.local").pathname;
  if(p==="/api/state")return resp(state());
  if(p==="/api/edits"){const i=JSON.parse(opt.body),e={op:i.op};for(const f of["team","with","add","remove","reason_code","explanation","undo_of"])if(i[f])e[f]=String(i[f]);
    if(i.to_line)e.to_line=+i.to_line;if(i.confidence!=null)e.confidence=+i.confidence;e.id="e"+Math.random().toString(36).slice(2,10);e.at=iso();
    const bad=checkEdit(e);if(bad.length)return resp({error:bad.join("; ")},422);
    const a=b3(edits),b=b3([...edits,e]);if(e.op!=="undo"&&!b.applied.some(x=>x.id===e.id))return resp({error:(b.notes.find(n=>n.includes(e.id))||"Not possible").replace(/^Edit \\S+ (not applied|skipped): /,"")},422);
    const L0=linesOf(a.order,SL),L1=linesOf(b.order,SL),ch=[...new Set([...Object.keys(L0),...Object.keys(L1)])].filter(k=>L0[k]!==L1[k]).map(k=>({key:k,team:(RV.all_info[k]||{}).team||k,from:L0[k]??null,to:L1[k]??null}));
    if(i.dry_run)return resp({preview:true,edit:e,changes:ch});edits.push(e);return resp({saved:true,edit:e,changes:ch})}
  if(p==="/api/freeze"||p==="/api/verify")return resp({status:"error",error:"Not available in this offline preview.",ok:false,problems:["offline preview"]});
  return resp({error:"not found"},404)};
})();
</script>`;
const out = page.replace("<title>Bracket Review</title>", "<title>Bracket Review (offline preview)</title>")
  .replace('<header><h1 id="title">', '<div style="background:#a85d12;color:#fff;font:13px system-ui;padding:6px 16px;text-align:center">Offline preview · edits are not saved anywhere · real 2027 early-season data</div><header><h1 id="title">')
  .replace("<script>\n\"use strict\";", stub + "\n<script>\n\"use strict\";");
writeFileSync(path.join(REPO, "private/review_preview.html"), out);
console.log("private/review_preview.html", out.length, "bytes");
