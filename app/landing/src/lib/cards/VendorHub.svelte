<script lang="ts">
	/**
	 * The explorer's front page: one question on one line, and right under it the four makers as
	 * showroom blocks in their own colours (NVIDIA green, AMD red, Intel blue, Apple silver: identity
	 * only, speed stays on the heat ramp). Each block shows the maker's face card (its best measured
	 * gain, else the first card in the queue), how many cards are measured and queued, and opens the
	 * maker page. Search across every card stays below for people who know their model. A versus
	 * band (NVIDIA green against AMD red) opens the compare view on the two makers' best cards.
	 *
	 * Motion: blocks rise in on a spring, on hover they lift, the render floats and its fans spin,
	 * a light sweep crosses the block. Transforms and opacity only; reduced motion: all static.
	 */
	import { tilt } from '$lib/fx/actions';
	import { fmtTps } from '$lib/format';
	import { cardsHref, currentLang, href, num } from '$lib/i18n';
	import { cardsCopy } from './copy';
	import { ENTRIES, entryVendor, GROUPS, headline, heatOf, LINEUP, matches, MEASURED, QUEUED, splitName, VENDORS, type Entry } from './explorer';
	import EstTag from './EstTag.svelte';
	import GpuArt from './GpuArt.svelte';
	import Ratio from './Ratio.svelte';
	import ProductPhoto from './ProductPhoto.svelte';
	import { MAKER_PHOTO, photoOf, VENDOR, vendorVars } from './vendor';

	const lang = $derived(currentLang());
	const t = $derived(cardsCopy[lang].gallery);
	const tv = $derived(cardsCopy[lang].vendor);
	const NB = '\u00a0';

	let hover = $state<string | null>(null);
	let q = $state('');
	const hits = $derived(q.trim() ? ENTRIES.filter((e) => matches(e, q)) : []);
	const name = (e: Entry) => (e.kind === 'measured' ? e.card.name : e.gpu.name);

	/* versus band: the two makers' face cards (both measured) */
	const A = GROUPS.nvidia.face;
	const B = GROUPS.amd.face;
	const vsVars = `--a:${VENDOR.nvidia.rgb}; --a-hi:${VENDOR.nvidia.hi}; --b:${VENDOR.amd.rgb}; --b-hi:${VENDOR.amd.hi}`;
	const cmpHref = $derived(cardsHref(lang, `${lang === 'pl' ? 'porownaj' : 'compare'}/?a=${A.id}&b=${B.id}`));
	const faceShort = (id: string) => MEASURED.find((e) => e.id === id)!.card.short;
	const faceSpeed = (id: string) => headline(MEASURED.find((e) => e.id === id)!.card)?.ours.decode?.v ?? null;
</script>

