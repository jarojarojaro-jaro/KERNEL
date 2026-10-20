<script lang="ts">
	/**
	 * One maker's page (`/pl/karty/nvidia/`): a dark showroom band in the maker's colour with its
	 * wordmark (it morphs from the block on the front page), the face card's render, the measured and
	 * queued counts and the best measured gain; then the measured cards as showroom tiles (render,
	 * speed-up, before and after on one scale) and the cards in the measurement queue as quieter,
	 * dashed tiles whose numbers are labelled estimates. The other makers and the versus view close
	 * the page. Identity colour from vendor.ts; speed keeps the heat ramp.
	 */
	import { play, tilt } from '$lib/fx/actions';
	import { fmtTps } from '$lib/format';
	import { cardsHref, currentLang, num } from '$lib/i18n';
	import { MODEL_STYLE } from '$lib/modelStyle';
	import { variantLabel } from '$lib/data/measurements';
	import { cardsCopy } from './copy';
	import { GROUPS, headline, heatOf, LINEUP, MEASURED, queueEstimate, splitName, VENDORS } from './explorer';
	import EstTag from './EstTag.svelte';
	import GpuArt from './GpuArt.svelte';
	import Ratio from './Ratio.svelte';
	import { VENDOR, vendorVars, type Vendor } from './vendor';
	import VendorTheme from './VendorTheme.svelte';

	let { vendor }: { vendor: Vendor } = $props();

	const lang = $derived(currentLang());
	const t = $derived(cardsCopy[lang].gallery);
	const tv = $derived(cardsCopy[lang].vendor);
	const tc = $derived(cardsCopy[lang].card);
	const g = $derived(GROUPS[vendor]);
	const name = $derived(VENDOR[vendor].name);
	const NB = '\u00a0';

	let hover = $state<string | null>(null);
	let rep = $state(0);

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

