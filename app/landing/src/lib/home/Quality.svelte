<script lang="ts">
	/**
	 * Jakość as one picture on a LINEAR KLD scale:
	 * - the main plot puts our engine's difference vs upstream (SHEET.correctness.quality, RTX 3060)
	 *   and upstream's own noise (ubatch 256 vs 512) next to the smallest format change
	 *   (SHEET.lfmFormats5060: another model, for scale). On that scale ours and the noise are a
	 *   hairline at zero; the format change towers, with the "≈ 310×" dimension next to it;
	 * - a magnifier inset shows the same hairlines ZOOM× closer: ours ≈ noise, pair by pair;
	 * - below: the lossless switches keep the greedy text bit-identical (md5 gates), while the
	 *   default build differs at noise level, which is why KLD is measured at all.
	 */
	import { reveal } from '$lib/fx/actions';
	import { findCard, MODEL_INFO, SHEET } from '$lib/data/measurements';
	import { num, type Lang } from '$lib/i18n';
	import ModelMark from '$lib/ModelMark.svelte';
	import { MODEL_STYLE } from '$lib/modelStyle';
	import { copy } from '$lib/site/copy';
	import { fill } from './data';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(copy[lang].quality);
	const titleParts = $derived(c.title.split('|'));
	const q = SHEET.correctness.quality;
	const where = findCard('rtx-3060-12')?.name ?? '';
	const where5060 = findCard('rtx-5060-ti-16')?.name ?? '';

	const ours = (['saluki', 'bonsai'] as const).map((k) => ({ k, name: MODEL_INFO[k].name, ...q[k] }));
	/** The smallest format change with a same-text check: QAD-Q4_0 vs Q8_0 on LFM2.5. */
	const fmt = SHEET.lfmFormats5060.filter((r) => r.md5Same !== null).reduce((a, b) => (b.kld.v < a.kld.v ? b : a));
	const fmtName = fmt.file.replace(/\s*\(.*\)$/, '');
	const worstOurs = Math.max(...ours.map((r) => r.ours.v));
	/** Rounded down to two significant digits: never overstated. */
	const ratio = (() => {
		const r = fmt.kld.v / worstOurs;
		const p = 10 ** (Math.floor(Math.log10(r)) - 1);
		return Math.floor(r / p) * p;
	})();

	/* Linear scales with round ends: the main plot tops out just above the format change, the inset
	   is the same scale ZOOM× closer, so its top sits just above our worst value. */
	const STEPS = [1, 2, 2.5, 5, 10];
	const decade = (v: number) => 10 ** Math.floor(Math.log10(v));
	const niceUp = (v: number) => (STEPS.find((s) => s * decade(v) >= v * (1 - 1e-9)) ?? 10) * decade(v);
	const niceDown = (v: number) => ([...STEPS].reverse().find((s) => s * decade(v) <= v * (1 + 1e-9)) ?? 1) * decade(v);
	const MAX = niceUp(fmt.kld.v * 1.15);
	const ZOOM = niceDown(MAX / (worstOurs * 1.25));
	const ZMAX = MAX / ZOOM;
	const ticksOf = (max: number) => {
		const step = niceUp(max / 2.5);
		return Array.from({ length: Math.floor(max / step + 1e-9) + 1 }, (_, i) => i * step);
	};
	const ticks = ticksOf(MAX);
	const zticks = ticksOf(ZMAX);
	/** Fewest decimals that show the value exactly (0,1 · 0,0004). */
	const dec = (v: number) => {
		for (let d = 0; d < 7; d++) if (Math.abs(Math.round(v * 10 ** d) - v * 10 ** d) < 1e-6) return d;
		return 6;
	};
	const tick = (v: number) => num(v, lang, dec(v));
	const val = (v: number) => num(v, lang, Math.max(2, -Math.floor(Math.log10(v)) + 1));

	const summary = $derived(
		`${fill(c.lede, { x: num(ratio, lang, 0) })} ${ours.map((r) => `${r.name}: ${c.ours} ${val(r.ours.v)}, ${c.noise} ${val(r.noise.v)}`).join('; ')}. ${c.fmtBar} (${fmtName}): ${num(fmt.kld.v, lang, 3)}.`
	);
