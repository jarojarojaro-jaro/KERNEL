#!/usr/bin/env python3
"""Interactive knowledge-graph view of KERNEL/wiki in the browser (Obsidian-like), stdlib only.

    python3 wiki/tools/graph.py [out.html]      # default: ~/.cache/wiki-graph/index.html

Nodes = notes (colour = top folder, size = number of links), edges = [[wikilinks]].
Click a node: its text and links in the side panel; search box filters by title.
The page loads the force-graph library from unpkg, so the viewing browser needs internet.
"""
import json
import re
import sys
from pathlib import Path

WIKI = Path(__file__).resolve().parent.parent
LINK = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / ".cache/wiki-graph/index.html"
    notes = {}
    for p in sorted(WIKI.rglob("*.md")):
        rel = p.relative_to(WIKI)
        if rel.parts[0] in ("tools", ".obsidian"):
            continue
        key = str(rel.with_suffix(""))
        notes[key] = p.read_text(encoding="utf-8", errors="replace")
    by_name = {}
    for key in notes:
        by_name.setdefault(Path(key).name, key)

    def resolve(target: str):
        t = target.strip()
        return t if t in notes else by_name.get(Path(t).name)

    links, nodes = set(), []
    for key, text in notes.items():
        for m in LINK.finditer(text):
            dst = resolve(m.group(1))
            if dst and dst != key:
                links.add(tuple(sorted((key, dst))))
    degree = {k: 0 for k in notes}
    for a, b in links:
        degree[a] += 1
        degree[b] += 1
    for key, text in notes.items():
        title = next((ln[2:].strip() for ln in text.splitlines() if ln.startswith("# ")), Path(key).name)
        group = key.split("/")[0] if "/" in key else "root"
        nodes.append({"id": key, "title": title, "group": group, "deg": degree[key], "text": text[:6000]})
    data = {"nodes": nodes, "links": [{"source": a, "target": b} for a, b in sorted(links)]}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(PAGE.replace("__DATA__", json.dumps(data, ensure_ascii=False)), encoding="utf-8")
    print(f"{out}: {len(nodes)} notes, {len(links)} links")


