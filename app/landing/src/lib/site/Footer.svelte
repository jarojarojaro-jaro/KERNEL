<script lang="ts">
	import { SITE_PUBLIC } from '$lib/site/public';
	import { BRAND } from '$lib/brand';
	import { cardsHref, currentLang, href, switchLangHref } from '$lib/i18n';
	import { visible } from '$lib/fx/actions';
	import { page } from '$app/state';
	import { consent } from './consent.svelte';
	import ThemeToggle from './ThemeToggle.svelte';
	import { copy } from './copy';
	import Logo from './Logo.svelte';

	const lang = $derived(currentLang());
	const other = $derived(lang === 'pl' ? 'en' : 'pl');
	const t = $derived(copy[lang]);
	const legal = ['terms', 'privacy', 'cookies', 'ai', 'imprint'] as const;
	// the showcase pages (home, cards, results) are dark-only, so the theme switch is offered elsewhere
	const themeable = $derived(!page.url.pathname.match(/^\/(pl|en)\/((karty|cards|wyniki|results)\/.*)?$/));
	// the sweep runs only while the footer is on screen
	let live = $state(false);

	/* Background wordmark. SVG text (fixed viewBox + textLength) so it always fills the width
	   exactly, before and after the web font swaps in, with no layout shift. Two lockups: one line
	   (wide) and ENIGMA over LABZ (narrow phones). Each line: [text, font-size, baseline y, x,
	   textLength]; x and length put the ink (900, 125% Showcase Sans) at 12..988 of the 1000 width. */
	const [first, second] = BRAND.name.toUpperCase().split(' ');
	const MARKS = [
		{ id: 'one', h: 108, lines: [[BRAND.name.toUpperCase(), 125, 100, 6, 984]] },
		{ id: 'two', h: 454, lines: [[first, 214, 168, 2, 984], [second, 330, 446, -3, 995]] }
	] as const;
</script>

