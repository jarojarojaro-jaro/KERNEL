<script lang="ts">
	/**
	 * One maker's showroom (`/pl/karty/amd/`). The band: the product on a lit floor with its
	 * reflection, a slow light sweep and the maker's hairlines BEHIND it (never over it), pointer
	 * parallax between the layers; the maker's wordmark; the headline result as one strong number
	 * with the model, the card and both measured speeds (makers with nothing measured yet show the
	 * first card in the queue with a labelled estimate, visually muted); a segmented maker switch in
	 * the makers' colours whose indicator slides from page to page (view transition). Below: measured
	 * cards as rich tiles, the queue as quiet estimate rows, the other makers and the versus view.
	 * Identity colour from vendor.ts; speed keeps the heat ramp. Reduced motion: no parallax, no
	 * sweep, no rise-in.
	 */
	import { play, tilt, visible } from '$lib/fx/actions';
	import { reducedMotion } from '$lib/fx/motion';
	import { fmtTps } from '$lib/format';
	import { cardsHref, currentLang, num } from '$lib/i18n';
	import ModelMark from '$lib/ModelMark.svelte';
	import { MODEL_INFO, variantLabel } from '$lib/data/measurements';
	import { cardsCopy } from './copy';
	import { GROUPS, headline, heatOf, LINEUP, MEASURED, queueEstimate, splitName, VENDORS } from './explorer';
	import EstTag from './EstTag.svelte';
	import Hl from '$lib/home/Hl.svelte';
	import GpuArt from './GpuArt.svelte';
	import Ratio from './Ratio.svelte';
	import { MAKER_PHOTO, photoOf, VENDOR, vendorVars, type Vendor } from './vendor';
	import ProductPhoto from './ProductPhoto.svelte';
	import VendorTheme from './VendorTheme.svelte';

	let { vendor }: { vendor: Vendor } = $props();

	const lang = $derived(currentLang());
	const t = $derived(cardsCopy[lang].gallery);
	const tv = $derived(cardsCopy[lang].vendor);
	const tc = $derived(cardsCopy[lang].card);
	const g = $derived(GROUPS[vendor]);
	const name = $derived(VENDOR[vendor].name);
	/* Apple: a quieter, centred, aluminium showroom; nothing measured yet, so a plan instead of a number */
	const apple = $derived(vendor === 'apple');
	const NB = '\u00a0';

	/* the headline: the maker's best measured card and run, else the first card in the queue */
	const faceCard = $derived(MEASURED.find((e) => e.id === g.face.id)?.card ?? null);
	const hd = $derived(faceCard ? headline(faceCard) : null);
	const hdTop = $derived(hd ? Math.max(hd.before.decode!.v, hd.ours.decode!.v) : 1);
	const nextGpu = $derived(g.measured.length ? null : (g.queued[0]?.gpu ?? null));
	const nextEst = $derived(nextGpu ? (queueEstimate(nextGpu)[0] ?? null) : null);

	let hover = $state<string | null>(null);
	let rep = $state(0);
	let onScreen = $state(false);

	/* pointer parallax: the product, the light and the floor move at different depths */
	let band: HTMLElement | undefined = $state();
	let frame = 0;
	function parallax(e: PointerEvent) {
		if (!band || e.pointerType !== 'mouse' || reducedMotion()) return;
		const b = band;
		cancelAnimationFrame(frame);
		frame = requestAnimationFrame(() => {
			const r = b.getBoundingClientRect();
			b.style.setProperty('--px', (((e.clientX - r.left) / r.width) * 2 - 1).toFixed(3));
			b.style.setProperty('--py', (((e.clientY - r.top) / r.height) * 2 - 1).toFixed(3));
		});
	}
	function settle() {
		cancelAnimationFrame(frame);
		band?.style.setProperty('--px', '0');
		band?.style.setProperty('--py', '0');
	}
	$effect(() => () => cancelAnimationFrame(frame));

	/* The versus view opens on this maker's face card against the best card of another maker. */
	const rival = $derived(vendor === 'amd' ? GROUPS.nvidia : GROUPS.amd);
	const cmpHref = $derived.by(() => {
		const a = g.measured.length ? g.face.id : GROUPS.nvidia.face.id;
		return cardsHref(lang, `${lang === 'pl' ? 'porownaj' : 'compare'}/?a=${a}&b=${rival.face.id}`);
	});
	const others = $derived(VENDORS.filter((v) => v !== vendor));
	const prefixOf = (n: string, short: string) => n.split(short)[0].trim();
</script>

<svelte:head>
	<title>{tv.metaTitle(name)}</title>
	<meta name="description" content={tv.metaDescription(name)} />
	<meta property="og:title" content={tv.metaTitle(name)} />
	<meta property="og:description" content={tv.metaDescription(name)} />
</svelte:head>

