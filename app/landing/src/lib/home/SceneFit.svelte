<script lang="ts">
	/**
	 * Scene 02, Dobór (memory is bone/steel, never heat): a full-width 24 GB VRAM tray. The measured
	 * model falls in under gravity, squashes and settles (file size, then what our engine really
	 * uses on top of it, dotted = overhead) → „pasuje”. Then the same model in Q8_0 (estimator size,
	 * hatched = does not fit) falls, its end hits the 24 GB wall, it is flung up past the top of the
	 * scene, drops back to hover above the tray and gets a „nie pasuje” stamp. One axis for
	 * everything: the tray is `--tw` wide = 24 GB, the ghost is q8/24 of that. Stages switch on scroll
	 * thresholds of an auto-played timeline (plays once on entering the viewport, replay button) and
	 * play as short physical animations; reduced motion shows the last stage.
	 */
	import { Autoplay } from '$lib/fx/autoplay.svelte';
	import Replay from '$lib/fx/Replay.svelte';
	import SourceTip from '$lib/fx/SourceTip.svelte';
	import { fmtGB } from '$lib/format';
	import { type Lang } from '$lib/i18n';
	import { copy } from '$lib/site/copy';
	import { HERO_CARD, HERO_MODEL, HERO_RUN, HERO_V, MODELS_SRC, Q8 } from './data';
	import SceneHead from './SceneHead.svelte';
	import ModelMark from '$lib/ModelMark.svelte';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(copy[lang].how.fit);
	// the whole sequence in ~1.3 s, starting at ~20% in view: nobody scrolls past it unplayed
	const tl = new Autoplay(1.3, '0px 0px -20% 0px');
	const p = $derived(tl.p);
	const stage = $derived(p >= 0.72 ? 4 : p >= 0.4 ? 3 : p >= 0.2 ? 2 : p > 0 ? 1 : 0);

	const vram = HERO_CARD.vramGB;
	const file = HERO_RUN.file!;
	const used = HERO_V.a2.vram!;
	const q8 = Q8.sizeGB;
	/** Memory always in decimal GB, one decimal (src/lib/format.ts). */
	const gb = (v: number, unit: string | undefined = undefined) => fmtGB(v, unit, lang).text;
	const ticks = Array.from({ length: Math.floor(vram / 4) + 1 }, (_, i) => i * 4);
</script>

