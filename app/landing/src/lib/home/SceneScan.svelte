<script lang="ts">
	/**
	 * Scene 01, Skan: our lab card, a Sapphire PULSE RX 7900 XTX (`PulseXtx`, a CSS 3D box at a slight
	 * three-quarter pose), and the detection log of what our scanner reads from it. One fast
	 * auto-played timeline (~4.4 s, `Autoplay`, once on entering the viewport, replay button):
	 *   card springs in → fans spin up to a blur → a quick red beam sweeps it with an x-ray band → six
	 *   steps, each opening an x-ray lens on its exact part, playing its effect and pulling the
	 *   finding out of the card into the log along a leader line (desktop), the log line typing in sync:
	 *   GPU → the Navi 31 die behind the middle fan · Driver → ROCm / HIP layers rising off the PCIe
	 *   fingers · VRAM → the 12 GDDR6 chips light up around the die (12 × 32-bit = 384-bit) ·
	 *   Bandwidth → data racing on the memory bus, the number counting up · Power → the 3 × 8-pin glow,
	 *   current flowing into the VRM · Recommended model → the 17,6 GB file drops into the memory
	 *   → „Gotowe · 4/4” → the fans coast to a stop and the floor light breathes while on screen.
	 * Desktop: hovering a log line re-opens its part. Values: the registry entry of the card (960 GB/s,
	 * the driver's default 303 W cap measured on our machine, the model file) and `XTX_BOARD` (Sapphire
	 * spec sheet, vulkaninfo, our ROCm notes). Illustration, callouts and log are aria-hidden (callout
	 * text is CSS content, never page text); screen readers get one sentence. Server HTML, reduced
	 * motion and leaving the viewport mid-play show the final state.
	 */
	import { tick } from 'svelte';
	import { Autoplay } from '$lib/fx/autoplay.svelte';
	import { clamp01, easeInOutCubic, reducedMotion } from '$lib/fx/motion';
	import Replay from '$lib/fx/Replay.svelte';
	import { fmtGB } from '$lib/format';
	import { num, type Lang } from '$lib/i18n';
	import { copy } from '$lib/site/copy';
	import { fill, SCAN_BOARD as B, SCAN_CARD as C } from './data';
	import PulseXtx from './PulseXtx.svelte';
	import SceneHead from './SceneHead.svelte';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(copy[lang].how.scan);

	/* ---- timeline: seconds of a 4.4 s play ---- */
	const D = 4.4;
	const at = (sec: number) => sec / D;
	const tl = new Autoplay(D, '0px 0px -25% 0px', { arm: true });
	const p = $derived(tl.p);
	const SWEEP: [number, number] = [at(0.45), at(0.95)];
	/** Each step starts 0.5 s after the previous; its log line types 0.12–0.34 s into it. */
	const START = [0, 1, 2, 3, 4, 5].map((i) => at(1.0 + 0.5 * i));
	const DONE = at(4.05);
	/** The x-ray band behind the beam, as a fraction of the card width. */
	const BAND = 0.25;
	const b = $derived(easeInOutCubic(clamp01((p - SWEEP[0]) / (SWEEP[1] - SWEEP[0]))) * (1 + BAND));
	const sweeping = $derived(p > SWEEP[0] && p < SWEEP[1]);

	/** Fans: spin up, full speed, coast to a stop; `spin` integrates `rpm` so they end hubs upright. */
	const UP = at(0.4);
	const DOWN = at(3.9);
	const TURNS = 16;
	const K = TURNS / (UP / 2 + (DOWN - UP) + (1 - DOWN) / 3);
	const rpm = $derived(p < UP ? p / UP : p < DOWN ? 1 : (1 - (p - DOWN) / (1 - DOWN)) ** 2);
	const spin = $derived(
		p < UP ? (K * p * p) / (2 * UP) : p < DOWN ? K * (UP / 2 + p - UP) : K * (UP / 2 + DOWN - UP + ((1 - DOWN) * (1 - (1 - (p - DOWN) / (1 - DOWN)) ** 3)) / 3)
	);

	/* ---- where each finding sits on the card (800 × 330 grid of `PulseXtx`) ---- */
	type PartId = 'gpu' | 'drv' | 'vram' | 'bw' | 'pwr' | 'model';
	/** `r`: the x-ray lens, `a`: the anchor (pin, leader start). */
	const PARTS: Record<PartId, { r: [number, number, number, number]; a: [number, number] }> = {
		gpu: { r: [323, 82, 483, 238], a: [403, 112] },
		drv: { r: [92, 196, 350, 330], a: [220, 168] },
		vram: { r: [275, 38, 531, 282], a: [343, 59] },
		bw: { r: [275, 38, 531, 282], a: [319, 147] },
		pwr: { r: [540, 0, 712, 236], a: [646, 11] },
		model: { r: [275, 38, 531, 282], a: [300, 59] }
	};
	/** The four hardware findings counted in „4/4”. */
	const HW = ['gpu', 'vram', 'bw', 'pwr'] as const;
	const PIN: Record<(typeof HW)[number], string> = { gpu: 'GPU', vram: 'VRAM', bw: 'GB/s', pwr: 'W' };
	const CHIPS = 12;
	const gfx = C.arch.split(' ').pop() ?? '';
	const run = C.runs.find((r) => r.model === C.pick.model);
	const model = run?.title ?? '';
	const fileGB = run?.file?.v ?? 0;
	const fileText = $derived(run?.file ? fmtGB(run.file.v, run.file.unit, lang).text : '');
	const pct = (v: number, of: number) => `${((v / of) * 100).toFixed(2)}%`;

	/** Typing progress of step `i`. */
	const kOf = (i: number) => clamp01((p - START[i] - at(0.12)) / at(0.22));
	const bwNow = $derived(`${num(Math.round(C.bwGBs.v * (1 - (1 - kOf(3)) ** 3)), lang, 0)}\u00a0GB/s`);
	const lines = $derived(
		[
			{ part: 'gpu', key: c.gpu, value: `AMD ${C.name}`, sub: `${B.chip.v} · ${gfx}` },
			{ part: 'drv', key: c.driver, value: `ROCm ${B.rocm.v} · HIP`, sub: '' },
			{ part: 'vram', key: c.vram, value: `${C.vramGB}\u00a0GB ${B.memType.v}`, sub: `${B.busBits.v}-bit · ${CHIPS} × ${B.busBits.v / CHIPS}-bit` },
			{ part: 'bw', key: c.bw, value: bwNow, sub: `${B.gbps.v}\u00a0Gbps × ${B.busBits.v}\u00a0bit`, count: true },
			{ part: 'pwr', key: c.power, value: `${num(C.powerW.v, lang, 0)}\u00a0W`, sub: c.powerSub },
			{ part: 'model', key: c.model, value: model, sub: '' }
		].map((l, i) => ({ ...l, part: l.part as PartId, k: kOf(i) }))
	);
	const seen = $derived(Object.fromEntries(lines.map((l, i) => [l.part, p >= START[i]])) as Record<PartId, boolean>);
	const found = $derived(HW.filter((id) => lines.find((l) => l.part === id)!.k >= 1).length);

	/** Desktop: the log line under the pointer (after the play). */
	let hover: number | null = $state(null);
	/** The highlighted step: the hovered line, else the step playing now. */
	const active = $derived.by((): number | null => {
		if (hover !== null && !tl.playing) return hover;
		if (p < START[0] || p >= DONE) return null;
		return START.findLastIndex((s) => p >= s);
	});
	const focus = $derived(active === null ? null : lines[active].part);
	const lit = $derived({
		gpu: seen.gpu,
		mem: seen.vram,
		bus: seen.bw,
		pwr: seen.pwr,
		fill: seen.model ? fileGB / C.vramGB : 0,
		flow: focus === 'bw',
		current: focus === 'pwr'
	});
	const xclip = $derived.by(() => {
		if (sweeping) return `inset(-12% ${((1 - Math.min(b, 1)) * 100).toFixed(2)}% -12% ${((b - BAND) * 100).toFixed(2)}%)`;
		if (!focus) return 'inset(50% 50% 50% 50% round 14px)';
		const [x1, y1, x2, y2] = PARTS[focus].r;
		return `inset(${pct(y1, 330)} ${pct(800 - x2, 800)} ${pct(330 - y2, 330)} ${pct(x1, 800)} round 14px)`;
	});
	/** On-card callouts: the finding comes out of its part (CSS text). */
	const calls = $derived([
		{ id: 'gpu' as PartId, x: 403, y: 86, below: false, l: `${B.chip.v} · ${gfx}` },
		{ id: 'vram' as PartId, x: 403, y: 40, below: false, l: `${CHIPS} × ${B.busBits.v / CHIPS}-bit = ${B.busBits.v}-bit` },
		{ id: 'bw' as PartId, x: 403, y: 284, below: true, l: bwNow },
		{ id: 'pwr' as PartId, x: 626, y: 236, below: true, l: `${B.pins8.v} × 8-pin → VRM · ${num(C.powerW.v, lang, 0)}\u00a0W` }
	]);
	const prog = $derived(clamp01((p - SWEEP[0]) / (DONE - SWEEP[0])));
	const done = $derived(p >= DONE);
	const live = $derived(tl.inView && !tl.playing);
	const sr = $derived(
		fill(c.sr, {
			card: `${B.maker} ${B.series} ${C.name}`,
			chip: B.chip.v,
			gfx,
			driver: `ROCm ${B.rocm.v} (HIP)`,
			vram: `${C.vramGB} GB`,
			mem: B.memType.v,
			bus: `${B.busBits.v}-bit`,
			bw: `${num(C.bwGBs.v, lang, 0)} GB/s`,
			w: `${num(C.powerW.v, lang, 0)} W`,
			model
		})
	);

	/* ---- leader line from the part to its log line (desktop), measured after each step change ---- */
	let layoutEl: HTMLElement | undefined = $state();
	let size = $state(0);
	let leader: { d: string; ax: number; ay: number; lx: number; ly: number } | null = $state(null);
	$effect(() => {
		const el = layoutEl;
		if (!el) return;
		const ro = new ResizeObserver(() => size++);
		ro.observe(el);
		return () => ro.disconnect();
	});
	$effect(() => {
		const i = active;
		void size;
		const el = layoutEl;
		if (i === null || !el || !matchMedia('(min-width: 901px)').matches) {
			leader = null;
			return;
		}
		let raf = 0;
		tick().then(() => {
			raf = requestAnimationFrame(() => {
				const a = el.querySelector(`[data-a="${lines[i].part}"]`);
				const li = el.querySelector(`.line[data-i="${i}"]`);
				const log = el.querySelector('.log');
				if (!a || !li || !log) return;
				const L = el.getBoundingClientRect();
				const ar = a.getBoundingClientRect();
				const lr = li.getBoundingClientRect();
				const ax = ar.left + ar.width / 2 - L.left;
				const ay = ar.top + ar.height / 2 - L.top;
				const lx = log.getBoundingClientRect().right - L.left;
				const ly = lr.top + lr.height / 2 - L.top;
				const mx = (ax + lx) / 2;
				leader = { d: `M${ax.toFixed(1)} ${ay.toFixed(1)}C${mx.toFixed(1)} ${ay.toFixed(1)} ${mx.toFixed(1)} ${ly.toFixed(1)} ${lx.toFixed(1)} ${ly.toFixed(1)}`, ax, ay, lx, ly };
			});
		});
		return () => cancelAnimationFrame(raf);
	});

	/** Desktop: hovering a log line points the x-ray lens at its part. */
	function lineHover(node: HTMLElement) {
		if (reducedMotion() || !matchMedia('(hover: hover) and (pointer: fine)').matches) return;
		const over = (e: PointerEvent) => {
			const li = e.target instanceof Element ? e.target.closest<HTMLElement>('[data-i]') : null;
			hover = li ? Number(li.dataset.i) : null;
		};
		const leave = () => (hover = null);
		node.addEventListener('pointerover', over);
		node.addEventListener('pointerleave', leave);
		return {
			destroy() {
				node.removeEventListener('pointerover', over);
				node.removeEventListener('pointerleave', leave);
			}
		};
	}
