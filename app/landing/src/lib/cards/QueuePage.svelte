<script lang="ts">
	import SourceTip from '$lib/fx/SourceTip.svelte';
	import type { Gpu } from '$lib/estimator';
	import { cardsHref, currentLang, href, num } from '$lib/i18n';
	import CardHead from './CardHead.svelte';
	import EstTag from './EstTag.svelte';
	import { cardsCopy } from './copy';
	import { EST_SRC, GPU_SRC, MEASURED, queueEstimate, splitName } from './explorer';
	import { Play } from './play.svelte';

	let { gpu }: { gpu: Gpu } = $props();

	const lang = $derived(currentLang());
	const t = $derived(cardsCopy[lang].card);
	const est = $derived(queueEstimate(gpu));
	const { prefix, short } = $derived(splitName(gpu.name, gpu.vendor));
	/** The estimate bars fill when the list enters the view; at rest (and on SSR) they are full. */
	const fill = new Play(() => est.length * 220 + 1300);
	/** Estimated memory as a share of the card's memory (the estimator counts both in GiB). */
	const share = (v: number) => `${Math.round((v / gpu.vram!) * 100)}`;
</script>

<CardHead id={gpu.id} {prefix} {short} vendor={gpu.vendor} vram={gpu.vram ?? null} heat={0} queued spec="{gpu.vram ? `${gpu.vram} GB · ` : ''}{gpu.arch}">
	<div class="q">
		<p class="qt hx-h">{t.queueTitle}</p>
		<p class="lede">{t.queueLede}</p>
	</div>
	{#if est[0]}
		{@const e = est[0]}
		{@const scale = Math.ceil((e.decode.hi * 1.6) / 10) * 10}
		<div class="hero-est">
			<EstTag text={t.estimateTitle} />
			<p class="he-n fig"><span class="ap">≈</span>{num(e.decode.lo, lang, 0)}–{num(e.decode.hi, lang, 0)}<span class="u">t/s</span></p>
			<p class="he-l">{t.estimateBefore} · {e.model.name} {e.model.quant} · {t.estimateAfter}: {cardsCopy[lang].gallery.soon}</p>
			<div class="range" role="img" aria-label="{t.estimateBefore}: {num(e.decode.lo, lang, 0)}–{num(e.decode.hi, lang, 0)} t/s">
				<div class="rg" style="left:{(e.decode.lo / scale) * 100}%; width:{((e.decode.hi - e.decode.lo) / scale) * 100}%"></div>
				<span class="r0 mono">0</span>
				<span class="r1 mono">{scale} t/s</span>
			</div>
			<SourceTip {lang} src={[EST_SRC, GPU_SRC, 'app/landing/src/lib/data/models.json']} note={t.estimateLede} />
		</div>
	{/if}
</CardHead>

<section class="wrap fp" aria-label={t.fingerprint}>
	<dl class="strip hx-surface">
		<div><dt>{t.hw.vram}</dt>{#if gpu.vram}<dd class="fig">{gpu.vram}<span>GB</span></dd>{:else}<dd class="txt">{gpu.unified ? t.hw.unified : '—'}</dd>{/if}</div>
		<div>
			<dt>{t.hw.bw}</dt>
			<dd class="fig">{num(gpu.bw, lang, 0)}<span>GB/s</span></dd>
			{#if gpu.bwSource === 'spec'}<dd class="tag mono">{t.vendorSpec}</dd>{/if}
		</div>
		<div><dt>{t.hw.arch}</dt><dd class="txt">{gpu.arch}</dd></div>
	</dl>
	<SourceTip {lang} src={GPU_SRC} note={gpu.bwSource === 'spec' ? t.vendorSpec : ''} />
</section>

<section class="wrap est" aria-labelledby="est-title" use:fill.view>
	<div class="est-head">
		{#if est.length}<EstTag text={t.estimateTitle} />{/if}
		<h2 id="est-title" class="giga hx-grad">{t.fitTitle}</h2>
		{#if est.length}<p class="lede">{t.estimateLede}</p>
			<SourceTip {lang} src={[EST_SRC, GPU_SRC, 'app/landing/src/lib/data/models.json']} note={t.estimateLede} />{/if}
	</div>
	{#if est.length}
		<ul class="rows" class:play={fill.on} role="list">
			{#each est as e, i (e.model.id)}
				<li class="row" style="--d:{i * 220}ms">
					<div class="name">
						<span class="m">{e.model.name}</span>
						<span class="mono qn">{e.model.quant}</span>
					</div>
					<div class="track" style="--cells:{gpu.vram}" role="img" aria-label="{e.model.name}: {t.estimateNeed} ≈ {t.fitShare(share(e.need.lo), share(e.need.hi))}">
						<div class="need" style="width:calc({((e.need.hi / gpu.vram!) * 100).toFixed(2)}% - 6px); --lo:{((e.need.lo / e.need.hi) * 100).toFixed(2)}%"></div>
						<span class="cap mono">{gpu.vram} GB</span>
					</div>
					<div class="nums">
						<p class="mono"><span class="k">{t.estimateNeed}</span> <b>≈ {t.fitShare(share(e.need.lo), share(e.need.hi))}</b></p>
						<p class="mono"><span class="k">{t.estimateBefore}</span> <b>≈ {num(e.decode.lo, lang, 0)}–{num(e.decode.hi, lang, 0)} t/s</b></p>
						<p class="mono"><span class="k">{t.estimateAfter}</span> <b>{cardsCopy[lang].gallery.soon}</b></p>
					</div>
				</li>
			{/each}
		</ul>
	{:else}
		<p class="soon">{gpu.unified ? t.soonNoVram : t.soonNoFit}</p>
	{/if}
</section>

<section class="wrap next" aria-labelledby="next-title">
	<div class="next-in panel hx-surface hx-ring">
		<h2 id="next-title" class="giga hx-grad">{t.next}</h2>
		<div class="ctas">
			<a class="cta cta--bone" href={href(lang, '/start')}>{t.start} <span class="arrow" aria-hidden="true">→</span></a>
			<a class="cta cta--line" href={cardsHref(lang)}>{t.back}</a>
		</div>
	</div>
	<h3 class="others-h eyebrow">{t.measuredOthers}</h3>
	<ul class="others" role="list">
		{#each MEASURED as e (e.id)}
			<li><a href={cardsHref(lang, `${e.id}/`)}>{e.card.name} <span class="mono">{e.card.vramGB} GB</span></a></li>
		{/each}
	</ul>
</section>

<style>
	.wrap {
		width: min(100% - 2 * var(--gutter), 88rem);
		margin-inline: auto;
	}
	.q {
		display: grid;
		gap: var(--sp-3);
		margin-top: var(--sp-5);
		padding-top: var(--sp-5);
		border-top: 1px solid transparent;
		border-image: var(--hx-line) 1;
	}
	.qt {
		margin: 0;
		font-size: var(--fs-xl);
		font-weight: 750;
		font-stretch: 108%;
		color: var(--text-hi);
	}
	.q .lede {
		margin: 0;
	}
	.hero-est {
		display: grid;
		gap: var(--sp-3);
		justify-items: start;
		width: 100%;
		margin-top: var(--sp-4);
		padding: var(--sp-5);
		border: 1px dashed rgb(255 122 26 / 0.5);
		border-radius: var(--r-lg);
		background:
			radial-gradient(80% 70% at 0% 0%, rgb(255 122 26 / 0.1), transparent 65%),
			repeating-linear-gradient(135deg, rgb(255 122 26 / 0.025) 0 6px, transparent 6px 12px),
			rgb(10 9 9 / 0.9);
	}
	.he-n {
		margin: 0;
		font-size: clamp(2.4rem, 1.4rem + 2.6vw, 3.75rem);
		font-weight: 600;
		line-height: 1;
		color: var(--text-hi);
	}
	.he-n .ap {
		margin-right: 0.15em;
		color: var(--hx-ink);
	}
	.he-n .u {
		margin-left: 0.4rem;
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.he-l {
		margin: 0;
		font-size: var(--fs-sm);
		color: var(--text);
	}
	/* the estimate as a range: warm, but hatched and dashed (an estimate, never a solid measured fill) */
	.range {
		position: relative;
		width: 100%;
		height: 0.9rem;
		margin-bottom: 1.1rem;
		border-radius: var(--r-pill);
		background: var(--bg-2);
		box-shadow: inset 0 0 0 1px var(--line);
	}
	.rg {
		position: absolute;
		top: -3px;
		bottom: -3px;
		border: 1px dashed var(--heat-4);
		border-radius: var(--r-sm);
		background: repeating-linear-gradient(135deg, rgb(255 160 80 / 0.55) 0 4px, transparent 4px 8px);
		box-shadow: 0 0 16px -4px rgb(255 122 26 / 0.55);
	}
	.r0,
	.r1 {
		position: absolute;
		top: calc(100% + 0.3rem);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.r0 {
		left: 0;
	}
	.r1 {
		right: 0;
	}
	.fp {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-3);
	}
	.strip {
		flex: 1 1 100%;
		margin: 0;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 10rem), 1fr));
		border: 1px solid rgb(255 122 26 / 0.22);
		border-radius: var(--r-lg);
		overflow: hidden;
	}
	.strip div {
		padding: var(--sp-4);
		border-right: 1px solid rgb(255 122 26 / 0.14);
	}
	.strip div:last-child {
		border-right: 0;
	}
	.strip dt {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.12em;
		color: var(--text-mute);
	}
	.strip dd {
		margin: var(--sp-2) 0 0;
		font-family: var(--font-mono);
		font-size: var(--fs-2xl);
		font-weight: 600;
		color: var(--text-hi);
	}
	.strip dd span {
		margin-left: 0.3rem;
		font-size: var(--fs-2xs);
		color: var(--hx-ink);
	}
	.strip dd.txt {
		font-size: var(--fs-md);
		padding-top: 0.6rem;
	}
	.strip dd.tag {
		font-size: var(--fs-2xs);
		color: var(--text-mute);
		font-weight: 400;
	}

	.est {
		padding: var(--section-y) 0 0;
		display: grid;
		gap: var(--sp-10);
	}
	.est-head {
		display: grid;
		gap: var(--sp-4);
		justify-items: start;
	}
	.est-head .giga,
	.est-head .lede {
		margin: 0;
	}
	.rows {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: var(--sp-6);
	}
	/* heat-line dividers between estimate rows */
	.row + .row {
		padding-top: var(--sp-6);
		border-top: 1px solid transparent;
		border-image: var(--hx-line-c) 1;
	}
	.row {
		display: grid;
		grid-template-columns: minmax(9rem, 13rem) minmax(0, 1fr) minmax(14rem, 20rem);
		align-items: center;
		gap: var(--sp-4) var(--sp-6);
	}
	.name {
		display: grid;
		gap: 0.15rem;
	}
	.m {
		font-weight: 700;
		color: var(--text-hi);
	}
	.qn {
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.track {
		position: relative;
		height: 3.25rem;
		border: 1px dashed rgb(255 122 26 / 0.45);
		border-radius: var(--r-md);
		background:
			repeating-linear-gradient(90deg, transparent 0 calc(100% / var(--cells) - 1px), rgb(255 122 26 / 0.07) calc(100% / var(--cells) - 1px) calc(100% / var(--cells))),
			linear-gradient(90deg, rgb(255 122 26 / 0.05), transparent),
			#09080a;
	}
	.need {
		position: absolute;
		top: 3px;
		bottom: 3px;
		left: 3px;
		border-radius: calc(var(--r-md) - 3px);
		/* solid up to the low end of the range, hatched across the uncertainty */
		/* estimate: warm, but hatched and dashed (never a solid measured fill) */
		background:
			linear-gradient(90deg, rgb(255 140 60 / 0.38) var(--lo), transparent var(--lo)),
			repeating-linear-gradient(135deg, rgb(255 140 60 / 0.38) 0 5px, transparent 5px 10px);
		border: 1px dashed rgb(255 160 80 / 0.7);
		transform-origin: left center;
	}
	.cap {
		position: absolute;
		right: 0;
		bottom: calc(100% + 0.35rem);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.nums {
		display: grid;
		gap: 0.25rem;
		justify-items: start;
	}
	.nums p {
		margin: 0;
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.nums b {
		color: var(--text-hi);
		font-weight: 600;
	}
	.soon {
		margin: 0;
		font-size: var(--fs-xl);
		color: var(--text);
		max-width: 40ch;
	}
	@media (prefers-reduced-motion: no-preference) {
		.play .need {
			animation: need-grow 1.1s var(--ease-out) var(--d) both;
		}
	}
	@keyframes need-grow {
		from {
			transform: scaleX(0);
		}
	}

	.next {
		padding: var(--section-y) 0;
		display: grid;
		gap: var(--sp-6);
	}
	.next-in {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: var(--sp-6);
		padding: clamp(1.5rem, 4vw, 3rem);
	}
	.next-in .giga {
		margin: 0;
	}
	.ctas {
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-3);
	}
	.others-h {
		margin: var(--sp-4) 0 0;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		font-weight: 500;
		text-transform: uppercase;
		letter-spacing: 0.12em;
		color: var(--text-mute);
	}
	.others {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-3);
	}
	.others a {
		display: inline-flex;
		gap: 0.6rem;
		align-items: center;
		min-height: 2.75rem;
		padding: 0 1rem;
		border: 1px solid var(--line-strong);
		border-radius: var(--r-pill);
		color: var(--text-hi);
		text-decoration: none;
		font-weight: 600;
	}
	.others a {
		transition:
			border-color var(--dur-2),
			box-shadow var(--dur-2),
			color var(--dur-2);
	}
	.others a:hover {
		border-color: var(--heat-3);
		color: var(--hx-ink);
		box-shadow: 0 10px 28px -12px rgb(255 122 26 / 0.65);
	}
	.others .mono {
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	@media (max-width: 60rem) {
		.row {
			grid-template-columns: 1fr;
		}
	}
</style>
