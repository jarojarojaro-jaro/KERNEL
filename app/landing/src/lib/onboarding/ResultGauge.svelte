<script lang="ts">
	/**
	 * Result hero: the user's card on a tachometer. The needle starts at the "typical app" speed and
	 * then sweeps to our engine's speed.
	 * - Measured cards (`CARDS`): both numbers come from the registry, with sources and a link to the
	 *   card page. A different-script pair (RX 7900 XTX Qwen) says so.
	 * - Other cards: the needle rests at the middle of our formula's range, and the range itself is the
	 *   readout, labelled as an estimate.
	 */
	import { findCard, MODEL_INFO, variantLabel, variantOf } from '$lib/data/measurements';
	import type { Range } from '$lib/estimator';
	import { fmtRatio } from '$lib/format';
	import { visible } from '$lib/fx/actions';
	import Odometer from '$lib/fx/Odometer.svelte';
	import Tacho from '$lib/fx/Tacho.svelte';
	import { reducedMotion } from '$lib/fx/motion';
	import { cardsHref, num, type Lang } from '$lib/i18n';
	import { ob } from './copy';

	let {
		gpuId,
		gpuName,
		lang,
		estimate
	}: { gpuId: string | null | undefined; gpuName: string; lang: Lang; estimate: { before: Range; best: Range; l1: boolean } | null } = $props();

	const t = $derived(ob[lang].result);

	const measured = $derived.by(() => {
		const card = gpuId ? findCard(gpuId) : null;
		if (!card) return null;
		const run = card.runs.find((r) => r.model === card.pick.model) ?? card.runs[0];
		const before = variantOf(run, run.before)?.decode;
		const ours = variantOf(run, run.ours)?.decode;
		return before && ours ? { card, run, before, ours } : null;
	});

	const target = $derived(measured ? measured.ours.v : estimate ? (estimate.best.lo + estimate.best.hi) / 2 : 0);
	const start = $derived(measured ? measured.before.v : estimate ? (estimate.before.lo + estimate.before.hi) / 2 : 0);
	const step = $derived(target > 300 ? 50 : target > 120 ? 20 : 10);
	const max = $derived(Math.max(step * 4, Math.ceil((target * 1.25) / step) * step));
	const redline = $derived(Math.round((max * 0.7) / step) * step);

	// 0 → typical app → our engine, once the gauge is on screen.
	let phase = $state<0 | 1 | 2>(0);
	let started = false;
	function go(on: boolean) {
		if (!on || started) return;
		started = true;
		if (reducedMotion()) {
			phase = 2;
			return;
		}
		phase = 1;
		setTimeout(() => (phase = 2), 1300);
	}
	const needle = $derived(phase === 0 ? 0 : phase === 1 ? start : target);
	const fmtR = (r: Range) => (Math.abs(r.hi - r.lo) < 0.5 ? num(r.lo, lang, 0) : `${num(r.lo, lang, 0)}–${num(r.hi, lang, 0)}`);
	const dec = (v: number) => (Number.isInteger(v) ? 1 : Math.min(2, String(v).split('.')[1].length));
</script>