{#snippet product(eager: boolean)}
	<ProductPhoto id={MAKER_PHOTO[vendor]} sizes="(max-width: 56rem) min(92vw, 34rem), 46vw" {eager}>
		{#snippet fallback()}<GpuArt label={g.face.label} {vendor} vram={g.face.vram} heat={heatOf(g.face.ratio)} live={onScreen} />{/snippet}
	</ProductPhoto>
{/snippet}

<VendorTheme {vendor}>
	<div class="amb" aria-hidden="true"></div>
	<section class="vh vh--{vendor}" class:on={onScreen} aria-labelledby="vendor-title" style="--th:{heatOf(g.best)}" bind:this={band} onpointermove={parallax} onpointerleave={settle} use:visible={(v) => (onScreen = v)}>
		<div class="wrap vh-in">
			<a class="back mono" href={cardsHref(lang)}><span aria-hidden="true">←</span> {tv.back}</a>

			<div class="vh-grid">
				<div class="vh-text">
					<p class="eyebrow">{tv.eyebrow}{NB}· {LINEUP[vendor]}</p>
					<h1 id="vendor-title" class="wm" class:upright={vendor === 'intel' || vendor === 'apple'} style="view-transition-name: vendor-{vendor}">{name}</h1>

					{#if hd && faceCard}
						<div class="res">
							<p class="res-k mono">{tv.best}</p>
							<p class="res-m mono"><ModelMark model={hd.run.model} /> <span>{MODEL_INFO[hd.run.model].name}</span> <span>{hd.run.quant}</span></p>
							{#if hd.ratio}
								<p class="res-x"><Ratio value={hd.ratio} {lang} size="lg" /> <span class="res-w">{t.faster}</span></p>
							{/if}
							<div class="res-bars">
								<p class="rb cold">
									<span class="lb">{variantLabel(hd.run, hd.before.key)[lang]}</span>
									<b>{fmtTps(hd.before.decode!.v, lang)}</b>
									<span class="track"><i style="--w:{(hd.before.decode!.v / hdTop).toFixed(4)}"></i></span>
								</p>
								<p class="rb hot">
									<span class="lb">{variantLabel(hd.run, hd.ours.key)[lang]}</span>
									<b>{fmtTps(hd.ours.decode!.v, lang)}{NB}<small>t/s</small></b>
									<span class="track"><i style="--w:{(hd.ours.decode!.v / hdTop).toFixed(4)}"></i></span>
								</p>
							</div>
							<p class="res-on mono">{tv.measuredOn(faceCard.name)}{#if !hd.run.sameHarness} · {tc.scriptsWarn}{/if}</p>
						</div>
					{:else if nextGpu}
						<div class="res res--est">
							<p class="res-k mono"><span class="ring" aria-hidden="true"></span>{tv.next}</p>
							<p class="est-nm">{nextGpu.name}</p>
							{#if nextEst}
								<p class="est-v"><EstTag text={t.estimateShort} /> <span class="mono">≈{NB}{num(nextEst.decode.lo, lang, 0)}–{num(nextEst.decode.hi, lang, 0)}{NB}t/s · {nextEst.model.name} {nextEst.model.quant}</span></p>
								<p class="res-on">{tv.nextNote}</p>
							{:else}
								<p class="res-on">{tv.planNote}</p>
								<ul class="plan" role="list" aria-label={tv.plan}>
									{#each tv.planItems as p (p)}<li class="mono">{p}</li>{/each}
								</ul>
							{/if}
						</div>
					{/if}

					<p class="lede">{g.measured.length ? tv.lede(name) : apple ? tv.prepLede : tv.noneLede(name)}</p>
				</div>

				<div class="stage" aria-hidden="true" style="view-transition-name: vendor-stage">
					<div class="beam"><span></span></div>
					<div class="lines"><i></i><i></i><i></i></div>
					<div class="floor"></div>
					<div class="prod">{@render product(true)}</div>
					<div class="refl">{@render product(false)}</div>
				</div>
			</div>

			<nav class="seg" aria-label={tv.nav} style="--k:{VENDORS.indexOf(vendor)}">
				<span class="seg-ind" style="{vendorVars(vendor)}; view-transition-name: vendor-seg" aria-hidden="true"></span>
				{#each VENDORS as v (v)}
					<a href={cardsHref(lang, `${v}/`)} class="seg-i" class:on={v === vendor} aria-current={v === vendor ? 'page' : undefined} style={vendorVars(v)}>
						<i aria-hidden="true"></i>{VENDOR[v].name}
					</a>
				{/each}
			</nav>
		</div>
	</section>

	{#if g.measured.length}
		<section class="wrap blk" aria-labelledby="v-measured">
			<header class="blk-h">
				<h2 id="v-measured" class="h hx-h"><Hl text={tv.measured} /></h2>
				<p class="fine">{tv.measuredLede}</p>
			</header>
			<ul class="measured" role="list" use:play={{ threshold: 0.2, onplay: () => rep++ }} class:played={rep > 0}>
				{#each g.measured as e, i (e.id)}
					{@const d = headline(e.card)}
					{@const top = d ? Math.max(d.before.decode!.v, d.ours.decode!.v) : 1}
					{@const ph = photoOf(e.id)}
					<li style="--th:{heatOf(d?.ratio)}; --i:{i}">
						<article class="tile" class:live={hover === e.id} use:tilt={{ max: 4 }} onpointerenter={() => (hover = e.id)} onpointerleave={() => (hover = null)} onfocusin={() => (hover = e.id)} onfocusout={() => (hover = null)}>
							<span class="acc" aria-hidden="true"><i></i><i></i></span>
							<p class="brand mono">
								<span class="maker" class:upright={vendor === 'intel' || vendor === 'apple'}>{name}</span>
								<span class="pre">{prefixOf(e.card.name, e.card.short)}</span>
							</p>
							<div class="t-stage" style="view-transition-name: art-{e.id}; view-transition-class: gpu" aria-hidden="true">
								<span class="sweep"></span>
								<div class="t-art">
									{#if ph}
										<ProductPhoto id={ph} sizes="(max-width: 40rem) 90vw, 26rem">
											{#snippet fallback()}<GpuArt label={e.card.short} vendor={e.card.vendor} vram={e.card.vramGB} heat={heatOf(d?.ratio)} live={hover === e.id} flat />{/snippet}
										</ProductPhoto>
									{:else}
										<GpuArt label={e.card.short} vendor={e.card.vendor} vram={e.card.vramGB} heat={heatOf(d?.ratio)} live={hover === e.id} flat />
									{/if}
								</div>
							</div>
							<div class="id">
								<h3 class="short" style="view-transition-name: name-{e.id}">
									<a class="stretch" href={cardsHref(lang, `${e.id}/`)} aria-label={t.open(e.card.name)}>{e.card.short}</a>
								</h3>
								{#if d?.ratio}<span class="x"><Ratio value={d.ratio} {lang} size="md" replay={rep} /></span>{/if}
							</div>
							<ul class="chips mono" role="list">
								<li><b>{e.card.vramGB}{NB}GB</b> {tv.mem}</li>
								<li><b>{num(e.card.bwGBs.v, lang, 0)}{NB}GB/s</b> {tv.bw}</li>
								<li>{e.card.arch}</li>
							</ul>
							{#if d}
								<div class="bars">
									<p class="model mono"><span class="m"><ModelMark model={d.run.model} /> {MODEL_INFO[d.run.model].name} {d.run.quant}</span><span class="k">{tv.bestModel}</span></p>
									<p class="speed cold">
										<span class="lb">{variantLabel(d.run, d.before.key)[lang]}</span>
										<b>{fmtTps(d.before.decode!.v, lang)}</b>
										<span class="track"><i style="--w:{(d.before.decode!.v / top).toFixed(4)}"></i></span>
									</p>
									<p class="speed hot">
										<span class="lb">{variantLabel(d.run, d.ours.key)[lang]}</span>
										<b>{fmtTps(d.ours.decode!.v, lang)}{NB}<small>t/s</small></b>
										<span class="track"><i style="--w:{(d.ours.decode!.v / top).toFixed(4)}"></i></span>
									</p>
									{#if !d.run.sameHarness}<p class="warn mono">{tc.scriptsWarn}</p>{/if}
								</div>
							{/if}
						</article>
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	{#if g.queued.length}
		<section class="wrap blk blk--q" class:apple aria-labelledby="v-queue">
			<header class="blk-h">
				<h2 id="v-queue" class="h h--q"><span class="ring" aria-hidden="true"></span><span><Hl text={tv.queue} /></span></h2>
				{#if !apple}<EstTag text={t.estimateShort} />{/if}
				<p class="fine">{apple ? tc.soonNoVram : tv.queueLede}</p>
			</header>
			<ul class="queued" role="list">
				{#each g.queued as e (e.id)}
					{@const est = queueEstimate(e.gpu)[0]}
					{@const nm = splitName(e.gpu.name, e.gpu.vendor)}
					<li>
						<a class="qrow" href={cardsHref(lang, `${e.id}/`)} aria-label={t.open(e.gpu.name)}>
							<span class="q-id">
								<span class="q-pre mono">{nm.prefix}</span>
								<span class="q-name" style="view-transition-name: name-{e.id}">{nm.short}</span>
							</span>
							<span class="q-spec mono">{e.gpu.vram ? `${e.gpu.vram}${NB}GB · ` : ''}{num(e.gpu.bw, lang, 0)}{NB}GB/s</span>
							<span class="q-est mono">
								{#if est}
									<span class="v">≈{NB}{num(est.decode.lo, lang, 0)}–{num(est.decode.hi, lang, 0)}{NB}t/s</span>
									<span class="lbl">{t.estimate}</span>
									<span class="lbl">{est.model.name} {est.model.quant}</span>
								{:else}
									<span class="lbl">{t.soon}</span>
								{/if}
							</span>
							<span class="q-go" aria-hidden="true">→</span>
						</a>
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	<section class="wrap more" class:apple aria-labelledby="v-others">
		<div class="vsx">
			<div>
				<h2 id="v-others" class="h hx-h"><Hl text={tv.compareTitle} /></h2>
				<p class="fine">{tv.compareLede}</p>
			</div>
			<a class="cta cta--bone" href={cmpHref}>{t.compareCta} <span class="arrow" aria-hidden="true">→</span></a>
		</div>
		<h2 class="sr-only">{tv.others}</h2>
		<ul class="others" role="list">
			{#each others as v (v)}
				{@const og = GROUPS[v]}
				<li style={vendorVars(v)}>
					<a class="ot" href={cardsHref(lang, `${v}/`)}>
						<span class="ot-wm" class:upright={v === 'intel' || v === 'apple'}>{VENDOR[v].name}</span>
						<span class="ot-c mono">{og.measured.length ? t.vendorMeasured(og.measured.length) : t.vendorNone}{og.queued.length ? ` · ${t.vendorQueued(og.queued.length)}` : ''}</span>
						<span class="ot-a" aria-hidden="true">→</span>
					</a>
				</li>
			{/each}
		</ul>
	</section>
</VendorTheme>

<style>
	/* the explorer's warm embers, in the maker's colour on its page */
	.amb {
		position: fixed;
		inset: 0;
		z-index: -1;
		pointer-events: none;
		background:
			radial-gradient(38vmax 26vmax at 12% 18%, rgb(var(--v) / 0.12), transparent 70%),
			radial-gradient(44vmax 30vmax at 88% 62%, rgb(var(--v) / 0.09), transparent 70%),
			radial-gradient(30vmax 22vmax at 55% 95%, rgb(var(--v) / 0.05), transparent 70%);
		will-change: transform;
	}
	:global(.explorer:has(.amb))::before {
		display: none;
	}
	.wrap {
		width: min(100% - 2 * var(--gutter), 88rem);
		margin-inline: auto;
	}
	.mono {
		font-family: var(--font-mono);
	}
	ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.ring {
		display: inline-block;
		flex: none;
		width: 0.55rem;
		height: 0.55rem;
		border-radius: 50%;
		border: 1.5px dashed currentColor;
	}
	.wm.upright,
	.maker.upright,
	.ot-wm.upright {
		font-style: normal;
	}

	/* ================= the showroom band (dark in both themes) ================= */
	.vh {
		--text-hi: #edeae3;
		--text: #bdb9b1;
		--text-mute: #8e8a83;
		--before: #7d8794;
		--px: 0;
		--py: 0;
		color-scheme: dark;
		position: relative;
		padding: calc(4.25rem + clamp(0.75rem, 2.5vh, 2rem)) 0 clamp(1.5rem, 3.5vw, 2.75rem);
		color: var(--text);
		background:
			radial-gradient(55% 80% at 74% 46%, rgb(var(--v) / 0.34), transparent 72%),
			radial-gradient(45% 60% at 0% 0%, rgb(var(--v) / 0.28), transparent 70%),
			linear-gradient(165deg, rgb(var(--v) / 0.18), transparent 42%),
			linear-gradient(200deg, var(--v-deep), #070708 72%);
		overflow: hidden;
		isolation: isolate;
	}
	/* Apple: the same light as the other makers, in cool silver over brushed aluminium */
	.vh--apple {
		background:
			repeating-linear-gradient(90deg, rgb(255 255 255 / 0.018) 0 1px, transparent 1px 3px),
			radial-gradient(55% 80% at 74% 46%, rgb(236 240 247 / 0.2), transparent 72%),
			radial-gradient(45% 60% at 0% 0%, rgb(232 234 239 / 0.2), transparent 70%),
			linear-gradient(165deg, rgb(232 234 239 / 0.1), transparent 42%),
			linear-gradient(200deg, #18191c, #070708 72%);
	}
	/* a lit edge closes the band */
	.vh::after {
		content: '';
		position: absolute;
		inset: auto 0 0;
		height: 1px;
		background: linear-gradient(90deg, rgb(var(--v)), rgb(var(--v) / 0.3) 60%, transparent);
	}
	.vh-in {
		display: grid;
		gap: var(--sp-3);
	}
	.back {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		width: fit-content;
		min-height: 2.75rem;
		font-size: var(--fs-xs);
		color: var(--text-mute);
		text-decoration: none;
		transition: color var(--dur-2);
	}
	.back:hover {
		color: var(--text-hi);
	}
	.vh-grid {
		display: grid;
		grid-template-columns: minmax(0, 0.92fr) minmax(0, 1.08fr);
		align-items: center;
		gap: var(--sp-6) clamp(1.5rem, 4vw, 4rem);
	}
	.vh-text {
		display: grid;
		gap: var(--sp-5);
		min-width: 0;
		align-content: center;
	}
	.eyebrow {
		margin: 0;
	}
	/* gradient wordmark: the padding is room for the italic overhang (the colour is painted only
	   inside the box), the negative margin keeps the layout */
	.wm {
		margin: -0.05em -0.22em -0.12em -0.05em;
		padding: 0.05em 0.22em 0.12em 0.05em;
		width: fit-content;
		max-width: calc(100% + 0.27em);
		font-family: var(--font-display);
		font-size: clamp(3.25rem, 1rem + 9vw, 9.5rem);
		font-weight: 900;
		font-stretch: 118%;
		font-style: italic;
		letter-spacing: -0.04em;
		line-height: 0.88;
		background: linear-gradient(100deg, #fff 15%, var(--v-hi) 65%, rgb(var(--v)));
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
		filter: drop-shadow(0 0 30px rgb(var(--v) / 0.45));
	}
	.lede {
		margin: 0;
		max-width: 36rem;
		font-size: var(--fs-base);
		color: var(--text);
	}

	/* the headline result: one strong number, the model, both measured speeds */
	.res {
		display: grid;
		gap: var(--sp-3);
		max-width: 34rem;
		padding: var(--sp-4) var(--sp-5) var(--sp-5);
		border-radius: var(--r-lg);
		background: linear-gradient(135deg, rgb(255 255 255 / 0.06), rgb(255 255 255 / 0.015)), rgb(7 7 8 / 0.6);
		box-shadow:
			inset 0 0 0 1px rgb(var(--v) / 0.3),
			inset 0 1px 0 rgb(255 255 255 / 0.08),
			0 30px 60px -40px #000;
	}
	.res-k {
		margin: 0;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.3rem 0.5rem;
		font-size: var(--fs-2xs);
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--text);
	}
	.res-m {
		margin: -0.35rem 0 0;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.1rem 0.45rem;
		font-size: var(--fs-xs);
		color: var(--text-hi);
	}
	.res-m span {
		white-space: nowrap;
	}
	.res-x {
		margin: 0;
		display: flex;
		align-items: baseline;
		gap: 0.6rem;
		line-height: 0.9;
	}
	.res-x :global(.rx--lg) {
		--rx-fs: clamp(3rem, 1.6rem + 3.6vw, 5.25rem);
	}
	.res-w {
		font-size: var(--fs-md);
		font-weight: 650;
		color: var(--text-hi);
	}
	.res-bars {
		display: grid;
		gap: 0.6rem;
	}
	.rb,
	.speed {
		margin: 0;
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		gap: 0.3rem var(--sp-2);
		align-items: baseline;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
	}
	.lb {
		color: var(--text-mute);
	}
	.rb b,
	.speed b {
		font-weight: 600;
		font-variant-numeric: tabular-nums;
		white-space: nowrap;
	}
	.rb b {
		font-size: var(--fs-sm);
	}
	small {
		font-size: 1em;
		color: var(--text-mute);
		font-weight: 400;
	}
	.cold b {
		color: var(--before);
	}
	.hot b {
		color: var(--heat-4);
	}
	.track {
		grid-column: 1 / -1;
		height: 0.45rem;
		border-radius: var(--r-pill);
		background: rgb(255 255 255 / 0.07);
		overflow: hidden;
	}
	.track i {
		display: block;
		height: 100%;
		width: 100%;
		border-radius: inherit;
		transform: scaleX(var(--w));
		transform-origin: 0 50%;
	}
	.cold .track i {
		background: var(--before);
		opacity: 0.7;
	}
	.hot .track i {
		background: var(--heat-ramp-hot);
		box-shadow: 0 0 12px rgb(255 122 26 / 0.6);
	}
	.res-on {
		margin: 0;
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	/* nothing measured yet: the first card in the queue, muted, the estimate labelled */
	.res--est {
		background: rgb(7 7 8 / 0.4);
		box-shadow: inset 0 0 0 1px rgb(255 255 255 / 0.1);
		border: 1px dashed rgb(var(--v) / 0.45);
	}
	.res--est .res-k {
		color: var(--text-mute);
	}
	.est-nm {
		margin: 0;
		font-family: var(--font-display);
		font-size: var(--fs-2xl);
		font-weight: 800;
		font-stretch: 110%;
		letter-spacing: -0.02em;
		line-height: 1.05;
		color: var(--text-hi);
	}
	.est-v {
		margin: 0;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-2) var(--sp-3);
		font-size: var(--fs-xs);
		color: var(--text);
	}

	/* ---------- the product stage: light and lines behind, the product, its reflection ---------- */
	.stage {
		position: relative;
		min-width: 0;
		aspect-ratio: 3 / 2.15;
		display: grid;
		place-items: center;
		user-select: none;
		isolation: isolate;
	}
	.beam,
	.lines,
	.floor,
	.prod,
	.refl {
		position: absolute;
		transition: transform 0.9s var(--ease-out);
	}
	/* the halo and a slow light sweep behind the product */
	.beam {
		z-index: 0;
		inset: -12% -20%;
		background: radial-gradient(42% 46% at 50% 46%, rgb(var(--v) / 0.42), rgb(var(--v) / 0.1) 55%, transparent 72%);
		transform: translate3d(calc(var(--px) * 18px), calc(var(--py) * 12px), 0);
		overflow: hidden;
		mask-image: radial-gradient(60% 60% at 50% 50%, #000 40%, transparent 80%);
	}
	.beam span {
		position: absolute;
		top: -20%;
		bottom: -20%;
		left: 35%;
		width: 22%;
		background: linear-gradient(90deg, transparent, rgb(255 255 255 / 0.16), transparent);
		transform: translate3d(-180%, 0, 0) skewX(-18deg);
	}
	@media (prefers-reduced-motion: no-preference) {
		.vh.on .beam span {
			animation: beam 7.5s var(--ease-in-out) infinite alternate;
		}
	}
	@keyframes beam {
		to {
			transform: translate3d(180%, 0, 0) skewX(-18deg);
		}
	}
	/* the maker's hairlines, raking behind the product */
	.lines {
		z-index: 0;
		inset: -30% -10% -10% 0;
		transform: translate3d(calc(var(--px) * 28px), calc(var(--py) * 18px), 0);
		mask-image: radial-gradient(70% 70% at 60% 40%, #000 30%, transparent 75%);
	}
	.lines i {
		position: absolute;
		top: 0;
		left: 62%;
		width: 2px;
		height: 120%;
		border-radius: 2px;
		background: linear-gradient(180deg, rgb(var(--v) / 0), rgb(var(--v) / 0.9) 40%, rgb(var(--v) / 0));
		box-shadow: 0 0 18px 1px rgb(var(--v) / 0.5);
		transform: rotate(26deg);
		transform-origin: top;
	}
	.lines i:nth-child(2) {
		left: 74%;
		width: 1px;
		opacity: 0.55;
		box-shadow: none;
	}
	.lines i:nth-child(3) {
		left: 82%;
		width: 1px;
		opacity: 0.3;
		box-shadow: none;
	}
	/* the floor: a lit ellipse and a contact shadow under the product */
	.floor {
		z-index: 1;
		left: 6%;
		right: 6%;
		bottom: 6%;
		height: 24%;
		border-radius: 50%;
		background:
			radial-gradient(closest-side, rgb(0 0 0 / 0.75), rgb(0 0 0 / 0.3) 55%, transparent 80%),
			radial-gradient(closest-side, rgb(var(--v) / 0.5), transparent);
		filter: blur(8px);
		transform: translate3d(calc(var(--px) * 6px), 0, 0) scaleY(0.6);
	}
	.prod {
		z-index: 2;
		inset: 0 4% 18%;
		display: grid;
		place-items: center;
		transform: translate3d(calc(var(--px) * -12px), calc(var(--py) * -8px), 0) rotateY(calc(var(--px) * 5deg));
		/* its own layer: pointer parallax moves pixels, it never repaints the photo and its shadow */
		will-change: transform;
	}
	.prod > :global(*),
	.refl > :global(*) {
		width: 100%;
	}
	.prod :global(.glow) {
		background: radial-gradient(closest-side, rgb(var(--v) / calc(0.3 + var(--th) * 0.2)), transparent);
	}
	/* the reflection on the floor: the product mirrored, fading away */
	.refl {
		z-index: 1;
		inset: 64% 4% -46%;
		display: grid;
		place-items: start center;
		opacity: 0.22;
		transform: translate3d(calc(var(--px) * -12px), 0, 0) scaleY(-1);
		mask-image: linear-gradient(0deg, #000, transparent 46%);
		filter: blur(1.5px);
		will-change: transform;
	}
	/* entrances: transform only and short; everything is visible from the first paint */
	@media (prefers-reduced-motion: no-preference) {
		:global(html.js) .wm {
			animation: wm-in 0.6s var(--ease-out) backwards;
		}
		:global(html.js) .stage {
			animation: stage-in 0.7s var(--ease-out) backwards;
		}
		:global(html.js) .res {
			animation: res-in 0.6s var(--ease-out) 0.05s backwards;
		}
	}
	@keyframes wm-in {
		from {
			transform: translate3d(-0.08em, 0, 0) skewX(-4deg);
		}
	}
	@keyframes stage-in {
		from {
			transform: translate3d(4%, 1.5%, 0) scale(0.97);
		}
	}
	@keyframes res-in {
		from {
			transform: translate3d(0, 12px, 0);
		}
	}
	@keyframes rise {
		from {
			opacity: 0;
			transform: translate3d(0, 22px, 0);
		}
	}

	/* ---------- the maker switch: a segmented control in the makers' colours ---------- */
	.seg {
		position: relative;
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		width: min(100%, 34rem);
		margin-top: var(--sp-4);
		padding: 0.3rem;
		border-radius: var(--r-pill);
		background: rgb(0 0 0 / 0.45);
		box-shadow:
			inset 0 0 0 1px rgb(255 255 255 / 0.1),
			inset 0 2px 6px rgb(0 0 0 / 0.5);
	}
	/* the lit segment slides to the new maker on navigation (view transition) */
	.seg-ind {
		position: absolute;
		top: 0.3rem;
		bottom: 0.3rem;
		left: 0.3rem;
		width: calc((100% - 0.6rem) / 4);
		border-radius: var(--r-pill);
		background: linear-gradient(135deg, rgb(var(--v) / 0.75), rgb(var(--v) / 0.35));
		box-shadow:
			inset 0 1px 0 rgb(255 255 255 / 0.25),
			0 0 26px -4px rgb(var(--v) / 0.75);
		transform: translate3d(calc(var(--k) * 100%), 0, 0);
	}
	.seg-i {
		position: relative;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		gap: 0.45rem;
		min-height: 2.6rem;
		padding: 0 0.5rem;
		border-radius: var(--r-pill);
		font-family: var(--font-display);
		font-weight: 750;
		font-size: var(--fs-sm);
		letter-spacing: 0.01em;
		color: var(--text);
		text-decoration: none;
		white-space: nowrap;
		transition:
			color var(--dur-2),
			background-color var(--dur-2);
	}
	.seg-i i {
		flex: none;
		width: 0.5rem;
		height: 0.5rem;
		border-radius: 50%;
		background: rgb(var(--v));
		box-shadow: 0 0 8px rgb(var(--v) / 0.8);
	}
	.seg-i:not(.on):hover {
		color: var(--text-hi);
		background: rgb(var(--v) / 0.14);
	}
	.seg-i.on {
		color: #fff;
	}
	.seg-i.on i {
		background: #fff;
	}
	.seg-i:focus-visible {
		outline: 2px solid var(--focus);
		outline-offset: 2px;
	}

	/* ================= sections ================= */
	.blk {
		display: grid;
		gap: var(--sp-5);
		padding-top: clamp(2.5rem, 6vw, 4.5rem);
	}
	.blk-h {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-2) var(--sp-4);
	}
	.blk-h .fine {
		margin: 0 0 0 auto;
		max-width: 36rem;
	}
	.h {
		margin: 0;
		font-family: var(--font-display);
		font-size: var(--fs-2xl);
		font-weight: 800;
		font-stretch: 110%;
		letter-spacing: -0.02em;
		color: var(--text-hi);
	}
	.h--q {
		display: inline-flex;
		align-items: center;
		gap: 0.6rem;
		font-size: var(--fs-xl);
		color: var(--text);
	}
	.h--q .ring {
		color: var(--text-mute);
	}

	/* ---------- measured: rich showroom tiles ---------- */
	.measured {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(min(100%, 22rem), 1fr));
		gap: var(--sp-4);
	}
	.measured > li {
		display: grid;
		min-width: 0;
	}
	@media (prefers-reduced-motion: no-preference) {
		:global(html.js) .measured > li {
			animation: rise 0.9s var(--ease-spring) backwards;
			animation-delay: calc(200ms + var(--i) * 90ms);
		}
		:global(html.js) .measured .track i {
			transform: scaleX(0);
		}
		:global(html.js) .played .track i {
			transform: scaleX(var(--w));
			transition: transform 1.3s var(--ease-out);
		}
		:global(html.js) .played .hot .track i {
			transition-delay: 0.25s;
		}
	}
	.tile {
		--text-hi: #edeae3;
		--text: #bdb9b1;
		--text-mute: #8e8a83;
		--before: #7d8794;
		color-scheme: dark;
		position: relative;
		display: flex;
		flex-direction: column;
		padding: var(--sp-4) var(--sp-4) var(--sp-5);
		border-radius: var(--r-xl);
		color: var(--text);
		background: var(--v-grad);
		box-shadow:
			inset 0 0 0 1px rgb(var(--v) / 0.32),
			inset 0 1px 0 rgb(255 255 255 / 0.08),
			0 24px 50px -30px rgb(0 0 0 / 0.9);
		overflow: hidden;
		isolation: isolate;
		transition: box-shadow 0.6s var(--ease-out);
	}
	.tile.live,
	.tile:focus-within {
		box-shadow:
			inset 0 0 0 1px rgb(var(--v) / 0.75),
			inset 0 1px 0 rgb(255 255 255 / 0.12),
			0 0 50px -14px rgb(var(--v) / 0.55),
			0 24px 50px -30px rgb(0 0 0 / 0.9);
	}
	.tile:has(.stretch:focus-visible) {
		outline: 2px solid var(--focus);
		outline-offset: 3px;
	}
	/* hairlines in the top corner, fading out above the product */
	.acc {
		position: absolute;
		z-index: -1;
		top: 0;
		right: 0;
		width: 44%;
		height: 4.5rem;
		overflow: hidden;
		pointer-events: none;
		mask-image: linear-gradient(180deg, #000 20%, transparent 100%);
	}
	.acc i {
		position: absolute;
		top: -40%;
		left: 52%;
		width: 2px;
		height: 200%;
		border-radius: 2px;
		background: linear-gradient(180deg, rgb(var(--v) / 0), rgb(var(--v) / 0.95) 45%, rgb(var(--v) / 0.25));
		box-shadow: 0 0 14px 1px rgb(var(--v) / 0.55);
		transform: rotate(32deg);
	}
	.acc i + i {
		left: 70%;
		width: 1px;
		opacity: 0.55;
		box-shadow: none;
	}
	.brand {
		margin: 0;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.2rem 0.55rem;
		min-width: 0;
		font-size: var(--fs-2xs);
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.maker {
		padding-right: 0.15em;
		font-family: var(--font-display);
		font-size: 0.8rem;
		font-weight: 850;
		font-style: italic;
		letter-spacing: 0.06em;
		color: var(--v-hi);
		text-shadow: 0 0 14px rgb(var(--v) / 0.6);
	}
	.t-stage {
		position: relative;
		margin: var(--sp-3) calc(-1 * var(--sp-2));
		user-select: none;
	}
	.t-art {
		position: relative;
		transition: transform 0.8s var(--ease-spring);
	}
	.tile.live .t-art {
		transform: translate3d(0, -3%, 0) scale(1.03);
	}
	.t-stage :global(.glow) {
		background: radial-gradient(closest-side, rgb(var(--v) / calc(0.22 + var(--th) * 0.2)), transparent);
	}
	.sweep {
		position: absolute;
		inset: -30% auto -30% 0;
		width: 30%;
		background: linear-gradient(90deg, transparent, rgb(255 255 255 / 0.12), transparent);
		transform: translate3d(-160%, 0, 0) skewX(-16deg);
		pointer-events: none;
	}
	@media (prefers-reduced-motion: no-preference) {
		.tile.live .sweep {
			transform: translate3d(420%, 0, 0) skewX(-16deg);
			transition: transform 1.1s var(--ease-out);
		}
	}
	.id {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		justify-content: space-between;
		gap: 0 var(--sp-3);
		min-width: 0;
	}
	.short {
		margin: 0;
		font-family: var(--font-display);
		font-size: clamp(1.7rem, 1.2rem + 1vw, 2.4rem);
		font-weight: 850;
		font-stretch: 112%;
		line-height: 1;
		letter-spacing: -0.035em;
	}
	.stretch {
		color: var(--text-hi);
		text-decoration: none;
		transition: color var(--dur-2);
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
	.tile:is(:hover, :focus-within) .stretch {
		color: #fff;
	}
	.x {
		line-height: 1;
	}
	.chips {
		display: flex;
		flex-wrap: wrap;
		gap: 0.35rem;
		margin-top: var(--sp-3);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.chips li {
		padding: 0.25rem 0.55rem;
		border-radius: var(--r-pill);
		background: rgb(255 255 255 / 0.04);
		box-shadow: inset 0 0 0 1px rgb(var(--v) / 0.3);
	}
	.chips b {
		font-weight: 600;
		color: var(--text-hi);
	}
	.bars {
		display: grid;
		gap: 0.55rem;
		margin-top: auto;
		padding-top: var(--sp-4);
	}
	.model {
		margin: 0 0 0.15rem;
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		gap: 0.1rem 0.6rem;
		padding-top: var(--sp-3);
		border-top: 1px solid rgb(var(--v) / 0.22);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.model .m {
		color: var(--text);
	}
	.model .k {
		text-transform: uppercase;
		letter-spacing: 0.08em;
	}
	.warn {
		margin: 0.2rem 0 0;
		font-size: var(--fs-2xs);
		color: var(--text);
	}

	/* ---------- queue: quiet estimate rows, visually secondary ---------- */
	.queued {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(min(100%, 30rem), 1fr));
		gap: 0 var(--sp-6);
	}
	.qrow {
		position: relative;
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto auto;
		grid-template-areas: 'id est go' 'spec est go';
		align-items: center;
		gap: 0.15rem var(--sp-4);
		padding: var(--sp-3) var(--sp-2);
		border-bottom: 1px dashed rgb(var(--v) / 0.28);
		color: var(--text);
		text-decoration: none;
		transition:
			background-color var(--dur-2),
			transform 0.5s var(--ease-spring);
	}
	.qrow:hover {
		background: rgb(var(--v) / 0.06);
		transform: translate3d(3px, 0, 0);
	}
	.qrow:focus-visible {
		outline: 2px solid var(--focus);
		outline-offset: 2px;
	}
	.q-id {
		grid-area: id;
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0 0.5rem;
		min-width: 0;
	}
	.q-pre {
		font-size: var(--fs-2xs);
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.q-name {
		font-family: var(--font-display);
		font-size: var(--fs-lg);
		font-weight: 750;
		font-stretch: 110%;
		letter-spacing: -0.02em;
		color: var(--text);
	}
	.q-spec {
		grid-area: spec;
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.q-est {
		grid-area: est;
		display: grid;
		justify-items: end;
		gap: 0.1rem;
		text-align: right;
		font-size: var(--fs-xs);
	}
	.q-est .v {
		color: var(--text);
	}
	.q-est .lbl {
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.q-go {
		grid-area: go;
		color: var(--text-mute);
		transition: color var(--dur-2);
	}
	.qrow:hover .q-go {
		color: var(--hx-ink);
	}

	/* ---------- the versus view, the other makers ---------- */
	.more {
		display: grid;
		gap: var(--sp-5);
		padding: clamp(3rem, 7vw, 5.5rem) 0 var(--section-y);
	}
	.vsx {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-end;
		justify-content: space-between;
		gap: var(--sp-4) var(--sp-8);
	}
	.vsx .fine {
		margin: var(--sp-2) 0 0;
	}
	.others {
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: var(--sp-3);
	}
	.ot {
		--text-hi: #edeae3;
		--text: #bdb9b1;
		--text-mute: #8e8a83;
		position: relative;
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto;
		gap: 0.2rem var(--sp-3);
		align-items: center;
		padding: var(--sp-4) var(--sp-5);
		border-radius: var(--r-lg);
		background: var(--v-grad);
		box-shadow: inset 0 0 0 1px rgb(var(--v) / 0.3);
		color: var(--text);
		text-decoration: none;
		transition:
			transform 0.6s var(--ease-spring),
			box-shadow 0.4s;
	}
	.ot:is(:hover, :focus-visible) {
		transform: translate3d(0, -4px, 0);
		box-shadow:
			inset 0 0 0 1px rgb(var(--v) / 0.8),
			0 0 40px -14px rgb(var(--v) / 0.6);
	}
	.ot-wm {
		width: fit-content;
		padding: 0.04em 0.2em 0.1em 0.04em;
		margin: -0.04em -0.2em -0.1em -0.04em;
		font-family: var(--font-display);
		font-size: var(--fs-xl);
		font-weight: 900;
		font-style: italic;
		font-stretch: 115%;
		letter-spacing: -0.02em;
		background: linear-gradient(100deg, #fff 10%, var(--v-hi) 80%);
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
	}
	.ot-c {
		grid-column: 1;
		font-size: var(--fs-2xs);
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.ot-a {
		grid-row: 1 / span 2;
		grid-column: 2;
		color: var(--v-hi);
		font-size: var(--fs-lg);
		transition: transform 0.6s var(--ease-spring);
	}
	.ot:is(:hover, :focus-visible) .ot-a {
		transform: translate3d(4px, 0, 0);
	}

	/* maker to maker: the band's colour crossfades, the product slides, the segment glides */
	:global(::view-transition-group(vendor-seg)) {
		animation-duration: 0.35s;
		animation-timing-function: var(--ease-spring);
	}
	:global(::view-transition-old(vendor-stage)) {
		animation: 0.15s ease-in both vs-out;
	}
	:global(::view-transition-new(vendor-stage)) {
		animation: 0.3s var(--ease-out) both vs-in;
	}
	@keyframes -global-vs-out {
		to {
			opacity: 0;
			transform: translate3d(-6%, 0, 0) scale(0.97);
		}
	}
	@keyframes -global-vs-in {
		from {
			transform: translate3d(6%, 0, 0) scale(0.97);
		}
	}

	/* one measured card: a wide tile, the product on the left, the numbers beside it */
	@media (min-width: 48rem) {
		.measured:has(> li:only-child) {
			grid-template-columns: minmax(0, 62rem);
		}
		.measured > li:only-child .tile {
			display: grid;
			grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr);
			grid-template-rows: auto auto auto 1fr;
			column-gap: var(--sp-8);
			padding: var(--sp-6);
		}
		.measured > li:only-child .t-stage {
			grid-column: 1;
			grid-row: 1 / span 4;
			align-self: center;
			margin: 0;
		}
		.measured > li:only-child :is(.brand, .id, .chips, .bars) {
			grid-column: 2;
		}
		.measured > li:only-child .bars {
			align-self: end;
		}
	}
	/* ================= Apple: the same showroom, in silver ================= */
	.vh--apple::after {
		background: linear-gradient(90deg, rgb(232 234 239 / 0.7), rgb(232 234 239 / 0.2) 60%, transparent);
	}
	/* "Apple" is upright and has descenders (pp): room for them in the painted box */
	.vh--apple .wm {
		padding-bottom: 0.28em;
		margin-bottom: -0.28em;
	}
	/* nothing measured, no estimate: what we will measure, as quiet chips */
	.plan {
		list-style: none;
		margin: 0;
		padding: 0;
		display: flex;
		flex-wrap: wrap;
		gap: 0.35rem;
	}
	.plan li {
		padding: 0.25rem 0.6rem;
		border-radius: var(--r-pill);
		box-shadow: inset 0 0 0 1px rgb(var(--v) / 0.35);
		font-size: var(--fs-2xs);
		color: var(--text);
	}
	/* accent words in silver on the Apple page */
	.apple :global(.hx-accent) {
		background: linear-gradient(90deg, #ffffff, #cfd4dc 60%, #9aa1ad);
		-webkit-background-clip: text;
		background-clip: text;
	}
	/* the queue on the Apple page: quiet rows on a silver hairline */
	.blk--q.apple .qrow {
		border-bottom-style: solid;
		border-bottom-color: rgb(232 234 239 / 0.12);
	}

	@media (max-width: 56rem) {
		.vh-grid {
			grid-template-columns: minmax(0, 1fr);
		}
		.stage {
			order: -1;
			width: min(100%, 34rem);
			justify-self: center;
			margin-block: calc(-1 * var(--sp-4)) calc(-1 * var(--sp-6));
		}
		.others {
			grid-template-columns: minmax(0, 1fr);
		}
		.blk-h .fine {
			margin-left: 0;
		}
	}
	@media (max-width: 40rem) {
		.vh {
			padding-top: calc(4.25rem + 0.25rem);
		}
		.vh-text {
			gap: var(--sp-4);
		}
		.res {
			padding: var(--sp-3) var(--sp-4) var(--sp-4);
		}
		.seg {
			width: 100%;
		}
		.seg-i {
			gap: 0.3rem;
			padding: 0 0.25rem;
			font-size: var(--fs-xs);
		}
		.seg-i i {
			width: 0.4rem;
			height: 0.4rem;
		}
		.tile {
			padding: var(--sp-3) var(--sp-3) var(--sp-4);
		}
		.qrow {
			grid-template-columns: minmax(0, 1fr) auto;
			grid-template-areas: 'id go' 'spec go' 'est go';
			gap: 0.2rem var(--sp-3);
		}
		.q-est {
			justify-items: start;
			text-align: left;
			margin-top: 0.2rem;
		}
	}
	@media (max-width: 22rem) {
		.seg-i i {
			display: none;
		}
	}
</style>
