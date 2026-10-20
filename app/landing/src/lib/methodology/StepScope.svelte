<script lang="ts">
	import { num, type Lang } from '$lib/i18n';
	import { COPY } from './copy';
	import { STEP, W16 } from './facts';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(COPY[lang]);
	const f = (v: number, d = 2) => num(v, lang, d);

	let mode = $state(0);
	/** Common scale for all three modes, so switching shows the step grow and shrink. */
	const MAX = W16.off.wall;

	type Seg = { kind: 'busy' | 'gap' | 'idle'; ms: number; label?: string };
	/** MTP: the real sequence of one traced step (bursts and host gaps, wall 30.22 ms). */
	const mtpSegs: Seg[] = STEP.bursts.flatMap((b, i) => [
		{ kind: 'busy' as const, ms: b.span },
		{ kind: 'gap' as const, ms: STEP.gaps[i] }
	]);
	/** W16: GPU busy time, the three large gaps, the rest of the idle time (schematic order). */
	const w16Segs = (m: { busy: number; idle: number; gaps: readonly number[] }): Seg[] => [
		{ kind: 'busy', ms: m.busy },
		...m.gaps.map((g) => ({ kind: 'gap' as const, ms: g })),
		{ kind: 'idle', ms: m.idle - m.gaps.reduce((s, g) => s + g, 0) }
	];
	const modes = [
		{ wall: STEP.wall, busy: STEP.busy, idle: STEP.idle, gaps: STEP.gaps, segs: mtpSegs, scale: STEP.wall / STEP.sampleWall },
		{ ...W16.off, segs: w16Segs(W16.off), scale: 1 },
		{ ...W16.on, segs: w16Segs(W16.on), scale: 1 }
	];
	const m = $derived(modes[mode]);
	/** Segment offsets in % of MAX, with the MTP sample step stretched to the 96-step mean wall. */
	const laid = $derived.by(() => {
		let x = 0;
		return m.segs.map((s) => {
			const w = ((s.ms * m.scale) / MAX) * 100;
			const seg = { ...s, x, w };
			x += w;
			return seg;
		});
	});
	const bigGaps = $derived(m.gaps.filter((g) => g >= 0.1));

	/* busy time split by kernel class (MTP step only) */
	const known = STEP.ops.reduce((s, o) => s + o.ms, 0);
	const ops = [...STEP.ops, { id: 'other', label: '', ms: STEP.busy - known }];
	let sel = $state('mmvq5');
	const opsLaid = (() => {
		let x = 0;
		return ops.map((o) => {
			const w = (o.ms / STEP.busy) * 100;
			const r = { ...o, x, w };
			x += w;
			return r;
		});
	})();
	const cur = $derived(ops.find((o) => o.id === sel)!);
	const desc = $derived(sel === 'mmvq5' ? c.s.mmvq5 : sel === 'mmvq1' ? c.s.mmvq1 : '');
</script>

