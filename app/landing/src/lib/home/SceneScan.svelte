<script lang="ts">
	/**
	 * Scene 01, Skan: our lab card, a Sapphire PULSE RX 7900 XTX (`PulseXtx`, assembled as a CSS 3D box
	 * seen at a slight three-quarter angle), and a detection log of what our scanner reads from it. One
	 * auto-played timeline (`Autoplay`, plays once on entering the viewport, replay button):
	 *   card springs in (motion blur) → fans spin up to a blur → a red beam sweeps the card with an x-ray
	 *   band behind it → the log types one line per finding, and each line opens an x-ray lens on its
	 *   part of the board, lights that part red and drops a pin on it → recommended model → „Gotowe ·
	 *   4/4” → the fans coast to a stop and the floor light breathes while the scene is on screen.
	 * Desktop: hovering a log line re-opens its lens; the card leans toward the pointer. Every value is
	 * real: the registry entry of the card (960 GB/s, the driver's default power cap 303 W measured on
	 * our machine) and `XTX_BOARD` (Sapphire spec sheet, vulkaninfo, our ROCm notes). The illustration
	 * and the log are aria-hidden; screen readers get one sentence. The server HTML, reduced motion and
	 * an off-screen exit show the final state. Red is the Radeon accent; heat colours stay for speed.
	 */
	import { Autoplay } from '$lib/fx/autoplay.svelte';
	import { clamp01, easeInOutCubic, reducedMotion } from '$lib/fx/motion';
	import Replay from '$lib/fx/Replay.svelte';
	import { num, type Lang } from '$lib/i18n';
	import { copy } from '$lib/site/copy';
	import { fill, SCAN_BOARD as B, SCAN_CARD as C } from './data';
	import PulseXtx from './PulseXtx.svelte';
	import SceneHead from './SceneHead.svelte';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(copy[lang].how.scan);
	const tl = new Autoplay(4.8, '0px 0px -25% 0px', { arm: true });
	const p = $derived(tl.p);

	/* ---- timeline (fractions of the 4.8 s) ---- */
	const SWEEP: [number, number] = [0.15, 0.36];
	/** Start of each log line; each types over TYPE. */
	const START = [0.38, 0.47, 0.55, 0.64, 0.73, 0.82];
	const TYPE = 0.055;
	const DONE = 0.9;
	/** The x-ray band behind the beam, as a fraction of the card width. */
	const BAND = 0.25;
	const b = $derived(easeInOutCubic(clamp01((p - SWEEP[0]) / (SWEEP[1] - SWEEP[0]))) * (1 + BAND));
	const sweeping = $derived(p > SWEEP[0] && p < SWEEP[1]);

	/**
	 * Fans: spin up over [0, UP], full speed until DOWN, then coast to a stop ((1 − u)² decay). `spin`
	 * is the integral of `rpm`, scaled so the rotors end after exactly TURNS turns (hubs upright).
	 */
	const UP = 0.1;
	const DOWN = 0.84;
	const TURNS = 14;
	const K = TURNS / (UP / 2 + (DOWN - UP) + (1 - DOWN) / 3);
	const rpm = $derived(p < UP ? p / UP : p < DOWN ? 1 : (1 - (p - DOWN) / (1 - DOWN)) ** 2);
	const spin = $derived(
		p < UP ? (K * p * p) / (2 * UP) : p < DOWN ? K * (UP / 2 + p - UP) : K * (UP / 2 + DOWN - UP + ((1 - DOWN) * (1 - (1 - (p - DOWN) / (1 - DOWN)) ** 3)) / 3)
	);

	/* ---- what the scan reads, and where it sits on the card (800 × 330 grid of `PulseXtx`) ---- */
	type PartId = 'gpu' | 'vram' | 'bw' | 'pwr';
	const PARTS: Record<PartId, { r: [number, number, number, number]; pin: [number, number]; tag: string }> = {
		gpu: { r: [204, 74, 376, 246], pin: [290, 96], tag: 'GPU' },
		vram: { r: [158, 34, 422, 286], pin: [310, 38], tag: 'VRAM' },
		bw: { r: [158, 34, 422, 286], pin: [240, 272], tag: 'GB/s' },
		pwr: { r: [436, 0, 712, 236], pin: [628, 34], tag: 'W' }
	};
	const PART_IDS = Object.keys(PARTS) as PartId[];
	const gfx = C.arch.split(' ').pop() ?? '';
	const model = C.runs.find((r) => r.model === C.pick.model)?.title ?? '';
	const lines = $derived(
		[
			{ part: 'gpu', key: c.gpu, value: `AMD ${C.name}`, sub: `${B.chip.v} · ${gfx}` },
			{ part: 'gpu', key: c.driver, value: `ROCm ${B.rocm.v} · HIP`, sub: '' },
			{ part: 'vram', key: c.vram, value: `${C.vramGB}\u00a0GB ${B.memType.v}`, sub: `${B.busBits.v}-bit` },
			{ part: 'bw', key: c.bw, value: `${num(C.bwGBs.v, lang, 0)}\u00a0GB/s`, sub: `${B.gbps.v}\u00a0Gbps × ${B.busBits.v}\u00a0bit` },
			{ part: 'pwr', key: c.power, value: `${num(C.powerW.v, lang, 0)}\u00a0W`, sub: c.powerSub },
			{ part: null, key: c.model, value: model, sub: '' }
		].map((l, i) => ({ ...l, part: l.part as PartId | null, k: clamp01((p - START[i]) / TYPE) }))
	);
	/** First log line of each part: the part lights and gets its pin when that line starts. */
	const seen = $derived(Object.fromEntries(PART_IDS.map((id) => [id, lines.some((l) => l.part === id && l.k > 0)])) as Record<PartId, boolean>);
	const lit = $derived({ gpu: seen.gpu, mem: seen.vram, bus: seen.bw, pwr: seen.pwr });
	const found = $derived(PART_IDS.filter((id) => lines.some((l) => l.part === id && l.k >= 1)).length);
	/** Desktop: the log line under the pointer. */
	let hover: number | null = $state(null);
	/** The highlighted log line: the hovered one, else the one being typed (until the model line). */
	const active = $derived.by((): number | null => {
		if (hover !== null && !tl.playing) return hover;
		if (p >= START[5] || p < START[0]) return null;
		const i = lines.findLastIndex((l) => l.k > 0);
		return i < 0 ? null : i;
	});
	/** The part under the x-ray lens. */
	const focus = $derived(active === null ? null : lines[active].part);
	const pct = (v: number, of: number) => `${((v / of) * 100).toFixed(2)}%`;
	const xclip = $derived.by(() => {
		if (sweeping) return `inset(-12% ${((1 - Math.min(b, 1)) * 100).toFixed(2)}% -12% ${((b - BAND) * 100).toFixed(2)}%)`;
		if (!focus) return 'inset(50% 50% 50% 50% round 14px)';
		const [x1, y1, x2, y2] = PARTS[focus].r;
		return `inset(${pct(y1, 330)} ${pct(800 - x2, 800)} ${pct(330 - y2, 330)} ${pct(x1, 800)} round 14px)`;
	});
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

	const fine = () => !reducedMotion() && matchMedia('(hover: hover) and (pointer: fine)').matches;

	/** Desktop: the card leans toward the pointer (CSS vars on the stage, one write per frame). */
	function tilt(node: HTMLElement) {
		if (!fine()) return;
		let raf = 0;
		let x = 0;
		let y = 0;
		const apply = () => {
			raf = 0;
			node.style.setProperty('--tx', x.toFixed(3));
			node.style.setProperty('--ty', y.toFixed(3));
		};
		const queue = () => {
			if (!raf) raf = requestAnimationFrame(apply);
		};
		const move = (e: PointerEvent) => {
			const r = node.getBoundingClientRect();
			x = Math.max(-1, Math.min(1, ((e.clientX - r.left) / r.width) * 2 - 1));
			y = Math.max(-1, Math.min(1, ((e.clientY - r.top) / r.height) * 2 - 1));
			queue();
		};
		const leave = () => {
			x = 0;
			y = 0;
			queue();
		};
		node.addEventListener('pointermove', move);
		node.addEventListener('pointerleave', leave);
		return {
			destroy() {
				cancelAnimationFrame(raf);
				node.removeEventListener('pointermove', move);
				node.removeEventListener('pointerleave', leave);
			}
		};
	}

	/** Desktop: hovering a log line points the x-ray lens at its part. */
	function lineHover(node: HTMLElement) {
		if (!fine()) return;
		const over = (e: PointerEvent) => {
			const li = (e.target as Element).closest<HTMLElement>('[data-i]');
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
	<div class="layout">
		<div class="head"><SceneHead id="scene-scan" k={c.k} step={c.title} head={c.head} body={c.body} /></div>
		<div class="log" class:done>
			<div class="lh" aria-hidden="true">
				<span class="dot" class:busy={tl.playing}></span>
				<span class="lab">{B.maker} {B.series} · {c.lab}</span>
				<span class="track"><span class="fillbar" style="--g:{prog}"></span></span>
			</div>
			<ol class="lines" aria-hidden="true" use:lineHover>
				{#each lines as l, i (l.key)}
					<li class="line" class:on={l.k > 0} class:ok={l.k >= 1} class:cur={i === active && l.part !== null} class:pick={l.part === null} data-i={i} style="--k:{l.k}">
						<span class="lk">{l.key}</span>
						<span class="lv"><b>{l.value}</b>{#if l.sub}<i>{l.sub}</i>{/if}</span>
					</li>
				{/each}
			</ol>
			<div class="lf">
				<span class="st" aria-hidden="true">{done ? c.done : c.reading} · {found}/{PART_IDS.length}</span>
				<Replay {lang} onclick={tl.replay} disabled={tl.playing} />
			</div>
			<p class="sr-only">{sr}</p>
		</div>
		<div class="stage" aria-hidden="true" use:tilt>
			<div class="gpu" class:go={p > 0} class:wait={p === 0} style="--spin:{spin}; --rpm:{rpm}">
				<span class="shadow"></span>
				<span class="floor"></span>
				<div class="box">
					<div class="face top"><PulseXtx part="top" /></div>
					<div class="face end"><PulseXtx part="end" /></div>
					<!-- one flat face: shroud, x-ray lens, beam and pins never depth-fight -->
					<div class="face front">
						<PulseXtx part="front" />
						<div class="xray" class:sweeping style="clip-path:{xclip}"><PulseXtx part="xray" {lit} /></div>
						<div class="sweep" class:on={sweeping}><span class="beam"></span></div>
						{#each PART_IDS as id (id)}
							<span class="pin" class:on={seen[id]} class:cur={focus === id} data-l={PARTS[id].tag} style="left:{pct(PARTS[id].pin[0], 800)}; top:{pct(PARTS[id].pin[1], 330)}"></span>
						{/each}
					</div>
				</div>
			</div>
		</div>
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
	/* the 3D box: three-quarter pose plus the pointer lean (desktop) */
	.box {
		position: absolute;
		inset: 0;
		transform-style: preserve-3d;
		transform: perspective(1700px) rotateX(calc(var(--rx) + var(--ty, 0) * 3deg)) rotateY(calc(var(--ry) + var(--tx, 0) * 6deg));
		transition: transform 0.9s var(--glide);
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
		transition: clip-path 0.6s var(--glide);
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
	.sweep {
		position: absolute;
		inset: -8% 0;
		transform: translate3d(calc(min(var(--b), 1) * 100%), 0, 0);
		opacity: 0;
		pointer-events: none;
	}
	.sweep.on {
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
	.lab {
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
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
		.pin::before {
			animation: none;
		}
		.box,
		.xray,
		.pin,
		.line,
		.line .lk,
		.line::after,
		.st {
			transition: none;
		}
	}
</style>
