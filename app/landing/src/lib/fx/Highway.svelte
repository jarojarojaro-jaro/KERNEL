<script lang="ts" module>
	export interface HighwayLane {
		id: 'cold' | 'hot';
		/** Measured decode speed (t/s, the median). */
		tps: number;
		/** Measured tokens accepted per step (MTP); 1 without speculation. */
		burst: number;
	}
</script>

<script lang="ts">
	/**
	 * The token highway: two lanes of generated text on a road that runs to a vanishing point and
	 * flows toward the viewer. Each lane writes the same long text at its measured median t/s (in
	 * steps of the measured MTP tokens per step): the newest row is written at the horizon and the
	 * road moves one row per row written, so the typical app's text crawls and ours rushes past
	 * 3,2× faster. Rows brighten as they come closer; ours flare white-hot near the camera with a
	 * short motion smear, and light dashes run along the lane edges at each lane's own speed.
	 *
	 * One 2D canvas (devicePixelRatio ≤ 1,5). Each row is rendered once into a pooled bitmap and then
	 * only scaled per frame (no text layout per frame); rows that pass the camera are recycled. The
	 * frame loop runs only after the page is idle, while on screen and not paused, and continues
	 * where it stopped. Reduced motion: one still frame of a filled road. `keepClear`: an element
	 * laid over the scene's bottom centre (the gauge); the lanes leave the median free for it.
	 */
	import { onMount, untrack } from 'svelte';
	import { TOK_PER_WORD } from '$lib/estimator';
	import { visible } from './actions';
	import { onFrame, reducedMotion, whenIdle } from './motion';

	let {
		lanes,
		opening,
		more,
		lang,
		playing = true,
		keepClear
	}: {
		/** [cold, hot]. */
		lanes: HighwayLane[];
		/** The text's first paragraph (written until `more` has loaded). */
		opening: string;
		/** The rest of the text, paragraph by paragraph (loaded once the page is idle). */
		more?: () => Promise<string[]>;
		lang: 'pl' | 'en';
		playing?: boolean;
		keepClear?: HTMLElement;
	} = $props();

	/** Far/near depth ratio: the horizon row is 1/K the size of the nearest one. */
	const K = 3.4;
	const DPR = typeof devicePixelRatio === 'number' ? Math.min(1.5, devicePixelRatio) : 1;
	const COLD = '#9aa3ae';
	const HOT = '#ffad4a';
	const WHITE = '#fff6e4';

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

	type Row = { idx: number; text: string; ends: number[]; start: number; n: number; bmp?: HTMLCanvasElement; glow?: HTMLCanvasElement };
	type Lane = { tps: number; burst: number; hot: boolean; tau: number; origin: number; built: number; next: number; pi: number; wi: number; rows: Row[]; cur: number };
	// svelte-ignore state_referenced_locally
	const road: Lane[] = lanes.map((l) => ({ tps: l.tps, burst: l.burst, hot: l.id === 'hot', tau: 0, origin: 0, built: 0, next: 0, pi: 0, wi: 0, rows: [], cur: 0 }));

	/** Scene geometry (CSS px), recomputed on resize. */
	const G = { W: 0, H: 0, vx: 0, yH: 0, Hs: 0, R: 40, fN: 16, cw: 0.6, chars: 30, bw: 0, bh: 0, family: 'monospace', lane: [0, 0] as number[], wl: 0 };
	let canvas: HTMLCanvasElement | undefined = $state();
	let ctx: CanvasRenderingContext2D | null = null;
	let pool: HTMLCanvasElement[] = [];
	let started = $state(false);
	let onScreen = $state(false);

	const aOf = (d: number) => 1 / (1 + ((G.R - d) * (K - 1)) / G.R);
	const yOf = (a: number) => G.yH + G.Hs * a;
	const xOf = (x: number, a: number) => G.vx + (x - G.vx) * a;
	const clamp01 = (x: number) => Math.min(1, Math.max(0, x));

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
		L.rows.push({ idx: L.next++, text: pieces.join('').trimEnd(), ends, start: L.built, n: pieces.length });
		L.built += pieces.length;
	}
	/** Lay the road out again (new size or font): the text goes on, the road is filled with rows. */
	function reset(L: Lane) {
		for (const r of L.rows) release(r);
		L.rows = [];
		L.cur = 0;
		const fill = Math.ceil(G.R);
		while (L.rows.length < fill + 2) build(L);
		// the newest row sits at the horizon, unwritten; everything behind it is written
		L.origin = L.rows[fill].start - L.tps * L.tau;
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
		// the farthest row near the top of the scene (higher on phones, where nothing covers it), the
		// nearest at the bottom; the vanishing point itself sits above the scene
		const yFar = H * (W < 900 ? 0.05 : 0.15);
		G.Hs = (H * 0.99 - yFar) / (1 - 1 / K);
		G.yH = yFar - G.Hs / K;
		// the median: clear for the gauge when it sits over the scene's lower half
		let m = W < 600 ? 7 : 12;
		if (keepClear) {
			const k = keepClear.getBoundingClientRect();
			const c = canvas.getBoundingClientRect();
			if (k.width && k.bottom > c.top + H * 0.5 && k.top < c.bottom) m = k.width / 2 + 16;
		}
		const pad = W < 600 ? 10 : 24;
		const wl = Math.max(80, Math.min(W / 2 - m - pad, 620));
		G.wl = wl;
		G.lane = [G.vx - m - wl, G.vx + m];
		G.family = getComputedStyle(canvas).fontFamily || 'monospace';
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
		if (relaid) {
			pool = [];
			for (const L of road) reset(L);
		}
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

	function drawLane(c: CanvasRenderingContext2D, L: Lane, li: number) {
		const P = L.origin + L.tps * L.tau;
		const written = L.origin + Math.floor(Math.floor((L.tps * L.tau) / L.burst) * L.burst);
		ensure(L, P);
		const head = L.rows[L.cur];
		const Q = head.idx + (P - head.start) / head.n;
		while (L.rows.length && L.rows[0].idx < Q - G.R - 2) {
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
		g.addColorStop(1, L.hot ? 'rgb(255 122 26 / 0.09)' : 'rgb(125 135 148 / 0.05)');
		c.fillStyle = g;
		c.beginPath();
		c.moveTo(xOf(x0, far), yOf(far));
		c.lineTo(xOf(x1, far), yOf(far));
		c.lineTo(xOf(x1, near), yOf(near));
		c.lineTo(xOf(x0, near), yOf(near));
		c.fill();
		// the lane's edges
		for (const x of [x0, x1]) {
			const e = c.createLinearGradient(0, G.yH, 0, G.H);
			e.addColorStop(0, 'rgb(0 0 0 / 0)');
			e.addColorStop(1, L.hot ? 'rgb(255 160 70 / 0.75)' : 'rgb(140 150 162 / 0.35)');
			c.strokeStyle = e;
			c.lineWidth = L.hot ? 1.6 : 1;
			c.beginPath();
			c.moveTo(xOf(x, far), yOf(far));
			c.lineTo(xOf(x, near), yOf(near));
			c.stroke();
		}
		// light dashes on the edges, at the lane's own speed
		const step = L.hot ? 2 : 4;
		const len = L.hot ? 1.1 : 0.7;
		for (let i = Math.ceil(Q - G.R - 1); i <= Q; i++) {
			if (i % step) continue;
			const d = Q - i;
			const a0 = aOf(d);
			if (a0 < 0.4) continue;
			const a1 = aOf(Math.min(d + len, G.R + 2));
			const f = clamp01((a0 - 0.4) / 0.25);
			for (const x of [x0, x1]) {
				if (L.hot) {
					c.globalAlpha = 0.22 * f;
					c.strokeStyle = '#ff7a1a';
					c.lineWidth = 2 + 9 * a0;
					c.beginPath();
					c.moveTo(xOf(x, a0), yOf(a0));
					c.lineTo(xOf(x, a1), yOf(a1));
					c.stroke();
				}
				c.globalAlpha = (L.hot ? 0.95 : 0.45) * f;
				c.strokeStyle = L.hot ? WHITE : '#b8c0ca';
				c.lineWidth = L.hot ? 0.8 + 2.6 * a0 : 0.6 + 1.4 * a0;
				c.beginPath();
				c.moveTo(xOf(x, a0), yOf(a0));
				c.lineTo(xOf(x, a1), yOf(a1));
				c.stroke();
			}
		}
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
			const shown = r.ends[wr - 1];
			if (!r.bmp) {
				r.bmp = paint(r.text, L.hot ? HOT : COLD);
				if (L.hot) r.glow = paint(r.text, WHITE);
			}
			const sw = Math.min(G.bw, Math.ceil(shown * G.cw * G.fN * DPR) + 3);
			const h = rowK * a * a * 0.74;
			const w = (sw / DPR) * a;
			const x = xOf(tx, a);
			const top = yOf(a) - h;
			const f = clamp01((a - far) / 0.09);
			if (L.hot) {
				const n = clamp01((a - 0.55) / 0.5);
				if (n > 0) {
					// the smear it leaves behind: the same row, stretched back up the road
					c.globalAlpha = 0.16 * n;
					c.drawImage(r.bmp, 0, 0, sw, G.bh, x, top - h * 1.4, w, h * 2.4);
				}
				c.globalAlpha = f * (0.55 + 0.45 * a);
				c.drawImage(r.bmp, 0, 0, sw, G.bh, x, top, w, h);
				if (n > 0 && r.glow) {
					c.globalAlpha = f * n;
					c.drawImage(r.glow, 0, 0, sw, G.bh, x, top, w, h);
				}
			} else {
				c.globalAlpha = f * (0.4 + 0.5 * a);
				c.drawImage(r.bmp, 0, 0, sw, G.bh, x, top, w, h);
			}
		}
		c.globalAlpha = 1;
	}

	function draw() {
		const c = ctx;
		if (!c || !G.W) return;
		c.setTransform(DPR, 0, 0, DPR, 0, 0);
		c.clearRect(0, 0, G.W, G.H);
		road.forEach((L, i) => drawLane(c, L, i));
	}

	onMount(() => {
		layout();
		const ro = new ResizeObserver(() => layout());
		if (canvas) ro.observe(canvas);
		if (keepClear) ro.observe(keepClear);
		// the webfont arrives after first paint: lay the rows out again in it
		document.fonts?.ready.then(() => {
			G.bw = 0;
			layout();
		});
		if (reducedMotion()) return () => ro.disconnect();
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
				draw();
			})
		);
	});
</script>

<canvas class="highway" bind:this={canvas} aria-hidden="true" use:visible={(v) => (onScreen = v)}></canvas>

<style>
	.highway {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		display: block;
		font-family: var(--font-mono);
		/* the far road dissolves into the haze; the nearest rows leave through a soft bottom edge */
		-webkit-mask-image: linear-gradient(180deg, transparent, #000 9%, #000 76%, transparent);
		mask-image: linear-gradient(180deg, transparent, #000 9%, #000 76%, transparent);
	}
</style>
