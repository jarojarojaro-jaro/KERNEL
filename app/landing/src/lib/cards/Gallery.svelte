<script lang="ts">
	import { MODEL_STYLE } from '$lib/modelStyle';
	/**
	 * The explorer's front page: a compact index of cards, grouped by vendor. Measured cards are
	 * small product tiles (a small render heated by the measured gain, the speed-up, before → after);
	 * cards in the measurement queue are dense typographic tiles with, where the formula allows, a
	 * labelled estimate. The big render lives on the card page. Search and the VRAM filter narrow every
	 * group; the live count says how many cards are shown.
	 */
	import { onDestroy, onMount } from 'svelte';
	import { reveal, tilt } from '$lib/fx/actions';
	import HeatField from '$lib/fx/HeatField.svelte';
	import { onFrame, reducedMotion, whenIdle } from '$lib/fx/motion';
	import SourceTip from '$lib/fx/SourceTip.svelte';
	import { fmtTps } from '$lib/format';
	import { cardsHref, currentLang, href, num } from '$lib/i18n';
	import { cardsCopy } from './copy';
	import Choice from './Choice.svelte';
	import {
		EST_SRC,
		GPU_SRC,
		headline,
		heatOf,
		inBand,
		matches,
		MEASURED,
		QUEUED,
		queueEstimate,
		splitName,
		VRAM_BANDS,
		type Entry,
		type MeasuredEntry,
		type QueuedEntry,
		type VramBand
	} from './explorer';
	import EstTag from './EstTag.svelte';
	import GpuArt from './GpuArt.svelte';
	import Kinetic from './Kinetic.svelte';
	import Ratio from './Ratio.svelte';

	const lang = $derived(currentLang());
	const t = $derived(cardsCopy[lang].gallery);
	const tc = $derived(cardsCopy[lang].card);

	let q = $state('');
	let band = $state<VramBand>('all');
	let hover = $state<string | null>(null);

	const keep = (e: Entry) => inBand(e, band) && matches(e, q);
	const VENDORS = ['nvidia', 'amd', 'intel', 'apple'];
	const vendorOf = (e: Entry) => (e.kind === 'measured' ? e.card.vendor : e.gpu.vendor);
	const groups = $derived(
		VENDORS.map((v) => ({
			v,
			measured: MEASURED.filter((e) => vendorOf(e) === v && keep(e)) as MeasuredEntry[],
			queued: QUEUED.filter((e) => vendorOf(e) === v && keep(e)) as QueuedEntry[]
		})).filter((g) => g.measured.length + g.queued.length > 0)
	);
	const total = MEASURED.length + QUEUED.length;
	const shown = $derived(groups.reduce((n, g) => n + g.measured.length + g.queued.length, 0));
	const NB = '\u00a0';

	/*
	 * Hover "rev": the hovered card cold-starts and revs to its measured gain: the strip and the
	 * underglow fill to the gain, the fans spin up into a blur, the speed-up counts up once. On leave
	 * the fans spin down. Fine pointers only; reduced motion: nothing moves.
	 */
	let rev = $state<{ id: string; c: number; r: number } | null>(null);
	let replay = $state<Record<string, number>>({});
	let held = false;
	let revStop: (() => void) | null = null;
	function revUp(id: string) {
		hover = id;
		if (reducedMotion() || !matchMedia('(hover: hover) and (pointer: fine)').matches) return;
		held = true;
		replay[id] = (replay[id] ?? 0) + 1;
		revStop?.();
		let t = 0;
		rev = { id, c: 0, r: 0.3 };
		revStop = onFrame((dt) => {
			t += dt;
			const k = Math.min(1, t / 1.1);
			const c = 1 - (1 - k) ** 3;
			const r = held ? Math.min(1, 0.3 + t * 1.1) : Math.max(0, (rev?.r ?? 0) - dt * 0.7);
			rev = { id, c, r };
			if (!held && k >= 1 && r === 0) {
				rev = null;
				revStop = null;
				return false;
			}
		});
	}
	function revDown() {
		hover = null;
		held = false;
	}
	onDestroy(() => revStop?.());

	/* The ember shader is decoration: start it once the page has loaded and the main thread is idle. */
	let fieldOn = $state(false);
	onMount(() => whenIdle(() => (fieldOn = true), 800));
