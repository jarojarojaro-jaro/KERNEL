<script lang="ts" module>
	export interface HighwayLane {
		id: 'cold' | 'hot';
		/** The lane's name on its HUD chip. */
		name: string;
		/** Measured decode speed (t/s, the median). */
		tps: number;
		/** Measured tokens accepted per step (MTP); 1 without speculation. */
		burst: number;
	}
</script>

<script lang="ts">
	/**
	 * The token highway: two lanes of generated text on a road that runs to a vanishing point and
	 * flows toward the viewer, as a race. Both lanes write the same text, cut into answers of
	 * `answer` tokens, at their measured median t/s (in steps of the measured MTP tokens per step):
	 * the newest row is written at the horizon and the road moves one row per row written. So the
	 * typical app's road crawls and ours rushes past 3,2× faster: its painted speed lettering, its
	 * edge dashes and every finished answer's chequered finish line come by 3,2× as often.
	 *
	 * Speed, ours only: rows near the camera smear back up the road and flare white-hot, warp
	 * streaks fly out of the vanishing point over our lane. The typical lane is dimmer and still.
	 *
	 * The near end (`.near`, in the page flow): two glass windshields, one per lane, each with the
	 * lane's name, the answer number, a live token counter, a progress bar and the answer itself,
	 * readable, written token by token at the lane's measured rate behind a caret (four lines, the
	 * newest at the bottom). When a lane finishes an answer, a stamp „Gotowe · 4,4 s” (answer ÷
	 * measured t/s) flashes once and the next answer starts in an empty panel. Lanes loop
	 * independently; nothing resets. `center` renders between the panels (the gauge). The canvas is
	 * absolutely positioned against the caller's positioned ancestor (full bleed behind the hero).
	 *
	 * One 2D canvas (devicePixelRatio ≤ 1,5). Each row is rendered once into a pooled bitmap and then
	 * only scaled per frame; rows that pass the camera are recycled. The loop runs only after the
	 * page is idle, while on screen and not paused, and continues where it stopped. Server HTML, no
	 * JS and reduced motion: the finish of the slower answer (both lanes' finish times on the chips,
	 * one still frame of the road). `keepClear`: an element laid over the scene's bottom centre (the
	 * gauge); the lanes leave the median free for it.
	 */
	import type { Snippet } from 'svelte';
	import { onMount, untrack } from 'svelte';
	import { TOK_PER_WORD } from '$lib/estimator';
	import { num } from '$lib/i18n';
	import { visible } from './actions';
	import { onFrame, reducedMotion, whenIdle } from './motion';

	let {
		lanes,
		opening,
		more,
		lang,
		answer,
		labels,
		playing = true,
		keepClear,
		center
	}: {
		/** [cold, hot]. */
		lanes: HighwayLane[];
		/** The text's first paragraph (written until `more` has loaded). */
		opening: string;
		/** The rest of the text, paragraph by paragraph (loaded once the page is idle). */
		more?: () => Promise<string[]>;
		lang: 'pl' | 'en';
		/** Tokens per answer (the demo answer's length). */
		answer: number;
		labels: { answer: string; tokens: string; done: string };
		playing?: boolean;
		keepClear?: HTMLElement;
		/** Between the two panels (the gauge). */
		center?: Snippet;
	} = $props();

	/** Far/near depth ratio: the horizon row is 1/K the size of the nearest one. */
	const K = 3.4;
	const DPR = typeof devicePixelRatio === 'number' ? Math.min(1.5, devicePixelRatio) : 1;
	const COLD = '#8f98a3';
	const HOT = '#ffad4a';
	const WHITE = '#fff6e4';
	/** Painted speed lettering every MARK rows. */
	const MARK = 13;

	/** A paragraph as words of token-sized pieces (piece count ≈ words × TOK_PER_WORD). */
	function words(text: string): string[][] {
		const ws = text.split(/\s+/).filter(Boolean);
		const chars = ws.reduce((n, w) => n + w.length, 0);
		const per = chars / (ws.length * TOK_PER_WORD[lang]);
		return ws.map((w) => {
			const n = Math.max(1, Math.round(w.length / per));
			const size = Math.ceil(w.length / n);
			const out: string[] = [];
			for (let i = 0; i < w.length; i += size) out.push(w.slice(i, i + size) + (i + size >= w.length ? ' ' : ''));
			return out;
		});
	}
	// svelte-ignore state_referenced_locally
	let paras: string[][][] = [words(opening)];

	type Row = { idx: number; text: string; pieces: string[]; ends: number[]; start: number; n: number; bmp?: HTMLCanvasElement; glow?: HTMLCanvasElement };
	type Lane = { tps: number; burst: number; hot: boolean; tau: number; origin: number; built: number; next: number; pi: number; wi: number; rows: Row[]; cur: number; mark?: HTMLCanvasElement };
	// svelte-ignore state_referenced_locally
	const road: Lane[] = lanes.map((l) => ({ tps: l.tps, burst: l.burst, hot: l.id === 'hot', tau: 0, origin: 0, built: 0, next: 0, pi: 0, wi: 0, rows: [], cur: 0 }));
	/** Seconds per answer: the answer's tokens ÷ the measured t/s. */
	// svelte-ignore state_referenced_locally
	const finish = lanes.map((l) => answer / l.tps);
	const sec = (s: number) => `${num(s, lang, 1)}\u00a0s`;

	/** Scene geometry (CSS px), recomputed on resize. */
	const G = { W: 0, H: 0, vx: 0, yH: 0, Hs: 0, R: 40, fN: 16, cw: 0.6, chars: 30, bw: 0, bh: 0, family: 'monospace', display: 'sans-serif', lane: [0, 0] as number[], wl: 0, m: 12 };
	let canvas: HTMLCanvasElement | undefined = $state();
	let ctx: CanvasRenderingContext2D | null = null;
	let pool: HTMLCanvasElement[] = [];
	let started = $state(false);
	let onScreen = $state(false);
	/** The server/static frame (both answers finished) until the race starts. */
	let still = $state(true);
	/** Answers finished per lane (a change replays the lane's stamp). */
	let done = $state([0, 0]);
	let counts: HTMLElement[] = $state([]);
	let bars: HTMLElement[] = $state([]);
	let nums: HTMLElement[] = $state([]);
	let says: HTMLElement[] = $state([]);
	const shown = [-1, -1];
	/** The live answer in each panel: one text node, the answer it shows, tokens appended so far. */
	const said: (Text | null)[] = [null, null];
	const saidK = [-1, -1];
	const saidT = [0, 0];

	const aOf = (d: number) => 1 / (1 + ((G.R - d) * (K - 1)) / G.R);
	const yOf = (a: number) => G.yH + G.Hs * a;
	const xOf = (x: number, a: number) => G.vx + (x - G.vx) * a;
	const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
	/** Tokens a lane has written since the race started (whole MTP steps). */
	const writtenOf = (L: Lane) => Math.floor(Math.floor((L.tps * L.tau) / L.burst) * L.burst);

	function take(): HTMLCanvasElement {
		const c = pool.pop() ?? document.createElement('canvas');
		if (c.width !== G.bw || c.height !== G.bh) {
			c.width = G.bw;
			c.height = G.bh;
		}
		return c;
	}
	function release(r: Row) {
		if (r.bmp) pool.push(r.bmp);
		if (r.glow) pool.push(r.glow);
		r.bmp = r.glow = undefined;
	}
	function paint(text: string, color: string): HTMLCanvasElement {
		const c = take();
		const x = c.getContext('2d')!;
		x.clearRect(0, 0, c.width, c.height);
		x.font = `${G.fN * DPR}px ${G.family}`;
		x.fillStyle = color;
		x.textBaseline = 'alphabetic';
		x.fillText(text, 2, G.bh * 0.76);
		return c;
	}
	/** The lane's speed, painted on the road like asphalt lettering (one bitmap per layout). */
	function paintMark(L: Lane, tps: number) {
		const c = L.mark ?? document.createElement('canvas');
		const text = `${num(tps, lang, 1)} t/s`;
		const x = c.getContext('2d')!;
		const base = 100;
		x.font = `800 ${base}px ${G.display}`;
		const fs = (base * G.wl * 0.84) / x.measureText(text).width;
		c.width = Math.ceil(G.wl * 0.86 * DPR);
		c.height = Math.ceil(fs * 1.05 * DPR);
		x.font = `800 ${fs * DPR}px ${G.display}`;
		x.textBaseline = 'alphabetic';
		if (L.hot) {
			const g = x.createLinearGradient(0, 0, c.width, 0);
			g.addColorStop(0, '#e2401c');
			g.addColorStop(0.55, '#ff7a1a');
			g.addColorStop(1, '#ffc15a');
			x.fillStyle = g;
		} else x.fillStyle = '#8d97a4';
		x.fillText(text, 2, c.height * 0.86);
		L.mark = c;
	}

	/** The next row of a lane: whole words up to the line length; a paragraph ends a row. */
	function build(L: Lane) {
		const pieces: string[] = [];
		const ends: number[] = [];
		let chars = 0;
		for (;;) {
			const para = paras[L.pi % paras.length];
			const w = para[L.wi];
			const len = w.reduce((n, p) => n + p.length, 0);
			if (pieces.length && chars + len > G.chars + 1) break;
			for (const p of w) {
				pieces.push(p);
				chars += p.length;
				ends.push(chars);
			}
			if (++L.wi >= para.length) {
				L.wi = 0;
				L.pi = (L.pi + 1) % paras.length;
				break;
			}
		}
		L.rows.push({ idx: L.next++, text: pieces.join('').trimEnd(), pieces, ends, start: L.built, n: pieces.length });
		L.built += pieces.length;
	}
	/** Lay the road out again (new size or font): the text goes on, the road is filled with rows. */
	function reset(L: Lane) {
		for (const r of L.rows) release(r);
		L.rows = [];
		L.cur = 0;
		const fill = Math.ceil(G.R);
		while (L.rows.length < fill + 2) build(L);
		// the newest row sits at the horizon; everything behind it is written. The race clock
		// (tau) is kept, so the answers and the HUD go on where they were.
		L.origin = L.rows[fill].start - Math.floor(L.tps * L.tau);
		L.cur = fill;
	}

	function layout() {
		if (!canvas) return;
		const W = canvas.clientWidth;
		const H = canvas.clientHeight;
		if (!W || !H) return;
		canvas.width = Math.round(W * DPR);
		canvas.height = Math.round(H * DPR);
		ctx = canvas.getContext('2d');
		G.W = W;
		G.H = H;
		G.vx = W / 2;
		// the farthest row behind the headline, the nearest at the bottom: the road runs out from
		// under the headline toward the viewer
		const yFar = H * (W < 900 ? 0.24 : 0.2);
		G.Hs = (H * 0.99 - yFar) / (1 - 1 / K);
		G.yH = yFar - G.Hs / K;
		// the median: clear for the gauge when it sits over the scene's lower half
		let m = W < 600 ? 7 : 12;
		if (keepClear) {
			const k = keepClear.getBoundingClientRect();
			const c = canvas.getBoundingClientRect();
			if (k.width && k.bottom > c.top + H * 0.5 && k.top < c.bottom) m = k.width / 2 + 16;
		}
		G.m = m;
		const pad = W < 600 ? 10 : 24;
		const wl = Math.max(80, Math.min(W / 2 - m - pad, 620));
		G.wl = wl;
		G.lane = [G.vx - m - wl, G.vx + m];
		const cs = getComputedStyle(canvas);
		G.family = cs.fontFamily || 'monospace';
		G.display = cs.getPropertyValue('--font-sans').trim() || 'sans-serif';
		const fN = Math.max(11.5, Math.min(21, wl / 23));
		const probe = canvas.getContext('2d')!;
		probe.font = `${fN}px ${G.family}`;
		const cw = probe.measureText('0123456789').width / 10 / fN || 0.6;
		const chars = Math.max(10, Math.floor((wl * 0.92) / (fN * cw)));
		// rows: deep enough that the nearest glyphs are a little flatter than wide (road perspective)
		const R = Math.max(18, Math.min(72, Math.round((G.Hs * (K - 1) * 0.72) / fN)));
		const relaid = chars !== G.chars || fN !== G.fN || R !== G.R || cw !== G.cw || !G.bw;
		Object.assign(G, { fN, cw, chars, R });
		G.bw = Math.ceil((chars + 1) * cw * fN * DPR) + 4;
		G.bh = Math.ceil(fN * 1.3 * DPR);
		road.forEach((L, i) => paintMark(L, lanes[i].tps));
		if (relaid) {
			pool = [];
			for (const L of road) reset(L);
		}
		warpSeed();
		draw();
	}

	/** Move a lane forward to `P` tokens: the row being written, more rows ahead if needed. */
	function ensure(L: Lane, P: number) {
		while (L.cur >= L.rows.length - 1) build(L);
		while (L.rows[L.cur].start + L.rows[L.cur].n <= P) {
			L.cur++;
			while (L.cur >= L.rows.length - 1) build(L);
		}
	}

	/** A quad across the lane between depths a0 (near) and a1 (far), from lane fraction u0 to u1. */
	function quad(c: CanvasRenderingContext2D, x0: number, a0: number, a1: number, u0: number, u1: number) {
		const xa = x0 + G.wl * u0;
		const xb = x0 + G.wl * u1;
		c.moveTo(xOf(xa, a0), yOf(a0));
		c.lineTo(xOf(xb, a0), yOf(a0));
		c.lineTo(xOf(xb, a1), yOf(a1));
		c.lineTo(xOf(xa, a1), yOf(a1));
		c.closePath();
	}

	function drawLane(c: CanvasRenderingContext2D, L: Lane, li: number) {
		const P = L.origin + L.tps * L.tau;
		const written = L.origin + writtenOf(L);
		ensure(L, P);
		const head = L.rows[L.cur];
		const Q = head.idx + (P - head.start) / head.n;
		while (L.rows.length && L.rows[0].idx < Q - G.R - 4) {
			release(L.rows.shift()!);
			L.cur--;
		}
		const x0 = G.lane[li];
		const x1 = x0 + G.wl;
		const far = 1 / K;
		const near = 1.12;
		// the lane's floor
		const g = c.createLinearGradient(0, G.yH, 0, G.H);
		g.addColorStop(0, 'rgb(0 0 0 / 0)');
		g.addColorStop(1, L.hot ? 'rgb(255 122 26 / 0.11)' : 'rgb(125 135 148 / 0.04)');
		c.fillStyle = g;
		c.beginPath();
		quad(c, x0, near, far, 0, 1);
		c.fill();
		// the lane's edges
		for (const x of [x0, x1]) {
			const e = c.createLinearGradient(0, G.yH, 0, G.H);
			e.addColorStop(0, 'rgb(0 0 0 / 0)');
			e.addColorStop(1, L.hot ? 'rgb(255 160 70 / 0.85)' : 'rgb(140 150 162 / 0.28)');
			c.strokeStyle = e;
			c.lineWidth = L.hot ? 1.8 : 1;
			c.beginPath();
			c.moveTo(xOf(x, far), yOf(far));
			c.lineTo(xOf(x, near), yOf(near));
			c.stroke();
		}
		// light dashes on the edges, at the lane's own speed: ours long light trails, the typical crawl
		const step = L.hot ? 2 : 4;
		const len = L.hot ? 1.5 : 0.6;
		for (let i = Math.ceil(Q - G.R - 1); i <= Q; i++) {
			if (i % step) continue;
			const d = Q - i;
			const a0 = aOf(d);
			if (a0 < 0.4) continue;
			const a1 = aOf(Math.min(d + len, G.R + 2));
			const f = clamp01((a0 - 0.4) / 0.25);
			for (const x of [x0, x1]) {
				if (L.hot) {
					c.globalAlpha = 0.25 * f;
					c.strokeStyle = '#ff7a1a';
					c.lineWidth = 2 + 10 * a0;
					c.beginPath();
					c.moveTo(xOf(x, a0), yOf(a0));
					c.lineTo(xOf(x, a1), yOf(a1));
					c.stroke();
				}
				c.globalAlpha = (L.hot ? 0.95 : 0.32) * f;
				c.strokeStyle = L.hot ? WHITE : '#a9b1bc';
				c.lineWidth = L.hot ? 0.8 + 2.8 * a0 : 0.6 + 1.2 * a0;
				c.beginPath();
				c.moveTo(xOf(x, a0), yOf(a0));
				c.lineTo(xOf(x, a1), yOf(a1));
				c.stroke();
			}
		}
		c.globalAlpha = 1;
		// chequered finish lines: one after every finished answer, on the far side of its last row
		const first = L.rows[0].start;
		for (let j = Math.max(1, Math.ceil((first - L.origin) / answer)); L.origin + j * answer <= written; j++) {
			const B = L.origin + j * answer;
			const r = L.rows.find((x) => x.start <= B - 1 && B - 1 < x.start + x.n);
			if (!r) continue;
			const d = Q - r.idx;
			const a0 = aOf(d - 0.5);
			const a1 = aOf(d - 1.05);
			if (a1 > 1.2 || a0 < far) continue;
			const f = clamp01((a0 - far) / 0.12);
			const am = aOf(d - 0.78);
			c.globalAlpha = (L.hot ? 0.95 : 0.5) * f;
			c.fillStyle = L.hot ? WHITE : '#c9cfd8';
			c.beginPath();
			quad(c, x0, a0, a1, 0, 1);
			c.fill();
			c.fillStyle = '#050506';
			c.beginPath();
			const n = 14;
			for (let k = 0; k < n; k++) {
				quad(c, x0, k % 2 ? a0 : am, k % 2 ? am : a1, k / n, (k + 1) / n);
			}
			c.fill();
			if (L.hot) {
				c.globalAlpha = 0.35 * f;
				c.strokeStyle = '#ff7a1a';
				c.lineWidth = 4 + 10 * a0;
				c.beginPath();
				c.moveTo(xOf(x0, a0), yOf(a0));
				c.lineTo(xOf(x1, a0), yOf(a0));
				c.stroke();
			}
		}
		c.globalAlpha = 1;
		// the text rows, from the horizon toward the camera
		const tx = x0 + G.wl * 0.04;
		const rowK = (G.Hs * (K - 1)) / G.R;
		for (const r of L.rows) {
			const d = Q - r.idx;
			if (d < 0) break;
			const a = aOf(d);
			if (a > 1.2) continue;
			const wr = Math.min(r.n, Math.max(0, written - r.start));
			if (!wr) continue;
			const shownChars = r.ends[wr - 1];
			if (!r.bmp) {
				r.bmp = paint(r.text, L.hot ? HOT : COLD);
				if (L.hot) r.glow = paint(r.text, WHITE);
			}
			const sw = Math.min(G.bw, Math.ceil(shownChars * G.cw * G.fN * DPR) + 3);
			const h = rowK * a * a * 0.74;
			const w = (sw / DPR) * a;
			const x = xOf(tx, a);
			const top = yOf(a) - h;
			const f = clamp01((a - far) / 0.09);
			if (L.hot) {
				const n = clamp01((a - 0.45) / 0.5);
				if (n > 0) {
					// directional motion blur: the row smeared back up the road, toward the vanishing point
					const xs = xOf(tx, a * 0.985);
					c.globalAlpha = 0.07 * n;
					c.drawImage(r.bmp, 0, 0, sw, G.bh, xs, top - h * 3.4, w * 0.985, h * 4.4);
					c.globalAlpha = 0.17 * n;
					c.drawImage(r.bmp, 0, 0, sw, G.bh, x, top - h * 1.5, w, h * 2.5);
				}
				c.globalAlpha = f * (0.6 + 0.4 * a);
				c.drawImage(r.bmp, 0, 0, sw, G.bh, x, top, w, h);
				if (n > 0 && r.glow) {
					c.globalAlpha = f * n;
					c.drawImage(r.glow, 0, 0, sw, G.bh, x, top, w, h);
				}
			} else {
				c.globalAlpha = f * (0.3 + 0.4 * a);
				c.drawImage(r.bmp, 0, 0, sw, G.bh, x, top, w, h);
			}
		}
		// the speed painted on the road over the rows, every MARK rows (ours passes it 3,2× as often)
		if (L.mark) {
			const span = 3.4;
			for (let i = Math.ceil(Q - G.R - 1); i <= Q; i++) {
				if (((i % MARK) + MARK) % MARK) continue;
				const d = Q - i;
				const an = aOf(d);
				const af = aOf(d - span);
				if (an < 0.36 || af > 1.25) continue;
				const am = aOf(d - span / 2);
				const yn = yOf(an);
				const yf = yOf(af);
				c.globalAlpha = (L.hot ? 0.5 : 0.2) * clamp01((an - 0.36) / 0.2);
				c.drawImage(L.mark, xOf(x0 + G.wl * 0.07, am), yf, (L.mark.width / DPR) * am, yn - yf);
			}
			c.globalAlpha = 1;
		}
		c.globalAlpha = 1;
	}

	/** Warp streaks over our lane: out of the vanishing point, faster the farther out. */
	type Streak = { dx: number; dy: number; D: number; s: number };
	let warp: Streak[] = [];
	function spawn(st: Streak, fresh: boolean) {
		// a ray from the vanishing point to a point on our lane's near end
		const tx = G.vx + G.m + G.wl * (0.04 + 0.92 * Math.random());
		const ty = G.H * (0.82 + 0.25 * Math.random());
		const dx = tx - G.vx;
		const dy = ty - G.yH;
		const D = Math.hypot(dx, dy);
		st.dx = dx / D;
		st.dy = dy / D;
		st.D = D;
		st.s = fresh ? 0.15 + Math.random() * 1.1 : 0.12 + Math.random() * 0.12;
	}
	function warpSeed() {
		warp = Array.from({ length: G.W < 600 ? 12 : 22 }, () => {
			const st = { dx: 0, dy: 0, D: 1, s: 0 };
			spawn(st, true);
			return st;
		});
	}
	function warpStep(dt: number) {
		for (const st of warp) {
			st.s += st.s * 1.5 * dt;
			if (st.s > 1.5) spawn(st, false);
		}
	}
	function warpDraw(c: CanvasRenderingContext2D) {
		c.strokeStyle = '#ffd9a8';
		for (const st of warp) {
			const s1 = st.s * st.D;
			const s0 = s1 * 0.8;
			const f = clamp01((st.s - 0.25) / 0.35) * clamp01((1.5 - st.s) / 0.3);
			if (f <= 0) continue;
			c.globalAlpha = 0.28 * f;
			c.lineWidth = 0.6 + 1.4 * st.s;
			c.beginPath();
			c.moveTo(G.vx + st.dx * s0, G.yH + st.dy * s0);
			c.lineTo(G.vx + st.dx * s1, G.yH + st.dy * s1);
			c.stroke();
		}
		c.globalAlpha = 1;
	}

	function draw() {
		const c = ctx;
		if (!c || !G.W) return;
		c.setTransform(DPR, 0, 0, DPR, 0, 0);
		c.clearRect(0, 0, G.W, G.H);
		road.forEach((L, i) => drawLane(c, L, i));
		warpDraw(c);
	}

	/** The HUD: answer number, counter, progress bar, and a stamp when an answer is done. */
	function hud() {
		road.forEach((L, i) => {
			const w = writtenOf(L);
			const k = Math.floor(w / answer);
			const p = w - k * answer;
			if (p !== shown[i]) {
				shown[i] = p;
				if (counts[i]) counts[i].textContent = num(p, lang, 0);
				if (bars[i]) bars[i].style.transform = `scaleX(${(p / answer).toFixed(4)})`;
				if (nums[i]) nums[i].textContent = String(k + 1);
			}
			if (k !== done[i]) done[i] = k;
			// the panel: the current answer, token by token (a new answer starts an empty panel)
			const node = said[i];
			if (!node) return;
			if (k !== saidK[i]) {
				saidK[i] = k;
				saidT[i] = k * answer;
				node.data = '';
			}
			let add = '';
			for (; saidT[i] < w; saidT[i]++) add += pieceAt(L, L.origin + saidT[i]);
			if (add) node.appendData(add);
		});
	}
	/** The piece at absolute token index `g` (rows are kept back to the camera). */
	function pieceAt(L: Lane, g: number): string {
		for (let j = L.rows.length - 1; j >= 0; j--) {
			const r = L.rows[j];
			if (r.start <= g) return g < r.start + r.n ? r.pieces[g - r.start] : '';
		}
		return '';
	}

	onMount(() => {
		const rm = reducedMotion();
		// the static frame: the moment the slower lane finishes its answer
		if (rm) for (const L of road) L.tau = Math.max(...finish);
		layout();
		const ro = new ResizeObserver(() => layout());
		if (canvas) ro.observe(canvas);
		if (keepClear) ro.observe(keepClear);
		// the webfont arrives after first paint: lay the rows out again in it
		document.fonts?.ready.then(() => {
			G.bw = 0;
			layout();
		});
		if (rm) return () => ro.disconnect();
		// the race starts at 0 / answer on both lanes, with empty panels
		still = false;
		says.forEach((el, i) => {
			if (!el) return;
			el.textContent = '';
			said[i] = el.appendChild(document.createTextNode(''));
		});
		hud();
		const cancel = whenIdle(() => {
			started = true;
			more?.()
				.then((rest) => (paras = [paras[0], ...rest.map(words)]))
				.catch(() => {
					/* the opening alone keeps going round */
				});
		});
		return () => {
			cancel();
			ro.disconnect();
		};
	});

	// the frame loop lives only while running on screen; it continues where it stopped
	$effect(() => {
		if (!started || !playing || !onScreen) return;
		return untrack(() =>
			onFrame((dt) => {
				const d = Math.min(dt, 0.1);
				for (const L of road) L.tau += d;
				warpStep(d);
				draw();
				hud();
			})
		);
	});