{#snippet mark(m: (typeof MARKS)[number])}
	<div class="wm wm-{m.id}" aria-hidden="true">
		<svg class="wm-base" viewBox="0 0 1000 {m.h}" preserveAspectRatio="xMidYMax meet" focusable="false">
			<defs>
				<g id="fw-t-{m.id}">
					{#each m.lines as [txt, size, y, x, len] (txt)}
						<!-- inline style: <use> clones live in a shadow tree that scoped selectors can't reach -->
						<text {x} {y} font-size={size} textLength={len} lengthAdjust="spacingAndGlyphs" style="font-family: var(--font-display); font-weight: 900; font-stretch: 125%">{txt}</text>
					{/each}
				</g>
				<clipPath id="fw-clip-{m.id}"><use href="#fw-t-{m.id}" /></clipPath>
				<linearGradient id="fw-stroke-{m.id}" x1="0" x2="1" y1="0" y2="0">
					<stop offset="0" class="s0" />
					<stop offset="0.45" class="s1" />
					<stop offset="0.8" class="s2" />
					<stop offset="1" class="s3" />
				</linearGradient>
				<linearGradient id="fw-fill-{m.id}" x1="0" x2="0" y1="0" y2="1">
					<stop offset="0" class="f0" />
					<stop offset="1" class="f1" />
				</linearGradient>
				<filter id="fw-blur-{m.id}" x="-5%" y="-20%" width="110%" height="140%"><feGaussianBlur stdDeviation="3.5" /></filter>
			</defs>
			<use href="#fw-t-{m.id}" class="fill" fill="url(#fw-fill-{m.id})" />
			<!-- inner glow: a wide blurred stroke kept inside the letters -->
			<g clip-path="url(#fw-clip-{m.id})"><use href="#fw-t-{m.id}" class="glow" filter="url(#fw-blur-{m.id})" /></g>
			<use href="#fw-t-{m.id}" class="edge" stroke="url(#fw-stroke-{m.id})" />
		</svg>
		<!-- light sweep: a warm band through the letters that also lights their outline; its own
		     layer, so only this small drawing repaints while it moves -->
		<svg class="wm-sweep" viewBox="0 0 1000 {m.h}" preserveAspectRatio="xMidYMax meet" focusable="false">
			<defs>
				<linearGradient id="fw-sweep-{m.id}" x1="0" x2="1" y1="0" y2="0">
					<stop offset="0" class="w0" />
					<stop offset="0.5" class="w1" />
					<stop offset="1" class="w0" />
				</linearGradient>
				<linearGradient id="fw-sweepm-{m.id}" x1="0" x2="1" y1="0" y2="0">
					<stop offset="0" stop-color="#000" />
					<stop offset="0.5" stop-color="#fff" />
					<stop offset="1" stop-color="#000" />
				</linearGradient>
				<mask id="fw-hot-{m.id}" maskUnits="userSpaceOnUse" x="-200" y="0" width="1400" height={m.h}>
					<g transform="skewX(-18)"><rect class="band" x="-260" y="0" width="260" height={m.h} fill="url(#fw-sweepm-{m.id})" /></g>
				</mask>
			</defs>
			<g clip-path="url(#fw-clip-{m.id})">
				<g transform="skewX(-18)"><rect class="band" x="-260" y="0" width="260" height={m.h} fill="url(#fw-sweep-{m.id})" /></g>
			</g>
			<use href="#fw-t-{m.id}" class="hot" mask="url(#fw-hot-{m.id})" />
		</svg>
	</div>
{/snippet}

<footer class="site-footer" class:live use:visible={(on) => (live = on)}>
	<div class="stage">
		{#each MARKS as m (m.id)}{@render mark(m)}{/each}
		<div class="wrap grid">
			<div class="about">
				<Logo />
				<p class="tag">{t.footer.tagline}</p>
				<a class="f-cta" href={href(lang, '/start')}>
					<span>{t.nav.start}</span>
					<svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true"><path d="M3 8h9M8.5 4.5 12 8l-3.5 3.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" /></svg>
				</a>
				<div class="notes">
					<p>{t.footer.credit}</p>
					<p>{t.footer.aiMedia}</p>
				</div>
			</div>
			<nav aria-labelledby="f-product">
				<h2 id="f-product" class="lbl">{t.footer.product}</h2>
				<ul>
					<li><a href={href(lang, '/#how')}>{t.nav.how}</a></li>
					<li><a href={href(lang, '/#results')}>{t.nav.results}</a></li>
					<li><a href={cardsHref(lang)}>{t.nav.cards}</a></li>
					{#if !SITE_PUBLIC}<li><a href={href(lang, '/methodology')}>{t.nav.methodology}</a></li>{/if}
					<li><a href={href(lang, '/scan')}>{t.privacy.scanLink}</a></li>
					<li><a href={href(lang, '/start')}>{t.nav.start}</a></li>
					<li><a href={href(lang, '/app')}>{t.footer.prototype}</a></li>
				</ul>
			</nav>
			<nav aria-labelledby="f-legal">
				<h2 id="f-legal" class="lbl">{t.footer.legal}</h2>
				<ul>
					{#each legal as d (d)}
						<li><a href={href(lang, `/legal/${d}`)}>{t.footer.legalLinks[d]}</a></li>
					{/each}
					<li><button class="linklike" type="button" onclick={() => (consent.open = true)}>{t.footer.cookieSettings}</button></li>
				</ul>
			</nav>
		</div>
	</div>
	<div class="f-bar">
		<div class="wrap base">
			<div class="f-fine">
				<p>{t.footer.draftNote} {t.footer.company}</p>
				<p>© 2026 {BRAND.company.legalName ?? BRAND.name}</p>
			</div>
			<div class="tools">
				<a class="lang" href={switchLangHref(other)} hreflang={other} title={t.nav.langLabel} data-sveltekit-reload>
					<span class="cur">{lang.toUpperCase()}</span><span class="sep" aria-hidden="true">/</span><span class="oth">{other.toUpperCase()}</span><span class="sr-only" lang={other}> – {t.nav.lang}</span>
				</a>
				{#if themeable}<ThemeToggle toDark={t.nav.themeToDark} toLight={t.nav.themeToLight} />{/if}
			</div>
		</div>
	</div>
</footer>

<style>
	.site-footer {
		/* wordmark palette: ember outline, a faint ember body, a warm sweep */
		--wm-s0: var(--heat-2);
		--wm-s1: var(--heat-3);
		--wm-s2: var(--heat-4);
		--wm-s3: var(--heat-5);
		--wm-edge: 0.55;
		--wm-f0: rgb(255 122 26 / 0.11);
		--wm-f1: rgb(255 122 26 / 0.015);
		--wm-glow: rgb(255 122 26 / 0.5);
		--wm-sweep: rgb(255 200 140 / 0.14);
		--wm-hot: var(--heat-5);
		/* the text on top keeps a solid ring of the page colour (eight 1 px offsets dilate the glyph,
		   then a soft glow), so no outline or sweep ever runs next to a glyph: contrast >= 4.5:1 */
		--halo:
			1px 0 1px var(--bg-0), -1px 0 1px var(--bg-0), 0 1px 1px var(--bg-0), 0 -1px 1px var(--bg-0),
			1px 1px 1px var(--bg-0), -1px -1px 1px var(--bg-0), 1px -1px 1px var(--bg-0), -1px 1px 1px var(--bg-0),
			0 0 4px var(--bg-0), 0 0 12px var(--bg-0);
		position: relative;
		container-type: inline-size;
		overflow: clip;
		border-top: 1px solid var(--line);
		background:
			radial-gradient(70% 55% at 50% 105%, rgb(255 122 26 / 0.13), transparent 70%),
			var(--bg-0);
		margin-top: var(--sp-16);
	}
	:global([data-theme='light']) .site-footer {
		--wm-s0: #c2410c;
		--wm-s1: var(--accent);
		--wm-s2: #f08a2c;
		--wm-s3: #f5a54a;
		--wm-edge: 0.6;
		--wm-f0: rgb(226 84 26 / 0.09);
		--wm-f1: rgb(226 84 26 / 0.01);
		--wm-glow: rgb(226 84 26 / 0.35);
		--wm-sweep: rgb(255 150 70 / 0.16);
		--wm-hot: #b4380a;
		background:
			radial-gradient(70% 55% at 50% 105%, rgb(226 84 26 / 0.09), transparent 70%),
			var(--bg-0);
	}
	:global([data-showcase]) .site-footer {
		margin-top: 0;
	}
	.wrap {
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
	}

	/* ---------- stage: content on top, the wordmark behind its lower part ---------- */
	.stage {
		/* wordmark height follows the footer width (viewBox ratio); ~55% of it sits behind the
		   columns, the rest stands on the bottom bar's rule */
		--wm-h: calc(100cqi * 108 / 1000);
		position: relative;
		/* the rule is the floor: while rising (parallax) the letters come up from behind it */
		overflow: clip;
		padding-top: var(--sp-20);
		padding-bottom: calc(var(--wm-h) * 0.45 + var(--sp-4));
	}
	.wm {
		position: absolute;
		inset: auto 0 0;
		pointer-events: none;
		user-select: none;
		/* letters fade upward into the content, full strength in the clear band */
		mask-image: linear-gradient(180deg, rgb(0 0 0 / 0.3), rgb(0 0 0 / 0.55) 30%, #000 64%);
	}
	.wm-two {
		display: none;
	}
	.wm svg {
		display: block;
		width: 100%;
		height: auto;
		overflow: visible;
	}
	.wm-sweep {
		position: absolute;
		inset: 0;
		will-change: transform;
	}
	.s0 {
		stop-color: var(--wm-s0);
	}
	.s1 {
		stop-color: var(--wm-s1);
	}
	.s2 {
		stop-color: var(--wm-s2);
	}
	.s3 {
		stop-color: var(--wm-s3);
	}
	.f0 {
		stop-color: var(--wm-f0);
	}
	.f1 {
		stop-color: var(--wm-f1);
	}
	.w0 {
		stop-color: transparent;
	}
	.w1 {
		stop-color: var(--wm-sweep);
	}
	.glow {
		fill: none;
		stroke: var(--wm-glow);
		stroke-width: 7;
	}
	.edge {
		fill: none;
		stroke-width: 1.25px;
		stroke-opacity: var(--wm-edge);
		vector-effect: non-scaling-stroke;
	}
	.hot {
		fill: none;
		stroke: var(--wm-hot);
		stroke-width: 1.75px;
		vector-effect: non-scaling-stroke;
	}
	.band {
		visibility: hidden;
	}
	@media (prefers-reduced-motion: no-preference) {
		/* one slow pass of light, then a long rest; paused while the footer is off screen */
		.band {
			visibility: visible;
			animation: fw-sweep 15s cubic-bezier(0.45, 0, 0.25, 1) 1.2s infinite paused;
		}
		.live .band {
			animation-play-state: running;
		}
		/* gentle parallax: the wordmark rises into place as the footer scrolls in (compositor only) */
		@supports (animation-timeline: view()) {
			.wm {
				animation: fw-rise linear both;
				animation-timeline: view();
				animation-range: entry 0% entry 100%;
			}
		}
	}
	@keyframes fw-sweep {
		0% {
			transform: translateX(0);
		}
		40%,
		100% {
			transform: translateX(1420px);
		}
	}
	@keyframes fw-rise {
		from {
			transform: translateY(28%);
			opacity: 0.35;
		}
		to {
			transform: none;
			opacity: 1;
		}
	}

	/* ---------- content ---------- */
	.grid {
		position: relative;
		display: grid;
		grid-template-columns: minmax(0, 1.6fr) minmax(0, 1fr) minmax(0, 1fr);
		gap: var(--sp-10) var(--sp-8);
	}
	.about {
		display: grid;
		gap: var(--sp-5);
		align-content: start;
		justify-items: start;
		max-width: 27rem;
	}
	.tag {
		font-family: var(--font-display);
		font-size: var(--fs-xl);
		font-weight: 600;
		letter-spacing: -0.01em;
		line-height: 1.25;
		color: var(--text-hi);
		text-wrap: balance;
	}
	/* same pill as the header CTA: bone hairline, never heat */
	.f-cta {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		height: 2.6rem;
		padding: 0 1.05rem 0 1.15rem;
		border-radius: var(--r-pill);
		color: var(--text-hi);
		font-size: var(--fs-sm);
		font-weight: 600;
		text-decoration: none;
		background: linear-gradient(var(--bg-2), var(--bg-2)) padding-box, linear-gradient(120deg, color-mix(in srgb, var(--text-hi) 35%, transparent), color-mix(in srgb, var(--text-hi) 8%, transparent) 60%) border-box;
		border: 1px solid transparent;
		transition: background 0.3s;
	}
	.f-cta:hover {
		background: linear-gradient(var(--bg-3), var(--bg-3)) padding-box, linear-gradient(120deg, var(--text-hi), color-mix(in srgb, var(--text-hi) 20%, transparent) 70%) border-box;
	}
	.f-cta svg {
		transition: transform 0.35s var(--ease-out);
	}
	.f-cta:hover svg {
		transform: translateX(3px);
	}
	.notes {
		position: relative;
		isolation: isolate;
		display: grid;
		gap: var(--sp-2);
		font-size: var(--fs-xs);
		line-height: 1.5;
		color: var(--text-mute);
		text-shadow: var(--halo);
	}
	/* the small print sits on the letters' crowns: a feathered plate of the page colour dims them there */
	.notes::before {
		content: '';
		position: absolute;
		inset: 0;
		z-index: -1;
		border-radius: var(--r-lg);
		background: var(--bg-0);
		box-shadow: 0 0 18px 12px var(--bg-0);
		opacity: 0.92;
	}
	.lbl {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		font-weight: 500;
		text-transform: uppercase;
		letter-spacing: 0.12em;
		color: var(--text-mute);
	}
	ul {
		list-style: none;
		padding: 0;
		margin: var(--sp-5) 0 0;
		display: grid;
		gap: var(--sp-3);
	}
	nav a,
	.linklike {
		color: var(--text);
		text-decoration: none;
		font-size: var(--fs-sm);
		text-shadow: var(--halo);
		transition: color var(--dur-2);
	}
	nav a:hover,
	.linklike:hover {
		color: var(--text-hi);
	}
	.linklike {
		background: none;
		border: 0;
		padding: 0;
		font: inherit;
		font-size: var(--fs-sm);
		cursor: pointer;
		text-align: left;
	}

	/* ---------- bottom bar ---------- */
	.f-bar {
		border-top: 1px solid color-mix(in srgb, var(--accent) 22%, var(--line));
	}
	.base {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--sp-3) var(--sp-8);
		padding-block: var(--sp-4) var(--sp-6);
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.f-fine {
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-1) var(--sp-6);
	}
	.tools {
		display: flex;
		align-items: center;
		gap: var(--sp-2);
		flex: none;
	}
	.lang {
		display: inline-flex;
		align-items: center;
		gap: 0.3rem;
		height: 2.5rem;
		padding: 0 0.7rem;
		border-radius: var(--r-pill);
		font-family: var(--font-mono);
		font-size: 0.68rem;
		letter-spacing: 0.08em;
		text-decoration: none;
		color: var(--text-mute);
		transition: background-color var(--dur-2);
	}
	.lang:hover {
		background: var(--bg-3);
	}
	.lang .cur,
	.lang:hover .oth {
		color: var(--text-hi);
	}
	.lang .sep {
		opacity: 0.4;
	}

	@media (max-width: 900px) {
		.grid {
			grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		}
		.about {
			grid-column: 1 / -1;
		}
	}
	@media (max-width: 600px) {
		.wm-one {
			display: none;
		}
		.wm-two {
			display: block;
		}
		.stage {
			--wm-h: calc(100cqi * 454 / 1000);
			padding-top: var(--sp-16);
			padding-bottom: calc(var(--wm-h) * 0.4 + var(--sp-4));
		}
		.grid {
			gap: var(--sp-10) var(--sp-5);
		}
		.tag {
			font-size: var(--fs-lg);
		}
		.base {
			flex-direction: column-reverse;
			align-items: stretch;
			gap: var(--sp-3);
		}
		.tools {
			justify-content: space-between;
			border-bottom: 1px solid var(--line);
			padding-bottom: var(--sp-2);
		}
		.lang {
			margin-left: -0.7rem;
		}
		.f-fine {
			flex-direction: column;
		}
	}
</style>