<section class="hero" aria-labelledby="cards-title">
	<div class="wrap">
		<p class="eyebrow">{t.eyebrow}{NB}· {t.measuredCount(MEASURED.length)}{NB}· {t.queuedCount(QUEUED.length)}</p>
		<h1 id="cards-title" class="title hx-h" style="--chars:{t.title.length}">{t.title}</h1>

		<nav class="makers" aria-label={tv.nav}>
			<ul role="list">
				{#each VENDORS as v, i (v)}
					{@const g = GROUPS[v]}
					<li class="mk mk--{v}" style="{vendorVars(v)}; --i:{i}; --th:{heatOf(g.best)}">
						<a class="mk-tile" href={cardsHref(lang, `${v}/`)} use:tilt={{ max: 4 }} onpointerenter={() => (hover = v)} onpointerleave={() => (hover = null)} onfocus={() => (hover = v)} onblur={() => (hover = null)}>
							<span class="acc" aria-hidden="true"><i></i><i></i></span>
							<div class="mk-top">
								<span class="wm" style="view-transition-name: vendor-{v}">{VENDOR[v].name}</span>
								<span class="line mono">{LINEUP[v]}</span>
							</div>
							<div class="stage" aria-hidden="true">
								<span class="sweep"></span>
								<div class="art">
									<ProductPhoto id={MAKER_PHOTO[v]} sizes="(max-width: 40rem) 46vw, (max-width: 64rem) 46vw, 24rem" eager>
										{#snippet fallback()}<GpuArt label={g.face.label} vendor={v} vram={g.face.vram} heat={heatOf(g.face.ratio)} live={hover === v} flat />{/snippet}
									</ProductPhoto>
								</div>
							</div>
							<div class="mk-foot">
								<span class="gain">
									{#if g.best}
										<span class="up">{t.upTo}</span> <Ratio value={g.best} {lang} size="md" /> <span class="up">{t.faster}</span>
									{:else}
										<span class="none">{t.vendorNone}</span>
									{/if}
								</span>
								<span class="counts mono">
									{#if g.measured.length}<span class="c-m"><i class="dot"></i>{t.vendorMeasured(g.measured.length)}</span>{/if}
									{#if g.queued.length}<span class="c-q"><i class="ring"></i>{t.vendorQueued(g.queued.length)}</span>{/if}
								</span>
								<span class="go"><span class="go-l">{t.enter}</span><span class="arr" aria-hidden="true">→</span></span>
							</div>
						</a>
					</li>
				{/each}
			</ul>
		</nav>

		<div class="below">
			<p class="lede">{t.lede}</p>
			<div class="search">
				<label for="card-q" class="sr-only">{t.search}</label>
				<div class="field">
					<svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="8.5" cy="8.5" r="5.5" fill="none" stroke="currentColor" stroke-width="1.6" /><path d="m13 13 4 4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" /></svg>
					<input id="card-q" type="search" bind:value={q} placeholder={t.searchPh} autocomplete="off" spellcheck="false" aria-describedby="card-count" />
				</div>
				<p class="count mono" id="card-count" role="status">{q.trim() ? t.results(hits.length, ENTRIES.length) : ''}</p>
			</div>
		</div>

		{#if q.trim()}
			{#if hits.length}
				<ul class="hits" role="list">
					{#each hits as e (e.id)}
						{@const v = entryVendor(e)}
						{@const nm = e.kind === 'measured' ? { prefix: e.card.name.split(e.card.short)[0].trim(), short: e.card.short } : splitName(e.gpu.name, e.gpu.vendor)}
						{@const vram = e.kind === 'measured' ? e.card.vramGB : e.gpu.vram}
						{@const d = e.kind === 'measured' ? headline(e.card) : null}
						<li style={vendorVars(v)}>
							<a class="hit" class:est={e.kind === 'queued'} href={cardsHref(lang, `${e.id}/`)} aria-label={t.open(name(e))}>
								<span class="h-id"><span class="h-pre mono">{nm.prefix}</span><span class="h-nm">{nm.short}</span></span>
								<span class="h-spec mono">{vram ? `${vram}${NB}GB` : ''}</span>
								<span class="h-st">
									{#if d?.ratio}
										<Ratio value={d.ratio} {lang} size="sm" /><span class="h-sub mono">{fmtTps(d.ours.decode!.v, lang)}{NB}t/s</span>
									{:else if e.kind === 'measured'}
										<span class="h-sub mono">{t.measuredShort}</span>
									{:else}
										<span class="h-sub mono">{t.queuedShort}</span>
									{/if}
								</span>
							</a>
						</li>
					{/each}
				</ul>
			{:else}
				<div class="empty">
					<p class="h-empty">{t.empty}</p>
					<a class="cta cta--bone" href={href(lang, '/start')}>{t.emptyCta} <span class="arrow" aria-hidden="true">→</span></a>
				</div>
			{/if}
		{/if}
	</div>
</section>

<section class="wrap vsb" aria-labelledby="cmp-title" style={vsVars}>
	<div class="vsb-in">
		<div class="vsb-side vsb-a" aria-hidden="true">
			<span class="vsb-wm">{VENDOR.nvidia.name}</span>
			<div class="vsb-art">
				{#if photoOf(A.id)}<ProductPhoto id={photoOf(A.id)!} sizes="(max-width: 64rem) 45vw, 22rem" />{:else}<GpuArt label={A.label} vendor="nvidia" vram={A.vram} heat={heatOf(A.ratio)} flat />{/if}
			</div>
			<span class="vsb-nm">{faceShort(A.id)}</span>
			{#if faceSpeed(A.id)}<span class="vsb-v mono">{fmtTps(faceSpeed(A.id)!, lang)}{NB}t/s</span>{/if}
		</div>
		<div class="vsb-mid">
			<span class="vsb-vs" aria-hidden="true">VS</span>
			<h2 id="cmp-title" class="vsb-t">{t.compareTitle}</h2>
			<p class="vsb-l">{t.compareLede}</p>
			<a class="cta cta--bone" href={cmpHref}>{t.compareCta} <span class="arrow" aria-hidden="true">→</span></a>
		</div>
		<div class="vsb-side vsb-b" aria-hidden="true">
			<span class="vsb-wm">{VENDOR.amd.name}</span>
			<div class="vsb-art">
				{#if photoOf(B.id)}<ProductPhoto id={photoOf(B.id)!} sizes="(max-width: 64rem) 45vw, 22rem" />{:else}<GpuArt label={B.label} vendor="amd" vram={B.vram} heat={heatOf(B.ratio)} flat />{/if}
			</div>
			<span class="vsb-nm">{faceShort(B.id)}</span>
			{#if faceSpeed(B.id)}<span class="vsb-v mono">{fmtTps(faceSpeed(B.id)!, lang)}{NB}t/s</span>{/if}
		</div>
	</div>
</section>

<style>
	.wrap {
		width: min(100% - 2 * var(--gutter), 88rem);
		margin-inline: auto;
	}
	.mono {
		font-family: var(--font-mono);
	}

	/* ---------- the question, on one line ---------- */
	.hero {
		padding: calc(4.25rem + clamp(1.25rem, 4.5vh, 3.5rem)) 0 clamp(2.5rem, 6vw, 5rem);
	}
	.eyebrow {
		margin: 0 0 var(--sp-4);
	}
	/* one line at every width: the size follows the space (≈0.6 em per glyph in the display face) */
	.title {
		margin: 0;
		font-family: var(--font-display);
		font-size: min(6.25rem, calc((100vw - 2 * var(--gutter)) / (var(--chars) * 0.6)));
		font-weight: 850;
		font-stretch: 112%;
		line-height: 1;
		letter-spacing: -0.035em;
		white-space: nowrap;
	}
	@media (prefers-reduced-motion: no-preference) {
		:global(html.js) .title {
			animation: title-in 0.9s var(--ease-out) backwards;
		}
	}
	@keyframes title-in {
		from {
			transform: translate3d(0, 0.25em, 0);
		}
	}

	/* ---------- the four makers ---------- */
	.makers {
		margin-top: clamp(1.25rem, 3vw, 2.25rem);
	}
	.makers ul {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: clamp(0.6rem, 1.2vw, 1.1rem);
	}
	.mk {
		display: grid;
		min-width: 0;
		transition: transform 0.7s var(--ease-spring);
	}
	.mk:has(.mk-tile:is(:hover, :focus-visible)) {
		transform: translate3d(0, -6px, 0);
	}
	@media (prefers-reduced-motion: no-preference) {
		:global(html.js) .mk {
			animation: mk-in 0.95s var(--ease-spring) backwards;
			animation-delay: calc(140ms + var(--i) * 80ms);
		}
	}
	@keyframes mk-in {
		from {
			opacity: 0;
			transform: translate3d(0, 28px, 0) scale(0.96);
		}
	}
	/* a showroom block: always dark, in the maker's colour (also in the light theme) */
	.mk-tile {
		--text-hi: #edeae3;
		--text: #bdb9b1;
		--text-mute: #8e8a83;
		color-scheme: dark;
		position: relative;
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		grid-template-rows: auto 1fr auto;
		min-height: clamp(19rem, 30vw, 27rem);
		padding: clamp(0.9rem, 1.6vw, 1.4rem);
		border-radius: var(--r-xl);
		color: var(--text);
		text-decoration: none;
		background:
			radial-gradient(120% 70% at 50% 110%, rgb(var(--v) / 0.28), transparent 60%),
			var(--v-grad);
		box-shadow:
			inset 0 0 0 1px rgb(var(--v) / 0.34),
			inset 0 1px 0 rgb(255 255 255 / 0.09),
			0 30px 60px -36px rgb(0 0 0 / 0.95);
		overflow: hidden;
		isolation: isolate;
		transition: box-shadow 0.6s var(--ease-out);
	}
	/*
	 * The maker's accent: two hairlines raking down from the top corner, fading out above the
	 * product (masked out of the stage, and painted under everything in the block).
	 */
	.acc {
		position: absolute;
		z-index: -1;
		top: 0;
		right: 0;
		width: 46%;
		height: clamp(4.5rem, 7vw, 7rem);
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
		transition: transform 0.9s var(--ease-spring);
	}
	.acc i + i {
		left: 70%;
		width: 1px;
		opacity: 0.55;
		box-shadow: none;
	}
	.mk-tile:is(:hover, :focus-visible) .acc i {
		transform: translate3d(-10px, 0, 0) rotate(32deg);
	}
	.mk-tile:is(:hover, :focus-visible) .acc i + i {
		transform: translate3d(-18px, 0, 0) rotate(32deg);
	}
	.mk-tile:is(:hover, :focus-visible) {
		box-shadow:
			inset 0 0 0 1px rgb(var(--v) / 0.8),
			inset 0 1px 0 rgb(255 255 255 / 0.14),
			0 0 60px -14px rgb(var(--v) / 0.6),
			0 30px 60px -30px rgb(0 0 0 / 0.95);
	}
	.mk-tile:focus-visible {
		outline: 2px solid var(--focus);
		outline-offset: 3px;
	}
	/* Apple: brushed aluminium, a cool sheen instead of a coloured wash */
	.mk--apple .mk-tile {
		background:
			repeating-linear-gradient(90deg, rgb(255 255 255 / 0.018) 0 1px, transparent 1px 3px),
			radial-gradient(90% 60% at 50% 30%, rgb(var(--v) / 0.26), transparent 70%),
			linear-gradient(160deg, rgb(232 234 239 / 0.3), rgb(var(--v) / 0.08) 30%, transparent 55%),
			linear-gradient(200deg, #16171a, #070708 64%);
	}

	.mk-top {
		display: grid;
		gap: 0.3rem;
		min-width: 0;
	}
	/* gradient text paints only inside its box: padding leaves room for the italic overhang and
	   descenders (p), the negative margins keep the layout where it was */
	.wm {
		width: fit-content;
		padding: 0.04em 0.2em 0.14em 0.04em;
		margin: -0.04em -0.2em -0.14em -0.04em;
		font-family: var(--font-display);
		font-size: clamp(1.5rem, 0.9rem + 2.1vw, 3rem);
		font-weight: 900;
		font-stretch: 115%;
		font-style: italic;
		letter-spacing: -0.02em;
		line-height: 0.95;
		background: linear-gradient(100deg, #fff 10%, var(--v-hi) 75%);
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
		filter: drop-shadow(0 0 18px rgb(var(--v) / 0.45));
	}
	.mk--intel .wm,
	.mk--apple .wm {
		font-style: normal;
	}
	/* never truncated: on the narrowest blocks the line wraps */
	.line {
		font-size: var(--fs-2xs);
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: var(--text-mute);
	}

	.stage {
		position: relative;
		align-self: center;
		margin: var(--sp-3) calc(-1 * clamp(0.3rem, 1vw, 0.8rem));
		user-select: none;
	}
	/* the floor lit in the maker's colour */
	.stage::before {
		content: '';
		position: absolute;
		left: 8%;
		right: 8%;
		bottom: -2%;
		height: 24%;
		border-radius: 50%;
		background: radial-gradient(closest-side, rgb(var(--v) / 0.45), rgb(var(--v) / 0.08) 60%, transparent);
		filter: blur(6px);
		transform: scaleY(0.7);
		transition: opacity 0.6s var(--ease-out);
		opacity: 0.75;
	}
	/* positioned after the sweep, so the light passes behind the product, never over it */
	.art {
		position: relative;
		display: block;
		transition: transform 0.8s var(--ease-spring);
	}
	.art :global(.glow) {
		background: radial-gradient(closest-side, rgb(var(--v) / calc(0.24 + var(--th) * 0.2)), transparent);
	}
	.mk-tile:is(:hover, :focus-visible) .art {
		transform: translate3d(0, -5%, 0) scale(1.05);
	}
	.mk-tile:is(:hover, :focus-visible) .stage::before {
		opacity: 1;
	}
	.sweep {
		position: absolute;
		inset: -40% auto -40% 0;
		width: 34%;
		background: linear-gradient(90deg, transparent, rgb(255 255 255 / 0.12), transparent);
		transform: translate3d(-160%, 0, 0) skewX(-16deg);
		pointer-events: none;
	}
	@media (prefers-reduced-motion: no-preference) {
		.mk-tile:is(:hover, :focus-visible) .sweep {
			transform: translate3d(420%, 0, 0) skewX(-16deg);
			transition: transform 1.1s var(--ease-out);
		}
	}

	.mk-foot {
		display: grid;
		gap: 0.5rem;
		padding-top: var(--sp-3);
		border-top: 1px solid rgb(var(--v) / 0.25);
	}
	.gain {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0 0.4rem;
		min-height: 2.6rem;
		line-height: 1.1;
	}
	.up {
		font-size: var(--fs-sm);
		font-weight: 600;
		color: var(--text);
	}
	.none {
		font-size: var(--fs-sm);
		color: var(--text-mute);
		align-self: center;
	}
	.counts {
		display: flex;
		flex-wrap: wrap;
		gap: 0.2rem 0.9rem;
		font-size: var(--fs-2xs);
		letter-spacing: 0.06em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.counts > span {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		white-space: nowrap;
	}
	.c-m {
		color: var(--text);
	}
	.dot,
	.ring {
		width: 0.45rem;
		height: 0.45rem;
		border-radius: 50%;
	}
	.dot {
		background: var(--v-hi);
		box-shadow: 0 0 8px rgb(var(--v) / 0.9);
	}
	.ring {
		border: 1.5px dashed var(--text-mute);
	}
	.go {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--sp-3);
		margin-top: 0.25rem;
		font-size: var(--fs-sm);
		font-weight: 650;
		color: var(--text-hi);
	}
	.arr {
		display: grid;
		place-items: center;
		width: 2.25rem;
		height: 2.25rem;
		border-radius: 50%;
		background: rgb(var(--v) / 0.16);
		box-shadow: inset 0 0 0 1px rgb(var(--v) / 0.5);
		color: var(--v-hi);
		transition:
			transform 0.6s var(--ease-spring),
			background-color 0.3s;
	}
	.mk-tile:is(:hover, :focus-visible) .arr {
		transform: translate3d(4px, 0, 0);
		background: rgb(var(--v) / 0.32);
	}

	/* ---------- below the makers: the lede and search ---------- */
	.below {
		display: grid;
		grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
		align-items: start;
		gap: var(--sp-4) clamp(2rem, 5vw, 5rem);
		margin-top: clamp(1.5rem, 3vw, 2.5rem);
	}
	.lede {
		margin: 0;
		max-width: 46rem;
		font-size: var(--fs-md);
		color: var(--text);
	}
	.search {
		display: grid;
		gap: var(--sp-2);
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
		min-height: 3rem;
		padding: 0 1rem 0 2.75rem;
		border: 1px solid var(--line-strong);
		border-radius: var(--r-md);
		background: var(--bg-1);
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
		border-color: var(--text-mute);
		box-shadow: 0 0 0 3px rgb(237 234 227 / 0.08);
	}
	.field input::placeholder {
		color: var(--text-mute);
	}
	.field input:focus-visible {
		outline: 2px solid var(--focus);
		outline-offset: 2px;
	}
	.count {
		margin: 0;
		min-height: 1.2em;
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}

	/* search hits: one row per card, a stripe of its maker's colour */
	.hits {
		list-style: none;
		margin: var(--sp-4) 0 0;
		padding: 0;
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(min(100%, 19rem), 1fr));
		gap: var(--sp-2);
	}
	.hit {
		--text-hi: #edeae3;
		--text: #bdb9b1;
		--text-mute: #8e8a83;
		display: grid;
		grid-template-columns: minmax(0, 1fr) auto auto;
		align-items: center;
		gap: var(--sp-3);
		min-height: 3.75rem;
		padding: 0.6rem 1rem;
		border-radius: var(--r-md);
		background:
			linear-gradient(90deg, rgb(var(--v) / 0.24), transparent 55%),
			linear-gradient(180deg, var(--v-deep), #070708);
		box-shadow: inset 3px 0 0 rgb(var(--v)), inset 0 0 0 1px rgb(var(--v) / 0.25);
		color: var(--text);
		text-decoration: none;
		transition:
			transform 0.5s var(--ease-spring),
			box-shadow 0.3s;
	}
	.hit.est {
		background: linear-gradient(90deg, rgb(var(--v) / 0.1), transparent 55%), linear-gradient(180deg, #0d0d0e, #070708);
	}
	.hit:is(:hover, :focus-visible) {
		transform: translate3d(3px, 0, 0);
		box-shadow: inset 3px 0 0 rgb(var(--v)), inset 0 0 0 1px rgb(var(--v) / 0.7);
	}
	.h-id {
		display: grid;
		min-width: 0;
	}
	.h-pre {
		font-size: var(--fs-2xs);
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.h-nm {
		font-family: var(--font-display);
		font-size: var(--fs-lg);
		font-weight: 800;
		font-stretch: 110%;
		color: var(--text-hi);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.h-spec,
	.h-sub {
		font-size: var(--fs-2xs);
		color: var(--text-mute);
		white-space: nowrap;
	}
	.h-st {
		display: grid;
		justify-items: end;
		line-height: 1;
		gap: 0.2rem;
	}
	.empty {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-4) var(--sp-6);
		margin-top: var(--sp-4);
	}
	.h-empty {
		margin: 0;
		font-size: var(--fs-xl);
		font-weight: 700;
		color: var(--text-hi);
	}

	/* ---------- versus band: green from the left, red from the right, a white-hot seam ---------- */
	.vsb {
		padding-bottom: var(--section-y);
	}
	.vsb-in {
		--text-hi: #edeae3;
		--text: #bdb9b1;
		--text-mute: #8e8a83;
		color-scheme: dark;
		position: relative;
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1.15fr) minmax(0, 1fr);
		align-items: center;
		gap: var(--sp-4);
		padding: clamp(1.5rem, 4vw, 3.5rem) clamp(1rem, 3vw, 3rem);
		border-radius: var(--r-xl);
		color: var(--text);
		background:
			radial-gradient(40% 80% at 50% 50%, rgb(255 243 214 / 0.08), transparent 70%),
			linear-gradient(90deg, rgb(var(--a) / 0.55), rgb(var(--a) / 0.16) 34%, transparent 56%),
			linear-gradient(270deg, rgb(var(--b) / 0.55), rgb(var(--b) / 0.16) 34%, transparent 56%),
			#070708;
		box-shadow: inset 0 0 0 1px rgb(255 255 255 / 0.08), 0 40px 80px -50px #000;
		overflow: hidden;
		isolation: isolate;
	}
	/* the seam where the two colours meet: a slanted white-hot blade */
	.vsb-in::before {
		content: '';
		position: absolute;
		z-index: -1;
		inset: -20% auto -20% 50%;
		width: 3px;
		background: linear-gradient(180deg, transparent, rgb(var(--a)) 20%, #fff3d6 50%, rgb(var(--b)) 80%, transparent);
		box-shadow: 0 0 24px 4px rgb(255 243 214 / 0.25);
		transform: translateX(-50%) rotate(12deg);
		/* it cuts through the VS, then gives way to the words under it */
		mask-image: linear-gradient(180deg, #000 0 40%, transparent 50% 90%, #000 100%);
	}
	.vsb-side {
		display: grid;
		justify-items: start;
		gap: 0.35rem;
		min-width: 0;
	}
	.vsb-b {
		justify-items: end;
		text-align: right;
	}
	.vsb-wm {
		font-family: var(--font-display);
		font-size: var(--fs-sm);
		font-weight: 900;
		font-style: italic;
		letter-spacing: 0.04em;
		color: var(--a-hi);
		text-shadow: 0 0 14px rgb(var(--a) / 0.6);
	}
	.vsb-b .vsb-wm {
		color: var(--b-hi);
		text-shadow: 0 0 14px rgb(var(--b) / 0.6);
	}
	.vsb-art {
		display: block;
		width: 100%;
		max-width: 22rem;
		transition: transform 0.9s var(--ease-spring);
	}
	.vsb-a .vsb-art :global(.glow) {
		background: radial-gradient(closest-side, rgb(var(--a) / 0.35), transparent);
	}
	.vsb-b .vsb-art :global(.glow) {
		background: radial-gradient(closest-side, rgb(var(--b) / 0.35), transparent);
	}
	.vsb-in:hover .vsb-a .vsb-art {
		transform: translate3d(4%, 0, 0);
	}
	.vsb-in:hover .vsb-b .vsb-art {
		transform: translate3d(-4%, 0, 0);
	}
	.vsb-nm {
		font-family: var(--font-display);
		font-size: clamp(1.4rem, 0.9rem + 1.6vw, 2.5rem);
		font-weight: 850;
		font-stretch: 112%;
		letter-spacing: -0.035em;
		line-height: 1;
		color: var(--text-hi);
		white-space: nowrap;
	}
	.vsb-v {
		font-size: var(--fs-xs);
		color: var(--heat-4);
	}
	.vsb-mid {
		display: grid;
		justify-items: center;
		text-align: center;
		gap: var(--sp-3);
	}
	.vsb-vs {
		padding: 0.06em 0.22em;
		font-family: var(--font-display);
		font-size: clamp(3.5rem, 2rem + 5vw, 7.5rem);
		font-weight: 900;
		font-style: italic;
		font-stretch: 120%;
		line-height: 0.85;
		letter-spacing: -0.04em;
		background: linear-gradient(90deg, var(--a-hi) 20%, #fff3d6 50%, var(--b-hi) 80%);
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
		filter: drop-shadow(0 0 26px rgb(255 243 214 / 0.25));
	}
	.vsb-t {
		margin: 0;
		font-family: var(--font-display);
		font-size: var(--fs-2xl);
		font-weight: 800;
		font-stretch: 110%;
		color: var(--text-hi);
	}
	.vsb-l {
		margin: 0;
		max-width: 28rem;
		color: var(--text);
	}

	@media (max-width: 64rem) {
		.makers ul {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
		.mk-tile {
			min-height: 0;
		}
		.below {
			grid-template-columns: minmax(0, 1fr);
		}
		.vsb-in {
			grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		}
		.vsb-mid {
			grid-column: 1 / -1;
			grid-row: 2;
		}
	}
	@media (max-width: 40rem) {
		.hero {
			padding-top: calc(4.25rem + 1rem);
		}
		.mk-tile {
			padding: 0.8rem;
			border-radius: var(--r-lg);
		}
		.stage {
			margin-block: var(--sp-2);
		}
		.mk-foot {
			gap: 0.35rem;
			padding-top: var(--sp-2);
		}
		.gain {
			min-height: 1.5rem;
		}
		.up,
		.none {
			font-size: var(--fs-xs);
		}
		.gain :global(.rx--md) {
			--rx-fs: 1.15rem;
		}
		.counts {
			flex-direction: column;
			letter-spacing: 0.02em;
		}
		.go-l {
			display: none;
		}
		.go {
			position: absolute;
			top: 0.7rem;
			right: 0.7rem;
			margin: 0;
		}
		.arr {
			width: 1.9rem;
			height: 1.9rem;
		}
		.lede {
			font-size: var(--fs-base);
		}
		.vsb-in {
			padding: var(--sp-5) var(--sp-4);
			gap: var(--sp-3);
		}
	}
	/* the narrowest phones: the block itself is the link, the arrow gives way to the wordmark */
	@media (max-width: 25rem) {
		.go {
			display: none;
		}
		.wm {
			font-size: 1.35rem;
		}
		.counts {
			font-size: 0.625rem;
			letter-spacing: 0;
		}
		.up,
		.none {
			font-size: 0.6875rem;
		}
	}
	/* stacked band: the blade runs between the two cards and stops above the words */
	@media (max-width: 64rem) {
		.vsb-in::before {
			mask-image: linear-gradient(180deg, #000 0 46%, transparent 56% 94%, #000 100%);
		}
	}
</style>