<div class="scope">
	<div class="seg" role="group" aria-label={c.s.timeline}>
		{#each c.s.modes as label, i (label)}
			<button type="button" aria-pressed={mode === i} onclick={() => (mode = i)}>{label}</button>
		{/each}
	</div>

	<div class="panel tl-panel">
		<dl class="kpis">
			<div><dt>{c.s.wall}</dt><dd class="mono"><b>{f(m.wall)}</b> {c.s.ms}</dd></div>
			<div><dt>{c.s.busy}</dt><dd class="mono"><b>{f(m.busy)}</b> {c.s.ms}</dd></div>
			<div class="warnk"><dt>{c.s.idle}</dt><dd class="mono"><b>{f(m.idle)}</b> {c.s.ms}</dd></div>
			<div class="warnk"><dt>{c.s.gaps}</dt><dd class="mono gapsv"><b>{bigGaps.map((g) => f(g)).join(' + ')}</b> {c.s.ms}</dd></div>
		</dl>

		<p class="panel-h">{c.s.timeline}</p>
		<div class="tl" role="img" aria-label="{c.s.wall} {f(m.wall)} {c.s.ms}; {c.s.busy} {f(m.busy)}; {c.s.idle} {f(m.idle)}">
			{#each laid as s, i (i)}
				<span class="s {s.kind}" style="transform:translateX({s.x}%) scaleX({s.w / 100})"></span>
			{/each}
			<span class="end" style="transform:translateX({(m.wall / MAX) * 100}%)"></span>
		</div>
		<div class="axis mono" aria-hidden="true">
			{#each [0, 10, 20, 30] as t (t)}<span style="left:{(t / MAX) * 100}%">{t} ms</span>{/each}
		</div>
		<ul class="legend">
			{#if mode === 0}
				{#each STEP.bursts as b, i (i)}<li><i class="busy"></i>{c.s.burst(b.n)} · {f(b.span)} {c.s.ms}</li>{/each}
			{:else}
				<li><i class="busy"></i>{c.s.busy}</li>
			{/if}
			<li><i class="gap"></i>{c.s.gap}</li>
			{#if mode > 0}<li><i class="idle"></i>{c.s.idle} ({c.s.other})</li>{/if}
		</ul>
		{#if mode > 0}
			<p class="small w16">{c.s.w16Lead} <strong>{c.s.w16Gain}</strong></p>
		{/if}
	</div>

	<div class="panel ops-panel">
		<p class="panel-h">{c.s.ops} <span class="mute">· {c.s.modes[0]}</span></p>
		<div class="stack" aria-hidden="true">
			{#each opsLaid as o (o.id)}
				<span class="o {o.id}" class:on={sel === o.id} style="left:{o.x}%;width:{o.w}%"></span>
			{/each}
		</div>
		<div class="ops-body">
			<ul class="ops" aria-label={c.s.pick}>
				{#each ops as o (o.id)}
					<li>
						<button type="button" class:on={sel === o.id} aria-pressed={sel === o.id} onclick={() => (sel = o.id)}>
							<span class="sw {o.id}" aria-hidden="true"></span>
							<span class="mono nm">{o.label || c.s.other}</span>
							<span class="mono ms">{f(o.ms)} {c.s.ms}</span>
						</button>
					</li>
				{/each}
			</ul>
			<div class="detail" aria-live="polite">
				<p class="mono big">{f(cur.ms)} <span>{c.s.ms}</span></p>
				<p class="share">{c.s.share(`${num((cur.ms / STEP.busy) * 100, lang, 1)}%`)}</p>
				{#if desc}<p class="small">{desc}</p>{/if}
			</div>
		</div>
		<p class="take">{c.s.takeaway}</p>
	</div>
</div>

<style>
	.scope {
		display: grid;
		gap: var(--sp-5);
	}
	.tl-panel,
	.ops-panel {
		display: grid;
		gap: var(--sp-4);
	}
	.kpis {
		margin: 0;
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: var(--sp-4);
	}
	.kpis > div {
		display: grid;
		gap: 0.2rem;
	}
	.kpis dt {
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.kpis dd {
		margin: 0;
		color: var(--text-mute);
		font-size: var(--fs-sm);
	}
	.kpis b {
		font-size: clamp(1.4rem, 1rem + 1.4vw, 2.2rem);
		font-weight: 600;
		color: var(--text-hi);
		letter-spacing: -0.03em;
	}
	.gapsv b {
		font-size: clamp(1rem, 0.8rem + 0.7vw, 1.35rem);
	}
	.warnk b {
		color: var(--warn-ink);
	}
	.tl {
		position: relative;
		height: 3.25rem;
		border-radius: var(--r-sm);
		background:
			repeating-linear-gradient(90deg, transparent 0 calc(100% / 37.38 * 5 - 1px), var(--grid) 0 calc(100% / 37.38 * 5)),
			var(--bg-2);
		overflow: hidden;
	}
	/* segments: positioned and sized with transforms only */
	.s {
		position: absolute;
		inset: 0 auto 0 0;
		width: 100%;
		transform-origin: left;
		transition: transform 0.7s var(--ease-spring);
	}
	.s.busy {
		background: linear-gradient(180deg, var(--heat-3), var(--heat-2));
		box-shadow: inset -1px 0 0 rgb(0 0 0 / 0.5);
	}
	.s.gap {
		background: repeating-linear-gradient(135deg, var(--warn) 0 3px, transparent 3px 6px);
		opacity: 0.95;
	}
	.s.idle {
		background: repeating-linear-gradient(135deg, color-mix(in srgb, var(--warn) 45%, transparent) 0 2px, transparent 2px 7px);
	}
	.end {
		position: absolute;
		top: -0.25rem;
		bottom: -0.25rem;
		left: 0;
		width: 100%;
		border-left: 2px solid var(--text-hi);
		transition: transform 0.7s var(--ease-spring);
		pointer-events: none;
	}
	.axis {
		position: relative;
		height: 1.1rem;
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.axis span {
		position: absolute;
		top: 0;
		transform: translateX(-50%);
	}
	.axis span:first-child {
		transform: none;
	}
	.legend {
		margin: 0;
		padding: 0;
		list-style: none;
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-2) var(--sp-5);
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.legend li {
		display: inline-flex;
		align-items: center;
		gap: var(--sp-2);
	}
	.legend i {
		width: 0.9rem;
		height: 0.9rem;
		border-radius: 3px;
	}
	.legend i.busy {
		background: var(--heat-3);
	}
	.legend i.gap {
		background: repeating-linear-gradient(135deg, var(--warn) 0 3px, transparent 3px 6px);
	}
	.legend i.idle {
		background: repeating-linear-gradient(135deg, color-mix(in srgb, var(--warn) 45%, transparent) 0 2px, transparent 2px 7px);
		border: 1px solid var(--line);
	}
	.w16 {
		max-width: 75ch;
	}
	.w16 strong {
		color: var(--ok-ink);
		font-weight: 560;
	}
	.mute {
		color: var(--text-mute);
	}
	.stack {
		position: relative;
		height: 2.5rem;
		border-radius: var(--r-sm);
		overflow: hidden;
		background: var(--bg-2);
	}
	.o {
		position: absolute;
		top: 0;
		bottom: 0;
		padding: 0;
		border: 0;
		border-right: 1px solid var(--bg-1);
		cursor: pointer;
		opacity: 0.55;
		transition: opacity var(--dur-2);
	}
	.o.on {
		opacity: 1;
	}
	/* kernel classes: heat for the weight reads, steel shades for the rest */
	.mmvq5 {
		background: linear-gradient(90deg, var(--heat-2), var(--heat-3) 60%, var(--heat-4));
	}
	.mmvq1 {
		background: var(--heat-1);
	}
	.rms,
	.gdn,
	.fa,
	.conv,
	.glu,
	.quant,
	.other {
		background: color-mix(in srgb, var(--before) calc(40% + var(--k, 0) * 10%), var(--bg-3));
	}
	.gdn {
		--k: 1;
	}
	.fa {
		--k: 2;
	}
	.conv {
		--k: 3;
	}
	.glu {
		--k: 4;
	}
	.quant {
		--k: 5;
	}
	.ops-body {
		display: grid;
		grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr);
		gap: var(--sp-6);
		align-items: start;
	}
	.ops {
		margin: 0;
		padding: 0;
		list-style: none;
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: var(--sp-1) var(--sp-3);
	}
	.ops button {
		width: 100%;
		display: grid;
		grid-template-columns: auto minmax(0, 1fr) auto;
		gap: var(--sp-2);
		align-items: center;
		min-height: 2.5rem;
		padding: 0 var(--sp-3);
		border: 1px solid transparent;
		border-radius: var(--r-sm);
		background: none;
		color: var(--text);
		font-size: var(--fs-xs);
		cursor: pointer;
		text-align: left;
		transition:
			background-color var(--dur-2),
			border-color var(--dur-2);
	}
	.ops button:hover {
		background: var(--bg-2);
	}
	.ops button.on {
		border-color: color-mix(in srgb, var(--heat-3) 50%, var(--line));
		background: var(--accent-soft);
		color: var(--text-hi);
	}
	.ops button:focus-visible {
		outline: 2px solid var(--focus);
		outline-offset: 2px;
	}
	.sw {
		width: 0.75rem;
		height: 0.75rem;
		border-radius: 3px;
	}
	.nm {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.ms {
		color: var(--text-mute);
	}
	.detail {
		display: grid;
		gap: var(--sp-2);
		padding: var(--sp-4);
		border-left: 2px solid var(--heat-3);
		background: linear-gradient(90deg, var(--accent-soft), transparent);
		border-radius: 0 var(--r-md) var(--r-md) 0;
	}
	.detail p {
		margin: 0;
	}
	.big {
		font-size: clamp(2rem, 1.4rem + 2vw, 3rem);
		font-weight: 600;
		letter-spacing: -0.04em;
		line-height: 1;
		color: var(--accent-ink);
	}
	.big span {
		font-size: var(--fs-sm);
		color: var(--text-mute);
	}
	.share {
		color: var(--text-hi);
		font-weight: 560;
	}
	.take {
		margin: 0;
		padding-top: var(--sp-3);
		border-top: 1px solid var(--line);
		color: var(--text-hi);
		max-width: 80ch;
	}
	@media (max-width: 860px) {
		.kpis {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
		.ops-body {
			grid-template-columns: minmax(0, 1fr);
		}
	}
	@media (max-width: 480px) {
		.ops {
			grid-template-columns: minmax(0, 1fr);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.s,
		.end {
			transition: none;
		}
	}
</style>