</script>

<section class="hero" aria-labelledby="cards-title">
	{#if fieldOn}<HeatField heat={0.25} class="hero-field" />{/if}
	<div class="wrap hero-in">
		<div class="hero-title">
			<p class="eyebrow">{t.eyebrow}{NB}· {t.measuredCount(MEASURED.length)}{NB}· {t.queuedCount(QUEUED.length)}</p>
			<Kinetic id="cards-title" lines={t.title} wide={1} heat={1} class="mega hx-h" />
			<p class="lede">{t.lede}</p>
		</div>
		<div class="controls">
			<div class="search">
				<label for="card-q" class="eyebrow">{t.search}</label>
				<div class="field">
					<svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="8.5" cy="8.5" r="5.5" fill="none" stroke="currentColor" stroke-width="1.6" /><path d="m13 13 4 4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" /></svg>
					<input id="card-q" type="search" bind:value={q} placeholder={t.searchPh} autocomplete="off" spellcheck="false" aria-describedby="card-count" />
				</div>
			</div>
			<div class="filter-row">
				<Choice legend={t.vram} name="vram-band" bind:value={band} options={VRAM_BANDS.map((b) => ({ value: b, label: t.bands[b] }))} />
				<p class="count mono" id="card-count" role="status">{t.results(shown, total)}</p>
			</div>
		</div>
	</div>
</section>

<div class="wrap index">
	{#each groups as g (g.v)}
		<section class="group" aria-labelledby="vendor-{g.v}">
			<header class="g-head hx-bb">
				<h2 id="vendor-{g.v}" class="g-name hx-grad">{t.vendors[g.v]}</h2>
				<p class="g-meta mono">{t.groupMeta(g.measured.length, g.queued.length)}</p>
			</header>

			{#if g.measured.length}
				<ul class="measured" role="list">
					{#each g.measured as e, i (e.id)}
						{@const d = headline(e.card)}
						{@const prefix = e.card.name.split(e.card.short)[0].trim()}
						<li style="--reveal-delay:{i * 60}ms; --th:{heatOf(d?.ratio)}" use:reveal>
							<article class="tile hx-ring" use:tilt={{ max: 5 }} onpointerenter={() => revUp(e.id)} onpointerleave={revDown} onfocusin={() => (hover = e.id)} onfocusout={() => (hover = null)}>
								<div class="tile-art" style="view-transition-name: art-{e.id}; view-transition-class: gpu">
									<GpuArt label={e.card.short} vendor={e.card.vendor} vram={e.card.vramGB} heat={heatOf(d?.ratio)} live={hover === e.id && rev?.id !== e.id} charge={rev?.id === e.id ? rev.c : null} rpm={rev?.id === e.id ? rev.r : 0} flat />
								</div>
								<div class="tile-body">
									<p class="pre mono"><span class="dot"></span>{prefix}</p>
									<h3 class="short" style="view-transition-name: name-{e.id}">
										<a href={cardsHref(lang, `${e.id}/`)} class="stretch" aria-label={t.open(e.card.name)}>{e.card.short}</a>
									</h3>
									<p class="spec mono">{e.card.vramGB}{NB}GB · {num(e.card.bwGBs.v, lang, 0)}{NB}GB/s</p>
									{#if d?.ratio}
										<div class="stat hx-bt" style="--glow:{heatOf(d.ratio)}">
											<p class="x"><Ratio value={d.ratio} {lang} size="md" replay={replay[e.id] ?? 0} /> <span class="w">{t.faster}</span></p>
											<p class="tps mono">
												<span class="m">{MODEL_STYLE[d.run.model].short}</span>
												<span><span class="cold-text">{fmtTps(d.before.decode!.v, lang)}</span> → <span class="hot hx-num">{fmtTps(d.ours.decode!.v, lang)}</span>{NB}t/s</span>
											</p>
										</div>
										<span class="tip"><SourceTip {lang} src={[d.before.decode!.src, d.ours.decode!.src, ...(d.run.gain?.total ? [d.run.gain.src] : [])]} note="{d.run.title} · {d.run.metric[lang]}" /></span>
									{/if}
								</div>
							</article>
						</li>
					{/each}
				</ul>
			{/if}

			{#if g.queued.length}
				<p class="q-label mono"><span class="ring"></span>{t.queuedShort}</p>
				<ul class="queued" role="list">
					{#each g.queued as e, i (e.id)}
						{@const est = queueEstimate(e.gpu)[0]}
						{@const nm = splitName(e.gpu.name, e.gpu.vendor)}
						<li style="--reveal-delay:{i * 40}ms" use:reveal>
							<article class="qtile">
								<div class="q-id">
									<p class="q-pre mono">{nm.prefix}</p>
									<h3 class="q-name" style="view-transition-name: name-{e.id}">
										<a href={cardsHref(lang, `${e.id}/`)} class="stretch" aria-label={t.open(e.gpu.name)}>{nm.short}</a>
									</h3>
									<p class="spec mono">{e.gpu.vram ? `${e.gpu.vram}${NB}GB · ` : ''}{num(e.gpu.bw, lang, 0)}{NB}GB/s</p>
								</div>
								<div class="q-est">
									{#if est}
										<p class="mono"><span class="hi">≈{NB}{num(est.decode.lo, lang, 0)}–{num(est.decode.hi, lang, 0)}{NB}t/s</span><span class="lbl">{est.model.name} {est.model.quant}</span></p>
										<div class="q-row"><EstTag text={t.estimateShort} /><span class="tip"><SourceTip {lang} src={[EST_SRC, GPU_SRC]} note={t.estimate} /></span></div>
									{:else}
										<p class="mono"><span class="lbl">{t.soon}</span></p>
									{/if}
								</div>
							</article>
						</li>
					{/each}
				</ul>
			{/if}
		</section>
	{/each}

	{#if !shown}
		<div class="empty">
			<p class="giga">{t.empty}</p>
			<a class="cta cta--bone" href={href(lang, '/start')}>{t.emptyCta} <span class="arrow" aria-hidden="true">→</span></a>
		</div>
	{/if}
	<p class="fine legend-note">{t.measuredLede} {tc.queueLede}</p>
</div>

<section class="band wrap" aria-labelledby="cmp-title">
	<div class="band-in panel hx-surface hx-ring">
		<div>
			<h2 id="cmp-title" class="giga hx-grad">{t.compareTitle}</h2>
			<p class="lede">{t.compareLede}</p>
		</div>
		<a class="cta cta--bone" href={cardsHref(lang, lang === 'pl' ? 'porownaj/' : 'compare/')}>{t.compareCta} <span class="arrow" aria-hidden="true">→</span></a>
	</div>
</section>

<style>
	.wrap {
		width: min(100% - 2 * var(--gutter), 88rem);
		margin-inline: auto;
	}

	/* ---------- hero: compact, the cards are the content ---------- */
	.hero {
		position: relative;
		padding: calc(4.25rem + clamp(1.25rem, 5vh, 4rem)) 0 clamp(1rem, 3vh, 2rem);
		overflow: hidden;
		isolation: isolate;
	}
	.hero :global(.hero-field) {
		position: absolute;
		inset: 0;
		z-index: -1;
		opacity: 0.8;
		mask-image: linear-gradient(#000 50%, transparent);
	}
	.hero-in {
		display: grid;
		grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr);
		align-items: end;
		gap: var(--sp-6) clamp(2rem, 5vw, 5rem);
	}
	.hero-title {
		display: grid;
		gap: var(--sp-4);
	}
	.hero-in :global(h1) {
		margin: 0;
		font-size: clamp(2.6rem, 0.6rem + 5.2vw, 6.25rem);
	}
	.hero .lede {
		margin: 0;
	}
	.controls {
		display: grid;
		gap: var(--sp-4);
		padding-bottom: 0.3rem;
	}
	.search {
		display: grid;
		gap: var(--sp-2);
	}
	.search .eyebrow::before {
		display: none;
	}
	.field {
		position: relative;
	}
	.field svg {
		position: absolute;
		left: 1rem;
		top: 50%;
		width: 1.1rem;
		height: 1.1rem;
		transform: translateY(-50%);
		color: var(--text-mute);
		pointer-events: none;
	}
	.field input {
		width: 100%;
		min-height: 3.1rem;
		padding: 0 1rem 0 2.75rem;
		border: 1px solid var(--line-strong);
		border-radius: var(--r-md);
		background: linear-gradient(90deg, rgb(255 122 26 / 0.07), transparent 60%), var(--bg-1);
		transition:
			border-color var(--dur-2),
			box-shadow var(--dur-2);
		color: var(--text-hi);
		font: inherit;
		font-family: var(--font-mono);
		font-size: var(--fs-sm);
	}
	.field input:hover,
	.field input:focus {
		border-color: var(--heat-3);
		box-shadow: 0 0 0 3px rgb(255 122 26 / 0.15), 0 0 24px -6px rgb(255 122 26 / 0.45);
	}
	.field:focus-within svg {
		color: var(--heat-4);
	}
	.field input::placeholder {
		color: var(--text-mute);
	}
	.field input:focus-visible {
		outline: 2px solid var(--focus);
		outline-offset: 2px;
	}
	.filter-row {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-end;
		justify-content: space-between;
		gap: var(--sp-3) var(--sp-5);
	}
	.count {
		margin: 0;
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	@media (max-width: 64rem) {
		.hero-in {
			grid-template-columns: 1fr;
		}
	}
	@media (max-width: 40rem) {
		.hero {
			padding-top: calc(4.25rem + 0.75rem);
		}
		.hero .lede {
			display: none;
		}
		.search .eyebrow {
			position: absolute;
			width: 1px;
			height: 1px;
			overflow: hidden;
			clip: rect(0 0 0 0);
		}
		.field input {
			min-height: 2.75rem;
		}
		.controls {
			gap: var(--sp-3);
		}
		.filter-row :global(legend) {
			position: absolute;
			width: 1px;
			height: 1px;
			overflow: hidden;
			clip: rect(0 0 0 0);
		}
	}

	/* ---------- vendor groups ---------- */
	.index {
		display: grid;
		gap: clamp(2.5rem, 5vw, 4rem);
		padding: var(--sp-6) 0 var(--section-y);
	}
	.group {
		display: grid;
		gap: var(--sp-4);
	}
	.g-head {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: var(--sp-4);
		padding-bottom: var(--sp-3);
	}
	.g-name {
		margin: 0;
		font-size: clamp(1.75rem, 1rem + 2.4vw, 3rem);
		font-weight: 850;
		font-stretch: 125%;
		letter-spacing: -0.02em;
		line-height: 1;
		color: var(--text-hi);
	}
	.g-meta {
		margin: 0;
		font-size: var(--fs-2xs);
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--text-mute);
		text-align: right;
	}
	ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	/* ---------- measured: compact product tiles ---------- */
	.measured {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(min(100%, 25rem), 1fr));
		gap: var(--sp-3);
	}
	.measured li {
		display: grid;
	}
	/* compact product tile: small render left, identity and numbers right */
	.tile {
		position: relative;
		display: grid;
		grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.2fr);
		align-items: center;
		gap: var(--sp-3) var(--sp-4);
		padding: var(--sp-4);
		border: 1px solid var(--line);
		border-radius: var(--r-lg);
		background:
			radial-gradient(120% 80% at 18% 50%, rgb(255 122 26 / 0.1), transparent 60%),
			radial-gradient(90% 70% at 100% 0%, rgb(226 64 28 / 0.06), transparent 60%),
			linear-gradient(180deg, rgb(17 15 14 / 0.94), rgb(7 7 8 / 0.94));
		overflow: hidden;
		transition: box-shadow var(--dur-3) var(--ease-out);
	}
	/* the measured gain warms the tile from behind the card; hover brings it up */
	.tile::before {
		content: '';
		position: absolute;
		inset: -10% -10% 40%;
		background: radial-gradient(50% 50% at 50% 50%, rgb(255 122 26 / calc(0.12 + var(--th) * 0.3)), transparent 70%);
		opacity: 0.6;
		transition: opacity 0.6s var(--ease-out);
		pointer-events: none;
	}
	.tile:hover::before,
	.tile:focus-within::before {
		opacity: 1;
	}
	.tile:has(.stretch:focus-visible) {
		outline: 2px solid var(--focus);
		outline-offset: 3px;
	}
	.tile-art {
		width: 100%;
		user-select: none;
	}
	.tile-body {
		display: grid;
		gap: 0.3rem;
		min-width: 0;
	}
	.pre {
		display: inline-flex;
		align-items: center;
		gap: 0.45rem;
		margin: 0;
		font-size: var(--fs-2xs);
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.dot {
		width: 0.4rem;
		height: 0.4rem;
		border-radius: 50%;
		background: var(--heat-3);
		box-shadow: 0 0 8px var(--heat-3);
	}
	.tile:is(:hover, :focus-within) .short .stretch {
		color: var(--hx-ink);
	}
	.short .stretch {
		transition: color var(--dur-2);
	}
	.short {
		margin: 0;
		font-size: clamp(1.6rem, 1.2rem + 0.9vw, 2.2rem);
		font-weight: 850;
		font-stretch: 118%;
		line-height: 0.95;
		letter-spacing: -0.035em;
		white-space: nowrap;
		width: fit-content;
	}
	.stretch {
		color: var(--text-hi);
		text-decoration: none;
	}
	.stretch::after {
		content: '';
		position: absolute;
		inset: 0;
		z-index: 1;
	}
	.stretch:focus-visible {
		outline: none;
	}
	.spec {
		margin: 0;
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.stat {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-end;
		justify-content: space-between;
		gap: var(--sp-1) var(--sp-3);
		margin-top: var(--sp-2);
		padding-top: var(--sp-3);
	}
	.x {
		margin: 0;
		display: flex;
		align-items: baseline;
		gap: 0.4rem;
		white-space: nowrap;
	}
	.x .w {
		font-size: var(--fs-sm);
		font-weight: 600;
		color: var(--text);
	}
	.tps {
		margin: 0;
		display: grid;
		justify-items: start;
		gap: 0.15rem;
		font-size: var(--fs-xs);
		color: var(--text-mute);
		white-space: nowrap;
	}
	.tps .m {
		font-size: var(--fs-2xs);
		letter-spacing: 0.04em;
	}
	.hot {
		color: var(--heat-4);
		font-weight: 600;
	}
	.hi {
		color: var(--text-hi);
	}
	.tip {
		position: relative;
		z-index: 2;
		justify-self: start;
		margin-top: var(--sp-2);
	}

	/* ---------- queue: dense typographic tiles ---------- */
	.q-label {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		margin: var(--sp-2) 0 0;
		font-size: var(--fs-2xs);
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text);
	}
	.ring {
		width: 0.45rem;
		height: 0.45rem;
		border-radius: 50%;
		border: 1.5px solid var(--heat-3);
	}
	.queued {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(min(100%, 15rem), 1fr));
		gap: var(--sp-3);
	}
	.queued li {
		display: grid;
	}
	.qtile {
		position: relative;
		display: flex;
		flex-direction: column;
		gap: var(--sp-3);
		padding: var(--sp-4);
		border: 1px dashed rgb(255 122 26 / 0.32);
		border-radius: var(--r-md);
		background:
			radial-gradient(100% 60% at 0% 0%, rgb(255 122 26 / 0.07), transparent 65%),
			linear-gradient(180deg, rgb(14 12 12 / 0.92), rgb(5 5 6 / 0.92));
		transition:
			border-color var(--dur-3),
			box-shadow var(--dur-3),
			transform var(--dur-3) var(--ease-out);
	}
	.qtile:is(:hover, :focus-within) {
		border-color: var(--heat-3);
		box-shadow: 0 18px 44px -24px rgb(255 122 26 / 0.6);
		transform: translateY(-2px);
	}
	.qtile:is(:hover, :focus-within) .q-name .stretch {
		color: var(--hx-ink);
	}
	.qtile:has(.stretch:focus-visible) {
		outline: 2px solid var(--focus);
		outline-offset: 3px;
	}
	.q-id {
		display: grid;
		gap: 0.25rem;
		min-width: 0;
	}
	.q-pre {
		margin: 0;
		font-size: var(--fs-2xs);
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	/* one slot per name: one size, one line, so the spec and estimate rows line up */
	.q-name {
		margin: 0;
		font-size: var(--fs-xl);
		font-weight: 800;
		font-stretch: 112%;
		letter-spacing: -0.03em;
		line-height: 1.05;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.q-name .stretch {
		color: var(--text-hi);
		transition: color var(--dur-2);
	}
	.q-est {
		display: grid;
		gap: var(--sp-2);
		align-content: start;
		margin-top: auto;
		padding-top: var(--sp-3);
		border-top: 1px solid rgb(255 122 26 / 0.22);
	}
	.q-est p {
		margin: 0;
		display: grid;
		gap: 0.15rem;
		font-size: var(--fs-xs);
	}
	.q-est .lbl {
		color: var(--text-mute);
		font-size: var(--fs-2xs);
		letter-spacing: 0.02em;
	}
	.q-row {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-2);
	}

	/* ---------- phones: rows, so several cards fit on one screen ---------- */
	@media (max-width: 40rem) {
		.index {
			padding-top: var(--sp-4);
			gap: var(--sp-8);
		}
		.measured {
			gap: var(--sp-2);
		}
		.tile {
			grid-template-columns: 36% minmax(0, 1fr);
			gap: var(--sp-2) var(--sp-3);
			padding: var(--sp-3);
		}
		.filter-row :global(.caps) {
			flex-wrap: nowrap;
			gap: 0.35rem;
		}
		.filter-row :global(.cap) {
			padding-inline: 0.55rem;
			min-height: 2.5rem;
		}
		.filter-row :global(.cap.on::before) {
			display: none;
		}
		.short {
			font-size: 1.6rem;
		}
		.spec {
			font-size: var(--fs-2xs);
		}
		.stat {
			margin-top: var(--sp-1);
			padding-top: var(--sp-2);
		}
		.tile .tip {
			display: none;
		}
		.queued {
			gap: var(--sp-2);
		}
		.qtile {
			display: grid;
			grid-template-columns: minmax(0, 1fr) minmax(0, 1.1fr);
			gap: var(--sp-3);
			padding: var(--sp-3);
		}
		.q-name {
			font-size: var(--fs-lg);
		}
		.q-est {
			margin: 0;
			padding: 0 0 0 var(--sp-3);
			border-top: 0;
			border-left: 1px solid rgb(255 122 26 / 0.22);
		}
	}

	.empty {
		display: grid;
		justify-items: start;
		gap: var(--sp-6);
		padding: var(--sp-12) 0;
	}
	.legend-note {
		margin: 0;
	}

	/* ---------- compare band ---------- */
	.band {
		padding-bottom: var(--section-y);
	}
	.band-in {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-end;
		justify-content: space-between;
		gap: var(--sp-8);
		padding: clamp(1.5rem, 4vw, 3.5rem);
		overflow: hidden;
	}
	.band .giga {
		margin: 0 0 var(--sp-4);
	}
	.band .lede {
		margin: 0;
	}
</style>