</script>

<canvas class="scene" class:run={started && playing && onScreen} bind:this={canvas} aria-hidden="true" use:visible={(v) => (onScreen = v)}></canvas>
<div class="near" class:run={started && playing && onScreen}>
	{#each lanes as l, i (l.id)}
		<div class="pane {l.id}" aria-hidden="true">
			{#key done[i]}
				{#if still || done[i] > 0}
					<p class="stamp" class:keep={still}><b>{labels.done}</b><span>{sec(finish[i])}</span></p>
				{/if}
			{/key}
			<div class="head">
				<p class="name"><span class="dot"></span>{l.name}<span class="ans">{labels.answer} <span bind:this={nums[i]}>1</span></span></p>
				<p class="count"><b bind:this={counts[i]}>{num(answer, lang, 0)}</b> / {num(answer, lang, 0)} {labels.tokens}</p>
			</div>
			<!-- a window on the answer being written: the newest line at the bottom -->
			<div class="win" data-clip-ok><p class="say" bind:this={says[i]}>{opening}</p></div>
			<span class="track"><span class="bar" bind:this={bars[i]}></span></span>
		</div>
		{#if i === 0 && center}<div class="center">{@render center()}</div>{/if}
	{/each}
</div>

<style>
	/* the road: full bleed behind the whole hero (the hero is its containing block) */
	.scene {
		position: absolute;
		inset: 0;
		z-index: -1;
		width: 100%;
		height: 100%;
		display: block;
		font-family: var(--font-mono);
		/* the far road dissolves into the dark behind the headline; the nearest rows into the floor */
		-webkit-mask-image: linear-gradient(180deg, transparent 12%, #000 34%, #000 84%, transparent);
		mask-image: linear-gradient(180deg, transparent 12%, #000 34%, #000 84%, transparent);
	}
	/* the near end: two glass windshields with the live answers, the gauge between them */
	.near {
		position: relative;
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
		display: grid;
		grid-template-columns: minmax(0, 32rem) auto minmax(0, 32rem);
		justify-content: space-between;
		align-items: end;
		column-gap: var(--sp-4);
	}
	.center {
		align-self: end;
	}
	.pane {
		position: relative;
		display: grid;
		gap: 0.6rem;
		padding: 0.85rem 1rem 0.9rem;
		border-radius: 1rem;
		background: linear-gradient(180deg, rgb(20 20 24 / 0.62), rgb(8 8 10 / 0.78));
		box-shadow:
			inset 0 1px 0 rgb(255 255 255 / 0.07),
			inset 0 0 0 1px rgb(255 255 255 / 0.08),
			0 24px 50px -24px rgb(0 0 0 / 0.9);
		-webkit-backdrop-filter: blur(10px) saturate(1.2);
		backdrop-filter: blur(10px) saturate(1.2);
		font-variant-numeric: tabular-nums lining-nums;
	}
	.pane.hot {
		background: linear-gradient(180deg, rgb(32 18 10 / 0.62), rgb(12 7 4 / 0.8));
		box-shadow:
			inset 0 1px 0 rgb(255 243 214 / 0.12),
			inset 0 0 0 1px rgb(255 122 26 / 0.5),
			0 0 50px -14px rgb(255 122 26 / 0.6),
			0 24px 50px -24px rgb(0 0 0 / 0.9);
	}
	.pane p {
		margin: 0;
	}
	.head {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		justify-content: space-between;
		gap: 0.2rem 0.75rem;
	}
	.name {
		display: inline-flex;
		align-items: baseline;
		gap: 0.5rem;
		font-family: var(--font-display);
		font-size: var(--fs-md);
		font-weight: 720;
		letter-spacing: -0.01em;
		color: var(--text);
	}
	.hot .name {
		color: var(--heat-5);
	}
	.dot {
		align-self: center;
		width: 0.45rem;
		height: 0.45rem;
		border-radius: 50%;
		background: var(--before);
	}
	.hot .dot {
		background: var(--heat-3);
		box-shadow: 0 0 10px var(--heat-3);
	}
	.ans {
		font-size: var(--fs-xs);
		font-weight: 500;
		letter-spacing: 0;
		color: var(--text-mute);
		white-space: nowrap;
	}
	.count {
		font-size: var(--fs-sm);
		color: var(--text-mute);
		white-space: nowrap;
	}
	.count b {
		font-family: var(--font-display);
		font-size: 1.3rem;
		font-weight: 760;
		letter-spacing: -0.02em;
		color: var(--before);
	}
	.hot .count b {
		color: var(--heat-4);
		text-shadow: 0 0 14px rgb(255 122 26 / 0.5);
	}
	/* four lines of the answer; older lines leave through the top */
	.win {
		--lh: 1.55em;
		height: calc(4 * var(--lh));
		overflow: hidden;
		display: flex;
		flex-direction: column;
		justify-content: flex-end;
		font-family: var(--font-mono);
		font-size: clamp(0.8rem, 0.7rem + 0.25vw, 0.95rem);
		contain: strict;
		-webkit-mask-image: linear-gradient(transparent, #000 1.1em);
		mask-image: linear-gradient(transparent, #000 1.1em);
	}
	.say {
		line-height: var(--lh);
		color: #a3a9b2;
		overflow-wrap: anywhere;
	}
	.hot .say {
		color: #ffe2bd;
		text-shadow: 0 0 12px rgb(255 122 26 / 0.35);
	}
	/* the caret after the newest token */
	.say::after {
		content: '';
		display: inline-block;
		width: 0.55em;
		height: 1.05em;
		margin-left: 0.1em;
		vertical-align: -0.15em;
		background: var(--before);
	}
	.hot .say::after {
		background: var(--heat-4);
		box-shadow: 0 0 10px var(--heat-3);
	}
	.track {
		display: block;
		height: 3px;
		border-radius: 3px;
		overflow: hidden;
		background: rgb(255 255 255 / 0.08);
	}
	.bar {
		display: block;
		height: 100%;
		transform-origin: 0 50%;
		background: var(--before);
	}
	.hot .bar {
		background: linear-gradient(90deg, var(--heat-2), var(--heat-4), var(--heat-5));
		box-shadow: 0 0 10px rgb(255 122 26 / 0.7);
	}
	/* the finish: a stamp over the panel, flashing once per finished answer */
	.stamp {
		position: absolute;
		left: 1rem;
		bottom: calc(100% + 0.5rem);
		display: flex;
		align-items: baseline;
		gap: 0.5rem;
		white-space: nowrap;
		font-family: var(--font-display);
		line-height: 1;
		pointer-events: none;
	}
	.hot .stamp {
		left: auto;
		right: 1rem;
	}
	.stamp b {
		font-size: var(--fs-sm);
		font-weight: 700;
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text);
	}
	.stamp span {
		font-size: clamp(1.6rem, 1rem + 1.6vw, 2.4rem);
		font-weight: 820;
		letter-spacing: -0.03em;
		color: var(--before);
	}
	.hot .stamp b {
		color: var(--heat-5);
	}
	.hot .stamp span {
		background: linear-gradient(180deg, #fff 10%, var(--heat-4) 60%, var(--heat-3));
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
		filter: drop-shadow(0 0 14px rgb(255 122 26 / 0.6));
		padding: 0.05em 0.08em 0.12em 0;
	}
	.stamp:not(.keep) {
		opacity: 0;
		animation: stamp 2.2s var(--ease-out) both;
	}
	@keyframes stamp {
		0% {
			opacity: 0;
			transform: translate3d(0, 0.4rem, 0) scale(1.12);
		}
		12%,
		70% {
			opacity: 1;
			transform: none;
		}
		100% {
			opacity: 0;
			transform: translate3d(0, -0.3rem, 0);
		}
	}
	/* tablets and phones: the two panels stacked (ours second), the gauge after them */
	@media (max-width: 900px) {
		.near {
			grid-template-columns: minmax(0, 1fr);
			row-gap: var(--sp-3);
		}
		.center {
			order: 3;
			justify-self: center;
		}
		.pane {
			padding: 0.6rem 0.8rem 0.7rem;
			gap: 0.4rem;
		}
		.name {
			font-size: var(--fs-sm);
		}
		.count b {
			font-size: 1.05rem;
		}
		.win {
			height: calc(3 * var(--lh));
			font-size: 0.75rem;
		}
		/* inside the panel, over the answer's bottom right */
		.stamp {
			bottom: 1.3rem;
			left: auto;
			right: 0.8rem;
			padding: 0.25rem 0.45rem;
			border-radius: 0.5rem;
			background: rgb(8 8 10 / 0.88);
		}
		.stamp span {
			font-size: 1.25rem;
		}
		.hot .stamp {
			right: 0.8rem;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.stamp:not(.keep) {
			animation: none;
			opacity: 1;
		}
	}
</style>