{#if measured || estimate}
	<section class="gauge heat-card" aria-labelledby="gauge-title" use:visible={go}>
		<div class="dial">
			<Tacho value={needle} {max} {redline} {step} label={measured ? `${variantLabel(measured.run, measured.run.ours)[lang]}: ${num(measured.ours.v, lang, dec(measured.ours.v))} t/s` : `${t.estimate}: ${fmtR(estimate!.best)} t/s`} slam={!!measured}>
				<div class="read">
					{#if measured}
						<Odometer value={phase === 2 ? measured.ours.v : phase === 1 ? measured.before.v : 0} decimals={dec(measured.ours.v)} {lang} duration={1100} />
					{:else}
						<span class="mono rng">{fmtR(estimate!.best)}</span>
					{/if}
					<span class="u mono">t/s</span>
				</div>
			</Tacho>
		</div>

		<div class="text">
			<p class="overline overline--accent">{measured ? t.gaugeMeasured(measured.card.name) : t.gaugeEstimate}</p>
			<h2 id="gauge-title" class="gpu">{gpuName}</h2>
			{#if measured}
				{@const ratio = measured.ours.v / measured.before.v}
				<p class="big">
					<span class="speedup {ratio > 1 ? '' : 'speedup--down'}">{fmtRatio(ratio, lang)}</span>
					{#if measured.run.sameHarness}<span class="faster">{t.faster}</span>{:else}<span class="badge badge--estimate">{t.indicative}</span>{/if}
				</p>
				<p class="pair mono">
					<span class="cold">{num(measured.before.v, lang, dec(measured.before.v))}</span>
					<span class="arrow" aria-hidden="true">→</span><span class="sr-only">→</span>
					<span class="hot">{num(measured.ours.v, lang, dec(measured.ours.v))}</span>
					<span class="u">t/s</span>
				</p>
				<p class="legend">
					<span><i class="sw cold-sw"></i>{variantLabel(measured.run, measured.run.before)[lang]}</span>
					<span><i class="sw hot-sw"></i>{variantLabel(measured.run, measured.run.ours)[lang]}</span>
					<span class="badge badge--measured">{t.measured}</span>
				</p>
				<p class="fine">{t.gaugeModel}: <strong>{MODEL_INFO[measured.run.model].name} {measured.run.quant}</strong>. {measured.run.metric[lang]}{measured.run.sameHarness ? '' : ` ${t.harnessWarn}`}</p>
				<p class="source">{measured.before.src} · {measured.ours.src}</p>
				<a class="btn btn--primary" href={cardsHref(lang, `${measured.card.id}/`)}>{t.gaugeCard} <span class="arrow" aria-hidden="true">→</span></a>
			{:else if estimate}
				<p class="big"><span class="heat-num rng-big mono">{fmtR(estimate.best)}</span> <span class="faster">t/s · {t.gaugeRange}</span></p>
				<p class="legend">
					<span class="badge badge--estimate">{t.estimate}</span>
					<span class="fine">{estimate.l1 ? t.l1 : t.before}</span>
				</p>
				{#if estimate.l1}<p class="fine">{t.before}: {fmtR(estimate.before)} t/s</p>{/if}
				<p class="fine">{t.nextLead}</p>
			{/if}
		</div>
	</section>
{/if}

<style>
	.gauge {
		display: grid;
		grid-template-columns: minmax(14rem, 22rem) minmax(0, 1fr);
		align-items: center;
		gap: clamp(1.5rem, 1rem + 3vw, 4rem);
		padding: clamp(1.5rem, 1rem + 2.5vw, 3rem);
		border-radius: var(--r-xl);
		margin-bottom: var(--sp-8);
		overflow: hidden;
	}
	.dial {
		position: relative;
	}
	.dial::before {
		content: '';
		position: absolute;
		inset: -12%;
		background: radial-gradient(closest-side, color-mix(in srgb, var(--heat-3) 22%, transparent), transparent);
		pointer-events: none;
	}
	.read {
		display: grid;
		justify-items: center;
		gap: 0.1rem;
		font-family: var(--font-mono);
		font-size: clamp(1.6rem, 1.2rem + 1.4vw, 2.4rem);
		font-weight: 400;
		font-stretch: 87.5%;
		letter-spacing: -0.04em;
		color: var(--text-hi);
	}
	.rng {
		font-size: 0.8em;
	}
	.u {
		font-size: var(--fs-xs);
		letter-spacing: 0.08em;
		color: var(--text-mute);
	}
	.text {
		display: grid;
		gap: var(--sp-3);
		justify-items: start;
	}
	.gpu {
		font-size: clamp(1.75rem, 1.2rem + 2vw, 3rem);
		font-weight: 760;
		font-stretch: 110%;
		letter-spacing: -0.035em;
		line-height: 1;
	}
	.big {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: var(--sp-2) var(--sp-4);
		margin-top: var(--sp-2);
	}
	.big .speedup {
		font-size: clamp(3.5rem, 2rem + 5vw, 6.5rem);
	}
	:global(:root[data-theme='light']) .big .speedup:not(.speedup--down) {
		background: linear-gradient(90deg, var(--heat-2), var(--heat-3) 60%, #c24f0c);
		-webkit-background-clip: text;
		background-clip: text;
	}
	.rng-big {
		font-size: clamp(2.5rem, 1.6rem + 3vw, 4.5rem);
		font-weight: 300;
		font-stretch: 87.5%;
		letter-spacing: -0.05em;
		line-height: 1;
	}
	.faster {
		font-size: var(--fs-md);
		color: var(--text);
	}
	.pair {
		display: flex;
		align-items: baseline;
		gap: var(--sp-3);
		font-size: var(--fs-xl);
		font-stretch: 87.5%;
		letter-spacing: -0.03em;
	}
	.pair .cold {
		color: var(--before);
	}
	.pair .hot {
		color: var(--accent-ink);
		font-weight: 600;
	}
	.pair .arrow {
		color: var(--text-mute);
	}
	.legend {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-2) var(--sp-4);
		font-size: var(--fs-xs);
		color: var(--text);
	}
	.legend > span {
		display: inline-flex;
		align-items: center;
		gap: 0.45rem;
	}
	.sw {
		width: 1.2rem;
		height: 3px;
		border-radius: var(--r-pill);
	}
	.cold-sw {
		background: var(--before);
	}
	.hot-sw {
		background: var(--heat-ramp-hot);
	}
	.text .fine strong {
		color: var(--text-hi);
		font-weight: 600;
	}
	.text .btn {
		margin-top: var(--sp-2);
	}
	@media (max-width: 760px) {
		.gauge {
			grid-template-columns: 1fr;
			justify-items: center;
		}
		.dial {
			width: min(100%, 18rem);
		}
		.text {
			justify-items: center;
			text-align: center;
		}
		.legend,
		.big,
		.pair {
			justify-content: center;
		}
	}
</style>
