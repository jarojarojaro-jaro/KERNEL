<script lang="ts">
	import { MODEL_STYLE } from '$lib/modelStyle';
	import { onDestroy } from 'svelte';
	import { visible } from '$lib/fx/actions';
	import { onFrame, reducedMotion, whenIdle } from '$lib/fx/motion';
	import Odometer from '$lib/fx/Odometer.svelte';
	import SourceTip from '$lib/fx/SourceTip.svelte';
	import { MODEL_INFO, variantLabel, words500, type CardView, type ModelKey } from '$lib/data/measurements';
	import { fmtGB, fmtSec, localizeDecimals } from '$lib/format';
	import ModelMark from '$lib/ModelMark.svelte';
	import { cardsHref, currentLang, href, num } from '$lib/i18n';
	import CardHead from './CardHead.svelte';
	import Choice from './Choice.svelte';
	import { cardsCopy } from './copy';
	import { headline, heatOf, MEASURED, roundTo } from './explorer';
	import GpuArt from './GpuArt.svelte';
	import Ratio from './Ratio.svelte';
	import RunShowcase from './RunShowcase.svelte';
	import VramFill from './VramFill.svelte';

	let { card }: { card: CardView } = $props();

	const lang = $derived(currentLang());
	const t = $derived(cardsCopy[lang].card);
	const d = $derived(headline(card));

	// svelte-ignore state_referenced_locally
	let model = $state<ModelKey>(card.pick.model);
	const run = $derived(card.runs.find((r) => r.model === model) ?? card.runs[0]);

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
				const k = Math.min(1, (t - 0.7) / 1.7);
				tp = k >= 1 ? o : b + (o - b) * easeOutCubic(k);
				rpm = k < 1 ? 0.25 + 0.75 * easeOutCubic(k) : Math.max(0, 1 - (t - 2.4) / 2.6);
				if (k >= 1 && landed === 0) landed = 1;
				if (k >= 1 && rpm === 0) {
					stop = null;
					return false;
				}
			}
		});
	}
	/** Start once the hero is on screen, after load, when the main thread is idle (keeps TBT low). */
	let cancelIdle: (() => void) | null = null;
	function startWhenIdle(on: boolean) {
		if (!on || started) return;
		started = true;
		cancelIdle = whenIdle(rev, 400);
	}
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
	const plateSrc = $derived(
		d
			? [
					...(d.run.file ? [d.run.file.src] : []),
					...(d.ours.vram ? [d.ours.vram.src] : []),
					...[words500(d.ours, lang), words500(d.before, lang)].filter((w) => w).map((w) => w!.src),
					d.run.conditionsSrc
				]
			: []
	);
	const plateNote = $derived(d ? [d.run.conditions[lang], d.ours.vram?.unit === 'GiB' ? t.gibNote : '', words500(d.ours, lang)?.derived ? t.wordsDerived : ''].filter(Boolean).join(' · ') : '');
</script>

