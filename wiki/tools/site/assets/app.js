/* KERNEL knowledge base: theme, navigation drawer, search (palette + page), filters, tables, peeks, timeline. */
(() => {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
  const icon = (n, c = 'i') => `<svg class="${c}" aria-hidden="true"><use href="/assets/icons.svg#${n}"></use></svg>`;
  const STATUS = { 'aktualne': 'aktualne', 'do-sprawdzenia': 'do sprawdzenia', 'nieaktualne': 'nieaktualne' };
  const statusChip = s => s ? `<span class="status s-${s}">${STATUS[s] || s}</span>` : '';
  const store = { get: k => { try { return JSON.parse(localStorage.getItem(k)); } catch { return null; } }, set: (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch { } } };

  /* ------------------------------------------------------------ folding (diacritics, case) */
  const DIA = { 'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n', 'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z', 'ä': 'a', 'ö': 'o', 'ü': 'u', 'é': 'e', 'è': 'e', 'á': 'a', 'à': 'a', 'í': 'i', 'ú': 'u', 'â': 'a', 'ê': 'e', 'î': 'i', 'ô': 'o', 'û': 'u', 'ç': 'c', 'ñ': 'n', 'ø': 'o', 'å': 'a', 'č': 'c', 'š': 's', 'ž': 'z', 'ř': 'r', 'ý': 'y' };
  const DIA_RE = /[ąćęłńóśźżäöüéèáàíúâêîôûçñøåčšžřý]/g;
  const fold = s => {
    const l = String(s || '').toLowerCase();
    return (l.length === String(s || '').length ? l : String(s).replace(/./gsu, c => { const x = c.toLowerCase(); return x.length === c.length ? x : c; })).replace(DIA_RE, c => DIA[c]);
  };

  /* ------------------------------------------------------------ theme + drawer */
  const root = document.documentElement;
  $('.theme-btn')?.addEventListener('click', () => {
    const t = root.dataset.theme === 'light' ? 'dark' : 'light';
    root.dataset.theme = t;
    try { localStorage.setItem('kb-theme', t); } catch { }
    window.dispatchEvent(new CustomEvent('kb-theme'));
  });
  const menuBtn = $('.menu-btn');
  const setNav = open => { document.body.classList.toggle('nav-open', open); menuBtn?.setAttribute('aria-expanded', String(open)); };
  menuBtn?.addEventListener('click', () => setNav(!document.body.classList.contains('nav-open')));
  $$('[data-close-nav]').forEach(e => e.addEventListener('click', () => setNav(false)));
  const cur = $('.nav-item[aria-current]');
  if (cur) cur.scrollIntoView({ block: 'center' });

  /* ------------------------------------------------------------ data loaders (cached per page) */
  const cache = {};
  const getJSON = url => (cache[url] ??= fetch(url).then(r => { if (!r.ok) throw new Error(url); return r.json(); }));

  let INDEX = null;
  const loadIndex = () => INDEX ? Promise.resolve(INDEX) : getJSON('/data/search.json').then(data => {
    const docs = data.docs.map(r => ({ u: r[0], t: r[1], c: r[2], s: r[3], g: r[4], d: r[5], x: r[6], b: r[7] }));
    for (const d of docs) { d.ft = fold(d.t); d.fg = fold(d.g); d.fx = fold(d.x); d.fb = fold(d.b); d.fu = fold(d.u); }
    INDEX = { cats: data.cats, docs, tags: data.tags };
    return INDEX;
  });

  /* ------------------------------------------------------------ search engine */
  function parseQuery(q) {
    const terms = [];
    String(q || '').replace(/"([^"]+)"|„([^”"]+)[”"]|(\S+)/g, (_, a, b, c) => { const t = fold((a || b || c || '').trim()); if (t) terms.push(t); return ''; });
    return terms.filter((t, i) => t.length > 1 || terms.length === 1);
  }
  const count = (h, n, cap) => { let k = 0, i = h.indexOf(n); while (i >= 0 && k < cap) { k++; i = h.indexOf(n, i + n.length); } return k; };
  function score(d, terms, fq) {
    let s = 0;
    for (const t of terms) {
      const inT = d.ft.indexOf(t), inG = d.fg.indexOf(t), inX = d.fx.indexOf(t), inU = d.fu.indexOf(t);
      const nb = inT < 0 && inG < 0 && inX < 0 && inU < 0 ? count(d.fb, t, 6) : count(d.fb, t, 6);
      if (inT < 0 && inG < 0 && inX < 0 && inU < 0 && !nb) return 0;
      if (inT >= 0) s += 30 + (inT === 0 || /\W/.test(d.ft[inT - 1]) ? 12 : 0);
      if (inG >= 0) s += 14;
      if (inX >= 0) s += 9;
      if (inU >= 0) s += 8;
      s += nb * 2;
    }
    if (fq && d.ft === fq) s += 60;
    else if (fq && terms.length > 1 && d.ft.includes(fq)) s += 25;
    if (d.s === 'nieaktualne') s *= .7;
    if (d.c === 'raporty') s *= .85;
    return s;
  }
  function search(q, filt = {}, limit = 1e9) {
    const terms = parseQuery(q), fq = fold(q.trim());
    const out = [];
    for (const d of INDEX.docs) {
      if (filt.cat && d.c !== filt.cat) continue;
      if (filt.status && d.s !== filt.status) continue;
      if (filt.tag && !(' ' + d.g + ' ').includes(' ' + filt.tag + ' ')) continue;
      if (filt.from && (!d.d || d.d < filt.from)) continue;
      if (filt.to && (!d.d || d.d > filt.to)) continue;
      const s = terms.length ? score(d, terms, fq) : 1;
      if (s > 0) out.push([s, d]);
    }
    out.sort((a, b) => b[0] - a[0] || (b[1].d || '').localeCompare(a[1].d || ''));
    return { terms, hits: out.slice(0, limit).map(x => x[1]), total: out.length };
  }
  function highlight(text, terms) {
    if (!terms.length) return esc(text);
    const f = fold(text), ranges = [];
    for (const t of terms) { let i = f.indexOf(t); while (i >= 0) { ranges.push([i, i + t.length]); i = f.indexOf(t, i + t.length); } }
    if (!ranges.length) return esc(text);
    ranges.sort((a, b) => a[0] - b[0]);
    let out = '', pos = 0;
    for (const [a, b] of ranges) { if (a < pos) continue; out += esc(text.slice(pos, a)) + '<mark>' + esc(text.slice(a, b)) + '</mark>'; pos = b; }
    return out + esc(text.slice(pos));
  }
  function snippet(d, terms, len = 220) {
    let best = -1;
    for (const t of terms) { const i = d.fb.indexOf(t); if (i >= 0 && (best < 0 || i < best)) best = i; }
    if (best < 0) return '';
    let a = Math.max(0, best - 70); if (a > 0) { const sp = d.b.indexOf(' ', a); if (sp > 0 && sp < best) a = sp + 1; }
    let b = Math.min(d.b.length, a + len); if (b < d.b.length) { const sp = d.b.lastIndexOf(' ', b); if (sp > best) b = sp; }
    return (a > 0 ? '… ' : '') + highlight(d.b.slice(a, b), terms) + (b < d.b.length ? ' …' : '');
  }

  /* ------------------------------------------------------------ recent pages */
  const art = $('article.doc[data-id]');
  if (art) {
    const h = (store.get('kb-recent') || []).filter(r => r.u !== location.pathname);
    h.unshift({ u: location.pathname, t: $('h1', art)?.textContent || document.title, c: art.dataset.cat || '' });
    store.set('kb-recent', h.slice(0, 8));
  }

  /* ------------------------------------------------------------ command palette */
  const pal = $('#palette'), pin = pal && $('input', pal), pres = pal && $('.palette-results', pal);
  let sel = 0, items = [];
  const catOf = c => (INDEX?.cats?.[c]) || ['', '#999', 'grid'];
  function palRow(d, terms, i) {
    const [label, color, ic] = catOf(d.c);
    const sub = terms.length ? (snippet(d, terms, 120) || highlight(d.x, terms)) : esc(d.x || '');
    return `<a class="pr" role="option" id="pr${i}" href="${esc(d.u)}" aria-selected="${i === sel}" style="--c:${color}"><span class="mini-ic">${icon(ic)}</span><span style="min-width:0"><b>${highlight(d.t, terms)}</b><small>${sub}</small></span><span class="pr-cat">${esc(label)}</span></a>`;
  }
  function palRender() {
    const q = pin.value;
    if (!q.trim()) {
      const recent = store.get('kb-recent') || [];
      const quick = [{ u: '/rekordy.html', t: 'Rekordy', c: '' }, { u: '/graf.html', t: 'Graf wiedzy', c: '' }, { u: '/os-czasu.html', t: 'Oś czasu', c: '' }, { u: '/decyzje/', t: 'Decyzje', c: 'decyzje' }];
      items = [...recent.slice(0, 6), ...quick.filter(x => !recent.some(r => r.u === x.u))].map(r => ({ u: r.u, t: r.t, c: r.c, x: '', b: '', fb: '' }));
      sel = Math.min(sel, items.length - 1);
      pres.innerHTML = (recent.length ? '<div class="palette-group">Ostatnio oglądane</div>' : '<div class="palette-group">Na skróty</div>') + items.map((d, i) => palRow(d, [], i)).join('');
      return;
    }
    if (!INDEX) { pres.innerHTML = '<div class="palette-msg">Ładowanie indeksu…</div>'; return; }
    const r = search(q, {}, 12);
    items = r.hits; sel = Math.min(sel, Math.max(0, items.length - 1));
    pres.innerHTML = items.length
      ? items.map((d, i) => palRow(d, r.terms, i)).join('') + (r.total > 12 ? `<a class="pr" href="/szukaj.html?q=${encodeURIComponent(q)}" style="--c:var(--accent)"><span class="mini-ic">${icon('search')}</span><span><b>Wszystkie wyniki (${r.total})</b><small>Otwórz wyszukiwanie z filtrami</small></span><span></span></a>` : '')
      : `<div class="palette-msg">Brak wyników dla „${esc(q)}”.</div>`;
  }
  function palOpen() {
    if (!pal) return;
    if ($('#sq')) { $('#sq').focus(); $('#sq').select(); return; }
    pal.hidden = false; document.body.style.overflow = 'hidden';
    pin.value = ''; sel = 0; palRender(); pin.focus();
    loadIndex().then(() => { if (!pal.hidden) palRender(); });
  }
  function palClose() { if (!pal || pal.hidden) return; pal.hidden = true; document.body.style.overflow = ''; }
  function palMove(dir) {
    const rows = $$('.pr', pres); if (!rows.length) return;
    sel = (sel + dir + rows.length) % rows.length;
    rows.forEach((r, i) => r.setAttribute('aria-selected', String(i === sel)));
    rows[sel].scrollIntoView({ block: 'nearest' });
  }
  if (pal) {
    pin.addEventListener('input', () => { sel = 0; palRender(); });
    pin.addEventListener('keydown', e => {
      if (e.key === 'ArrowDown') { e.preventDefault(); palMove(1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); palMove(-1); }
      else if (e.key === 'Enter') { e.preventDefault(); const r = $$('.pr', pres)[sel]; if (r) location.href = r.getAttribute('href'); else if (pin.value.trim()) location.href = '/szukaj.html?q=' + encodeURIComponent(pin.value); }
    });
    pal.addEventListener('click', e => { if (e.target === pal) palClose(); });
    $('.palette-all', pal).addEventListener('click', e => { if (pin.value.trim()) { e.preventDefault(); location.href = '/szukaj.html?q=' + encodeURIComponent(pin.value); } });
  }
  $$('[data-open-search]').forEach(b => b.addEventListener('click', palOpen));
  document.addEventListener('keydown', e => {
    const t = e.target, typing = t instanceof HTMLElement && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName));
    if ((e.key === '/' && !typing) || (e.key.toLowerCase() === 'k' && (e.metaKey || e.ctrlKey))) { e.preventDefault(); palOpen(); }
    else if (e.key === 'Escape') { palClose(); setNav(false); }
  });

  /* ------------------------------------------------------------ search page */
  if ($('#sq')) {
    const q = $('#sq'), fc = $('#sf-cat'), fs = $('#sf-status'), ft = $('#sf-tag'), ff = $('#sf-from'), fto = $('#sf-to');
    const res = $('#results'), cnt = $('#scount'), fac = $('#facets');
    const P = new URLSearchParams(location.search);
    q.value = P.get('q') || ''; fc.value = P.get('cat') || ''; fs.value = P.get('status') || ''; ft.value = P.get('tag') || ''; ff.value = P.get('od') || ''; fto.value = P.get('do') || '';
    let shown = 60;
    const run = () => {
      if (!INDEX) return;
      const filt = { cat: fc.value, status: fs.value, tag: ft.value.replace(/^#/, '').trim(), from: ff.value, to: fto.value };
      const P2 = new URLSearchParams();
      if (q.value.trim()) P2.set('q', q.value.trim());
      if (filt.cat) P2.set('cat', filt.cat); if (filt.status) P2.set('status', filt.status); if (filt.tag) P2.set('tag', filt.tag);
      if (filt.from) P2.set('od', filt.from); if (filt.to) P2.set('do', filt.to);
      history.replaceState(null, '', '?' + P2.toString());
      const any = q.value.trim() || filt.cat || filt.status || filt.tag || filt.from || filt.to;
      if (!any) { res.innerHTML = ''; fac.innerHTML = ''; cnt.textContent = `${INDEX.docs.length} dokumentów w indeksie. Wpisz zapytanie albo wybierz filtr.`; return; }
      const all = search(q.value, { ...filt, cat: '' });
      const per = {}; for (const d of all.hits) per[d.c] = (per[d.c] || 0) + 1;
      fac.innerHTML = Object.entries(per).sort((a, b) => b[1] - a[1]).map(([c, n]) => { const [l, col] = catOf(c); return `<button type="button" class="facet" data-c="${c}" aria-pressed="${filt.cat === c}" style="--c:${col}"><i></i>${esc(l)}<span>${n}</span></button>`; }).join('');
      const r = filt.cat ? search(q.value, filt) : all;
      if (!q.value.trim()) r.hits.sort((a, b) => (b.d || '').localeCompare(a.d || ''));
      cnt.textContent = r.total ? `${r.total} ${r.total === 1 ? 'wynik' : r.total % 10 >= 2 && r.total % 10 <= 4 && (r.total % 100 < 10 || r.total % 100 >= 20) ? 'wyniki' : 'wyników'}` : 'Brak wyników.';
      res.innerHTML = r.hits.slice(0, shown).map(d => {
        const [l, col] = catOf(d.c);
        const sn = r.terms.length ? snippet(d, r.terms) : '';
        return `<li><a class="res" href="${esc(d.u)}" style="--c:${col}"><div class="res-top"><span class="card-cat">${esc(l)}</span>${d.d ? `<time>${d.d}</time>` : ''}${statusChip(d.s)}</div><h3>${highlight(d.t, r.terms)}</h3>${d.x ? `<p>${highlight(d.x, r.terms)}</p>` : ''}${sn ? `<p class="snip">${sn}</p>` : ''}<div class="res-url">${esc(d.u)}</div></a></li>`;
      }).join('') + (r.hits.length > shown ? `<li><button type="button" class="btn" id="more">Pokaż więcej (${r.hits.length - shown})</button></li>` : '');
    };
    let timer;
    const later = () => { clearTimeout(timer); shown = 60; timer = setTimeout(run, 60); };
    [q, ft].forEach(e => e.addEventListener('input', later));
    [fc, fs, ff, fto].forEach(e => e.addEventListener('change', () => { shown = 60; run(); }));
    fac.addEventListener('click', e => { const b = e.target.closest('.facet'); if (!b) return; fc.value = fc.value === b.dataset.c ? '' : b.dataset.c; shown = 60; run(); });
    res.addEventListener('click', e => { if (e.target.id === 'more') { shown += 100; run(); } });
    $('#sf-reset').addEventListener('click', () => { q.value = ft.value = ff.value = fto.value = ''; fc.value = fs.value = ''; run(); q.focus(); });
    cnt.textContent = 'Ładowanie indeksu…';
    loadIndex().then(ix => { $('#sf-tags').innerHTML = ix.tags.map(t => `<option value="${esc(t)}">`).join(''); run(); });
  }

  /* ------------------------------------------------------------ category cards */
  const cardsBox = $('[data-cards]');
  if (cardsBox) {
    const tb = $('[data-cards-toolbar]'), all = $$('.card', cardsBox), shown = $('.shown', tb), empty = $('.empty');
    const fq = $('.filter input', tb), tag = $('[data-filter=tag]', tb), sort = $('[data-sort]', tb), seg = $('[data-filter=status]', tb);
    let status = '';
    for (const c of all) c._q = fold(c.dataset.q);
    const apply = () => {
      const terms = parseQuery(fq.value), t = tag?.value || '';
      let n = 0;
      for (const c of all) {
        const ok = (!status || c.dataset.s === status) && (!t || (' ' + c.dataset.g + ' ').includes(' ' + t + ' ')) && terms.every(x => c._q.includes(x));
        c.hidden = !ok; if (ok) n++;
      }
      shown.textContent = n === all.length ? `${n} pozycji` : `${n} z ${all.length}`;
      empty.hidden = n > 0;
    };
    const order = () => {
      const v = sort.value, arr = [...all];
      if (v === 'az') arr.sort((a, b) => $('h3', a).textContent.localeCompare($('h3', b).textContent, 'pl'));
      else arr.sort((a, b) => (a.dataset.d + a.dataset.a.padStart(12, '0')).localeCompare(b.dataset.d + b.dataset.a.padStart(12, '0')) * (v === 'old' ? 1 : -1));
      cardsBox.append(...arr);
    };
    fq.addEventListener('input', apply); tag?.addEventListener('change', apply); sort.addEventListener('change', order);
    seg?.addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; status = b.dataset.v; $$('button', seg).forEach(x => x.setAttribute('aria-pressed', String(x === b))); apply(); });
    apply();
  }

  /* ------------------------------------------------------------ tables: sort everywhere, filter on special pages */
  const num = s => { const m = String(s).replace(/\s(?=\d{3}\b)/g, '').replace(',', '.').match(/[-−]?\d+(?:\.\d+)?/); return m ? parseFloat(m[0].replace('−', '-')) : NaN; };
  for (const table of $$('.prose table')) {
    const body = table.tBodies[0]; if (!body || body.rows.length < 4) continue;
    $$('th', table).forEach((th, col) => {
      th.classList.add('sortable'); th.tabIndex = 0; th.setAttribute('aria-sort', 'none');
      const go = () => {
        const dir = th.getAttribute('aria-sort') === 'ascending' ? -1 : 1;
        $$('th', table).forEach(x => x.setAttribute('aria-sort', 'none'));
        th.setAttribute('aria-sort', dir === 1 ? 'ascending' : 'descending');
        const rows = [...body.rows], vals = rows.map(r => r.cells[col]?.textContent.trim() || '');
        const numeric = vals.filter(v => v).every(v => !isNaN(num(v)));
        const idx = rows.map((r, i) => i).sort((a, b) => {
          const x = vals[a], y = vals[b];
          if (!x !== !y) return x ? -1 : 1;
          return (numeric ? num(x) - num(y) : x.localeCompare(y, 'pl', { numeric: true })) * dir;
        });
        body.append(...idx.map(i => rows[i]));
      };
      th.addEventListener('click', go); th.addEventListener('keydown', e => { if (e.key === 'Enter') go(); });
    });
  }
  const tt = $('[data-table-tools]');
  if (tt) {
    const inp = $('input', tt), out = $('.rows-count', tt), scope = $('[data-tables]');
    const rows = $$('tbody tr', scope); for (const r of rows) r._f = fold(r.textContent);
    const upd = () => {
      const terms = parseQuery(inp.value); let n = 0;
      for (const r of rows) { const ok = terms.every(t => r._f.includes(t)); r.classList.toggle('hide', !ok); if (ok) n++; }
      out.textContent = terms.length ? `${n} z ${rows.length} wierszy` : `${rows.length} wierszy`;
      if (terms.length) $$('details.fold', scope).forEach(d => { d.open = $$('tbody tr:not(.hide)', d).length > 0; });
    };
    inp.addEventListener('input', upd); upd();
  }

  /* ------------------------------------------------------------ TOC scroll spy */
  const toc = $('.toc');
  if (toc && 'IntersectionObserver' in window) {
    const links = new Map($$('a', toc).map(a => [decodeURIComponent(a.hash.slice(1)), a]));
    const io = new IntersectionObserver(es => {
      for (const e of es) if (e.isIntersecting) { links.forEach(a => a.classList.remove('on')); links.get(e.target.id)?.classList.add('on'); }
    }, { rootMargin: '-70px 0px -70% 0px' });
    links.forEach((_, id) => { const h = document.getElementById(id); if (h) io.observe(h); });
  }

  /* ------------------------------------------------------------ wikilink hover previews */
  let NODES = null;
  const loadNodes = () => NODES ? Promise.resolve(NODES) : getJSON('/data/graph.json').then(g => (NODES = { cats: g.cats, by: new Map(g.nodes.map(n => [n[0], n])) }));
  if (matchMedia('(hover: hover)').matches && $('.prose a.wl')) {
    const peek = document.createElement('div'); peek.className = 'peek'; document.body.append(peek);
    let timer, curA = null;
    document.addEventListener('pointerover', e => {
      const a = e.target.closest?.('.prose a.wl[data-n]'); if (a === curA) return;
      curA = a; clearTimeout(timer); peek.classList.remove('on');
      if (!a) return;
      timer = setTimeout(() => loadNodes().then(({ cats, by }) => {
        const n = by.get(a.dataset.n); if (!n || curA !== a) return;
        const [l, col] = cats[n[2]] || ['', '#999'];
        peek.innerHTML = `<div class="pk-top"><span class="card-cat" style="--c:${col}">${esc(l)}</span>${n[5] ? `<time>${n[5]}</time>` : ''}${statusChip(n[4])}</div><b>${esc(n[1])}</b><p>${esc(n[6])}</p>`;
        const r = a.getBoundingClientRect(), w = 320;
        peek.style.left = Math.max(8, Math.min(innerWidth - w - 8, r.left)) + 'px';
        const below = r.bottom + 10, h = peek.offsetHeight || 140;
        peek.style.top = (below + h > innerHeight ? r.top - h - 10 : below) + 'px';
        peek.classList.add('on');
      }), 260);
    });
    addEventListener('scroll', () => { peek.classList.remove('on'); curA = null; }, { passive: true });
  }

  /* ------------------------------------------------------------ local graph widget (lazy) */
  const loadScript = src => new Promise((ok, bad) => { const s = document.createElement('script'); s.src = src; s.onload = ok; s.onerror = bad; document.head.append(s); });
  const lg = $('.local-graph[data-id]');
  if (lg) {
    const start = () => (window.ForceGraph ? Promise.resolve() : loadScript('/assets/vendor/force-graph.min.js'))
      .then(() => window.KBGraph ? null : loadScript('/assets/graph.js'))
      .then(() => window.KBGraph.mountLocal(lg, lg.dataset.id, $('.graph-card .seg')))
      .catch(() => { lg.innerHTML = '<span class="lg-empty">Graf niedostępny</span>'; });
    if ('IntersectionObserver' in window) {
      const io = new IntersectionObserver(es => { if (es.some(e => e.isIntersecting)) { io.disconnect(); start(); } }, { rootMargin: '200px' });
      io.observe(lg);
    } else start();
  }

  /* ------------------------------------------------------------ timeline */
  const tlData = $('#tl-data');
  if (tlData) {
    const items = JSON.parse(tlData.textContent).map(r => ({ u: r[0], t: r[1], c: r[2], s: r[3], d: r[4], e: r[5], a: r[6], x: r[7], g: r[8] }));
    for (const it of items) it.f = fold(it.t + ' ' + it.x + ' ' + it.g.join(' '));
    const colors = {}; $$('.tchip').forEach(b => colors[b.dataset.cat] = b.style.getPropertyValue('--c'));
    const labels = {}; $$('.tchip').forEach(b => labels[b.dataset.cat] = b.childNodes[1].textContent);
    const on = new Set(Object.keys(colors));
    let mode = 'a';
    const box = $('#tl'), hist = $('#tl-hist'), st = $('#tl-status'), q = $('#tl-q');
    const days = ['niedziela', 'poniedziałek', 'wtorek', 'środa', 'czwartek', 'piątek', 'sobota'];
    const render = () => {
      const terms = parseQuery(q.value), s = st.value, groups = new Map();
      for (const it of items) {
        if (!on.has(it.c) || (s && it.s !== s) || !terms.every(t => it.f.includes(t))) continue;
        const k = (mode === 'e' ? it.e || it.d : it.d) || '—';
        if (!groups.has(k)) groups.set(k, []);
        groups.get(k).push(it);
      }
      const keys = [...groups.keys()].sort().reverse();
      const max = Math.max(1, ...keys.map(k => groups.get(k).length));
      hist.innerHTML = [...keys].reverse().map(k => {
        const g = groups.get(k), per = {}; g.forEach(i => per[i.c] = (per[i.c] || 0) + 1);
        const segs = Object.entries(per).map(([c, n]) => `<span style="height:${(n / max) * 100}%;background:${colors[c]}"></span>`).join('');
        return `<button type="button" data-k="${k}" data-l="${k.slice(5)}" title="${k}: ${g.length}" style="height:100%">${segs}</button>`;
      }).join('');
      box.innerHTML = keys.map(k => {
        const g = groups.get(k).sort((a, b) => b.a - a.a);
        const dt = /^\d{4}-\d\d-\d\d$/.test(k) ? days[new Date(k + 'T12:00:00').getDay()] : '';
        return `<li class="tl-day" id="d-${k}"><div class="tl-dhead"><time>${k}</time><small>${dt} · ${g.length}</small></div><div class="tl-items">${g.map(it => `<a class="tl-it" href="${esc(it.u)}" style="--c:${colors[it.c]}"><b>${highlight(it.t, terms)}</b><span class="tl-side"><span class="tl-c">${esc(labels[it.c])}</span>${statusChip(it.s)}</span>${it.x ? `<p>${highlight(it.x, terms)}</p>` : ''}</a>`).join('')}</div></li>`;
      }).join('') || '<li class="empty">Nic nie pasuje do filtrów.</li>';
    };
    $$('.tchip').forEach(b => b.addEventListener('click', () => { const c = b.dataset.cat; on.has(c) ? on.delete(c) : on.add(c); b.setAttribute('aria-pressed', String(on.has(c))); render(); }));
    $('#tl-mode').addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; mode = b.dataset.v; $$('#tl-mode button').forEach(x => x.setAttribute('aria-pressed', String(x === b))); render(); });
    st.addEventListener('change', render); q.addEventListener('input', render);
    hist.addEventListener('click', e => { const b = e.target.closest('button'); if (b) document.getElementById('d-' + b.dataset.k)?.scrollIntoView({ behavior: 'smooth', block: 'start' }); });
    render();
  }
})();
