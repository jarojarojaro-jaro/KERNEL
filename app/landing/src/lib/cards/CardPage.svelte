<script lang="ts">
	import { MODEL_STYLE } from '$lib/modelStyle';
	import { onDestroy, onMount } from 'svelte';
	import { visible } from '$lib/fx/actions';
	import { onFrame, reducedMotion, whenIdle } from '$lib/fx/motion';
	import Odometer from '$lib/fx/Odometer.svelte';
	import { variantLabel, words500, type CardView, type ModelKey } from '$lib/data/measurements';
	import { fmtGB, fmtSec } from '$lib/format';
	import ModelMark from '$lib/ModelMark.svelte';
	import { cardsHref, currentLang, href, num } from '$lib/i18n';
	import CardHead from './CardHead.svelte';
	import { cardsCopy } from './copy';
	import { headline, heatOf, MEASURED, roundTo } from './explorer';
	import GpuArt from './GpuArt.svelte';
	import ProductPhoto from './ProductPhoto.svelte';
	import Ratio from './Ratio.svelte';
	import RunShowcase from './RunShowcase.svelte';
	import { photoOf, vendorVars } from './vendor';
	import VendorTheme from './VendorTheme.svelte';
	import VramFill from './VramFill.svelte';

	let { card }: { card: CardView } = $props();

	const lang = $derived(currentLang());
	const t = $derived(cardsCopy[lang].card);
	const d = $derived(headline(card));
	/** The ranking: our pick first, then the other measured models in the registry's order. */
	const ranked = $derived([...card.runs].sort((a, b) => Number(b.model === card.pick.model) - Number(a.model === card.pick.model)));

	/*
	 * The signature moment, one timeline for the counter and the card. The page paints its final,
	 * measured state (that is what no-JS readers and the first paint see). Once the hero is on screen
	 * and the page is idle, the card cold-starts: our figure drops to the typical app's speed and the
	 * card goes cold, then it revs back up to the measured t/s while the card heats with it (strip,
	 * underglow, backplate wash, the glow on the page; all scaled by the measured gain, so a ×1.05
	 * card barely warms) and the fans spin up into a blur. On landing: a short kick and settle, the
	 * speed-up flashes, the fans spin down. Reduced motion: final state only.
	 */
	const hot = $derived(d ? roundTo(d.ours.decode!.v, 1) : 0);
	const cold = $derived(d ? roundTo(d.before.decode!.v, 1) : 0);
	// svelte-ignore state_referenced_locally
	let tp = $state(hot);
	let rpm = $state(0);
	let landed = $state(0);
	let started = false;
	let stop: (() => void) | null = null;
	const easeOutCubic = (k: number) => 1 - (1 - k) ** 3;
	const easeInOut = (k: number) => (k < 0.5 ? 2 * k * k : 1 - (-2 * k + 2) ** 2 / 2);
	function rev() {
		if (!d || reducedMotion()) return;
		const o = hot;
		const b = cold;
		let t = 0;
		stop?.();
		stop = onFrame((dt) => {
			t += dt;
			if (t < 0.45) tp = o - (o - b) * easeInOut(t / 0.45);
			else if (t < 0.7) tp = b;
			else {
				// the counter climbs and locks onto the measured value (no slow tail of 77,9 → 78,0,
				// never above it); the fans keep spinning down after the lock
				const k = Math.min(1, (t - 0.7) / 1.7);
				const lock = Math.min(1, easeOutCubic(k) / 0.96);
				tp = lock >= 1 ? o : Math.min(o, b + (o - b) * lock);
				rpm = k < 1 ? 0.25 + 0.75 * easeOutCubic(k) : Math.max(0, 1 - (t - 2.4) / 2.6);
				if (lock >= 1 && landed === 0) landed = 1;
				if (k >= 1 && rpm === 0) {
					stop = null;
					return false;
				}
			}
		});
	}
	/** Any interruption (hero scrolled away, tab hidden, bfcache restore) lands on the measured state. */
	function finish() {
		if (!stop) return;
		stop();
		stop = null;
		tp = hot;
		rpm = 0;
	}
	/**
	 * Start once the hero is on screen, after load, when the main thread is idle (keeps TBT low);
	 * skip it if by then the hero has gone or the tab is hidden.
	 */
	let cancelIdle: (() => void) | null = null;
	let heroOn = false;
	function startWhenIdle(on: boolean) {
		heroOn = on;
		if (!on) {
			cancelIdle?.();
			finish();
			return;
		}
		if (started) return;
		started = true;
		cancelIdle = whenIdle(() => heroOn && !document.hidden && rev(), 400);
	}
	onMount(() => {
		const hide = () => document.hidden && finish();
		const show = (e: PageTransitionEvent) => e.persisted && finish();
		document.addEventListener('visibilitychange', hide);
		window.addEventListener('pageshow', show);
		return () => {
			document.removeEventListener('visibilitychange', hide);
			window.removeEventListener('pageshow', show);
		};
	});
	onDestroy(() => {
		stop?.();
		cancelIdle?.();
	});
	const charge = $derived(d && hot > cold ? Math.max(0, Math.min(1, (tp - cold) / (hot - cold))) : 1);
	const heat = $derived(heatOf(d?.ratio));

	const others = $derived(MEASURED.filter((e) => e.id !== card.id));
	const prefix = $derived(card.name.split(card.short)[0].trim());

	/* plate under the render: facts about the headline run, as many as were measured */
	const plateFacts = $derived.by(() => {
		if (!d) return [];
		const items: { k: string; v: string; sub?: string; bar?: number; star?: boolean; cold?: string; model?: ModelKey }[] = [];
		items.push({ k: t.models, v: MODEL_STYLE[d.run.model].short, sub: d.run.quant, star: d.run.model === card.pick.model, model: d.run.model });
		if (d.run.file) items.push({ k: t.fileSize, v: fmtGB(d.run.file.v, d.run.file.unit, lang).text });
		if (d.ours.vram) {
			const g = fmtGB(d.ours.vram.v, d.ours.vram.unit, lang);
			const gb = d.ours.vram.unit === 'GiB' ? (d.ours.vram.v * 2 ** 30) / 1e9 : d.ours.vram.v;
			items.push({ k: t.vram, v: g.text, sub: `/ ${card.vramGB}\u00a0GB`, bar: Math.min(1, gb / card.vramGB) });
		}
		const wb = words500(d.before, lang);
		const wo = words500(d.ours, lang);
		if (wb && wo) items.push({ k: t.words, v: fmtSec(wo.v, lang), cold: fmtSec(wb.v, lang) });
		return items;
	});