<VendorTheme {vendor}>
	<div class="amb" aria-hidden="true"></div>
	<section class="vh vh--{vendor}" aria-labelledby="vendor-title" style="--th:{heatOf(g.best)}">
		<div class="wrap vh-in">
			<a class="back mono" href={cardsHref(lang)}><span aria-hidden="true">←</span> {tv.back}</a>
			<div class="vh-grid">
				<div class="vh-text">
					<p class="eyebrow">{tv.eyebrow}{NB}· {LINEUP[vendor]}</p>
					<h1 id="vendor-title" class="wm" style="view-transition-name: vendor-{vendor}">{name}</h1>
					<p class="lede">{g.measured.length ? tv.lede(name) : tv.noneLede(name)}</p>
					<div class="stats">
						{#if g.best}
							<p class="st st--gain"><span class="up">{t.upTo}</span> <Ratio value={g.best} {lang} size="lg" /> <span class="up">{t.faster}</span></p>
						{/if}
						<p class="st mono">
							{#if g.measured.length}<span class="c-m"><i class="dot"></i>{t.vendorMeasured(g.measured.length)}</span>{:else}<span>{t.vendorNone}</span>{/if}
							{#if g.queued.length}<span><i class="ring"></i>{t.vendorQueued(g.queued.length)}</span>{/if}
						</p>
					</div>
				</div>
				<div class="vh-art" aria-hidden="true">
					<GpuArt label={g.face.label} vendor={vendor} vram={g.face.vram} heat={heatOf(g.face.ratio)} ignite live />
				</div>
			</div>
			<nav class="switch" aria-label={tv.nav}>
				{#each VENDORS as v (v)}
					<a href={cardsHref(lang, `${v}/`)} class="sw" class:on={v === vendor} aria-current={v === vendor ? 'page' : undefined} style={vendorVars(v)}><i></i>{VENDOR[v].name}</a>
				{/each}
			</nav>
		</div>
	</section>

	{#if g.measured.length}
		<section class="wrap blk" aria-labelledby="v-measured">
			<header class="blk-h">
				<h2 id="v-measured" class="h hx-h">{tv.measured}</h2>
				<p class="fine">{tv.measuredLede}</p>
			</header>
			<ul class="measured" role="list" use:play={{ threshold: 0.25, onplay: () => rep++ }} class:played={rep > 0}>
				{#each g.measured as e, i (e.id)}
					{@const d = headline(e.card)}
					{@const top = d ? Math.max(d.before.decode!.v, d.ours.decode!.v) : 1}
					<li style="--th:{heatOf(d?.ratio)}; --i:{i}">
						<article class="tile" class:live={hover === e.id} use:tilt={{ max: 4 }} onpointerenter={() => (hover = e.id)} onpointerleave={() => (hover = null)} onfocusin={() => (hover = e.id)} onfocusout={() => (hover = null)}>
							<p class="brand mono">
								<span class="maker">{name}</span>
								<span class="pre">{prefixOf(e.card.name, e.card.short)}</span>
								<span class="vram">{e.card.vramGB}{NB}GB</span>
							</p>
							<div class="stage" style="view-transition-name: art-{e.id}; view-transition-class: gpu" aria-hidden="true">
								<GpuArt label={e.card.short} vendor={e.card.vendor} vram={e.card.vramGB} heat={heatOf(d?.ratio)} live={hover === e.id} flat />
								<span class="sweep"></span>
							</div>
							<div class="id">
								<h3 class="short" style="view-transition-name: name-{e.id}">
									<a class="stretch" href={cardsHref(lang, `${e.id}/`)} aria-label={t.open(e.card.name)}>{e.card.short}</a>
								</h3>
								{#if d?.ratio}<span class="x"><Ratio value={d.ratio} {lang} size="md" replay={rep} /></span>{/if}
							</div>
							<p class="spec mono"><span>{e.card.arch}</span><span>{num(e.card.bwGBs.v, lang, 0)}{NB}GB/s</span></p>
							{#if d}
								<div class="bars">
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
									<p class="model mono"><span class="m">{MODEL_STYLE[d.run.model].short} {d.run.quant}</span>{#if !d.run.sameHarness}<span>{tc.scriptsWarn}</span>{/if}</p>
								</div>
							{/if}
						</article>
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	{#if g.queued.length}
		<section class="wrap blk blk--q" aria-labelledby="v-queue">
			<header class="blk-h">
				<h2 id="v-queue" class="h h--q"><span class="ring" aria-hidden="true"></span>{tv.queue}</h2>
				<p class="fine">{tv.queueLede}</p>
			</header>
			<ul class="queued" role="list">
				{#each g.queued as e (e.id)}
					{@const est = queueEstimate(e.gpu)[0]}
					{@const nm = splitName(e.gpu.name, e.gpu.vendor)}
					<li>
						<article class="qtile">
							<div class="q-id">
								<p class="q-pre mono">{nm.prefix}</p>
								<h3 class="q-name" style="view-transition-name: name-{e.id}">
									<a href={cardsHref(lang, `${e.id}/`)} class="stretch" aria-label={t.open(e.gpu.name)}>{nm.short}</a>
								</h3>
								<p class="q-spec mono">{e.gpu.vram ? `${e.gpu.vram}${NB}GB · ` : ''}{num(e.gpu.bw, lang, 0)}{NB}GB/s</p>
							</div>
							<div class="q-est">
								{#if est}
									<EstTag text={t.estimateShort} />
									<p class="mono"><span class="v">≈{NB}{num(est.decode.lo, lang, 0)}–{num(est.decode.hi, lang, 0)}{NB}t/s</span><span class="lbl">{t.estimate} · {est.model.name} {est.model.quant}</span></p>
								{:else}
									<p class="mono"><span class="lbl">{t.soon}</span></p>
								{/if}
							</div>
						</article>
					</li>
				{/each}
			</ul>
		</section>
	{/if}

	<section class="wrap more" aria-labelledby="v-others">
		<h2 id="v-others" class="h hx-h">{tv.others}</h2>
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
		<a class="cta cta--bone vs-cta" href={cmpHref}>{t.compareCta} <span class="arrow" aria-hidden="true">→</span></a>
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

	/* ---------- the maker's showroom band (dark in both themes) ---------- */
	.vh {
		--text-hi: #edeae3;
		--text: #bdb9b1;
		--text-mute: #8e8a83;
		color-scheme: dark;
		position: relative;
		padding: calc(4.25rem + clamp(1rem, 3vh, 2.5rem)) 0 clamp(1.75rem, 4vw, 3rem);
		color: var(--text);
		background:
			radial-gradient(60% 90% at 78% 40%, rgb(var(--v) / 0.3), transparent 70%),
			radial-gradient(50% 70% at 0% 0%, rgb(var(--v) / 0.32), transparent 70%),
			linear-gradient(160deg, rgb(var(--v) / 0.22), transparent 45%),
			linear-gradient(200deg, var(--v-deep), #070708 70%);
		overflow: hidden;
		isolation: isolate;
	}
	.vh--apple {
		background:
			repeating-linear-gradient(90deg, rgb(255 255 255 / 0.016) 0 1px, transparent 1px 3px),
			radial-gradient(60% 90% at 78% 40%, rgb(var(--v) / 0.22), transparent 70%),
			radial-gradient(50% 70% at 0% 0%, rgb(232 234 239 / 0.22), transparent 70%),
			linear-gradient(200deg, #17181b, #070708 70%);
	}
	/* the maker's diagonal accent, large, behind the render; a lit edge closes the band */
	.vh::before {
		content: '';
		position: absolute;
		z-index: -1;
		top: -20%;
		right: -8%;
		width: 60%;
		height: 140%;
		background: linear-gradient(115deg, transparent 0 40%, rgb(var(--v) / 0.3) 40% 42%, transparent 42% 47%, rgb(var(--v) / 0.14) 47% 48%, transparent 48%);
		pointer-events: none;
	}
	.vh::after {
		content: '';
		position: absolute;
		inset: auto 0 0;
		height: 1px;
		background: linear-gradient(90deg, rgb(var(--v)), rgb(var(--v) / 0.3) 60%, transparent);
	}
	.vh-in {
		display: grid;
		gap: var(--sp-4);
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
		grid-template-columns: minmax(0, 1fr) minmax(0, 0.95fr);
		align-items: center;
		gap: var(--sp-6) clamp(1.5rem, 4vw, 4rem);
	}
	.vh-text {
		display: grid;
		gap: var(--sp-4);
		min-width: 0;
	}
	.eyebrow {
		margin: 0;
	}
	.wm {
		margin: 0;
		width: fit-content;
		max-width: 100%;
		font-family: var(--font-display);
		font-size: clamp(3.4rem, 1rem + 11vw, 10.5rem);
		font-weight: 900;
		font-stretch: 118%;
		font-style: italic;
		letter-spacing: -0.04em;
		line-height: 0.88;
		padding-right: 0.08em;
		background: linear-gradient(100deg, #fff 15%, var(--v-hi) 70%, rgb(var(--v)));
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
		filter: drop-shadow(0 0 30px rgb(var(--v) / 0.45));
	}
	.vh--intel .wm,
	.vh--apple .wm {
		font-style: normal;
	}
	@media (prefers-reduced-motion: no-preference) {
		:global(html.js) .wm {
			animation: wm-in 1s var(--ease-spring) backwards;
		}
		:global(html.js) .vh-art {
			animation: art-in 1.2s var(--ease-spring) 0.12s backwards;
		}
	}
	@keyframes wm-in {
		from {
			transform: translate3d(-0.15em, 0, 0) skewX(-6deg);
		}
	}
	@keyframes art-in {
		from {
			opacity: 0;
			transform: translate3d(14%, 4%, 0) rotate(-4deg) scale(0.92);
		}
	}
	.lede {
		margin: 0;
		max-width: 38rem;
		font-size: var(--fs-md);
		color: var(--text);
	}
	.stats {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-end;
		gap: var(--sp-3) var(--sp-8);
	}
	.st {
		margin: 0;
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.3rem 1rem;
		font-size: var(--fs-2xs);
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.st > span {
		display: inline-flex;
		align-items: center;
		gap: 0.45rem;
		white-space: nowrap;
	}
	.st--gain {
		align-items: baseline;
		gap: 0 0.5rem;
		letter-spacing: 0;
		text-transform: none;
		line-height: 1;
	}
	.up {
		font-size: var(--fs-md);
		font-weight: 600;
		color: var(--text);
	}
	.c-m {
		color: var(--text);
	}
	.dot,
	.ring {
		display: inline-block;
		width: 0.5rem;
		height: 0.5rem;
		border-radius: 50%;
		flex: none;
	}
	.dot {
		background: var(--v-hi);
		box-shadow: 0 0 10px rgb(var(--v) / 0.9);
	}
	.ring {
		border: 1.5px dashed currentColor;
	}
	.vh-art {
		position: relative;
		min-width: 0;
		user-select: none;
	}
	.vh-art :global(.glow) {
		background: radial-gradient(closest-side, rgb(var(--v) / calc(0.3 + var(--th) * 0.2)), transparent);
	}
	.switch {
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-2);
		margin-top: var(--sp-2);
	}
	.sw {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		min-height: 2.5rem;
		padding: 0 1rem;
		border-radius: var(--r-pill);
		background: rgb(255 255 255 / 0.04);
		box-shadow: inset 0 0 0 1px rgb(255 255 255 / 0.12);
		font-family: var(--font-display);
		font-weight: 750;
		font-size: var(--fs-sm);
		letter-spacing: 0.02em;
		color: var(--text);
		text-decoration: none;
		transition:
			background-color var(--dur-2),
			box-shadow var(--dur-2),
			color var(--dur-2),
			transform 0.5s var(--ease-spring);
	}
	.sw i {
		width: 0.55rem;
		height: 0.55rem;
		border-radius: 50%;
		background: rgb(var(--v));
		box-shadow: 0 0 8px rgb(var(--v) / 0.8);
	}
	.sw:hover {
		color: var(--text-hi);
		transform: translate3d(0, -2px, 0);
		box-shadow: inset 0 0 0 1px rgb(var(--v) / 0.7);
	}
	.sw.on {
		color: #fff;
		background: linear-gradient(135deg, rgb(var(--v) / 0.5), rgb(var(--v) / 0.18));
		box-shadow: inset 0 0 0 1px rgb(var(--v) / 0.9), 0 0 24px -6px rgb(var(--v) / 0.7);
	}

	/* ---------- sections ---------- */
	.blk {
		display: grid;
		gap: var(--sp-5);
		padding-top: clamp(2.5rem, 6vw, 4.5rem);
	}
	.blk-h {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		justify-content: space-between;
		gap: var(--sp-2) var(--sp-6);
	}
	.blk-h .fine {
		margin: 0;
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
		width: 0.65rem;
		height: 0.65rem;
		color: var(--text-mute);
	}
	ul {
		list-style: none;
		margin: 0;
		padding: 0;
	}

	/* ---------- measured: showroom tiles ---------- */
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
	}
	@keyframes rise {
		from {
			opacity: 0;
			transform: translate3d(0, 24px, 0);
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
	.tile::before {
		content: '';
		position: absolute;
		z-index: -1;
		top: -30%;
		right: -18%;
		width: 55%;
		height: 70%;
		background: linear-gradient(115deg, transparent 0 38%, rgb(var(--v) / 0.42) 38% 41%, transparent 41% 47%, rgb(var(--v) / 0.2) 47% 48.5%, transparent 48.5%);
		pointer-events: none;
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
	.brand {
		margin: 0;
		display: flex;
		align-items: center;
		gap: 0.55rem;
		min-width: 0;
		font-size: var(--fs-2xs);
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-mute);
		white-space: nowrap;
	}
	.maker {
		font-family: var(--font-display);
		font-size: 0.8rem;
		font-weight: 850;
		font-style: italic;
		letter-spacing: 0.06em;
		color: var(--v-hi);
		text-shadow: 0 0 14px rgb(var(--v) / 0.6);
	}
	.pre {
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.vram {
		margin-left: auto;
		padding: 0.2rem 0.5rem;
		border-radius: var(--r-pill);
		box-shadow: inset 0 0 0 1px rgb(var(--v) / 0.45);
		color: var(--text);
		letter-spacing: 0.06em;
	}
	.stage {
		position: relative;
		margin: var(--sp-3) calc(-1 * var(--sp-2));
		user-select: none;
		transition: transform 0.8s var(--ease-spring);
	}
	.tile.live .stage {
		transform: translate3d(0, -3%, 0) scale(1.03);
	}
	.stage :global(.glow) {
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
		align-items: baseline;
		justify-content: space-between;
		gap: var(--sp-3);
		min-width: 0;
	}
	.short {
		margin: 0;
		font-family: var(--font-display);
		font-size: clamp(1.7rem, 1.2rem + 1vw, 2.4rem);
		font-weight: 850;
		font-stretch: 112%;
		line-height: 0.95;
		letter-spacing: -0.035em;
		white-space: nowrap;
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
		line-height: 0.9;
	}
	.spec {
		margin: 0.4rem 0 var(--sp-4);
		display: flex;
		justify-content: space-between;
		gap: var(--sp-3);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.bars {
		display: grid;
		gap: 0.55rem;
		margin-top: auto;
		padding-top: var(--sp-3);
		border-top: 1px solid rgb(var(--v) / 0.22);
	}
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
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		color: var(--text-mute);
	}
	.speed b {
		font-weight: 600;
		font-variant-numeric: tabular-nums;
	}
	.speed small {
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
		height: 0.4rem;
		border-radius: var(--r-pill);
		background: rgb(255 255 255 / 0.06);
		overflow: hidden;
	}
	.track i {
		display: block;
		height: 100%;
		width: calc(var(--w) * 100%);
		border-radius: inherit;
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
	@media (prefers-reduced-motion: no-preference) {
		:global(html.js) .measured .track i {
			transform: scaleX(0);
		}
		:global(html.js) .played .track i {
			transform: none;
			transition: transform 1.3s var(--ease-out);
		}
		:global(html.js) .played .hot .track i {
			transition-delay: 0.25s;
		}
	}
	.model {
		margin: 0.15rem 0 0;
		display: flex;
		flex-wrap: wrap;
		gap: 0.1rem 0.6rem;
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.model .m {
		color: var(--text);
	}

	/* ---------- queue: quieter, dashed, numbers labelled as estimates ---------- */
	.blk--q {
		gap: var(--sp-4);
	}
	.queued {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(min(100%, 16rem), 1fr));
		gap: var(--sp-3);
	}
	.queued > li {
		display: grid;
	}
	.qtile {
		--text-hi: #edeae3;
		--text: #bdb9b1;
		--text-mute: #8e8a83;
		color-scheme: dark;
		position: relative;
		display: flex;
		flex-direction: column;
		gap: var(--sp-3);
		padding: var(--sp-4);
		border: 1px dashed rgb(var(--v) / 0.38);
		border-radius: var(--r-lg);
		color: var(--text);
		background:
			radial-gradient(100% 70% at 0% 0%, rgb(var(--v) / 0.1), transparent 65%),
			linear-gradient(180deg, #0e0e10, #070708);
		transition:
			border-color var(--dur-3),
			box-shadow var(--dur-3),
			transform 0.6s var(--ease-spring);
	}
	.qtile:is(:hover, :focus-within) {
		border-color: rgb(var(--v) / 0.8);
		box-shadow: 0 18px 44px -24px rgb(var(--v) / 0.55);
		transform: translate3d(0, -3px, 0);
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
	.q-pre,
	.q-spec {
		margin: 0;
		font-size: var(--fs-2xs);
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.q-spec {
		letter-spacing: 0.02em;
		text-transform: none;
	}
	.q-name {
		margin: 0;
		font-family: var(--font-display);
		font-size: var(--fs-xl);
		font-weight: 800;
		font-stretch: 112%;
		letter-spacing: -0.03em;
		line-height: 1.05;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.q-est {
		display: grid;
		gap: var(--sp-2);
		align-content: start;
		justify-items: start;
		margin-top: auto;
		padding-top: var(--sp-3);
		border-top: 1px dashed rgb(var(--v) / 0.25);
	}
	.q-est p {
		margin: 0;
		display: grid;
		gap: 0.15rem;
		font-size: var(--fs-xs);
	}
	.q-est .v {
		color: var(--text);
	}
	.q-est .lbl {
		color: var(--text-mute);
		font-size: var(--fs-2xs);
	}

	/* ---------- the other makers, the versus view ---------- */
	.more {
		display: grid;
		gap: var(--sp-5);
		padding: clamp(3rem, 7vw, 5.5rem) 0 var(--section-y);
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
		overflow: hidden;
		transition:
			transform 0.6s var(--ease-spring),
			box-shadow 0.4s;
	}
	.ot:is(:hover, :focus-visible) {
		transform: translate3d(0, -4px, 0);
		box-shadow: inset 0 0 0 1px rgb(var(--v) / 0.8), 0 0 40px -14px rgb(var(--v) / 0.6);
	}
	.ot-wm {
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
	.ot-wm.upright {
		font-style: normal;
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
	.vs-cta {
		justify-self: start;
	}

	@media (max-width: 52rem) {
		.vh-grid {
			grid-template-columns: minmax(0, 1fr);
		}
		.vh-art {
			order: -1;
			width: min(100%, 26rem);
			justify-self: center;
			margin-bottom: calc(-1 * var(--sp-4));
		}
		.others {
			grid-template-columns: minmax(0, 1fr);
		}
	}
	@media (max-width: 40rem) {
		.vh {
			padding-top: calc(4.25rem + 0.5rem);
		}
		.vh-in {
			gap: var(--sp-3);
		}
		.vh-art {
			width: min(82%, 20rem);
		}
		.lede {
			font-size: var(--fs-base);
		}
		.up {
			font-size: var(--fs-sm);
		}
		.switch {
			display: grid;
			grid-template-columns: repeat(4, minmax(0, 1fr));
			gap: 0.35rem;
		}
		.sw {
			justify-content: center;
			gap: 0.35rem;
			padding: 0 0.4rem;
			font-size: var(--fs-xs);
		}
		.sw i {
			width: 0.45rem;
			height: 0.45rem;
		}
		.tile {
			padding: var(--sp-3) var(--sp-3) var(--sp-4);
		}
	}
</style>