<div class="wrap" use:tl.view style="--file:{file.v / vram}; --used:{used.v / vram}; --q8:{q8 / vram}">
		<div class="layout" data-stage={stage}>
			<div class="top">
				<SceneHead id="scene-fit" k={c.k} step={c.title} head={c.head} body={c.body} />
				<div class="verdicts">
					<div class="verdict yes">
						<span class="vh"><span class="ok" aria-hidden="true">✓</span>{c.fits}</span>
						<span class="vsub">{c.used} {gb(used.v, used.unit)} / {vram}&nbsp;GB</span>
						<SourceTip {lang} src={[file.src, used.src, HERO_RUN.conditionsSrc]} note="{c.usedNote} {HERO_RUN.conditions[lang]}" />
					</div>
					<div class="verdict no">
						<span class="vh"><span class="x" aria-hidden="true">✕</span>{c.nofit}</span>
						<span class="vsub">{c.ghost} · {gb(q8)} &gt; {vram}&nbsp;GB</span>
						<SourceTip {lang} src={MODELS_SRC} note={c.ghostNote} />
					</div>
				</div>
			</div>
			<div class="stage">
				<div class="caprow">
					<p class="cap" aria-hidden="true"><span>{HERO_CARD.name}</span><span>{vram}&nbsp;GB {c.vram}</span></p>
					<Replay {lang} onclick={tl.replay} disabled={tl.playing} />
				</div>
				<div class="fitfield">
					<!-- Q8_0 ghost: the file alone is wider than the card's memory (hatched = does not fit) -->
					<div class="ghost" class:in={stage >= 3} aria-hidden="true">
						<span class="gname"><ModelMark model={HERO_RUN.model} size="0.8em" /> <span class="gm">{HERO_MODEL}</span> <b>Q8_0</b> · {gb(q8)}</span>
						<!-- the part past the card's 24 GB: outlined in danger red -->
						<span class="over" aria-hidden="true"></span>
						<span class="stamp" class:in={stage >= 4}>{c.nofit}</span>
					</div>
					<span class="limit" class:in={stage >= 3} aria-hidden="true"></span>
					<ul class="legend" aria-hidden="true">
						<li class:in={stage >= 2}><i class="sw sw--extra"></i>{c.extra}</li>
						<li class:in={stage >= 2}><i class="sw sw--free"></i>{gb(vram - used.v, used.unit)} {c.free}</li>
					</ul>
					<div class="tray" class:hit={stage >= 3}>
						<div class="block" class:in={stage >= 1}>
							<span class="bname"><ModelMark model={HERO_RUN.model} size="0.7em" /> {HERO_MODEL} <span class="q">{HERO_RUN.quant}</span></span>
							<span class="bsize">{gb(file.v, file.unit)} · {c.file}</span>
						</div>
						<div class="extra" class:in={stage >= 2}></div>
						<div class="free" class:in={stage >= 2}><span>{gb(vram - used.v, used.unit)} {c.free}</span></div>
					</div>
					<div class="scale" aria-hidden="true">
						{#each ticks as t (t)}<span style="--t:{t / vram}">{t}</span>{/each}
					</div>
				</div>
				<p class="sr-only">
					{HERO_CARD.name}: {vram} GB VRAM. {HERO_MODEL} {HERO_RUN.quant}: {c.file} {gb(file.v, file.unit)}, {c.used} {gb(used.v, used.unit)} — {c.fits}.
					{c.ghost}: {gb(q8)} — {c.nofit}.
				</p>
			</div>
		</div>
</div>

<style>
	.wrap {
		position: relative;
		overflow-x: clip;
	}
	/* heading row on top, the tray across the full content width below it; the whole scene fits one
	 * viewport (gaps, the ghost row and the tray scale with the viewport height) */
	.layout {
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
		display: grid;
		gap: clamp(1rem, 3vh, 2rem);
		padding-block: var(--header-clear) clamp(1.25rem, 3vh, 2.5rem);
	}
	.caprow {
		display: flex;
		align-items: center;
		gap: var(--sp-4);
	}
	.top {
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		gap: clamp(2rem, 5vw, 6rem);
		align-items: end;
	}
	/* two lines of body on desktop: the heading row stays short */
	.top :global(.body) {
		max-width: 46ch;
	}
	.stage {
		display: grid;
		align-content: center;
		gap: clamp(0.5rem, 1.5vh, 1rem);
		/* the 24 GB tray: 80% of the width, so the 29 GB ghost (×1.21) still ends inside the page */
		--tw: 80%;
	}
	.cap {
		display: flex;
		justify-content: space-between;
		width: var(--tw);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	/* the drops and the bounce stay inside the chart row: they never pass over the headline.
	 * Columns: the 24 GB tray and its scale, then the legend under the Q8_0 overhang. */
	.fitfield {
		--gh: clamp(3rem, 6.5vh, 4.25rem);
		position: relative;
		display: grid;
		grid-template-columns: var(--tw) minmax(0, 1fr);
		gap: var(--sp-2) 0;
		overflow: clip;
		overflow-clip-margin: 1rem;
		padding-top: calc(var(--gh) + clamp(0.6rem, 1.6vh, 1.1rem));
	}
	.tray {
		position: relative;
		grid-column: 1;
		grid-row: 1;
		height: clamp(5.25rem, 13vh, 8.5rem);
		border: 1.5px solid var(--line-strong);
		border-radius: var(--r-lg);
		background:
			repeating-linear-gradient(90deg, transparent 0 calc(100% / 24 - 1px), rgb(237 234 227 / 0.05) calc(100% / 24 - 1px) calc(100% / 24)),
			var(--bg-1);
		box-shadow: inset 0 14px 40px -14px rgb(0 0 0 / 0.9);
	}
	.tray.hit {
		animation: shake 0.35s var(--ease-out) 0.18s both;
	}
	@keyframes shake {
		20% {
			transform: translate3d(0, 7px, 0);
		}
		45% {
			transform: translate3d(0, -3px, 0);
		}
		70% {
			transform: translate3d(0, 1px, 0);
		}
	}
	/* the card's memory ends here: a wall that rises when the Q8_0 block arrives */
	.limit {
		position: absolute;
		top: 0;
		left: var(--tw);
		height: calc(100% - 1.6rem);
		border-left: 1.5px dashed var(--text-hi);
		transform-origin: 50% 100%;
		transform: scaleY(0);
		transition: transform 0.3s var(--ease-out);
		pointer-events: none;
		z-index: 3;
	}
	.limit.in {
		transform: none;
	}
	.block {
		position: absolute;
		inset: 8px auto 8px 8px;
		width: calc(var(--file) * (100% - 16px));
		border-radius: var(--r-md);
		/* the winner glows hot (the model's teal stays only as its mark), lit from above */
		background:
			linear-gradient(180deg, rgb(255 255 255 / 0.3), transparent 45%, rgb(0 0 0 / 0.12)),
			linear-gradient(90deg, var(--heat-3), var(--heat-4) 60%, var(--heat-5));
		box-shadow:
			0 0 0 1px rgb(255 243 214 / 0.5) inset,
			0 0 40px -6px rgb(255 122 26 / 0.65),
			0 18px 40px -16px rgb(0 0 0 / 0.9);
		display: grid;
		align-content: center;
		gap: 0.3rem;
		padding: 0 1.4rem;
		color: var(--text-inv);
		opacity: 0;
		transform: translate3d(0, -40vh, 0);
		transform-origin: 50% 100%;
		z-index: 2;
	}
	/* gravity: accelerate down, squash on impact, one small bounce, settle */
	.block.in {
		opacity: 1;
		transform: none;
		animation: drop 0.55s both;
	}
	@keyframes drop {
		0% {
			opacity: 1;
			transform: translate3d(0, -40vh, 0);
			animation-timing-function: cubic-bezier(0.55, 0, 1, 0.45);
		}
		48% {
			transform: translate3d(0, 0, 0) scale(1.03, 0.82);
			animation-timing-function: cubic-bezier(0, 0.55, 0.45, 1);
		}
		66% {
			transform: translate3d(0, -2.2rem, 0) scale(0.98, 1.04);
			animation-timing-function: cubic-bezier(0.55, 0, 1, 0.45);
		}
		82% {
			transform: translate3d(0, 0, 0) scale(1.015, 0.95);
		}
		92% {
			transform: translate3d(0, -0.3rem, 0);
		}
		100% {
			opacity: 1;
			transform: none;
		}
	}
	.bname {
		font-weight: 780;
		font-stretch: 110%;
		font-size: clamp(1.1rem, 0.7rem + 1.2vw, 2rem);
		letter-spacing: -0.015em;
		white-space: nowrap;
	}
	.q {
		font-weight: 500;
		opacity: 0.7;
	}
	.bsize {
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		letter-spacing: 0.04em;
		opacity: 0.8;
	}
	/* what the engine needs on top of the file (context, KV cache, buffers): dotted = overhead */
	.extra {
		position: absolute;
		top: 8px;
		bottom: 8px;
		left: calc(8px + var(--file) * (100% - 16px));
		width: calc((var(--used) - var(--file)) * (100% - 16px));
		border-radius: 0 var(--r-md) var(--r-md) 0;
		background: radial-gradient(circle, rgb(237 234 227 / 0.75) 1.2px, transparent 1.6px) 0 0 / 7px 7px, rgb(237 234 227 / 0.08);
		transform-origin: 0 50%;
		transform: scaleX(0);
		transition: transform 0.35s var(--ease-out);
	}
	.extra.in {
		transform: none;
	}
	.free {
		position: absolute;
		top: 8px;
		bottom: 8px;
		right: 8px;
		left: calc(8px + var(--used) * (100% - 16px) + 8px);
		display: grid;
		place-items: center;
		border: 1px dashed var(--line-strong);
		border-radius: var(--r-md);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text);
		text-align: center;
		padding: 0 0.3rem;
		opacity: 0;
		transition: opacity 0.3s 0.15s;
	}
	.free.in {
		opacity: 1;
	}
	.scale {
		position: relative;
		grid-column: 1;
		grid-row: 2;
		height: 1.1rem;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.scale span {
		position: absolute;
		left: calc(var(--t) * 100%);
		transform: translateX(-50%);
	}
	/* Q8_0 ghost: hatched = does not fit */
	.ghost {
		position: absolute;
		top: 0;
		left: 0;
		width: calc(var(--q8) * var(--tw));
		height: var(--gh);
		border: 1.5px dashed rgb(237 234 227 / 0.55);
		border-radius: var(--r-md);
		/* the same model, desaturated and hatched: does not fit */
		background:
			repeating-linear-gradient(-45deg, rgb(125 135 148 / 0.24) 0 6px, transparent 6px 12px),
			color-mix(in srgb, color-mix(in srgb, var(--model-qwen38) 35%, var(--before)) 14%, transparent);
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--sp-4);
		padding: 0 1.4rem;
		color: var(--text-hi);
		opacity: 0;
		transform: translate3d(0, -36vh, 0);
	}
	.ghost.in {
		opacity: 1;
		transform: none;
		animation: fling 0.6s both;
	}
	/* slams down hard, its end hits the 24 GB wall: impact, one short bounce, rest */
	@keyframes fling {
		0% {
			opacity: 1;
			transform: translate3d(0, -36vh, 0);
			animation-timing-function: cubic-bezier(0.7, 0, 1, 0.5);
		}
		42% {
			transform: translate3d(0, 0.9rem, 0) rotate(1.4deg) scaleY(0.9);
			animation-timing-function: cubic-bezier(0, 0.6, 0.4, 1);
		}
		64% {
			transform: translate3d(0, -0.9rem, 0) rotate(-0.6deg);
			animation-timing-function: cubic-bezier(0.6, 0, 1, 0.6);
		}
		84% {
			transform: translate3d(0, 0.15rem, 0);
		}
		100% {
			opacity: 1;
			transform: none;
		}
	}
	.over {
		position: absolute;
		top: -1.5px;
		bottom: -1.5px;
		right: -1.5px;
		width: calc((1 - 1 / var(--q8)) * 100% + 1.5px);
		border: 2px solid var(--danger);
		border-left-style: dashed;
		border-radius: 0 var(--r-md) var(--r-md) 0;
		background: var(--danger-soft);
		pointer-events: none;
	}
	.gname {
		font-weight: 650;
		font-stretch: 108%;
		white-space: nowrap;
		font-size: clamp(0.9rem, 0.7rem + 0.5vw, 1.15rem);
	}
	.gname b {
		font-weight: 800;
	}
	/* the rubber stamp slammed onto the ghost */
	.stamp {
		flex: none;
		padding: 0.25rem 0.7rem;
		border: 2px solid var(--text-hi);
		outline: 1px solid var(--text-hi);
		outline-offset: 2px;
		border-radius: 3px;
		font-family: var(--font-mono);
		font-weight: 700;
		font-size: var(--fs-sm);
		text-transform: uppercase;
		letter-spacing: 0.16em;
		color: var(--text-hi);
		background: var(--bg-0);
		opacity: 0;
		transform: rotate(-8deg) scale(2.2);
	}
	.stamp.in {
		opacity: 1;
		transform: rotate(-6deg);
		transition:
			opacity 0.15s,
			transform 0.35s cubic-bezier(0.2, 1.6, 0.4, 1) 0.05s;
	}
	/* legend beside the tray, under the Q8_0 overhang (under the axis on mobile) */
	.legend {
		grid-column: 2;
		grid-row: 1;
		align-self: center;
		display: grid;
		gap: var(--sp-3);
		margin: 0;
		padding: 0 0 0 clamp(1rem, 2vw, 2rem);
		list-style: none;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		line-height: 1.4;
		color: var(--text);
	}
	.legend li {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		opacity: 0;
		transition: opacity 0.3s 0.1s;
	}
	.legend li.in {
		opacity: 1;
	}
	.sw {
		flex: none;
		width: 0.8rem;
		height: 0.8rem;
		border-radius: 2px;
	}

	.sw--extra {
		background: radial-gradient(circle, rgb(237 234 227 / 0.85) 1px, transparent 1.4px) 0 0 / 4px 4px;
		border: 1px solid var(--line-strong);
	}
	.sw--free {
		border: 1px dashed var(--line-strong);
	}
	.verdicts {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--sp-3);
	}
	/* both verdicts are readable from the first frame; the animation only shows why */
	.verdict {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		align-items: center;
		gap: 0.55rem var(--sp-3);
		padding: clamp(0.8rem, 1.8vh, 1.15rem) clamp(0.9rem, 1.5vw, 1.35rem);
		border: 1px solid var(--line);
		border-radius: var(--r-lg);
		background: var(--bg-1);
	}
	/* the winner carries the block's heat; the reject the over-the-limit red */
	.verdict.yes {
		border-color: rgb(255 122 26 / 0.5);
		background: linear-gradient(135deg, rgb(255 122 26 / 0.12), transparent 60%), var(--bg-1);
		box-shadow: 0 0 34px -16px rgb(255 122 26 / 0.8);
	}
	.verdict.no {
		border-color: color-mix(in srgb, var(--danger) 45%, transparent);
		background: repeating-linear-gradient(-45deg, rgb(125 135 148 / 0.07) 0 6px, transparent 6px 12px), var(--bg-1);
	}
	.vh {
		grid-column: 1 / -1;
		display: flex;
		align-items: center;
		gap: 0.55rem;
		font-family: var(--font-display);
		font-weight: 820;
		font-stretch: 120%;
		font-size: clamp(1.4rem, 0.9rem + 1.5vw, 2.3rem);
		letter-spacing: -0.03em;
		line-height: 1;
		color: var(--text-hi);
		white-space: nowrap;
	}
	.no .vh {
		color: var(--before);
	}
	.ok {
		display: inline-grid;
		place-items: center;
		width: 1.1em;
		height: 1.1em;
		border-radius: 50%;
		background: var(--text-hi);
		color: var(--bg-0);
		font-size: 0.7em;
	}
	.x {
		font-size: 0.7em;
	}
	.vsub {
		grid-column: 1;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.verdict :global(.src-btn) {
		grid-column: 2;
		grid-row: 2;
		align-self: end;
	}
	@media (max-width: 900px) {
		.layout {
			gap: var(--sp-3);
		}
		.caprow {
			width: 100%;
		}
		/* heading, then the full-width tray, then the two verdicts */
		.top {
			display: contents;
		}
		.top :global(.body) {
			max-width: 34ch;
		}
		.verdicts {
			order: 2;
			gap: var(--sp-2);
		}
		.verdict {
			gap: 0.35rem var(--sp-2);
			padding: 0.6rem 0.7rem;
		}
		.verdict :global(.src-btn) {
			padding-inline: 0.4rem;
		}
		.verdict :global(.src-btn span) {
			display: none;
		}
		.vsub {
			font-size: 0.625rem;
			letter-spacing: 0.02em;
			text-transform: none;
		}
		/* the Q8 ghost runs off the right edge (clipped by the sticky frame) */
		.stage {
			/* 80%: the 29 GB ghost (×1,21) still ends inside the screen */
			--tw: 80%;
			gap: var(--sp-2);
			align-content: start;
			order: 1;
		}
		.fitfield {
			--gh: 2.6rem;
			padding-top: 3.2rem;
		}
		/* the 24 GB wall starts at the bars, below the ghost and its stamp, and ends at the axis */
		.limit {
			top: 3rem;
			height: 6.4rem;
		}
		.ghost {
			padding: 0 0.7rem;
		}
		.gname {
			font-size: var(--fs-xs);
		}
		/* the same model as the block below: the ghost says only what differs */
		.gm {
			display: none;
		}
		.stamp {
			font-size: var(--fs-2xs);
			margin-right: 0;
		}
		/* legend under the axis, one line */
		.legend {
			grid-column: 1 / -1;
			grid-row: 3;
			display: flex;
			flex-wrap: wrap;
			gap: 0.3rem var(--sp-4);
			padding: 0;
			font-size: 0.625rem;
		}
		.block {
			gap: 0.15rem;
			padding: 0 0.8rem;
		}
		.bname {
			font-size: 0.95rem;
		}
		.bsize {
			font-size: 0.625rem;
		}
		.bname .q,
		.free span {
			display: none;
		}
		.tray {
			height: 4.75rem;
		}
		.vh {
			font-size: 1.3rem;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.block.in,
		.ghost.in,
		.tray.hit {
			animation: none;
		}
		.extra,
		.free,
		.verdict,
		.limit,
		.legend li,
		.stamp.in {
			transition: none;
		}
	}
</style>