<CardHead id={card.id} {prefix} short={card.short} vendor={card.vendor} vram={card.vramGB} {heat} kick={landed} spec="{card.vramGB} GB · {card.arch} · {num(card.bwGBs.v, lang, 0)} GB/s" charge={d ? charge : null} {rpm}>
	{#if d}
		<div class="hl hx-bt" class:landed={landed > 0} style="--g:{heat * charge}" use:visible={startWhenIdle}>
			<p class="hl-m mono">{t.headline(`${MODEL_STYLE[d.run.model].short} ${d.run.quant}`)}</p>
			<div class="hl-n">
				<span class="b">
					<span class="lbl">{variantLabel(d.run, d.run.before)[lang]}</span>
					<span class="v cold"><Odometer value={cold} decimals={1} {lang} duration={0} /></span>
				</span>
				<span class="arrow" aria-hidden="true">→</span>
				<span class="b">
					<span class="lbl">{variantLabel(d.run, d.run.ours)[lang]}</span>
					<span class="v hot"><Odometer value={roundTo(tp, 1)} decimals={1} {lang} duration={0} label={variantLabel(d.run, d.run.ours)[lang]} /><span class="u">t/s</span></span>
				</span>
			</div>
			<div class="hl-foot">
				{#if d.ratio}<span class="stamp"><Ratio value={d.ratio} {lang} size="lg" /> <span class="w">{t.faster}</span></span>{/if}
				<SourceTip {lang} src={[d.before.decode!.src, d.ours.decode!.src, ...(d.run.gain?.total ? [d.run.gain.src] : [])]} note={d.run.metric[lang]} />
			</div>
		</div>
	{/if}
	{#snippet plate()}
		{#if d}
			<div class="plate-wrap hx-bt">
				<dl class="plate" style="--n:{plateFacts.length === 4 ? 2 : plateFacts.length}">
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
				<SourceTip {lang} src={plateSrc} note={plateNote} />
			</div>
		{/if}
	{/snippet}
</CardHead>

<section class="wrap fp" aria-label={t.fingerprint}>
	<dl class="strip hx-surface">
		<div><dt>{t.hw.vram}</dt><dd>{card.vramGB}<span>GB</span></dd></div>
		<div><dt>{t.hw.bw}</dt><dd>{num(card.bwGBs.v, lang, 0)}<span>GB/s</span></dd></div>
		<div><dt>{t.hw.power}</dt><dd>{num(card.powerW.v, lang, 0)}<span>W</span></dd></div>
		<div><dt>{t.hw.arch}</dt><dd class="txt">{card.arch}</dd></div>
		{#if card.pcie}<div><dt>{t.hw.pcie}</dt><dd class="txt">{card.pcie}</dd></div>{/if}
	</dl>
	<span class="fp-tip"><SourceTip {lang} src={[card.bwGBs.src, card.powerW.src, card.hwSrc]} note={card.hwLine ? localizeDecimals(card.hwLine[lang], lang) : ''} /></span>
</section>

<VramFill {card} />

<section class="wrap runs" aria-labelledby="runs-title">
	<div class="picker">
		<h2 id="runs-title" class="runs-h hx-h" style="--mc:{MODEL_STYLE[run.model].color}"><ModelMark model={run.model} size="0.7em" /> {#each MODEL_INFO[run.model].name.split(' ') as w, i (i)}{i ? ' ' : ''}<span class="nw">{w}</span>{/each}</h2>
		{#if card.runs.length > 1}
			<Choice
				legend={t.models}
				name="model-{card.id}"
				size="lg"
				tight
				bind:value={model}
				options={card.runs.map((r) => ({ value: r.model, model: r.model, label: MODEL_STYLE[r.model].short, sub: r.model === card.pick.model ? `${r.quant} · ${t.pickBadge}` : r.quant }))}
			/>
		{/if}
	</div>
	{#key run.model}
		<div class="run-body">
			<RunShowcase {card} {run} {lang} />
		</div>
	{/key}
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
			<li>
				<a href={cardsHref(lang, `${e.id}/`)} class="other hx-ring hx-surface">
					<span class="o-art"><GpuArt label={e.card.short} vendor={e.card.vendor} vram={e.card.vramGB} heat={heatOf(od?.ratio)} flat /></span>
					<span class="o-name">{e.card.short}</span>
					<span class="o-x">{#if od?.ratio}<Ratio value={od.ratio} {lang} size="sm" />{/if}<span class="mono">{e.card.vramGB} GB</span></span>
				</a>
			</li>
		{/each}
	</ul>
</section>

<style>
	.wrap {
		width: min(100% - 2 * var(--gutter), 88rem);
		margin-inline: auto;
	}

	/* headline numbers inside the hero */
	.hl {
		display: grid;
		gap: var(--sp-3);
		margin-top: var(--sp-6);
		padding-top: var(--sp-6);
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
		flex-wrap: wrap;
		gap: var(--sp-2) var(--sp-5);
	}
	.b {
		display: grid;
		gap: 0.2rem;
	}
	.lbl {
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.v {
		font-family: var(--font-mono);
		font-weight: 600;
		line-height: 1;
		display: inline-flex;
		align-items: baseline;
		gap: 0.4rem;
	}
	.v.cold {
		font-size: clamp(1.8rem, 1rem + 2vw, 2.75rem);
		color: var(--before);
	}
	/* our figure glows as much as the measured gain (a ×1.05 card barely; ×2.0 white-hot) */
	.v.hot {
		font-size: clamp(3rem, 1.4rem + 4.4vw, 5.25rem);
		color: var(--text-hi);
		filter: drop-shadow(0 0 calc(4px + var(--g) * 22px) rgb(255 122 26 / calc(var(--g) * 0.75)));
	}
	.u {
		font-size: var(--fs-xs);
		color: var(--text-mute);
		text-shadow: none;
	}
	.arrow {
		font-size: var(--fs-xl);
		color: var(--text-mute);
		padding-bottom: 0.4rem;
	}
	.hl-foot {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: var(--sp-3) var(--sp-5);
		min-height: 3.5rem;
	}
	/* the speed-up stamps in when the counter lands */
	.stamp {
		display: inline-flex;
		align-items: baseline;
		gap: 0.5rem;
	}
	.stamp .w {
		font-weight: 650;
		color: var(--text-hi);
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
			transform: scale(1.18);
		}
	}
	@keyframes land {
		25% {
			filter: drop-shadow(0 0 calc(10px + var(--g) * 30px) rgb(255 193 90 / calc(0.2 + var(--g) * 0.8)));
		}
	}

	.nw {
		white-space: nowrap;
	}

	.nw {
		white-space: nowrap;
	}

	/* plate under the render: as many columns as facts */
	.plate-wrap {
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		align-items: start;
		gap: var(--sp-4);
		padding-top: var(--sp-4);
	}
	.plate {
		margin: 0;
		display: grid;
		grid-template-columns: repeat(var(--n), minmax(0, 1fr));
		gap: var(--sp-4);
	}
	.plate div {
		display: grid;
		gap: 0.35rem;
		align-content: start;
		min-width: 0;
	}
	.plate dt {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.12em;
		color: var(--text-mute);
	}
	.plate dd {
		margin: 0;
		overflow-wrap: anywhere;
		font-family: var(--font-mono);
		font-size: var(--fs-md);
		color: var(--text-hi);
	}
	.plate .q {
		display: block;
		margin-top: 0.15rem;
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.star {
		color: var(--text-hi);
	}
	.pbar {
		display: block;
		height: 3px;
		margin-top: 0.45rem;
		background: var(--bg-3);
		border-radius: 2px;
		overflow: hidden;
	}
	.pbar i {
		display: block;
		height: 100%;
		background: var(--text-hi);
	}
	@media (max-width: 40rem) {
		.plate {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
		.plate div:first-child,
		.plate div:last-child:nth-child(even) {
			grid-column: 1 / -1;
		}
		.plate dd {
			font-size: var(--fs-sm);
		}
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
		border: 1px solid rgb(255 122 26 / 0.22);
		border-radius: var(--r-lg);
	}
	.strip div {
		padding: var(--sp-3) var(--sp-4);
		border-right: 1px solid rgb(255 122 26 / 0.14);
		min-width: 0;
	}
	.strip div:last-child {
		border-right: 0;
		padding-right: 6rem;
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
	}
	.fp-tip {
		position: absolute;
		right: var(--sp-3);
		top: 50%;
		transform: translateY(-50%);
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
			border-top: 1px solid rgb(255 122 26 / 0.14);
		}
		.strip div:last-child:nth-child(odd) {
			grid-column: 1 / -1;
		}
		.strip div:last-child {
			padding-right: 6rem;
		}
		.fp-tip {
			top: auto;
			bottom: var(--sp-3);
			transform: none;
		}
	}

	/* runs */
	.runs {
		padding-top: var(--sp-6);
	}
	.picker {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-end;
		justify-content: space-between;
		gap: var(--sp-3) var(--sp-6);
		padding-bottom: var(--sp-2);
	}
	.runs-h {
		margin: 0;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0 0.4em;
		font-size: clamp(1.75rem, 1rem + 2.6vw, 3.25rem);
		font-weight: 800;
		font-stretch: 112%;
		letter-spacing: -0.03em;
		line-height: 1.05;
		color: var(--text-hi);
	}
	@media (prefers-reduced-motion: no-preference) {
		.run-body {
			animation: swap 0.6s var(--ease-out) both;
		}
	}
	@keyframes swap {
		from {
			opacity: 0;
			transform: translate3d(0, 1.5rem, 0);
		}
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
		font-stretch: 115%;
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
