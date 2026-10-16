<script lang="ts">
	/**
	 * "Where the gain comes from": one bar on the decode scale. The typical app (cold), then what
	 * upstream's best flags add (or take away), then what our engine adds on top. The segments grow
	 * in order when the bar enters the viewport. Multipliers come from the sheet's gain table.
	 */
	import { reveal } from '$lib/fx/actions';
	import SourceTip from '$lib/fx/SourceTip.svelte';
	import { fmtRatio, fmtTps, localizeDecimals } from '$lib/format';
	import Ratio from './Ratio.svelte';
	import type { Gain, Num } from '$lib/data/card-types';

	let {
		gain,
		text,
		before,
		flags,
		ours,
		lang,
		labels
	}: {
		gain: Gain;
		/** The sheet's cells (flags, engine, total) in the page language. */
		text?: [string, string, string];
		before: Num;
		flags: Num;
		ours: Num;
		lang: 'pl' | 'en';
		labels: { before: string; flags: string; engine: string; total: string; none: string };
	} = $props();

	const max = $derived(Math.max(before.v, flags.v, ours.v));
	const p = (v: number) => (v / max) * 100;
	const flagsUp = $derived(flags.v >= before.v);
	/** The sheet's explanation without the multiplier we already print ("×1.62 (MTP)" → "MTP"). */
	const detail = $derived((text ?? []).map((x) => localizeDecimals(x.replaceAll('`', '').replace(/^×[\d.,]+\s*/, '').replace(/^\((.*)\)$/, '$1'), lang)));
	let shown = $state(false);
</script>

<div class="gs" class:shown use:reveal={{ onin: () => (shown = true) }}>
	<div class="bar" role="img" aria-label="{labels.before} {fmtTps(before.v, lang)} t/s; {labels.flags} {fmtRatio(gain.flags!.v, lang)}; {labels.engine} {fmtRatio(gain.engine!.v, lang)}; {labels.total} {fmtRatio(gain.total!.v, lang)}">
		<div class="seg base" style="--w:{p(before.v)}%; --o:0%; --d:0s"></div>
		{#if flagsUp}
			<div class="seg flags" style="--w:{p(flags.v - before.v)}%; --o:{p(before.v)}%; --d:0.5s"></div>
		{:else}
			<div class="seg loss" style="--w:{p(before.v - flags.v)}%; --o:{p(flags.v)}%; --d:0.5s"></div>
		{/if}
		<div class="seg engine" style="--w:{p(ours.v - Math.max(before.v, flags.v))}%; --o:{p(Math.max(before.v, flags.v))}%; --d:1s"></div>
	</div>
	<ol class="legend">
		<li>
			<span class="k base"></span>
			<span class="t">{labels.before}</span>
			<span class="v mono cold-text">{fmtTps(before.v, lang)}{'\u00a0'}t/s</span>
		</li>
		<li>
			<span class="k" class:flags={flagsUp} class:loss={!flagsUp}></span>
			<span class="t">{labels.flags}{#if !flagsUp}{' '}<span class="none">({labels.none})</span>{/if}</span>
			<span class="v"><Ratio value={gain.flags!.v} {lang} /></span>
			{#if detail[0]}<span class="d">{detail[0]}</span>{/if}
		</li>
		<li>
			<span class="k engine"></span>
			<span class="t">{labels.engine}</span>
			<span class="v"><Ratio value={gain.engine!.v} {lang} /></span>
			{#if detail[1]}<span class="d">{detail[1]}</span>{/if}
		</li>
		<li class="total">
			<span class="t">{labels.total}</span>
			<span class="v"><Ratio value={gain.total!.v} {lang} size="lg" /></span>
			<SourceTip {lang} src={[gain.src, before.src, flags.src, ours.src]} />
		</li>
	</ol>
</div>

<style>
	.gs {
		display: grid;
		gap: var(--sp-6);
	}
	.bar {
		position: relative;
		height: 4.5rem;
		border-radius: var(--r-md);
		background: #08080a;
		border: 1px solid var(--line);
		overflow: hidden;
	}
	.seg {
		position: absolute;
		top: 0;
		bottom: 0;
		left: var(--o);
		width: var(--w);
		transform-origin: left center;
	}
	.base {
		background: linear-gradient(180deg, #8b95a2, #5f6874);
	}
	/* upstream's flags are a speed too: solid mid-ramp heat (hatching means "estimate / does not fit") */
	.flags {
		background: linear-gradient(90deg, var(--heat-1), var(--heat-2));
		box-shadow: -2px 0 0 #050506;
	}
	.loss {
		background: radial-gradient(circle, rgb(5 5 6 / 0.9) 1.2px, transparent 1.6px) 0 0 / 6px 6px;
	}
	.engine {
		background: var(--heat-ramp-hot);
		box-shadow:
			-2px 0 0 #050506,
			0 0 30px rgb(255 122 26 / 0.5);
	}
	.legend {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 13rem), 1fr));
		gap: var(--sp-5);
	}
	.legend li {
		display: grid;
		grid-template-columns: auto 1fr;
		align-items: baseline;
		column-gap: var(--sp-2);
		row-gap: 0.25rem;
	}
	.k {
		width: 0.75rem;
		height: 0.75rem;
		border-radius: 2px;
		transform: translateY(0.1rem);
	}
	.k.base {
		background: #8b95a2;
	}
	.k.flags {
		background: linear-gradient(90deg, var(--heat-1), var(--heat-2));
	}
	.k.loss {
		background: radial-gradient(circle, #8b95a2 1px, transparent 1.4px) 0 0 / 4px 4px;
		outline: 1px solid #8b95a2;
	}
	.k.engine {
		background: var(--heat-ramp-hot);
	}
	.t {
		color: var(--text);
		font-size: var(--fs-sm);
	}
	.none {
		color: var(--text-mute);
	}
	.v {
		grid-column: 2;
		font-size: var(--fs-xl);
		font-weight: 600;
		color: var(--text-hi);
		line-height: 1.1;
	}
	.d {
		grid-column: 2;
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.total {
		align-content: start;
	}
	.total .t,
	.total .v {
		grid-column: 1 / -1;
	}
	@media (prefers-reduced-motion: no-preference) {
		.seg {
			transform: scaleX(0);
			transition: transform 0.9s var(--ease-out) var(--d);
		}
		.shown .seg {
			transform: none;
		}
	}
</style>