</script>

<VendorTheme vendor={card.vendor}>
<CardHead id={card.id} {prefix} short={card.short} vendor={card.vendor} vram={card.vramGB} {heat} kick={landed} spec="{card.vramGB} GB · {card.arch} · {num(card.bwGBs.v, lang, 0)} GB/s" charge={d ? charge : null} {rpm}>
	{#if d}
		<div class="speedline hx-bt" class:landed={landed > 0} style="--g:{heat * charge}" use:visible={startWhenIdle}>
			<p class="hl-m mono">{t.headline(`${MODEL_STYLE[d.run.model].short} ${d.run.quant}`)}</p>
			<!-- one line: typical → ours · the speed-up (wraps only on narrow phones) -->
			<div class="hl-n">
				<span class="b">
					<span class="lbl">{variantLabel(d.run, d.run.before)[lang]}</span>
					<span class="v cold fig"><Odometer value={cold} decimals={1} {lang} duration={0} /></span>
				</span>
				<span class="arrow" aria-hidden="true">→</span>
				<span class="b">
					<span class="lbl">{variantLabel(d.run, d.run.ours)[lang]}</span>
					<span class="v hot fig"><Odometer value={roundTo(tp, 1)} decimals={1} {lang} duration={0} label={variantLabel(d.run, d.run.ours)[lang]} /><span class="u">t/s</span></span>
				</span>
				{#if d.ratio}
					<span class="b stamp">
						<span class="lbl">{t.faster}</span>
						<Ratio value={d.ratio} {lang} size="md" />
					</span>
				{/if}
			</div>
		</div>
	{/if}
	{#snippet plate()}
		{#if d}
			<div class="plate-wrap hx-bt">
				<dl class="plate" style="--n:{plateFacts.length}">
					{#each plateFacts as it (it.k)}
						<div>
							<dt>{it.k}</dt>
							<dd>
								{#if it.model}<ModelMark model={it.model} />{/if}
								{#if it.cold}<span class="cold-text">{it.cold}</span>{' → '}{/if}{it.v}{#if it.star}<span class="star" aria-hidden="true">{'\u00a0'}★</span>{/if}
								{#if it.sub}<span class="q">{it.sub}</span>{/if}
								{#if it.bar != null}<span class="pbar" aria-hidden="true"><i style="width:{it.bar * 100}%"></i></span>{/if}
							</dd>
						</div>
					{/each}
				</dl>
			</div>
		{/if}
	{/snippet}
</CardHead>

<section class="wrap fp" aria-label={t.fingerprint}>
	<dl class="strip hx-surface">
		<div><dt>{t.hw.vram}</dt><dd class="fig">{card.vramGB}<span>GB</span></dd></div>
		<div><dt>{t.hw.bw}</dt><dd class="fig">{num(card.bwGBs.v, lang, 0)}<span>GB/s</span></dd></div>
		<div><dt>{t.hw.power}</dt><dd class="fig">{num(card.powerW.v, lang, 0)}<span>W</span></dd></div>
		<div><dt>{t.hw.arch}</dt><dd class="txt">{card.arch}</dd></div>
		{#if card.pcie}<div><dt>{t.hw.pcie}</dt><dd class="txt">{card.pcie}</dd></div>{/if}
	</dl>
</section>

<VramFill {card} />

<section class="wrap runs" aria-labelledby="runs-title">
	<header class="runs-head">
		<h2 id="runs-title" class="runs-h hx-grad">{t.rankTitle}</h2>
		<p class="fine">{t.rankLede}</p>
		{#if ranked.length > 1}
			<nav class="jump" aria-label={t.rankTitle}>
				{#each ranked as r, i (r.model)}
					<a href="#model-{r.model}" style="--mc:{MODEL_STYLE[r.model].color}"><span class="mono">{String(i + 1).padStart(2, '0')}</span> <ModelMark model={r.model} /> {MODEL_STYLE[r.model].short}{#if r.model === card.pick.model}<span aria-hidden="true">{'\u00a0'}★</span>{/if}</a>
				{/each}
			</nav>
		{/if}
	</header>
	<ol class="rank-list" role="list">
		{#each ranked as r, i (r.model)}
			<li><RunShowcase {card} run={r} {lang} rank={i + 1} /></li>
		{/each}
	</ol>
</section>

<section class="wrap next" aria-labelledby="next-title">
	<div class="next-in panel hx-surface hx-ring">
		<h2 id="next-title" class="giga hx-grad">{t.next}</h2>
		<div class="ctas">
			<a class="cta cta--bone" href="{cardsHref(lang, lang === 'pl' ? 'porownaj/' : 'compare/')}?a={card.id}">{t.compareWith} <span class="arrow" aria-hidden="true">→</span></a>
			<a class="cta cta--line" href={href(lang, '/start')}>{t.start}</a>
		</div>
	</div>
	<h3 class="others-h eyebrow">{t.measuredOthers}</h3>
	<ul class="others" role="list">
		{#each others as e (e.id)}
			{@const od = headline(e.card)}
			{@const op = photoOf(e.id)}
			<li>
				<a href={cardsHref(lang, `${e.id}/`)} class="other hx-ring hx-surface" style={vendorVars(e.card.vendor)}>
					<span class="o-art">
						{#if op}<ProductPhoto id={op} sizes="8rem" />{:else}<GpuArt label={e.card.short} vendor={e.card.vendor} vram={e.card.vramGB} heat={heatOf(od?.ratio)} flat />{/if}
					</span>
					<span class="o-name">{e.card.short}</span>
					<span class="o-x">{#if od?.ratio}<Ratio value={od.ratio} {lang} size="sm" />{/if}<span class="mono">{e.card.vramGB} GB</span></span>
				</a>
			</li>
		{/each}
	</ul>
</section>
</VendorTheme>

<style>
	.wrap {
		width: min(100% - 2 * var(--gutter), 88rem);
		margin-inline: auto;
	}

	/* headline numbers inside the hero: one row, typical → ours · speed-up */
	.speedline {
		display: grid;
		gap: var(--sp-2);
		margin-top: var(--sp-3);
		padding-top: var(--sp-4);
		width: 100%;
	}
	.hl-m {
		margin: 0;
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-mute);
	}
	.hl-n {
		display: flex;
		align-items: flex-end;
		flex-wrap: nowrap;
		gap: var(--sp-2) clamp(0.7rem, 1.4vw, 1.4rem);
		min-width: 0;
	}
	.b {
		display: grid;
		gap: 0.3rem;
		min-width: 0;
	}
	.lbl {
		font-size: var(--fs-xs);
		color: var(--text-mute);
		white-space: nowrap;
	}
	.v {
		font-family: var(--font-mono);
		font-weight: 600;
		line-height: 0.95;
		display: inline-flex;
		align-items: baseline;
		gap: 0.35rem;
		white-space: nowrap;
	}
	.v.cold {
		font-size: clamp(1.5rem, 1rem + 1.2vw, 2.25rem);
		color: var(--before);
	}
	/* our figure glows as much as the measured gain (a ×1.05 card barely; ×2.0 white-hot) */
	.v.hot {
		font-size: clamp(2.2rem, 1.2rem + 2.6vw, 3.6rem);
		color: var(--text-hi);
		filter: drop-shadow(0 0 calc(4px + var(--g) * 22px) rgb(var(--hot-rgb, 255 122 26) / calc(var(--g) * 0.75)));
	}
	.u {
		font-size: var(--fs-xs);
		color: var(--text-mute);
		text-shadow: none;
	}
	.arrow {
		font-size: var(--fs-lg);
		color: var(--text-mute);
		padding-bottom: 0.25rem;
	}
	/* the speed-up closes the row behind a hairline; it stamps in when the counter lands */
	.stamp {
		padding-left: clamp(0.7rem, 1.4vw, 1.4rem);
		border-left: 1px solid rgb(var(--v, 255 122 26) / 0.35);
		line-height: 0.9;
	}
	.stamp :global(.rx--md) {
		--rx-fs: clamp(1.7rem, 1rem + 1.6vw, 2.6rem);
	}
	@media (max-width: 30rem) {
		.hl-n {
			flex-wrap: wrap;
		}
		.stamp {
			flex-basis: 100%;
			display: flex;
			flex-direction: row-reverse;
			justify-content: flex-end;
			align-items: baseline;
			gap: 0.5rem;
			padding: var(--sp-2) 0 0;
			border-left: 0;
		}
	}
	@media (prefers-reduced-motion: no-preference) {
		.stamp {
			transform-origin: left center;
		}
		/* on landing: the speed-up stamps (scale punch) and the hot figure blooms */
		.landed .stamp {
			animation: stamp 0.7s var(--ease-spring);
		}
		.landed .v.hot {
			animation: land 1.1s var(--ease-out);
		}
	}
	@keyframes stamp {
		30% {
			transform: scale(1.12);
		}
	}
	@keyframes land {
		25% {
			filter: drop-shadow(0 0 calc(10px + var(--g) * 30px) rgb(var(--amber-rgb, 255 193 90) / calc(0.2 + var(--g) * 0.8)));
		}
	}

	/* plate under the render: one tight row of facts */
	.plate-wrap {
		padding-top: var(--sp-3);
	}
	.plate {
		margin: 0;
		display: grid;
		grid-template-columns: repeat(var(--n), minmax(0, auto));
		justify-content: space-between;
		gap: var(--sp-2) var(--sp-5);
	}
	.plate div {
		display: grid;
		gap: 0.25rem;
		align-content: start;
		min-width: 0;
	}
	.plate dt {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.1em;
		color: var(--text-mute);
	}
	.plate dd {
		margin: 0;
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0 0.35rem;
		font-family: var(--font-mono);
		font-size: var(--fs-sm);
		color: var(--text-hi);
	}
	.plate .q {
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.star {
		color: var(--v-hi, var(--text-hi));
	}
	.pbar {
		flex-basis: 100%;
		display: block;
		height: 3px;
		margin-top: 0.3rem;
		background: var(--bg-3);
		border-radius: 2px;
		overflow: hidden;
	}
	.pbar i {
		display: block;
		height: 100%;
		background: rgb(var(--v, 237 234 227));
	}
	@media (max-width: 40rem) {
		.plate {
			grid-template-columns: repeat(2, minmax(0, 1fr));
			justify-content: stretch;
		}
	}
	.rank-list > li {
		min-width: 0;
	}

	/* fingerprint: one compact strip */
	.fp {
		position: relative;
		margin-bottom: var(--sp-6);
	}
	.strip {
		margin: 0;
		display: grid;
		grid-auto-flow: column;
		grid-auto-columns: minmax(0, 1fr);
		border: 1px solid rgb(var(--v) / 0.25);
		border-radius: var(--r-lg);
	}
	.strip div {
		padding: var(--sp-3) var(--sp-4);
		border-right: 1px solid rgb(var(--v) / 0.16);
		min-width: 0;
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
		margin: 0.3rem 0 0;
		font-family: var(--font-mono);
		font-size: var(--fs-xl);
		font-weight: 600;
		color: var(--text-hi);
		letter-spacing: -0.02em;
		white-space: nowrap;
	}
	.strip dd span {
		margin-left: 0.3rem;
		font-size: var(--fs-2xs);
		color: var(--hx-ink);
		letter-spacing: 0.06em;
	}
	.strip dd.txt {
		font-size: var(--fs-sm);
		padding-top: 0.35rem;
		white-space: normal;
	}
	/* two columns on narrow screens; an odd last cell spans the row */
	@media (max-width: 48rem) {
		.strip {
			grid-auto-flow: row;
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
		.strip div:nth-child(2n) {
			border-right: 0;
		}
		.strip div:nth-child(n + 3) {
			border-top: 1px solid rgb(var(--v) / 0.16);
		}
		.strip div:last-child:nth-child(odd) {
			grid-column: 1 / -1;
		}
	}

	/* the ranking: every model the same block, best first */
	.runs {
		padding-top: clamp(2rem, 4vw, 3rem);
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: var(--sp-5);
	}
	.runs-head {
		display: grid;
		gap: var(--sp-3);
	}
	.runs-head .fine {
		margin: 0;
		max-width: 60ch;
	}
	.runs-h {
		margin: 0;
		font-size: clamp(1.75rem, 1rem + 2.6vw, 3.25rem);
		font-weight: 800;
		font-stretch: 112%;
		letter-spacing: -0.03em;
		line-height: 1.05;
		color: var(--text-hi);
	}
	.jump {
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-2);
	}
	.jump a {
		display: inline-flex;
		align-items: center;
		gap: 0.45rem;
		min-height: 2.5rem;
		padding: 0 0.95rem;
		border: 1px solid rgb(var(--v) / 0.3);
		border-radius: var(--r-pill);
		background: rgb(255 255 255 / 0.02);
		font-size: var(--fs-sm);
		font-weight: 650;
		color: var(--text-hi);
		text-decoration: none;
		transition:
			border-color 0.4s var(--ease-out),
			background-color 0.4s var(--ease-out),
			transform 0.4s var(--ease-out);
	}
	.jump a .mono {
		font-size: var(--fs-2xs);
		color: var(--hx-ink);
	}
	.jump a:hover {
		border-color: var(--mc);
		background: color-mix(in srgb, var(--mc) 10%, transparent);
		transform: translateY(-1px);
	}
	.rank-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: clamp(2rem, 4vw, 3rem);
	}

	/* next */
	.next {
		padding: clamp(2.5rem, 6vw, 4.5rem) 0 var(--section-y);
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
		overflow: hidden;
	}
	.next-in .giga {
		margin: 0;
		font-size: clamp(2rem, 1rem + 3vw, 3.75rem);
	}
	.ctas {
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-3);
	}
	.others-h {
		margin: var(--sp-6) 0 0;
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
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 18rem), 1fr));
		gap: var(--sp-4);
	}
	.other {
		display: grid;
		grid-template-columns: 8rem minmax(0, 1fr);
		grid-template-rows: auto auto;
		align-items: center;
		column-gap: var(--sp-4);
		padding: var(--sp-3) var(--sp-4);
		border: 1px solid var(--line);
		border-radius: var(--r-lg);
		text-decoration: none;
		color: var(--text-hi);
		transition:
			box-shadow var(--dur-3) var(--ease-out),
			transform var(--dur-3) var(--ease-out);
	}
	.other:hover {
		transform: translateY(-3px);
	}
	.other:hover .o-name {
		color: var(--hx-ink);
	}
	.o-art {
		grid-row: 1 / span 2;
	}
	.o-name {
		font-size: var(--fs-xl);
		font-weight: 800;
		font-stretch: 112%;
		letter-spacing: -0.03em;
		width: fit-content;
	}
	.o-x {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: var(--sp-3);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
</style>
