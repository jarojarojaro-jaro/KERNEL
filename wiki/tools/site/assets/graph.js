/* KERNEL knowledge graph: clustered global view + local neighbourhood widget (force-graph, canvas 2D).
   Labels are short pills (<= 22 chars) drawn in screen space (constant 12-13 px), placed greedily without
   overlaps: cluster titles first, then the selected / hovered node and its neighbours, then (as you zoom in)
   the best-connected nodes in view. Edges are faint curves until a node is hovered or selected. */
(() => {
  'use strict';
  const FONT = "'Showcase Sans', ui-sans-serif, system-ui, sans-serif";
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const icon = n => `<svg class="i" aria-hidden="true"><use href="/assets/icons.svg#${n}"></use></svg>`;
  const STATUS = { 'aktualne': 'aktualne', 'do-sprawdzenia': 'do sprawdzenia', 'nieaktualne': 'nieaktualne' };
  const rgba = (hex, a) => { const h = hex.replace('#', ''); const n = parseInt(h.length === 3 ? h.replace(/./g, '$&$&') : h, 16); return `rgba(${n >> 16 & 255},${n >> 8 & 255},${n & 255},${a})`; };

  /* ------------------------------------------------------------ theme colours for the canvas */
  let C;
  const readTheme = () => {
    const s = getComputedStyle(document.documentElement), v = k => s.getPropertyValue(k).trim();
    const light = document.documentElement.dataset.theme === 'light';
    C = { light, bg: v('--bg-0'), bg1: v('--bg-1'), text: v('--text-hi'), mute: v('--text-mute'), accent: v('--accent'),
      pill: light ? 'rgba(255,255,255,0.94)' : 'rgba(14,14,17,0.88)', pillLine: light ? 'rgba(20,18,14,0.14)' : 'rgba(255,255,255,0.10)',
      edge: light ? 'rgba(20,18,14,' : 'rgba(237,234,227,' };
  };
  readTheme();
  const graphs = new Set();
  addEventListener('kb-theme', () => { readTheme(); graphs.forEach(g => g.refresh()); });
  document.fonts?.ready.then(() => { widths.clear(); graphs.forEach(g => g.refresh()); });

  /* ------------------------------------------------------------ data */
  let DATA;
  const load = () => DATA ??= fetch('/data/graph.json').then(r => r.json()).then(g => {
    const nodes = g.nodes.map((r, i) => ({ i, id: r[0], t: r[1], c: r[2], u: r[3], s: r[4], d: r[5], x: r[6], deg: r[7], hub: !!r[8], l: r[9] }));
    const byId = new Map(nodes.map(n => [n.id, n]));
    const adj = nodes.map(() => new Set());
    for (const [a, b, w] of g.links) if (w) { adj[a].add(b); adj[b].add(a); }
    const order = [...g.order, ...Object.keys(g.cats).filter(k => !g.order.includes(k))];
    return { cats: g.cats, order, nodes, byId, adj, links: g.links };
  });

  /* ------------------------------------------------------------ label pills */
  const widths = new Map();
  const textW = (ctx, text, px, weight) => {
    const k = weight + '|' + px + '|' + text;
    let w = widths.get(k);
    if (w === undefined) { ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.font = `${weight} ${px}px ${FONT}`; w = ctx.measureText(text).width; ctx.restore(); widths.set(k, w); }
    return w;
  };
  const roundRect = (ctx, x, y, w, h, r) => { ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); };
  const hit = (r, placed) => placed.some(p => r[0] < p[2] && r[2] > p[0] && r[1] < p[3] && r[3] > p[1]);

  /* Places a pill next to graph point (x, y) whose dot has graph radius rad. Sizes are screen px.
     o.bounds = visible area [x0, y0, x1, y1] in the same space: optional pills outside are skipped, forced ones clamped in. */
  function pill(ctx, k, placed, x, y, rad, text, color, o = {}) {
    const px = o.px || 12, weight = o.weight || 600, padX = 8, dotW = 12, h = px + 10;
    const tw = textW(ctx, text, px, weight), w = tw + padX * 2 + dotW;
    const rs = rad * k; // dot radius in screen px
    const sx = x * k, sy = y * k; // pre-transform screen coords relative to origin; we compare in this space
    const spots = o.center ? [[sx - w / 2, sy - h / 2]] : [[sx + rs + 5, sy - h / 2], [sx - rs - 5 - w, sy - h / 2], [sx - w / 2, sy + rs + 4], [sx - w / 2, sy - rs - 4 - h]];
    for (let [ax, ay] of spots) {
      const b = o.bounds;
      if (b) {
        const out = ax < b[0] || ay < b[1] || ax + w > b[2] || ay + h > b[3];
        if (out && !o.force) continue;
        if (out) { ax = Math.max(b[0], Math.min(ax, b[2] - w)); ay = Math.max(b[1], Math.min(ay, b[3] - h)); }
      }
      const r = [ax, ay, ax + w, ay + h];
      if (!o.force && hit(r, placed)) continue;
      placed.push(r);
      ctx.save();
      ctx.scale(1 / k, 1 / k);
      roundRect(ctx, ax, ay, w, h, h / 2);
      ctx.fillStyle = o.bg || C.pill; ctx.fill();
      ctx.lineWidth = 1; ctx.strokeStyle = o.ring || C.pillLine; ctx.stroke();
      ctx.beginPath(); ctx.arc(ax + padX + 3, ay + h / 2, 3.5, 0, 7); ctx.fillStyle = color; ctx.fill();
      ctx.font = `${weight} ${px}px ${FONT}`; ctx.textBaseline = 'middle'; ctx.fillStyle = o.fg || C.text;
      ctx.fillText(text, ax + padX + dotW, ay + h / 2 + .5);
      ctx.restore();
      return true;
    }
    return false;
  }

  const radius = n => n.hub ? 7 : 2.6 + Math.sqrt(n.deg) * 0.85;
  // visible canvas rect in pill space (graph coords × k), inset by 4 px
  const viewBounds = (G, el, k) => {
    const tl = G.screen2GraphCoords(0, 0), br = G.screen2GraphCoords(el.clientWidth, el.clientHeight);
    return [tl.x * k + 4, tl.y * k + 4, br.x * k - 4, br.y * k - 4];
  };

  /* ------------------------------------------------------------ local graph */
  function localData(D, id, hops) {
    const c = D.byId.get(id); if (!c) return null;
    const ok = n => !n.hub;
    const one = [...D.adj[c.i]].map(i => D.nodes[i]).filter(ok);
    let two = [];
    if (hops > 1) {
      const seen = new Set([c.i, ...one.map(n => n.i)]), cand = new Map();
      for (const n of one) for (const j of D.adj[n.i]) if (!seen.has(j) && ok(D.nodes[j])) cand.set(j, (cand.get(j) || 0) + 1);
      two = [...cand.entries()].sort((a, b) => b[1] - a[1] || D.nodes[b[0]].deg - D.nodes[a[0]].deg).slice(0, Math.max(0, 70 - one.length)).map(([j]) => D.nodes[j]);
    }
    const keep = [c, ...one, ...two], set = new Set(keep.map(n => n.i));
    const nodes = keep.map(n => ({ ...n, ring: n === c ? 0 : one.includes(n) ? 1 : 2, x: undefined, y: undefined }));
    const links = [];
    for (const n of keep) for (const j of D.adj[n.i]) if (j > n.i && set.has(j)) links.push({ source: n.i, target: j });
    return { nodes, links, center: c };
  }

  function mountLocal(el, id, seg, opts = {}) {
    return load().then(D => {
      el.innerHTML = '';
      let hops = 1, hover = null, fitted = false;
      const G = ForceGraph()(el)
        .width(el.clientWidth).height(el.clientHeight).backgroundColor('rgba(0,0,0,0)')
        .nodeId('i').autoPauseRedraw(true).enableZoomInteraction(false).enablePanInteraction(false)
        .linkCurvature(0.15).linkWidth(l => (hover && (l.source === hover || l.target === hover)) ? 1.6 : 0.8)
        .linkColor(l => {
          if (hover && (l.source === hover || l.target === hover)) return rgba(D.cats[hover.c][1], .9);
          return C.edge + (l.source.ring === 0 || l.target.ring === 0 ? '0.22)' : '0.08)');
        })
        .nodeLabel(n => `<b>${esc(n.t)}</b>`)
        .nodeCanvasObject((n, ctx, k) => {
          const r = n.ring === 0 ? 8 : n.ring === 1 ? 4.6 + Math.sqrt(n.deg) * 0.35 : 3.2;
          ctx.globalAlpha = hover && hover !== n && !(D.adj[hover.i].has(n.i)) ? .3 : 1;
          ctx.beginPath(); ctx.arc(n.x, n.y, r, 0, 7); ctx.fillStyle = D.cats[n.c][1]; ctx.fill();
          if (n.ring === 0) { ctx.lineWidth = 2.5 / k; ctx.strokeStyle = C.bg1; ctx.stroke(); ctx.beginPath(); ctx.arc(n.x, n.y, r + 3.5 / k + 1, 0, 7); ctx.lineWidth = 1.5 / k; ctx.strokeStyle = C.accent; ctx.stroke(); }
          ctx.globalAlpha = 1; n._r = r;
        })
        .nodePointerAreaPaint((n, color, ctx) => { ctx.beginPath(); ctx.arc(n.x, n.y, (n._r || 4) + 3, 0, 7); ctx.fillStyle = color; ctx.fill(); })
        .onRenderFramePost((ctx, k) => {
          const placed = [], ns = G.graphData().nodes, bounds = viewBounds(G, el, k);
          const center = ns.find(n => n.ring === 0);
          for (const n of ns) placed.push([n.x * k - n._r * k, n.y * k - n._r * k, n.x * k + n._r * k, n.y * k + n._r * k]);
          const order = [];
          if (hover) order.push(hover, ...ns.filter(n => D.adj[hover.i].has(n.i)));
          order.push(center, ...ns.filter(n => n.ring === 1).sort((a, b) => b.deg - a.deg), ...ns.filter(n => n.ring === 2).sort((a, b) => b.deg - a.deg));
          const done = new Set();
          for (const n of order) {
            if (!n || done.has(n)) continue; done.add(n);
            if (n.ring === 2 && n !== hover && !(hover && D.adj[hover.i].has(n.i))) continue;
            const big = n === center || n === hover;
            pill(ctx, k, placed, n.x, n.y, n._r, n.l, D.cats[n.c][1], { px: big ? 12.5 : 11.5, weight: big ? 650 : 560, force: big, bounds });
          }
        })
        .onNodeHover(n => { hover = n || null; el.style.cursor = n ? 'pointer' : ''; })
        .onNodeClick(n => opts.onClick ? opts.onClick(n) : (location.href = n.u))
        .cooldownTicks(120).warmupTicks(40)
        .onEngineStop(() => { if (!fitted) { fitted = true; G.zoomToFit(300, 46); } });
      G.d3Force('charge').strength(-170).distanceMax(260);
      G.d3Force('link').distance(l => (l.source.ring === 0 || l.target.ring === 0) ? 62 : 48).strength(.5);
      const set = () => {
        const d = localData(D, id, hops);
        if (!d || d.nodes.length < 2) { G.graphData({ nodes: d ? d.nodes : [], links: [] }); el.insertAdjacentHTML('beforeend', '<span class="lg-empty">Brak powiązań</span>'); return; }
        el.querySelector('.lg-empty')?.remove();
        d.nodes[0].fx = 0; d.nodes[0].fy = 0;
        fitted = false; G.graphData(d);
      };
      set();
      graphs.add(G);
      new ResizeObserver(() => { G.width(el.clientWidth).height(el.clientHeight); if (fitted) G.zoomToFit(0, 46); }).observe(el);
      const onSeg = e => { const b = e.target.closest('button[data-hops]'); if (!b) return; hops = +b.dataset.hops; seg.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', String(x === b))); set(); };
      if (seg) { seg.onclick = onSeg; seg.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', String(x.dataset.hops === '1'))); }
      return { G, setId: nid => { id = nid; set(); } };
    });
  }

  /* ------------------------------------------------------------ global graph */
  function hash32(s) { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
  function rng(seed) { return () => { seed = (seed + 0x6D2B79F5) | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }

  async function mountGlobal() {
    const el = document.getElementById('gp'), D = await load();
    const loading = document.getElementById('gp-loading');
    const nodes = D.nodes.map(n => ({ ...n }));
    const links = D.links.map(([a, b, w]) => ({ source: a, target: b, w }));
    // cluster centres on a ring, NAV order, each cluster's arc proportional to its size
    const count = {}; for (const n of nodes) count[n.c] = (count[n.c] || 0) + 1;
    const cats = D.order.filter(c => count[c]);
    const rad = c => 16 * Math.sqrt(count[c]) + 22;
    const total = cats.reduce((s, c) => s + 2 * rad(c) + 70, 0), R = total / (2 * Math.PI);
    // ellipse follows the canvas: wide on desktop, tall on a phone
    const tall = el.clientHeight > el.clientWidth * 1.2, sx = tall ? 1 : 1.25, sy = tall ? 1.6 : 1;
    const centre = {}; let acc = 0;
    for (const c of cats) { const a = ((acc + rad(c) + 35) / total) * 2 * Math.PI - Math.PI / 2; centre[c] = { x: Math.cos(a) * R * sx, y: Math.sin(a) * R * sy }; acc += 2 * rad(c) + 70; }
    const rand = rng(hash32(nodes.map(n => n.id).join()));
    const key = 'kb-layout-' + hash32(nodes.map(n => n.id).join() + '|' + links.length + (tall ? '|tall' : ''));
    let cached = null; try { cached = JSON.parse(localStorage.getItem(key)); } catch { }
    nodes.forEach((n, i) => {
      const c = centre[n.c];
      if (cached && cached[i]) { n.x = cached[i][0]; n.y = cached[i][1]; }
      else { const a = rand() * 6.283, r = rand() * rad(n.c); n.x = c.x + Math.cos(a) * r; n.y = c.y + Math.sin(a) * r; }
      if (n.hub) { n.fx = c.x; n.fy = c.y; }
    });

    let hover = null, selected = null, focusCat = null, clusters = [];
    const nb = n => n ? D.adj[n.i] : null;
    const lit = n => {
      const f = selected || hover;
      if (f) return n === f || nb(f).has(n.i) || (hover && (n === hover || nb(hover).has(n.i)));
      if (focusCat) return n.c === focusCat;
      return true;
    };
    const G = ForceGraph()(el).graphData({ nodes, links }).nodeId('i')
      .width(el.clientWidth).height(el.clientHeight).backgroundColor('rgba(0,0,0,0)')
      .autoPauseRedraw(true).enableNodeDrag(false).minZoom(0.15).maxZoom(14)
      .linkVisibility(l => l.w !== 0)
      .linkCurvature(0.22)
      .linkColor(l => {
        const f = selected || hover;
        if (f) { const on = l.source === f || l.target === f || (hover && (l.source === hover || l.target === hover)); return on ? rgba(D.cats[(l.source === f || l.source === hover ? l.target : l.source).c][1], .85) : C.edge + '0.025)'; }
        if (focusCat) return l.source.c === focusCat && l.target.c === focusCat ? C.edge + '0.2)' : C.edge + '0.02)';
        return C.edge + (l.source.c === l.target.c ? '0.07)' : '0.045)');
      })
      .linkWidth(l => { const f = selected || hover; return f && (l.source === f || l.target === f || l.source === hover || l.target === hover) ? 1.5 : 0.6; })
      .nodeLabel(n => `<div class="gp-tt"><b>${esc(n.t)}</b><small>${esc(D.cats[n.c][0])}${n.d ? ' · ' + n.d : ''}</small></div>`)
      .nodeCanvasObject((n, ctx, k) => {
        // dots grow sublinearly with zoom so a zoomed-in cluster stays airy
        const r = Math.max(radius(n) / (k > 1 ? Math.sqrt(k) : 1), 1.6 / k), col = D.cats[n.c][1];
        ctx.globalAlpha = lit(n) ? 1 : .13;
        ctx.beginPath(); ctx.arc(n.x, n.y, r, 0, 7);
        if (n.hub) { ctx.fillStyle = C.bg; ctx.fill(); ctx.lineWidth = 2.2 / k + .6; ctx.strokeStyle = col; ctx.stroke(); ctx.beginPath(); ctx.arc(n.x, n.y, r * .45, 0, 7); ctx.fillStyle = col; ctx.fill(); }
        else { ctx.fillStyle = col; ctx.fill(); }
        if (n === selected) { ctx.beginPath(); ctx.arc(n.x, n.y, r + 4 / k, 0, 7); ctx.lineWidth = 2 / k; ctx.strokeStyle = C.accent; ctx.stroke(); }
        ctx.globalAlpha = 1; n._r = r;
      })
      .nodePointerAreaPaint((n, color, ctx, k) => { ctx.beginPath(); ctx.arc(n.x, n.y, Math.max(n._r || 3, 5 / k), 0, 7); ctx.fillStyle = color; ctx.fill(); })
      .onRenderFramePost((ctx, k) => {
        const placed = [];
        const vw = el.clientWidth, vh = el.clientHeight, tl = G.screen2GraphCoords(0, 0), br = G.screen2GraphCoords(vw, vh);
        const bounds = viewBounds(G, el, k), er = el.getBoundingClientRect(), ox = tl.x * k - er.left, oy = tl.y * k - er.top;
        // overlays (title, legend, zoom, panel) are obstacles: no label hides under them
        for (const o of el.parentNode.querySelectorAll('.gp-title, .gp-find, .gp-legend, .gp-zoom, .gp-panel:not([hidden])')) {
          const r = o.getBoundingClientRect(); placed.push([r.left + ox, r.top + oy, r.right + ox, r.bottom + oy]);
        }
        const inView = n => n.x > tl.x && n.x < br.x && n.y > tl.y && n.y < br.y;
        const f = selected || hover;
        // 1. cluster titles (fade out when deep in)
        if (k < 2.6 || focusCat) {
          const fade = k < 1.8 ? 1 : Math.max(0, (2.6 - k) / .8);
          ctx.save();
          const small = vw < 640, px = small ? 12.5 : 15, spx = small ? 10.5 : 11.5, h = small ? 23 : 28;
          // biggest clusters claim their spot first; a title that cannot find a free spot is skipped (the legend names it)
          for (const c of [...clusters].sort((a, b) => (b.cat === focusCat) - (a.cat === focusCat) || b.n - a.n)) {
            c.box = null;
            const a = c.cat === focusCat ? 1 : fade;
            // clamping keeps a title on screen, but only for clusters actually in view
            if (!a || c.x < tl.x || c.x > br.x || c.y < tl.y || c.y > br.y) continue;
            const dim = (focusCat && c.cat !== focusCat) || (f && f.c !== c.cat);
            const text = c.label, sub = String(c.n);
            const tw = textW(ctx, text, px, 700), sw = textW(ctx, sub, spx, 600), w = tw + sw + (small ? 28 : 34);
            const cx = c.x * k - w / 2, top = (c.y - c.r) * k - h - 6, bot = (c.y + c.r) * k + 6, mid = c.y * k - h / 2;
            let box = null;
            for (const [x0, y0] of [[cx, top], [cx, bot], [cx, mid]]) {
              const x = Math.max(bounds[0], Math.min(x0, bounds[2] - w)), y = Math.max(bounds[1], Math.min(y0, bounds[3] - h));
              const r = [x, y, x + w, y + h];
              if (!hit(r, placed)) { box = r; break; }
            }
            if (!box && c.cat === focusCat) box = [cx, top, cx + w, top + h];
            if (!box) continue;
            const [sx, sy] = box;
            c.box = [sx / k, sy / k, (sx + w) / k, (sy + h) / k];
            placed.push(box);
            ctx.save(); ctx.scale(1 / k, 1 / k); ctx.globalAlpha = a * (dim ? .35 : 1);
            roundRect(ctx, sx, sy, w, h, 8); ctx.fillStyle = C.pill; ctx.fill();
            ctx.lineWidth = 1.2; ctx.strokeStyle = rgba(c.color, .55); ctx.stroke();
            ctx.beginPath(); ctx.arc(sx + (small ? 10 : 12), sy + h / 2, small ? 3.5 : 4, 0, 7); ctx.fillStyle = c.color; ctx.fill();
            ctx.font = `700 ${px}px ${FONT}`; ctx.textBaseline = 'middle'; ctx.fillStyle = C.text; ctx.fillText(text, sx + (small ? 18 : 22), sy + h / 2 + .5);
            ctx.font = `600 ${spx}px ${FONT}`; ctx.fillStyle = C.mute; ctx.fillText(sub, sx + (small ? 22 : 26) + tw, sy + h / 2 + 1);
            ctx.restore();
          }
          ctx.restore();
        } else clusters.forEach(c => { c.box = null; });
        // 2. dots are obstacles for labels
        for (const n of nodes) if (inView(n) && n._r) { const r = Math.max(n._r * k, 3); placed.push([n.x * k - r, n.y * k - r, n.x * k + r, n.y * k + r]); }
        // 3. focus labels, then level of detail by degree
        const order = [];
        if (selected) order.push(selected);
        if (hover && hover !== selected) order.push(hover);
        for (const g of [selected, hover]) if (g) order.push(...[...nb(g)].map(i => nodes[i]).filter(n => !n.hub).sort((a, b) => b.deg - a.deg));
        const budget = k < 0.9 ? 0 : Math.min(160, Math.round(14 * k * k));
        if (budget) {
          const pool = nodes.filter(n => !n.hub && inView(n) && lit(n) && (!focusCat || n.c === focusCat)).sort((a, b) => b.deg - a.deg).slice(0, budget * 2);
          order.push(...pool);
        }
        const done = new Set(); let shown = 0;
        for (const n of order) {
          if (done.has(n) || !inView(n)) continue; done.add(n);
          const isF = n === selected || n === hover;
          if (!isF && !lit(n)) continue;
          if (pill(ctx, k, placed, n.x, n.y, n._r || 3, n.l, D.cats[n.c][1], { px: isF ? 13 : 12, weight: isF ? 650 : 560, force: isF, bounds, ring: isF ? rgba(C.accent, .7) : null })) shown++;
          if (!isF && shown > budget + 40) break;
        }
      })
      .onNodeHover(n => { hover = n || null; el.style.cursor = n ? 'pointer' : ''; })
      .onNodeClick(n => select(n, true))
      .onBackgroundClick(e => {
        const p = G.screen2GraphCoords(e.offsetX, e.offsetY);
        const c = clusters.find(c => (c.box && p.x >= c.box[0] && p.x <= c.box[2] && p.y >= c.box[1] && p.y <= c.box[3])) || clusters.find(c => Math.hypot(p.x - c.x, p.y - c.y) < c.r);
        if (c && G.zoom() < 2.4) zoomCat(c.cat); else { select(null); setCat(null); }
      });

    // forces: own cluster pull + weak cross-cluster links
    const clusterForce = alpha => { for (const n of nodes) { const c = centre[n.c]; n.vx += (c.x - n.x) * 0.09 * alpha; n.vy += (c.y - n.y) * 0.09 * alpha; } };
    clusterForce.initialize = () => { };
    G.d3Force('cluster', clusterForce);
    G.d3Force('center', null);
    G.d3Force('charge').strength(n => n.hub ? -60 : -26).distanceMax(170);
    G.d3Force('link').distance(l => l.w === 0 ? rad(l.target.c ?? nodes[l.target].c) * .55 : 26).strength(l => {
      const a = l.source.c ?? nodes[l.source].c, b = l.target.c ?? nodes[l.target].c;
      return l.w === 0 ? 0.02 : a === b ? 0.18 : 0.004;
    });

    const finish = () => {
      clusters = cats.map(cat => {
        const ns = nodes.filter(n => n.c === cat);
        const x = ns.reduce((s, n) => s + n.x, 0) / ns.length, y = ns.reduce((s, n) => s + n.y, 0) / ns.length;
        const ds = ns.map(n => Math.hypot(n.x - x, n.y - y)).sort((a, b) => a - b);
        return { cat, x, y, r: (ds[Math.floor(ds.length * .92)] || 10) + 6, n: ns.filter(n => !n.hub).length, label: D.cats[cat][0], color: D.cats[cat][1] };
      });
      try { localStorage.setItem(key, JSON.stringify(nodes.map(n => [Math.round(n.x * 10) / 10, Math.round(n.y * 10) / 10]))); } catch { }
      loading.hidden = true;
    };
    G.warmupTicks(cached ? 0 : 260).cooldownTicks(0);
    G.onEngineStop(() => { if (!clusters.length) { finish(); fitAll(0); fromHash(); } });
    graphs.add(G);
    new ResizeObserver(() => G.width(el.clientWidth).height(el.clientHeight)).observe(el);

    // ------------------------------------------------ UI
    // zoomToFit ignores the overlays; fit into the canvas area they leave free instead
    const fitTo = (ms, filter = () => true, maxK = 14) => {
      const ns = nodes.filter(filter); if (!ns.length) return;
      const W = el.clientWidth, H = el.clientHeight, er = el.getBoundingClientRect();
      const top = document.querySelector('.gp-top').getBoundingClientRect(), lg = legend.getBoundingClientRect();
      const mobile = innerWidth < 640, pad = mobile ? 18 : 36;
      const x0 = (mobile ? 0 : lg.right - er.left) + pad, x1 = W - pad - (mobile ? 0 : 56);
      const y0 = top.bottom - er.top + 44, y1 = (mobile ? lg.top - er.top : H) - pad;
      let ax = Infinity, ay = Infinity, bx = -Infinity, by = -Infinity;
      for (const n of ns) { ax = Math.min(ax, n.x); ay = Math.min(ay, n.y); bx = Math.max(bx, n.x); by = Math.max(by, n.y); }
      const k = Math.min(maxK, Math.max(0.15, Math.min((x1 - x0) / Math.max(bx - ax, 1), (y1 - y0) / Math.max(by - ay, 1))));
      G.centerAt((ax + bx) / 2 - ((x0 + x1) / 2 - W / 2) / k, (ay + by) / 2 - ((y0 + y1) / 2 - H / 2) / k, ms);
      G.zoom(k, ms);
    };
    const fitAll = (ms = 600) => fitTo(ms);
    const legend = document.getElementById('gp-legend');
    const setCat = cat => {
      focusCat = cat;
      legend.querySelectorAll('.lg-chip').forEach(b => b.setAttribute('aria-pressed', String(!cat || b.dataset.cat === cat)));
    };
    const zoomCat = cat => { select(null); setCat(cat); fitTo(700, n => n.c === cat, 5); };
    legend.addEventListener('click', e => { const b = e.target.closest('.lg-chip'); if (b) focusCat === b.dataset.cat ? (setCat(null), fitAll()) : zoomCat(b.dataset.cat); });
    document.getElementById('gp-all').onclick = () => { select(null); setCat(null); fitAll(); };
    document.getElementById('gp-in').onclick = () => G.zoom(G.zoom() * 1.5, 300);
    document.getElementById('gp-out').onclick = () => G.zoom(G.zoom() / 1.5, 300);
    document.getElementById('gp-fit').onclick = () => { setCat(null); fitAll(); };

    const panel = document.getElementById('gp-panel'), pbody = panel.querySelector('.gp-panel-body'), pnb = panel.querySelector('.gp-nb');
    const plocal = panel.querySelector('.gp-local'), pseg = panel.querySelector('.seg');
    let local = null;
    function select(n, fly) {
      selected = n || null;
      if (!n) { panel.hidden = true; if (location.hash) history.replaceState(null, '', location.pathname); return; }
      const [label, color, ic] = D.cats[n.c];
      pbody.innerHTML = `<span class="cat-badge" style="--c:${color}">${icon(ic)}<span>${esc(label)}</span></span><h2>${esc(n.t)}</h2>${n.x ? '' : ''}<p>${esc(D.nodes[n.i].x)}</p>`
        + `<div class="chips">${n.d ? `<span class="chip">${icon('calendar')}${n.d}</span>` : ''}${n.s ? `<span class="status s-${n.s}">${STATUS[n.s]}</span>` : ''}<span class="chip">${icon('link')}${n.deg} powiązań</span></div>`
        + `<a class="btn btn-soft" href="${esc(n.u)}">Otwórz ${n.c === 'raporty' ? 'raport' : 'notatkę'} ${icon('arrowright')}</a>`;
      const ns = [...D.adj[n.i]].map(i => D.nodes[i]).filter(m => !m.hub).sort((a, b) => b.deg - a.deg);
      pnb.innerHTML = ns.map(m => `<a href="${esc(m.u)}" data-i="${m.i}" style="--c:${D.cats[m.c][1]}"><i></i>${esc(m.t)}</a>`).join('');
      panel.hidden = false;
      history.replaceState(null, '', '#' + encodeURIComponent(n.id));
      if (!local) mountLocal(plocal, n.id, pseg, { onClick: m => select(nodes[m.i], true) }).then(l => { local = l; });
      else local.setId(n.id);
      if (fly) { const off = innerWidth > 900 ? 190 / Math.max(G.zoom(), 2.2) : 0; G.centerAt(n.x + off, n.y + (innerWidth <= 640 ? 120 / Math.max(G.zoom(), 2.2) : 0), 650); if (G.zoom() < 2.2) G.zoom(2.2, 650); }
    }
    pnb.addEventListener('click', e => { const a = e.target.closest('a[data-i]'); if (!a) return; e.preventDefault(); select(nodes[+a.dataset.i], true); });
    document.getElementById('gp-close').onclick = () => select(null);
    document.addEventListener('keydown', e => { if (e.key === 'Escape' && !panel.hidden) select(null); });

    const list = document.getElementById('gp-list'), q = document.getElementById('gp-q');
    list.innerHTML = nodes.filter(n => !n.hub).map(n => `<option value="${esc(n.t)}">`).join('');
    const find = () => { const v = q.value.trim().toLowerCase(); if (!v) return; const n = nodes.find(n => n.t.toLowerCase() === v) || nodes.find(n => !n.hub && n.t.toLowerCase().includes(v)); if (n) { setCat(null); select(n, true); } };
    q.addEventListener('change', find); q.addEventListener('keydown', e => { if (e.key === 'Enter') find(); });
    const fromHash = () => { const id = decodeURIComponent(location.hash.slice(1)); const n = id && nodes[D.byId.get(id)?.i]; if (n) setTimeout(() => select(n, true), 50); };
  }

  window.KBGraph = { mountLocal: (el, id, seg, o) => mountLocal(el, id, seg, o) };
  if (document.getElementById('gp')) requestAnimationFrame(() => setTimeout(mountGlobal, 30));
})();