</script>

<div class="wrap" class:live use:tl.view style="--b:{b}">
	<div class="layout" bind:this={layoutEl}>
		<div class="head"><SceneHead id="scene-scan" k={c.k} step={c.title} head={c.head} body={c.body} /></div>
		<div class="log" class:done>
			<div class="lh" aria-hidden="true">
				<span class="dot" class:busy={tl.playing}></span>
				<span class="lab">{B.maker} {B.series} · {c.lab}</span>
				<span class="track"><span class="fillbar" style="--g:{prog}"></span></span>
			</div>
			<ol class="lines" aria-hidden="true" use:lineHover>
				{#each lines as l, i (l.key)}
					<li class="line" class:on={l.k > 0} class:ok={l.k >= 1} class:cur={i === active} class:pick={l.part === 'model'} class:count={l.count} data-i={i} style="--k:{l.k}">
						<span class="lk">{l.key}</span>
						<span class="lv"><b>{l.value}</b>{#if l.sub}<i>{l.sub}</i>{/if}</span>
					</li>
				{/each}
			</ol>
			<div class="lf">
				<span class="st" aria-hidden="true">{done ? c.done : c.reading} · {found}/{HW.length}</span>
				<Replay {lang} onclick={tl.replay} disabled={tl.playing} />
			</div>
			<p class="sr-only">{sr}</p>
		</div>
		<div class="stage" aria-hidden="true">
			<div class="gpu" class:go={p > 0} class:wait={p === 0} style="--spin:{spin}; --rpm:{rpm}">
				<span class="shadow"></span>
				<span class="floor"></span>
				<div class="box">
					<div class="face top"><PulseXtx part="top" {lit} /></div>
					<div class="face end"><PulseXtx part="end" /></div>
					<!-- one flat face: shroud, x-ray lens, effects, callouts and pins never depth-fight -->
					<div class="face front">
						<PulseXtx part="front" />
						<div class="xray" class:sweeping style="clip-path:{xclip}"><PulseXtx part="xray" {lit} /></div>
						<div class="sweep" class:on={sweeping}><span class="beam"></span></div>
						<!-- driver: the software layers rise off the PCIe fingers -->
						<div class="holo" class:on={focus === 'drv'}>
							<span class="slab s1" data-l="HIP"></span>
							<span class="slab s2" data-l="ROCm {B.rocm.v}"></span>
						</div>
						<!-- recommended model: the file drops into the memory -->
						<span class="drop" class:on={focus === 'model'} data-m={model.split(' ')[0]} data-s={fileText}></span>
						{#each calls as k (k.id)}
							<span class="call" class:below={k.below} class:on={focus === k.id} data-l={k.l} style="left:{pct(k.x, 800)}; top:{pct(k.y, 330)}"></span>
						{/each}
						{#each Object.entries(PARTS) as [id, P] (id)}
							<span class="anchor" data-a={id} style="left:{pct(P.a[0], 800)}; top:{pct(P.a[1], 330)}"></span>
						{/each}
						{#each HW as id (id)}
							<span class="pin" class:on={seen[id]} class:cur={focus === id} data-l={PIN[id]} style="left:{pct(PARTS[id].a[0], 800)}; top:{pct(PARTS[id].a[1], 330)}"></span>
						{/each}
					</div>
				</div>
			</div>
		</div>
		{#if leader}
			<svg class="leader" aria-hidden="true">
				{#key leader.d}
					<path d={leader.d} pathLength="1" class="ld" />
					<circle cx={leader.ax} cy={leader.ay} r="4.5" class="ldot" />
					<circle cx={leader.lx} cy={leader.ly} r="3" class="ldot end" />
				{/key}
			</svg>
		{/if}
	</div>
</div>

<style>
	/* the launch slide and the sweep travel past the right edge: never widen the page */
	.wrap {
		--amd: #ff3b4f;
		--spring: cubic-bezier(0.34, 1.4, 0.64, 1);
		--glide: cubic-bezier(0.22, 1, 0.36, 1);
		/* card depth (52.67 / 313 mm of the length) and its pose */
		--depth: 16.875cqw;
		--rx: -13deg;
		--ry: -17deg;
		position: relative;
		overflow-x: clip;
		scroll-margin-top: var(--header-clear);
	}
	/* heading across the top, then the detection log beside the card; one viewport tall */
	.layout {
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
		display: grid;
		grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.45fr);
		grid-template-areas: 'head head' 'log card';
		align-items: center;
		gap: clamp(1.25rem, 3.5vh, 2.25rem) clamp(2rem, 4vw, 5rem);
		padding-block: var(--header-clear) clamp(1.25rem, 3vh, 2.5rem);
		position: relative;
	}
	.head {
		grid-area: head;
	}
	/* desktop: the body sits beside the heading, so the log and the card get the height */
	.head :global(.sh) {
		grid-template-columns: max-content minmax(0, 1fr);
		align-items: end;
		column-gap: clamp(2rem, 4vw, 4rem);
	}
	.head :global(.idx) {
		grid-column: 1 / -1;
	}
	.head :global(.body) {
		max-width: 40ch;
	}
	/* ---- the card ---- */
	.stage {
		grid-area: card;
		display: grid;
		place-items: center;
		padding: 2.5rem clamp(0.5rem, 3vw, 3rem) 1.5rem 0;
		user-select: none;
	}
	.gpu {
		position: relative;
		container-type: size;
		width: min(100%, 56rem, (100svh - var(--header-clear) - 22rem) * 800 / 400);
		aspect-ratio: 800 / 330;
	}
	.gpu.wait {
		opacity: 0;
	}
	/* launch: the card shoots in from the right with motion blur, overshoots and springs to rest */
	.gpu.go {
		animation: launch 1.05s var(--glide) both;
	}
	@keyframes launch {
		0% {
			opacity: 0;
			filter: blur(10px);
			transform: translate3d(55%, 0, 0) skewX(-14deg);
		}
		12% {
			opacity: 1;
		}
		40% {
			filter: blur(1.5px);
			transform: translate3d(-3.5%, 0, 0) skewX(3.5deg);
		}
		62% {
			filter: none;
			transform: translate3d(1.2%, 0, 0) skewX(-1.2deg);
		}
		80% {
			transform: translate3d(-0.4%, 0, 0) skewX(0.3deg);
		}
		100% {
			transform: none;
		}
	}
	/* the 3D box at its three-quarter pose (static, so the leader lines land exactly) */
	.box {
		position: absolute;
		inset: 0;
		transform-style: preserve-3d;
		transform: perspective(1700px) rotateX(var(--rx)) rotateY(var(--ry));
	}
	.face {
		position: absolute;
		inset: 0;
	}
	/* the top edge stands on the shroud's top line (y 16 of 330) and runs back */
	.top {
		inset: auto;
		left: 2.75%;
		width: 95.25%;
		top: calc(4.85% - var(--depth));
		height: var(--depth);
		transform-origin: 50% 100%;
		transform: rotateX(90deg);
	}
	/* the tail end stands on the shroud's right line (x 784 of 800) and runs back */
	.end {
		inset: auto;
		left: 98%;
		top: 4.85%;
		width: var(--depth);
		height: 85.45%;
		transform-origin: 0 50%;
		transform: rotateY(90deg);
	}
	.xray {
		position: absolute;
		inset: 0;
		transition: clip-path 0.38s var(--glide);
	}
	.xray.sweeping {
		transition: none;
	}
	.shadow,
	.floor {
		position: absolute;
		pointer-events: none;
	}
	.shadow {
		inset: 86% 0 -16% 4%;
		background: radial-gradient(50% 50% at 50% 50%, rgb(0 0 0 / 0.75), transparent 72%);
	}
	/* red floor light under the card; it breathes while the scene is on screen and idle */
	.floor {
		inset: 76% 2% -22%;
		background: radial-gradient(50% 50% at 50% 50%, rgb(255 59 79 / 0.24), transparent 70%);
		opacity: 0.85;
	}
	.live .floor {
		animation: breathe 4.8s ease-in-out infinite;
	}
	@keyframes breathe {
		50% {
			opacity: 0.4;
			transform: scale(0.94, 0.85);
		}
	}
	/* the beam layer moves only while it sweeps; at rest it sits on the card, so it never adds
	 * overflow to the scene (the wrap clips it anyway) */
	.sweep {
		position: absolute;
		inset: -8% 0;
		opacity: 0;
		pointer-events: none;
	}
	.sweep.on {
		transform: translate3d(calc(min(var(--b), 1) * 100%), 0, 0);
		opacity: clamp(0, calc(min(var(--b), 1.04 - var(--b)) * 25), 1);
	}
	.beam {
		position: absolute;
		top: 0;
		bottom: 0;
		left: -1px;
		width: 2px;
		background: #fff1f2;
		box-shadow:
			0 0 10px 2px rgb(255 120 135 / 0.95),
			0 0 44px 14px rgb(255 59 79 / 0.45);
	}
	.beam::before {
		content: '';
		position: absolute;
		top: 0;
		bottom: 0;
		right: 0;
		width: 7rem;
		background: linear-gradient(90deg, transparent, rgb(255 59 79 / 0.18));
	}
	/* ---- per-step effects on the card (positions in % of the 800 × 330 grid) ---- */
	.anchor {
		position: absolute;
		width: 1px;
		height: 1px;
	}
	/* driver: two translucent layers rising off the PCIe fingers (x 104–336, standing on y 300) */
	.holo {
		position: absolute;
		left: 13%;
		width: 29%;
		bottom: 9%;
		height: 44%;
		pointer-events: none;
		perspective: 500px;
	}
	.holo::before {
		content: '';
		position: absolute;
		inset: auto 6% 0;
		height: 100%;
		background: linear-gradient(0deg, rgb(255 59 79 / 0.32), transparent 85%);
		transform-origin: 50% 100%;
		transform: scaleY(0);
	}
	.slab {
		position: absolute;
		left: 0;
		right: 0;
		height: 38%;
		display: grid;
		place-items: center;
		border: 1px solid rgb(255 120 135 / 0.8);
		border-radius: 4px;
		background:
			repeating-linear-gradient(0deg, rgb(255 255 255 / 0.06) 0 1px, transparent 1px 4px),
			linear-gradient(180deg, rgb(255 59 79 / 0.34), rgb(255 59 79 / 0.1));
		box-shadow:
			0 0 18px -2px rgb(255 59 79 / 0.7),
			inset 0 1px 0 rgb(255 255 255 / 0.25);
		opacity: 0;
		transform: translate3d(0, 70%, 0) rotateX(55deg) scaleY(0.4);
	}
	.slab::after {
		content: attr(data-l);
		font-family: var(--font-mono);
		font-size: max(0.5625rem, 1.55cqw);
		font-weight: 600;
		letter-spacing: 0.12em;
		color: #fff4f5;
		text-shadow: 0 0 8px rgb(255 59 79 / 0.9);
		white-space: nowrap;
	}
	.s1 {
		bottom: 0;
	}
	.s2 {
		bottom: 50%;
	}
	.holo.on::before {
		transform: none;
		transition: transform 0.3s var(--glide);
	}
	.holo.on .slab {
		opacity: 1;
		transform: rotateX(14deg);
		transition:
			opacity 0.2s,
			transform 0.5s var(--spring);
	}
	.holo.on .s2 {
		transition-delay: 0.1s;
	}
	/* recommended model: the file block drops onto the memory (over the top chip row, x 300–506, y 48–70) */
	.drop {
		position: absolute;
		left: 37.5%;
		width: 25.75%;
		top: 14.5%;
		z-index: 1;
		height: 6.7%;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 0.6em;
		border-radius: 3px;
		background: linear-gradient(180deg, #8fe6e0, var(--model-qwen38));
		box-shadow:
			0 0 18px rgb(94 200 194 / 0.7),
			inset 0 1px 0 rgb(255 255 255 / 0.6);
		font-family: var(--font-mono);
		font-size: max(0.5rem, 1.05cqw);
		font-weight: 700;
		color: #062321;
		white-space: nowrap;
		opacity: 0;
	}
	.drop::before {
		content: attr(data-m);
	}
	.drop::after {
		content: attr(data-s);
	}
	.drop.on {
		opacity: 1;
		animation: land 0.5s var(--glide) both;
	}
	@keyframes land {
		0% {
			opacity: 0;
			transform: translate3d(0, -520%, 0) scale(1.15, 0.85);
		}
		55% {
			opacity: 1;
			transform: translate3d(0, 0, 0) scale(1.06, 0.8);
		}
		75% {
			transform: translate3d(0, -35%, 0) scale(0.98, 1.04);
		}
		100% {
			transform: none;
		}
	}
	/* callouts: the finding pops out of its part (CSS text, not page text) */
	.call {
		position: absolute;
		padding: 0.25em 0.6em;
		border: 1px solid rgb(255 120 135 / 0.75);
		border-radius: 4px;
		background: rgb(11 11 13 / 0.9);
		box-shadow: 0 0 18px -4px rgb(255 59 79 / 0.8);
		font-family: var(--font-mono);
		font-size: max(0.5625rem, 1.25cqw);
		font-weight: 600;
		letter-spacing: 0.04em;
		color: var(--text-hi);
		white-space: nowrap;
		opacity: 0;
		transform: translate(-50%, -80%) scale(0.5);
		transform-origin: 50% 100%;
	}
	.call::after {
		content: attr(data-l);
	}
	.call.below {
		transform: translate(-50%, -20%) scale(0.5);
		transform-origin: 50% 0;
	}
	.call.on {
		opacity: 1;
		transform: translate(-50%, -100%);
		transition:
			opacity 0.15s,
			transform 0.45s var(--spring);
	}
	.call.below.on {
		transform: translate(-50%, 0);
	}
	/* ---- leader: from the part to its log line (desktop) ---- */
	.leader {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		overflow: visible;
		pointer-events: none;
		z-index: 2;
	}
	.ld {
		fill: none;
		stroke: var(--amd);
		stroke-width: 1.5;
		stroke-dasharray: 1;
		stroke-dashoffset: 1;
		filter: drop-shadow(0 0 4px rgb(255 59 79 / 0.85));
		animation: draw 0.32s var(--glide) forwards;
	}
	@keyframes draw {
		to {
			stroke-dashoffset: 0;
		}
	}
	.ldot {
		fill: #0b0b0d;
		stroke: var(--amd);
		stroke-width: 2;
		filter: drop-shadow(0 0 6px rgb(255 59 79 / 0.9));
	}
	.ldot.end {
		fill: var(--amd);
		opacity: 0;
		animation: pop 0.2s linear 0.28s forwards;
	}
	@keyframes pop {
		to {
			opacity: 1;
		}
	}
	/* pins: a red dot on each part the scan has read, with a short tag (CSS text, not page text) */
	.pin {
		position: absolute;
		width: 12px;
		height: 12px;
		margin: -6px 0 0 -6px;
		border-radius: 50%;
		border: 2px solid var(--amd);
		background: #0b0b0d;
		box-shadow: 0 0 14px rgb(255 59 79 / 0.8);
		transform: scale(0);
		transition: transform 0.25s var(--glide);
	}
	.pin.on {
		transform: none;
		transition: transform 0.5s var(--spring);
	}
	.pin::before {
		content: '';
		position: absolute;
		inset: -8px;
		border-radius: 50%;
		border: 1px solid var(--amd);
		opacity: 0;
	}
	.pin.cur::before,
	.live .pin.on::before {
		animation: ping 2.4s var(--glide) infinite;
	}
	.pin.cur::before {
		animation-duration: 1.1s;
	}
	@keyframes ping {
		0% {
			opacity: 0.9;
			transform: scale(0.4);
		}
		100% {
			opacity: 0;
			transform: scale(1.6);
		}
	}
	.pin::after {
		content: attr(data-l);
		position: absolute;
		left: 14px;
		top: 50%;
		translate: 0 -50%;
		padding: 0.1rem 0.35rem;
		border-radius: 3px;
		background: rgb(11 11 13 / 0.88);
		border: 1px solid rgb(255 59 79 / 0.55);
		font-family: var(--font-mono);
		font-size: 0.625rem;
		letter-spacing: 0.08em;
		color: var(--text-hi);
		white-space: nowrap;
	}
	.pin.cur {
		background: var(--amd);
	}
	/* ---- detection log ---- */
	.log {
		grid-area: log;
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: 0.15rem;
		padding: var(--sp-3) var(--sp-4) var(--sp-3);
		border: 1px solid var(--line);
		border-left: 2px solid var(--amd);
		border-radius: var(--r-lg);
		background: linear-gradient(90deg, rgb(255 59 79 / 0.06), transparent 55%), rgb(11 11 13 / 0.75);
		font-family: var(--font-mono);
	}
	.lh {
		display: flex;
		align-items: center;
		gap: var(--sp-3);
		padding-bottom: var(--sp-2);
		margin-bottom: 0.2rem;
		border-bottom: 1px solid var(--line);
		font-size: var(--fs-2xs);
		letter-spacing: 0.12em;
		text-transform: uppercase;
	}
	.dot {
		width: 0.45rem;
		height: 0.45rem;
		border-radius: 50%;
		background: var(--amd);
		box-shadow: 0 0 8px rgb(255 59 79 / 0.8);
	}
	.dot.busy {
		animation: blink 0.9s steps(2, jump-none) infinite;
	}
	@keyframes blink {
		50% {
			opacity: 0.25;
		}
	}
	.track {
		position: relative;
		flex: 1;
		min-width: 2rem;
		height: 2px;
		background: var(--bg-3);
		overflow: hidden;
	}
	.fillbar {
		position: absolute;
		inset: 0;
		transform-origin: 0 50%;
		transform: scaleX(var(--g));
		background: linear-gradient(90deg, #8f1b29, var(--amd) 60%, #ffd5da);
		box-shadow: 0 0 8px rgb(255 59 79 / 0.8);
	}
	/* wraps on narrow logs, never truncated */
	.lab {
		min-width: 0;
		line-height: 1.4;
		text-wrap: balance;
		color: var(--text);
		letter-spacing: 0.06em;
	}
	.lines {
		display: grid;
		margin: 0;
		padding: 0;
		list-style: none;
	}
	/* one finding per line: key, value typed in (clip, full contrast), tick when read */
	.line {
		position: relative;
		display: grid;
		grid-template-columns: 7.8rem minmax(0, 1fr) 1rem;
		align-items: baseline;
		gap: var(--sp-3);
		padding: 0.32rem 0.5rem;
		margin-inline: -0.5rem;
		border-radius: var(--r-sm);
		transition:
			background-color 0.35s var(--glide),
			box-shadow 0.35s var(--glide);
	}
	.line.cur {
		background: rgb(255 59 79 / 0.09);
		box-shadow: inset 2px 0 0 var(--amd);
	}
	.lk {
		font-size: var(--fs-2xs);
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--text-mute);
		opacity: 0;
		transform: translate3d(-0.4rem, 0, 0);
	}
	.line.on .lk {
		opacity: 1;
		transform: none;
		transition:
			opacity 0.25s,
			transform 0.4s var(--glide);
	}
	.line.cur .lk {
		color: var(--amd);
	}
	.lv {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0.1rem 0.6rem;
		min-width: 0;
		clip-path: inset(-0.4em calc((1 - var(--k)) * 100%) -0.4em 0);
	}
	.line.count .lv {
		clip-path: none;
		opacity: min(1, calc(var(--k) * 4));
	}
	.lv b {
		font-family: var(--font-display);
		font-size: clamp(0.95rem, 0.8rem + 0.35vw, 1.1rem);
		font-weight: 720;
		font-stretch: 108%;
		letter-spacing: -0.01em;
		color: var(--text-hi);
	}
	.lv i {
		font-style: normal;
		font-size: var(--fs-2xs);
		letter-spacing: 0.03em;
		color: var(--text-mute);
	}
	.line::after {
		content: '✓';
		align-self: center;
		font-size: 0.75rem;
		color: var(--amd);
		transform: scale(0);
	}
	.line.ok::after {
		transform: none;
		transition: transform 0.45s var(--spring);
	}
	/* the outcome: what we pick for this card (key above the value) */
	.line.pick {
		grid-template-columns: minmax(0, 1fr) 1rem;
		row-gap: 0.15rem;
		margin-top: 0.35rem;
		padding-top: 0.55rem;
		border-top: 1px dashed var(--line);
		border-radius: 0;
	}
	.line.pick .lk {
		grid-column: 1 / -1;
	}
	.line.pick .lv b {
		white-space: nowrap;
	}
	.line.pick .lk::before {
		content: '→ ';
		color: var(--amd);
	}
	.line.pick .lv b {
		font-size: clamp(1rem, 0.8rem + 0.5vw, 1.25rem);
	}
	.lf {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--sp-3);
		padding-top: var(--sp-2);
		margin-top: 0.2rem;
		border-top: 1px solid var(--line);
	}
	.st {
		font-size: var(--fs-2xs);
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-mute);
		font-variant-numeric: tabular-nums;
		transition: color 0.4s;
	}
	.done .st {
		color: var(--text-hi);
	}
	.done .st::before {
		content: '✓ ';
		color: var(--amd);
	}

	/* short desktop screens (laptops): a tighter log keeps the scene in one viewport */
	@media (min-width: 901px) and (max-height: 800px) {
		.line {
			grid-template-columns: 7rem minmax(0, 1fr) 1rem;
			padding-block: 0.2rem;
		}
		.lv b {
			font-size: 0.95rem;
		}
	}
	@media (max-width: 900px) {
		.wrap {
			--rx: -6deg;
			--ry: -11deg;
		}
		.head :global(.sh) {
			grid-template-columns: minmax(0, 1fr);
		}
		/* simplified on the phone: the lens, the effects and the log line, no text callouts */
		.call,
		.drop::before {
			display: none;
		}
		/* heading, the card, then the log */
		.layout {
			grid-template-columns: minmax(0, 1fr);
			grid-template-areas: 'head' 'card' 'log';
			gap: var(--sp-3);
		}
		.stage {
			padding: 0.5rem 0 0.4rem;
		}
		/* the ticks show the progress; the lab note gets the whole header */
		.track {
			display: none;
		}
		.log {
			padding: var(--sp-2) var(--sp-3);
		}
		.gpu {
			width: min(94%, 36rem);
		}
		.line {
			grid-template-columns: 6.1rem minmax(0, 1fr) 0.8rem;
			gap: var(--sp-2);
			padding-block: 0.14rem;
		}
		.lk {
			font-size: 0.625rem;
			letter-spacing: 0.05em;
		}
		.lv b {
			font-size: 0.875rem;
		}
		.lv i {
			font-size: 0.625rem;
		}
		.line.pick {
			grid-template-columns: minmax(0, 1fr) 0.8rem;
			margin-top: 0.2rem;
			padding-top: 0.35rem;
		}
		.line.pick .lv b {
			font-size: 0.9375rem;
		}
		.lab {
			font-size: 0.625rem;
		}
		.pin::after {
			display: none;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.gpu.go,
		.live .floor,
		.dot.busy,
		.pin::before,
		.drop.on,
		.ld,
		.ldot.end {
			animation: none;
		}
		.ld {
			stroke-dashoffset: 0;
		}
		.ldot.end {
			opacity: 1;
		}
		.xray,
		.holo::before,
		.holo .slab,
		.call,
		.pin,
		.line,
		.line .lk,
		.line::after,
		.st {
			transition: none;
		}
	}
</style>