</script>

<section id="quality" class="quality heat-top" aria-labelledby="quality-title">
	<div class="inner">
		<header class="head">
			<h2 id="quality-title" class="statement">
				{#each titleParts as p, i (i)}<span class:hot={i === titleParts.length - 1}>{p}</span>{/each}
			</h2>
			<p class="lede">{fill(c.lede, { x: num(ratio, lang, 0) })}</p>
		</header>

		<figure class="board" use:reveal={{ threshold: 0.25 }}>
			<p class="sr-only">{summary}</p>
			<div class="stage" aria-hidden="true">
			<div class="plot">
				{#each ticks as t, i (i)}
					<span class="gl" class:zero={t === 0} style="--t:{t / MAX}"><i>{tick(t)}</i></span>
				{/each}

				<!-- ours and upstream's noise: on this scale, a hairline at zero -->
				<div class="tiny">
					{#each ours as r (r.k)}
						<span class="b noise" style="--h:{r.noise.v / MAX}"></span>
						<span class="b ours" style="--h:{r.ours.v / MAX}"></span>
					{/each}
				</div>
				<span class="lens"></span>
				<span class="beam"></span>
				<span class="here">{c.here}</span>

				<!-- the format change: same scale, towering -->
				<div class="tall" style="--h:{fmt.kld.v / MAX}">
					<span class="tv">{num(fmt.kld.v, lang, 3)}</span>
				</div>
				<div class="dim" style="--h:{fmt.kld.v / MAX}">
					<span class="dl"><b>≈&nbsp;{num(ratio, lang, 0)}×</b><small>{c.times}</small></span>
				</div>

				<p class="lab lab-tiny"><b>{c.tinyLabel}</b></p>
				<p class="lab lab-tall"><b>{c.fmtBar}</b><small><ModelMark model="lfm25" size="0.85em" /> {fill(c.fmtSub, { fmt: fmtName })}</small></p>
			</div>

				<!-- the magnifier: the same hairlines ZOOM× closer -->
				<div class="inset">
					<p class="ih"><span class="zx">×{num(ZOOM, lang, 0)}</span>{c.zoomTitle}</p>
					<p class="legend">
						<span><i class="sw noise"></i>{c.noise}</span>
						<span><i class="sw ours"></i>{c.ours}</span>
					</p>
					<div class="iplot">
						{#each zticks as t, i (i)}
							<span class="gl" class:zero={t === 0} style="--t:{t / ZMAX}"><i>{tick(t)}</i></span>
						{/each}
						{#each ours as r, i (r.k)}
							<div class="pair" style="--i:{i}">
								<span class="zb noise" style="--h:{r.noise.v / ZMAX}"><em>{val(r.noise.v)}</em></span>
								<span class="zb ours" style="--h:{r.ours.v / ZMAX}"><em>{val(r.ours.v)}</em></span>
								<span class="pn"><ModelMark model={r.k} size="0.85em" /> {MODEL_STYLE[r.k].short}</span>
							</div>
						{/each}
					</div>
					<p class="verdict">{c.verdict}</p>
				</div>
			</div>
			<figcaption class="caption">{fill(c.caption, { card: where, card2: where5060 })}</figcaption>
		</figure>

		<div class="same">
			<div class="st">
				<h3>{c.same.title}</h3>
				<p>{c.same.note}</p>
			</div>
			<ul class="sl">
				{#each c.same.items as it (it)}
					<li><span class="sn">{it}</span><span class="eq" aria-hidden="true"></span><span class="ok">✓ {c.same.ok}</span></li>
				{/each}
			</ul>
		</div>
	</div>
</section>

<style>
	.quality {
		position: relative;
		background:
			radial-gradient(60% 50% at 85% 35%, rgb(255 122 26 / 0.07), transparent 70%),
			var(--bg-0);
	}
	.inner {
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
		padding-block: clamp(3.5rem, 2.5rem + 3vw, 6rem);
		display: grid;
		gap: clamp(1.75rem, 3.5vw, 3rem);
	}
	.head {
		display: grid;
		grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr);
		gap: clamp(1.25rem, 4vw, 4rem);
		align-items: end;
	}
	.statement {
		margin: 0;
		font-family: var(--font-display);
		font-size: clamp(2.1rem, 0.8rem + 3vw, 4.2rem);
		font-weight: 800;
		font-stretch: 108%;
		line-height: 0.98;
		letter-spacing: -0.04em;
		color: var(--text-hi);
		text-wrap: balance;
	}
	.statement span {
		display: block;
	}
	.statement .hot {
		width: fit-content;
		max-width: 100%;
		background: var(--heat-large);
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
		padding-bottom: 0.08em;
	}
	.lede {
		margin: 0;
		max-width: 38rem;
		font-size: var(--fs-md);
		line-height: 1.5;
		color: var(--text);
		text-wrap: pretty;
	}

	/* ---- the board: one linear plot with a magnifier ---- */
	.board {
		--lx: 1.4rem; /* left edge of the hairline group */
		--gw: 2.6rem; /* its width */
		--lr: 1.9rem; /* lens radius */
		--tw: clamp(5.5rem, 3rem + 7vw, 10rem); /* tall bar width */
		--tr: 3rem; /* room for tick labels at the right */
		margin: 0;
		display: grid;
		gap: 1rem;
		padding: clamp(1rem, 2.5vw, 2rem) clamp(1rem, 3vw, 2.25rem) clamp(0.9rem, 2vw, 1.4rem);
		border-radius: var(--r-xl);
		background: linear-gradient(180deg, rgb(255 255 255 / 0.02), transparent), var(--bg-1);
		box-shadow: inset 0 0 0 1px var(--line);
	}
	.stage {
		--ph: clamp(24rem, 16rem + 11vw, 30rem);
		--iw: min(34rem, 50%);
		--ih: calc(var(--ph) - var(--lr) - 3.4rem);
		position: relative;
	}
	.plot {
		position: relative;
		height: var(--ph);
		margin-bottom: 3.6rem; /* the labels under the baseline */
	}
	.gl {
		position: absolute;
		left: 0;
		right: 0;
		bottom: calc(var(--t) * 100%);
		height: 0;
		border-top: 1px dashed color-mix(in srgb, var(--text) 16%, transparent);
	}
	.gl.zero {
		border-top: 1px solid var(--line-strong);
	}
	.gl i {
		position: absolute;
		right: 0;
		bottom: 0.25rem;
		font-family: var(--font-mono);
		font-style: normal;
		font-size: var(--fs-2xs);
		font-variant-numeric: tabular-nums;
		color: var(--text-mute);
	}
	/* bars: steel = upstream vs itself, amber = ours vs upstream (same mapping in the inset) */
	.b.noise,
	.zb.noise,
	.sw.noise {
		background: linear-gradient(0deg, color-mix(in srgb, var(--before) 70%, transparent), var(--before));
	}
	.b.ours,
	.zb.ours,
	.sw.ours {
		background: linear-gradient(0deg, var(--heat-3), var(--heat-4));
	}
	.tiny {
		position: absolute;
		left: var(--lx);
		bottom: 0;
		width: var(--gw);
		height: 100%;
		display: flex;
		align-items: flex-end;
		justify-content: space-between;
	}
	.b {
		width: 0.45rem;
		height: max(2px, calc(var(--h) * 100%));
		border-radius: 1px 1px 0 0;
	}
	.lens {
		position: absolute;
		left: calc(var(--lx) + var(--gw) / 2 - var(--lr));
		bottom: calc(-1 * var(--lr));
		width: calc(2 * var(--lr));
		height: calc(2 * var(--lr));
		border-radius: 50%;
		border: 2px solid var(--heat-4);
		box-shadow:
			0 0 0 4px color-mix(in srgb, var(--heat-4) 14%, transparent),
			0 0 24px rgb(255 193 90 / 0.35);
		background: radial-gradient(circle, rgb(255 193 90 / 0.08), transparent 70%);
	}
	/* light from the lens up into the inset */
	.beam {
		position: absolute;
		z-index: 1;
		left: 0;
		width: var(--iw);
		top: var(--ih);
		bottom: var(--lr);
		background: linear-gradient(0deg, rgb(255 193 90 / 0.34), rgb(255 193 90 / 0.06));
		clip-path: polygon(0 0, 100% 0, calc(var(--lx) + var(--gw) / 2 + var(--lr) * 0.8) 100%, calc(var(--lx) + var(--gw) / 2 - var(--lr) * 0.8) 100%);
	}
	.here {
		display: none;
	}
	.tall {
		position: absolute;
		right: var(--tr);
		bottom: 0;
		width: var(--tw);
		height: calc(var(--h) * 100%);
		border-radius: 6px 6px 0 0;
		background:
			repeating-linear-gradient(135deg, rgb(255 255 255 / 0.07) 0 2px, transparent 2px 9px),
			linear-gradient(0deg, var(--heat-1), var(--heat-2));
		box-shadow: 0 0 40px rgb(226 64 28 / 0.25);
		transform-origin: 50% 100%;
	}
	.tv {
		position: absolute;
		left: 50%;
		bottom: calc(100% + 0.35rem);
		transform: translateX(-50%);
		font-family: var(--font-display);
		font-variant-numeric: tabular-nums lining-nums;
		font-size: var(--fs-lg);
		font-weight: 700;
		color: var(--text-hi);
		white-space: nowrap;
	}
	/* the dimension: from zero (where ours sits) to the top of the format change */
	.dim {
		position: absolute;
		right: calc(var(--tr) + var(--tw) + 0.9rem);
		bottom: 0;
		height: calc(var(--h) * 100%);
		width: 0.7rem;
		border: 2px solid var(--heat-3);
		border-left: 0;
		transform-origin: 50% 100%;
	}
	.dl {
		position: absolute;
		right: calc(100% + 0.6rem);
		top: 50%;
		transform: translateY(-50%);
		display: grid;
		justify-items: end;
		text-align: right;
		gap: 0.2rem;
	}
	.dl b {
		font-family: var(--font-display);
		font-size: clamp(2rem, 1rem + 2.6vw, 3.6rem);
		font-weight: 820;
		line-height: 0.95;
		letter-spacing: -0.04em;
		white-space: nowrap;
		background: var(--heat-large);
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
		filter: drop-shadow(0 0 0.25em rgb(255 122 26 / 0.35));
	}
	.dl small {
		max-width: 10rem;
		font-size: var(--fs-xs);
		line-height: 1.3;
		color: var(--text);
	}
	.lab {
		position: absolute;
		top: calc(100% + var(--lr) + 0.3rem);
		margin: 0;
		display: grid;
		gap: 0.15rem;
		font-size: var(--fs-xs);
		line-height: 1.3;
		color: var(--text);
	}
	.lab b {
		font-weight: 600;
		color: var(--text-hi);
	}
	.lab small {
		display: block;
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.lab-tiny {
		left: 0;
		max-width: 12rem;
	}
	.lab-tall {
		top: calc(100% + 0.5rem);
		right: var(--tr);
		width: max-content;
		max-width: min(16rem, 60%);
		justify-items: end;
		text-align: right;
	}

	.inset {
		position: absolute;
		left: 0;
		top: 0;
		width: var(--iw);
		height: var(--ih);
		display: grid;
		grid-template-rows: auto auto minmax(0, 1fr) auto;
		gap: 0.6rem;
		padding: clamp(0.9rem, 1.6vw, 1.25rem);
		border-radius: var(--r-lg, 14px);
		background: color-mix(in srgb, var(--bg-2, var(--bg-1)) 92%, transparent);
		box-shadow:
			inset 0 0 0 1.5px color-mix(in srgb, var(--heat-4) 55%, transparent),
			0 0 44px rgb(255 193 90 / 0.08);
		transform-origin: 10% 100%;
	}
	.ih {
		margin: 0;
		display: flex;
		align-items: baseline;
		flex-wrap: wrap;
		gap: 0.2rem 0.6rem;
		font-size: var(--fs-sm);
		font-weight: 600;
		color: var(--text-hi);
	}
	.zx {
		font-family: var(--font-display);
		font-size: var(--fs-lg);
		font-weight: 800;
		color: var(--heat-4);
	}
	.legend {
		margin: 0;
		display: flex;
		flex-wrap: wrap;
		gap: 0.3rem 1.1rem;
		font-size: var(--fs-xs);
		color: var(--text);
	}
	.legend span {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
	}
	.sw {
		width: 0.7rem;
		height: 0.7rem;
		border-radius: 2px;
	}
	.iplot {
		position: relative;
		min-height: 7rem;
		margin: 1.4rem 2.4rem 1.6rem 0; /* value labels above, tick labels right, names below */
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 1rem;
	}
	.iplot .gl i {
		right: auto;
		left: calc(100% + 0.4rem);
		bottom: -0.45em;
	}
	.pair {
		position: relative;
		display: flex;
		justify-content: center;
		align-items: flex-end;
		gap: clamp(0.35rem, 1vw, 0.7rem);
	}
	.zb {
		position: relative;
		width: clamp(1.6rem, 0.8rem + 2.4vw, 3rem);
		height: calc(var(--h) * 100%);
		border-radius: 4px 4px 0 0;
		transform-origin: 50% 100%;
	}
	.zb.ours {
		box-shadow: 0 0 22px rgb(255 122 26 / 0.3);
	}
	.zb em {
		position: absolute;
		left: 50%;
		bottom: calc(100% + 0.25rem);
		transform: translateX(-50%);
		font-family: var(--font-mono);
		font-style: normal;
		font-size: var(--fs-2xs);
		font-variant-numeric: tabular-nums;
		color: var(--text-hi);
		white-space: nowrap;
	}
	.zb.noise em {
		color: var(--text);
	}
	.pn {
		position: absolute;
		top: calc(100% + 0.4rem);
		left: 0;
		right: 0;
		display: flex;
		justify-content: center;
		align-items: center;
		gap: 0.3rem;
		font-size: var(--fs-xs);
		color: var(--text);
		white-space: nowrap;
	}
	.verdict {
		margin: 0;
		font-size: var(--fs-sm);
		font-weight: 600;
		line-height: 1.35;
		color: var(--heat-4);
		text-wrap: balance;
	}
	.caption {
		font-size: var(--fs-xs);
		line-height: 1.5;
		color: var(--text-mute);
		max-width: 62rem;
	}

	/* ---- the lossless switches ---- */
	.same {
		display: grid;
		grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr);
		gap: clamp(1rem, 3vw, 3rem);
		align-items: center;
		padding: clamp(1.1rem, 2.5vw, 1.75rem) clamp(1rem, 3vw, 2.25rem);
		border-radius: var(--r-xl);
		background: var(--bg-1);
		box-shadow: inset 0 0 0 1px var(--line);
	}
	.st h3 {
		margin: 0 0 0.45rem;
		font-family: var(--font-display);
		font-size: var(--fs-lg);
		font-weight: 750;
		letter-spacing: -0.02em;
		color: var(--text-hi);
	}
	.st p {
		margin: 0;
		font-size: var(--fs-sm);
		line-height: 1.55;
		color: var(--text);
		text-wrap: pretty;
	}
	.sl {
		margin: 0;
		padding: 0;
		list-style: none;
		display: grid;
		gap: 0.55rem;
	}
	.sl li {
		display: grid;
		grid-template-columns: auto minmax(1rem, 1fr) auto;
		align-items: center;
		gap: 0.7rem;
		font-size: var(--fs-sm);
	}
	.sn {
		color: var(--text-hi);
		font-weight: 600;
	}
	.eq {
		height: 0;
		border-top: 1px dashed var(--line-strong);
	}
	.ok {
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		color: var(--heat-4);
		white-space: nowrap;
	}

	/* ---- motion: resting state is final; entering view replays the build-up ---- */
	@media (prefers-reduced-motion: no-preference) {
		:global(html.js) .board:global([data-in]) .tall,
		:global(html.js) .board:global([data-in]) .dim {
			animation: grow 1.2s var(--ease-out) 0.1s backwards;
		}
		:global(html.js) .board:global([data-in]) .dl,
		:global(html.js) .board:global([data-in]) .tv {
			animation: rise 0.7s var(--ease-out) 0.9s backwards;
		}
		:global(html.js) .board:global([data-in]) .lens {
			animation: pop 0.8s var(--ease-spring) 0.45s backwards;
		}
		:global(html.js) .board:global([data-in]) .beam {
			animation: fade 0.8s var(--ease-out) 0.7s backwards;
		}
		:global(html.js) .board:global([data-in]) .inset {
			animation: zoom-in 0.9s var(--ease-out) 0.7s backwards;
		}
		:global(html.js) .board:global([data-in]) .zb {
			animation: grow 0.9s var(--ease-spring) calc(1.2s + var(--i, 0) * 0.15s) backwards;
		}
		:global(html.js) .board:global([data-in]) .verdict {
			animation: rise 0.6s var(--ease-out) 1.7s backwards;
		}
	}
	@keyframes grow {
		from {
			transform: scaleY(0);
		}
	}
	@keyframes rise {
		from {
			opacity: 0;
			translate: 0 0.6rem;
		}
	}
	@keyframes pop {
		from {
			opacity: 0;
			transform: scale(0.3);
		}
	}
	@keyframes fade {
		from {
			opacity: 0;
		}
	}
	@keyframes zoom-in {
		from {
			opacity: 0;
			transform: scale(0.4);
		}
	}

	/* light ("bone"): heat is light, never rust; small heat text becomes the accent ink */
	:global(:root[data-theme='light']) .tall {
		background:
			repeating-linear-gradient(135deg, rgb(255 255 255 / 0.14) 0 2px, transparent 2px 9px),
			linear-gradient(0deg, var(--heat-2), var(--heat-3));
	}
	:global(:root[data-theme='light']) :is(.zx, .verdict, .ok, .here) {
		color: var(--accent-ink);
	}

	@media (max-width: 900px) {
		.head,
		.same {
			grid-template-columns: minmax(0, 1fr);
		}
	}
	/* narrow: the inset leaves the plot and sits under it; the lens gets a pointer label */
	@media (max-width: 900px) {
		.board {
			--tw: 4.4rem;
			--lr: 1.6rem;
			--tr: 0rem;
		}
		.stage {
			--ph: clamp(17rem, 12rem + 10vw, 22rem);
		}
		.plot {
			margin-bottom: 4.6rem;
		}
		/* the bar carries its own value; the tick labels would collide with the dimension */
		.plot > .gl i {
			display: none;
		}
		.beam {
			display: none;
		}
		.here {
			display: block;
			position: absolute;
			left: calc(var(--lx) + var(--gw) / 2 - 0.5rem);
			bottom: calc(var(--lr) + 0.5rem);
			max-width: 7.5rem;
			font-size: var(--fs-2xs);
			line-height: 1.3;
			color: var(--heat-4);
		}
		.dl b {
			font-size: clamp(1.6rem, 1rem + 3vw, 2.2rem);
		}
		.dl small {
			max-width: 6.5rem;
		}
		.lab-tiny {
			max-width: 8.5rem;
		}
		.lab-tall {
			max-width: 55%;
		}
		.inset {
			position: relative;
			width: auto;
			height: auto;
			min-height: 18rem;
		}
		.iplot {
			min-height: 9rem;
		}
		.zb {
			width: 2.8rem;
		}
		.pair {
			gap: 0.5rem;
		}
		.zb em {
			font-size: 0.625rem;
		}
	}
	@media (max-width: 480px) {
		.iplot {
			margin-right: 0;
		}
		.iplot .gl i {
			display: none;
		}
	}
</style>