PAGE = """<!doctype html><html lang="pl"><head><meta charset="utf-8"><title>KERNEL wiki - graf wiedzy</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
html,body{margin:0;height:100%;background:#0b0b0d;color:#e8e6e3;font:14px/1.45 system-ui,sans-serif;overflow:hidden}
#g{position:absolute;inset:0}
#bar{position:absolute;top:12px;left:12px;z-index:2;display:flex;gap:8px;align-items:center}
#q{background:#17171b;color:#eee;border:1px solid #333;border-radius:8px;padding:8px 10px;width:260px}
#legend{position:absolute;bottom:12px;left:12px;z-index:2;display:flex;flex-wrap:wrap;gap:6px;max-width:60vw}
.chip{padding:3px 8px;border-radius:99px;font-size:12px;background:#17171b;border:1px solid #2a2a30;cursor:pointer}
#panel{position:absolute;top:0;right:0;width:min(520px,42vw);height:100%;background:#111114ee;border-left:1px solid #26262c;
 z-index:3;overflow:auto;padding:18px 20px;box-sizing:border-box;display:none}
#panel h2{margin:0 0 4px;font-size:18px}#panel .path{color:#888;font-size:12px;margin-bottom:12px}
#panel pre{white-space:pre-wrap;font:12.5px/1.5 ui-monospace,monospace;color:#cfcac4}
#panel a{color:#ff9a3c;cursor:pointer;text-decoration:none;display:inline-block;margin:2px 8px 2px 0}
#x{position:absolute;top:10px;right:14px;cursor:pointer;color:#888;font-size:20px}
#stats{color:#888;font-size:12px}
</style></head><body>
<div id="bar"><input id="q" placeholder="Szukaj notatki..."><span id="stats"></span></div>
<div id="legend"></div><div id="g"></div>
<div id="panel"><span id="x">&times;</span><h2 id="t"></h2><div class="path" id="p"></div><div id="nb"></div><pre id="c"></pre></div>
<script src="https://unpkg.com/force-graph@1.47.4/dist/force-graph.min.js"></script>
<script>
const data=__DATA__;
const pal=["#ff7a1a","#4cc9f0","#80ed99","#f72585","#ffd166","#b388ff","#06d6a0","#ef476f","#9ad1ff","#c9ada7","#f4a261","#90be6d","#e5989b","#a0c4ff","#ffadad","#cdb4db"];
const groups=[...new Set(data.nodes.map(n=>n.group))].sort();
const col=Object.fromEntries(groups.map((g,i)=>[g,pal[i%pal.length]]));
const nbr={};data.links.forEach(l=>{(nbr[l.source]??=new Set).add(l.target);(nbr[l.target]??=new Set).add(l.source)});
let hi=null,hidden=new Set();
document.getElementById('stats').textContent=data.nodes.length+' notatek \\u00b7 '+data.links.length+' powiązań';
const G=ForceGraph()(document.getElementById('g')).graphData(data).nodeId('id').backgroundColor('#0b0b0d')
 .nodeVal(n=>1+Math.sqrt(n.deg)*1.6).nodeColor(n=>hidden.has(n.group)?'rgba(0,0,0,0)':(hi&&hi!==n.id&&!(nbr[hi]||new Set()).has(n.id)?'#333':col[n.group]))
 .nodeLabel(n=>n.title+' ('+n.group+')').linkColor(l=>{const s=l.source.id??l.source,t=l.target.id??l.target;return hi&&(s===hi||t===hi)?'#ff9a3c':'rgba(255,255,255,0.08)'})
 .linkWidth(l=>{const s=l.source.id??l.source,t=l.target.id??l.target;return hi&&(s===hi||t===hi)?1.6:0.5})
 .nodeCanvasObjectMode(()=> 'after').nodeCanvasObject((n,ctx,s)=>{if(s<1.6&&n.deg<25&&n.id!==hi)return;ctx.font=(11/s)+'px sans-serif';ctx.fillStyle='#ddd';ctx.textAlign='center';ctx.fillText(n.title.slice(0,40),n.x,n.y+8/s+4)})
 .onNodeClick(n=>show(n)).onBackgroundClick(()=>{hi=null;document.getElementById('panel').style.display='none';G.refresh()});
G.d3Force('charge').strength(-40);
function show(n){hi=n.id;const P=document.getElementById('panel');P.style.display='block';
 document.getElementById('t').textContent=n.title;document.getElementById('p').textContent=n.id+'.md';
 document.getElementById('c').textContent=n.text;const nb=document.getElementById('nb');nb.innerHTML='';
 [...(nbr[n.id]||[])].sort().forEach(id=>{const a=document.createElement('a');a.textContent='\\u2192 '+id;a.onclick=()=>{const m=data.nodes.find(x=>x.id===id);G.centerAt(m.x,m.y,600);G.zoom(3,600);show(m)};nb.appendChild(a)});
 G.centerAt(n.x,n.y,600);G.refresh()}
document.getElementById('x').onclick=()=>{document.getElementById('panel').style.display='none';hi=null;G.refresh()};
document.getElementById('q').oninput=e=>{const q=e.target.value.toLowerCase();if(!q){hi=null;G.refresh();return}
 const m=data.nodes.find(n=>n.title.toLowerCase().includes(q)||n.id.toLowerCase().includes(q));if(m){G.centerAt(m.x,m.y,500);G.zoom(4,500);show(m)}};
const L=document.getElementById('legend');groups.forEach(g=>{const c=document.createElement('span');c.className='chip';
 c.innerHTML='<b style="color:'+col[g]+'">\\u25cf</b> '+g+' ('+data.nodes.filter(n=>n.group===g).length+')';
 c.onclick=()=>{hidden.has(g)?hidden.delete(g):hidden.add(g);c.style.opacity=hidden.has(g)?.35:1;G.refresh()};L.appendChild(c)});
</script></body></html>"""

if __name__ == "__main__":
    main()
