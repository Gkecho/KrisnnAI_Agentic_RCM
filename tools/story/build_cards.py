"""Build docs/story/guild-cards.html (character cards) from docs/story/THE-REVENUE-GUILD.md.

    python tools/story/build_cards.py

The story file is the source of truth: edit it, rebuild, and the cards follow. Override the output with KRISNNAI_CARDS_OUT.
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
STORY_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "docs", "story"))
SRC = os.path.join(STORY_DIR, "THE-REVENUE-GUILD.md")
OUT = os.environ.get("KRISNNAI_CARDS_OUT") or os.path.join(STORY_DIR, "guild-cards.html")
text = open(SRC, encoding="utf-8").read()

# ---- the four oaths
oaths = [{"title": m.group(1), "text": m.group(2)}
         for m in re.finditer(r"^\d\. \*\*(.+?)\*\* (.+)$", text.split("**The Ranks**")[0], re.M)]

# ---- agents, grouped by the stage heading above them
part2 = text.split("## Part 2. The Guild")[1].split("## Part 3.")[0]
agents, stage, cur = [], "", None


def finish(cur):
    f = cur["f"]
    g = f.get("Grimoire", "")
    reads, _, writes = g.partition("; writes")
    agents.append(dict(
        code=cur["code"], name="The " + cur["name"], role=cur["role"], stage=cur["stage"],
        power=f.get("Power", ""), move=f.get("Signature move", ""), trait=f.get("Trait", ""), weakness=f.get("Weakness", ""),
        villain=f.get("Villain", ""), officer=f.get("Officer partner", ""),
        reads=re.findall(r"`([^`]+)`", reads) or [reads.replace("reads", "").strip()],
        writes=re.findall(r"`([^`]+)`", writes)))


for line in part2.splitlines():
    if line.startswith("### "):
        if cur:
            finish(cur); cur = None
        stage = line[4:].strip()
        continue
    m = re.match(r"\*\*(A\d+)\. The (.+?)\*\* \*\((.+?)\)\*", line)
    if m:
        if cur:
            finish(cur)
        cur = dict(code=m.group(1), name=m.group(2), role=m.group(3), stage=stage, f={})
        continue
    m = re.match(r"- \*\*(.+?):\*\* (.+)$", line)
    if m and cur:
        cur["f"][m.group(1)] = m.group(2).strip()
if cur:
    finish(cur)

# ---- officers
part3 = text.split("## Part 3. The officers")[1].split("## Part 4.")[0]
officers = []
for line in part3.splitlines():
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cells) == 3 and cells[0].startswith("**"):
        officers.append(dict(name=cells[0].strip("*"), key=cells[1], works=cells[2]))

stages = []
for a in agents:
    if a["stage"] not in stages:
        stages.append(a["stage"])
print(f"{len(agents)} agents, {len(stages)} stages, {len(officers)} officers, {len(oaths)} oaths")
assert len(agents) == 15 and len(officers) >= 10 and len(oaths) == 4, "story file changed shape; check the parser"

tpl = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>The Revenue Guild</title>
<style>
:root{--bg:#f4f1ea;--panel:#fffdf8;--ink:#1c2333;--mute:#586277;--line:#ded8c8;--navy:#1f3864;--soft:#ece7da}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#10141c;--panel:#192030;--ink:#e8ecf4;--mute:#9ba8bc;--line:#2a3347;--navy:#6f95d8;--soft:#222b3d}}
:root[data-theme="dark"]{--bg:#10141c;--panel:#192030;--ink:#e8ecf4;--mute:#9ba8bc;--line:#2a3347;--navy:#6f95d8;--soft:#222b3d}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 "Segoe UI",system-ui,-apple-system,Arial,sans-serif}
.wrap{max-width:1200px;margin:0 auto;padding:0 16px 56px}
header{padding:34px 0 12px}
h1{margin:0;font-size:clamp(26px,4vw,40px);letter-spacing:-.01em;line-height:1.1}
.sub{color:var(--mute);margin:8px 0 0;max-width:70ch}
.top{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}
button,input{font:inherit;color:inherit}
.btn{border:1px solid var(--line);background:var(--panel);padding:6px 12px;border-radius:8px;cursor:pointer}
.btn:hover{background:var(--soft)}
:focus-visible{outline:3px solid var(--navy);outline-offset:2px}
.oaths{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:10px;margin:18px 0 6px}
.oath{background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--navy);border-radius:8px;padding:10px 12px}
.oath b{display:block;font-size:14px}
.oath span{color:var(--mute);font-size:13px}
.bar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:18px 0 14px}
.bar input{flex:1;min-width:200px;max-width:340px;padding:8px 12px;border:1px solid var(--line);border-radius:8px;background:var(--panel)}
.pill{border:1px solid var(--line);background:var(--panel);padding:4px 11px;border-radius:999px;cursor:pointer;font-size:13px}
.pill[aria-pressed="true"]{background:var(--navy);border-color:var(--navy);color:#fff}
.count{color:var(--mute);font-size:13px;margin-left:auto}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:14px}
.card{--c:#1f3864;background:var(--panel);border:1px solid var(--line);border-top:5px solid var(--c);border-radius:12px;padding:14px 14px 12px;display:flex;flex-direction:column;gap:10px}
.card[hidden]{display:none}
.row{display:flex;gap:12px;align-items:center}
.shield{flex:none;width:52px;height:60px;background:var(--c);color:#fff;font-weight:800;font-size:17px;display:grid;place-items:center;clip-path:polygon(50% 0,100% 14%,100% 58%,50% 100%,0 58%,0 14%);padding-bottom:6px}
.card h2{margin:0;font-size:19px;line-height:1.2}
.role{color:var(--mute);font-size:13px}
.power{margin:0}
.chips{display:flex;flex-wrap:wrap;gap:6px}
.chip{font-size:12px;border-radius:6px;padding:2px 8px;background:color-mix(in srgb,var(--c) 14%,var(--panel));border:1px solid color-mix(in srgb,var(--c) 40%,var(--line))}
.chip.v::before{content:"Villain: ";font-weight:700}
.chip.o::before{content:"Officer: ";font-weight:700}
.rank{font-size:11px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--mute)}
details{border-top:1px dashed var(--line);padding-top:8px}
summary{cursor:pointer;font-weight:600;font-size:13px;color:var(--navy);list-style:none}
summary::-webkit-details-marker{display:none}
summary::before{content:"+ ";font-weight:800}
details[open] summary::before{content:"\2212  "}
dl{margin:10px 0 0;display:grid;gap:8px}
dt{font-size:11px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;color:var(--mute)}
dd{margin:2px 0 0}
code{font-family:Consolas,monospace;font-size:12px;background:var(--soft);border-radius:4px;padding:1px 5px}
.weak{border-left:3px solid #c0392b;padding-left:9px}
h3.sec{margin:34px 0 10px;font-size:20px}
.officers{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:10px}
.off{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.off b{display:block}
.off span{display:block;color:var(--mute);font-size:13px}
.note{margin-top:30px;color:var(--mute);font-size:13px;border-top:1px solid var(--line);padding-top:12px}
</style>
</head>
<body>
<div class="wrap">
<header>
  <div class="top">
    <div>
      <h1>The Revenue Guild of Maple Street</h1>
      <p class="sub">Fifteen agents, the leaks they hunt, and the officers who hold the keys. Fiction built on the real design: every power, weakness and table below is real.</p>
    </div>
    <button class="btn" id="theme" aria-label="Toggle light and dark">Theme</button>
  </div>
  <div class="oaths" id="oaths"></div>
</header>
<div class="bar">
  <input id="q" type="search" placeholder="Search powers, villains, tables..." aria-label="Search the guild">
  <span id="pills" style="display:contents"></span>
  <button class="btn" id="expand">Open all</button>
  <span class="count" id="count" aria-live="polite"></span>
</div>
<main class="grid" id="grid"></main>
<h3 class="sec">The officers</h3>
<p class="sub" style="margin-bottom:12px">Humans hold the keys. Nothing that moves money happens without a named officer.</p>
<div class="officers" id="officers"></div>
<p class="note">All agents stand at <b>L0, in the Shadow Grounds</b>: they write what they would do and send nothing. Patients are synthetic and appear only as hashes. Source: docs/story/THE-REVENUE-GUILD.md (rebuild with tools/story/build_cards.py).</p>
</div>
<script id="data" type="application/json">__DATA__</script>
<script>
(function(){
var D=JSON.parse(document.getElementById("data").textContent);
var COLORS={};var PAL=["#0f766e","#b45309","#6d28d9","#be123c","#15803d","#1d4ed8","#475569"];
D.stages.forEach(function(s,i){COLORS[s]=PAL[i%PAL.length]});
function esc(s){return String(s==null?"":s).replace(/[&<>"']/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]})}
function md(s){return esc(s).replace(/`([^`]+)`/g,"<code>$1</code>").replace(/\*\*([^*]+)\*\*/g,"<b>$1</b>").replace(/\*([^*]+)\*/g,"<i>$1</i>")}
function $(id){return document.getElementById(id)}
$("oaths").innerHTML=D.oaths.map(function(o){return '<div class="oath"><b>'+md(o.title)+'</b><span>'+md(o.text)+'</span></div>'}).join("");
$("officers").innerHTML=D.officers.map(function(o){return '<div class="off"><b>'+esc(o.name)+'</b><span>Holds: '+md(o.key)+'</span><span>Works with: '+md(o.works)+'</span></div>'}).join("");
var stage="All";
$("pills").innerHTML=["All"].concat(D.stages).map(function(s){return '<button class="pill" aria-pressed="'+(s==="All")+'" data-s="'+esc(s)+'">'+esc(s)+'</button>'}).join("");
$("grid").innerHTML=D.agents.map(function(a,i){
  var tabs=function(l){return l.map(function(t){return '<code>'+esc(t)+'</code>'}).join(" ")};
  return '<article class="card" style="--c:'+COLORS[a.stage]+'" data-i="'+i+'" data-s="'+esc(a.stage)+'">'
   +'<div class="row"><div class="shield" aria-hidden="true">'+esc(a.code)+'</div><div><h2>'+esc(a.name)+'</h2><div class="role">'+esc(a.role)+' &middot; '+esc(a.stage)+'</div></div></div>'
   +'<p class="power">'+md(a.power)+'</p>'
   +'<div class="chips"><span class="chip v">'+md(a.villain)+'</span><span class="chip o">'+md(a.officer)+'</span></div>'
   +'<div class="rank">Rank L0 &middot; Shadow Grounds</div>'
   +'<details><summary>Powers, traits and limits</summary><dl>'
   +'<div><dt>Signature move</dt><dd>'+md(a.move)+'</dd></div>'
   +'<div><dt>Trait</dt><dd>'+md(a.trait)+'</dd></div>'
   +'<div class="weak"><dt>Weakness (real limit today)</dt><dd>'+md(a.weakness)+'</dd></div>'
   +'<div><dt>Reads</dt><dd>'+tabs(a.reads)+'</dd></div>'
   +'<div><dt>Writes</dt><dd>'+tabs(a.writes)+'</dd></div>'
   +'</dl></details></article>'}).join("");
var cards=[].slice.call(document.querySelectorAll(".card"));
function apply(){
  var q=$("q").value.trim().toLowerCase(),n=0;
  cards.forEach(function(c){
    var a=D.agents[+c.dataset.i],hay=JSON.stringify(a).toLowerCase();
    var ok=(stage==="All"||a.stage===stage)&&(!q||hay.indexOf(q)>=0);
    c.hidden=!ok;if(ok)n++});
  $("count").textContent=n+" of "+cards.length+" agents"}
$("q").addEventListener("input",apply);
$("pills").addEventListener("click",function(e){var b=e.target.closest(".pill");if(!b)return;stage=b.dataset.s;
  [].forEach.call(document.querySelectorAll(".pill"),function(p){p.setAttribute("aria-pressed",p===b)});apply()});
var open=false;$("expand").addEventListener("click",function(){open=!open;
  [].forEach.call(document.querySelectorAll("details"),function(d){d.open=open});this.textContent=open?"Close all":"Open all"});
$("theme").addEventListener("click",function(){var r=document.documentElement,dark=r.getAttribute("data-theme")==="dark"||(!r.getAttribute("data-theme")&&matchMedia("(prefers-color-scheme:dark)").matches);r.setAttribute("data-theme",dark?"light":"dark")});
apply();
})();
</script>
</body>
</html>
'''
data = json.dumps(dict(agents=agents, stages=stages, officers=officers, oaths=oaths), ensure_ascii=False).replace("<", "\\u003c")
open(OUT, "w", encoding="utf-8").write(tpl.replace("__DATA__", data))
print("saved", OUT)
