<script lang="ts">
	import { afterNavigate } from '$app/navigation';
	import { page } from '$app/state';
	import { magnetic } from '$lib/fx/actions';
	import { onFrame, reducedMotion, Spring } from '$lib/fx/motion';
	import { cardsHref, currentLang, href, resultsHref, switchLangHref } from '$lib/i18n';
	import { tick, untrack } from 'svelte';
	import { copy } from './copy';
	import Logo from './Logo.svelte';

	const lang = $derived(currentLang());
	const t = $derived(copy[lang].nav);
	const other = $derived(lang === 'pl' ? 'en' : 'pl');
	let open = $state(false);
	let scrolled = $state(false);
	let progress = $state(0);

	/** Home, results and the cards explorer are dark-only (same rule as the inline script in app.html). */
	const SHOWCASE = /^\/(pl|en)\/((karty|cards|wyniki|results)\/.*)?$/;
	const showcase = $derived(SHOWCASE.test(page.url.pathname));

	// Client-side navigation does not rerun app.html's script: re-apply the theme rule here.
	afterNavigate(() => {
		open = false;
		const root = document.documentElement;
		if (SHOWCASE.test(location.pathname)) {
			root.dataset.theme = 'dark';
			root.toggleAttribute('data-showcase', true);
			return;
		}
		root.toggleAttribute('data-showcase', false);
		let theme: string | null = null;
		try {
			theme = localStorage.getItem('theme');
		} catch {
			/* storage blocked */
		}
		root.dataset.theme = theme === 'light' ? 'light' : 'dark';
	});

	const links = $derived([
		{ label: t.how, to: href(lang, '/#how') },
		{ label: t.results, to: resultsHref(lang) },
		{ label: t.cards, to: cardsHref(lang) },
		{ label: t.methodology, to: href(lang, '/methodology') },
		{ label: t.contact, to: href(lang, '/contact') }
	]);
	const current = (to: string) => !to.includes('#') && page.url.pathname.startsWith(to);

	/*
	 * Gliding highlight: one heat pill that follows the hovered/focused item, or rests on the section
	 * currently in view. Position and width run on springs (no CSS transitions, so no snapping);
	 * when it first appears it materialises in place instead of sliding in from the left.
	 */
	let list: HTMLUListElement | undefined = $state();
	let capsule: HTMLDivElement | undefined = $state();
	let pill: HTMLSpanElement | undefined = $state();
	let hoverIdx = $state<number | null>(null);
	let sectionIdx = $state<number | null>(null);
	const target = $derived(hoverIdx ?? sectionIdx ?? links.findIndex((l) => current(l.to)));
	const sx = new Spring(0, 260, 26);
	const sw = new Spring(0, 260, 26);
	let alpha = 0;
	let shown = false;

	$effect(() => {
		const idx = target;
		const hovering = hoverIdx !== null;
		if (!list || !pill) return;
		const a = list.querySelectorAll<HTMLAnchorElement>(':scope > li:not(.m-only) > a')[idx];
		const wantAlpha = idx >= 0 && a ? (hovering ? 1 : 0.55) : 0;
		if (a) {
			const r = a.getBoundingClientRect();
			const l = list.getBoundingClientRect();
			sx.target = r.left - l.left;
			sw.target = r.width;
			if (!shown || reducedMotion()) {
				sx.snap();
				sw.snap();
			}
		}
		const p = pill;
		return untrack(() =>
			onFrame((dt) => {
				sx.step(dt);
				sw.step(dt);
				alpha += (wantAlpha - alpha) * Math.min(1, dt * 12);
				shown = alpha > 0.02;
				p.style.transform = `translate3d(${sx.x.toFixed(2)}px, 0, 0)`;
				p.style.width = `${Math.max(0, sw.x).toFixed(2)}px`;
				p.style.opacity = alpha.toFixed(3);
				if (sx.settled && sw.settled && Math.abs(wantAlpha - alpha) < 0.01) return false;
			})
		);
	});

	function point(e: Event) {
		const a = (e.target as HTMLElement).closest('a');
		if (!a || !list || innerWidth <= 1020) return;
		const items = [...list.querySelectorAll<HTMLAnchorElement>(':scope > li:not(.m-only) > a')];
		const i = items.indexOf(a);
		if (i >= 0) hoverIdx = i;
	}

	// Light inside the capsule that follows the cursor (fine pointers only).
	function light(e: PointerEvent) {
		if (!capsule || e.pointerType !== 'mouse') return;
		const r = capsule.getBoundingClientRect();
		capsule.style.setProperty('--cx', `${e.clientX - r.left}px`);
		capsule.style.setProperty('--cy', `${e.clientY - r.top}px`);
	}

	// Section currently in view on the home page (#how): the pill rests there.
	afterNavigate(() => {
		sectionIdx = null;
		const ids: [string, number][] = [['how', 0]];
		const els = ids.map(([id, i]) => [document.getElementById(id), i] as const).filter(([el]) => el);
		if (!els.length || typeof IntersectionObserver === 'undefined') return;
		const seen = new Map<Element, number>();
		const io = new IntersectionObserver(
			(entries) => {
				for (const e of entries) seen.set(e.target, e.isIntersecting ? e.intersectionRatio : 0);
				let best: number | null = null;
				let bestR = 0;
				for (const [el, i] of els) {
					const r = seen.get(el!) ?? 0;
					if (r > bestR) {
						bestR = r;
						best = i;
					}
				}
				sectionIdx = best;
			},
			{ threshold: [0, 0.15, 0.3, 0.6], rootMargin: '-30% 0px -40% 0px' }
		);
		for (const [el] of els) io.observe(el!);
		return () => io.disconnect();
	});

	function onScroll() {
		scrolled = scrollY > 24;
		const max = document.documentElement.scrollHeight - innerHeight;
		progress = max > 0 ? Math.min(1, scrollY / max) : 0;
	}

	let menuBtn: HTMLButtonElement | undefined = $state();
	async function toggle() {
		open = !open;
		await tick();
		if (open) list?.querySelector('a')?.focus();
		else menuBtn?.focus();
	}
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && open && toggle()} onscroll={onScroll} />

<a class="skip-link" href="#main">{t.skip}</a>
<header class="site-header" class:scrolled class:showcase class:open>
	<!-- svelte-ignore a11y_no_static_element_interactions (decorative cursor light only) -->
	<div class="capsule" bind:this={capsule} onpointermove={light}>
		<a class="brand" href={href(lang)}>
			<Logo />
		</a>
		<nav aria-label={t.main} class="nav" id="site-nav">
			<!-- svelte-ignore a11y_mouse_events_have_key_events (focusin covers keyboard) -->
			<ul bind:this={list} onpointerover={point} onfocusin={point} onpointerleave={() => (hoverIdx = null)} onfocusout={() => (hoverIdx = null)}>
				<span class="hl" bind:this={pill} aria-hidden="true"></span>
				{#each links as l, i (l.to)}
					<li style="--i:{i}">
						<a href={l.to} class:hot={hoverIdx === i} aria-current={current(l.to) ? 'page' : undefined} onclick={() => (open = false)}>
							<span class="txt">{l.label}</span>
						</a>
					</li>
				{/each}
				<li class="m-only" style="--i:{links.length}"><a href={href(lang, '/start')} onclick={() => (open = false)}><span class="txt">{t.start} →</span></a></li>
			</ul>
		</nav>
		<div class="actions">
			<a class="lang" href={switchLangHref(other)} hreflang={other} title={t.langLabel} data-sveltekit-reload>
				<span class="cur">{lang.toUpperCase()}</span><span class="sep" aria-hidden="true">/</span><span class="oth">{other.toUpperCase()}</span><span class="sr-only" lang={other}> – {t.lang}</span>
			</a>
			<a class="go" href={href(lang, '/start')} use:magnetic={{ max: 3 }}><span>{t.start}</span><svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true"><path d="M3 8h9M8.5 4.5 12 8l-3.5 3.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" /></svg></a>
			<button bind:this={menuBtn} class="menu" type="button" aria-expanded={open} aria-controls="site-nav" aria-label={open ? t.close : t.menu} onclick={toggle}>
				<span class="burger" aria-hidden="true"><i></i><i></i></span>
			</button>
		</div>
		<span class="progress" style="transform: scaleX({reducedMotion() ? 0 : progress})" aria-hidden="true"></span>
	</div>
</header>

<style>
	.site-header {
		position: sticky;
		top: 0;
		z-index: var(--z-header);
		padding: 0.6rem clamp(0.5rem, 1.5vw, 1rem) 0;
		pointer-events: none;
	}
	.site-header.showcase {
		position: fixed;
		inset: 0 0 auto;
	}
	.capsule {
		position: relative;
		pointer-events: auto;
		display: flex;
		align-items: center;
		gap: var(--sp-4);
		height: 3.6rem;
		max-width: 92rem;
		margin-inline: auto;
		padding: 0 0.45rem 0 1.1rem;
		border: 1px solid color-mix(in srgb, var(--text-hi) 9%, transparent);
		border-radius: var(--r-pill);
		background: color-mix(in srgb, var(--bg-1) 72%, transparent);
		backdrop-filter: saturate(1.4) blur(18px);
		-webkit-backdrop-filter: saturate(1.4) blur(18px);
		box-shadow:
			0 1px 0 rgb(255 255 255 / 0.04) inset,
			0 12px 40px -18px rgb(0 0 0 / 0.8);
		transition:
			background 0.4s,
			border-color 0.4s;
	}
	/* Over the hero the capsule is lighter; it firms up once the page scrolls. */
	.showcase:not(.scrolled):not(.open) .capsule {
		background: color-mix(in srgb, var(--bg-0) 35%, transparent);
	}
	.brand {
		text-decoration: none;
		flex: none;
		color: var(--text-hi);
	}
	.nav {
		flex: 1;
		display: flex;
		justify-content: center;
	}
	ul {
		position: relative;
		display: flex;
		gap: 0.1rem;
		list-style: none;
		margin: 0;
		padding: 0;
	}
	/* The gliding heat pill (position/width/opacity driven by springs in the script). */
	.hl {
		position: absolute;
		top: 0;
		bottom: 0;
		left: 0;
		width: 0;
		opacity: 0;
		border-radius: var(--r-pill);
		background:
			radial-gradient(120% 140% at 50% 120%, rgb(255 122 26 / 0.28), transparent 60%),
			linear-gradient(180deg, rgb(255 193 90 / 0.08), rgb(226 64 28 / 0.1));
		box-shadow:
			inset 0 0 0 1px rgb(255 170 100 / 0.28),
			0 0 22px -4px rgb(255 122 26 / 0.45);
		pointer-events: none;
		will-change: transform, width, opacity;
	}
	.nav a {
		position: relative;
		display: flex;
		align-items: baseline;
		padding: 0.55rem 0.95rem;
		border-radius: var(--r-pill);
		color: var(--text);
		font-size: var(--fs-sm);
		font-weight: 520;
		line-height: 1.25;
		text-decoration: none;
		transition: color 0.3s var(--ease-out);
	}
	/* Label warms into the heat gradient: the gradient layer fades in over the plain text colour. */
	.txt {
		position: relative;
		display: inline-block;
		background: var(--heat-ramp-hot) 0 0 / 200% 100%;
		-webkit-background-clip: text;
		background-clip: text;
		color: inherit;
		transition:
			color 0.35s var(--ease-out),
			background-position 0.6s var(--ease-out);
	}
	.nav a.hot .txt,
	.nav a:focus-visible .txt {
		color: transparent;
		background-position: 100% 0;
	}
	.nav a:focus-visible {
		outline-offset: 0;
	}
	/* Light theme: the white-hot end would vanish on bone; use the deep end of the ramp. */
	:global(:root[data-theme='light']) .txt {
		background-image: linear-gradient(90deg, #8a2a06, #c2410c 50%, #e2541a);
	}
	.nav a[aria-current='page'] {
		color: var(--text-hi);
	}
	/* Cursor light inside the capsule. */
	.capsule::before {
		content: '';
		position: absolute;
		inset: 0;
		border-radius: inherit;
		pointer-events: none;
		background: radial-gradient(220px 120px at var(--cx, -300px) var(--cy, 50%), rgb(255 190 130 / 0.09), transparent 70%);
	}
	.nav a[aria-current='page']::after {
		content: '';
		position: absolute;
		left: 50%;
		bottom: 0.2rem;
		width: 0.25rem;
		height: 0.25rem;
		margin-left: -0.125rem;
		border-radius: 50%;
		background: var(--text-hi);
	}
	.actions {
		display: flex;
		align-items: center;
		gap: 0.3rem;
		margin-left: auto;
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
	}
	.lang .cur {
		color: var(--text-hi);
	}
	.lang .sep {
		opacity: 0.4;
	}
	.lang:hover .oth {
		color: var(--text-hi);
	}
	.go {
		--mx: 0px;
		--my: 0px;
		position: relative;
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
		transform: translate3d(var(--mx), var(--my), 0);
		transition:
			transform 0.35s var(--ease-out),
			background 0.3s;
	}
	.go:hover {
		background: linear-gradient(var(--bg-3), var(--bg-3)) padding-box, linear-gradient(120deg, var(--text-hi), color-mix(in srgb, var(--text-hi) 20%, transparent) 70%) border-box;
	}
	.go svg {
		transition: transform 0.35s var(--ease-out);
	}
	.go:hover svg {
		transform: translateX(3px);
	}
	.progress {
		position: absolute;
		left: 1.6rem;
		right: 1.6rem;
		bottom: -1px;
		height: 1px;
		background: linear-gradient(90deg, transparent, var(--text-hi) 30%, var(--text-hi) 70%, transparent);
		opacity: 0.35;
		transform-origin: 0 50%;
		pointer-events: none;
	}
	.menu {
		display: none;
		place-items: center;
		width: 2.75rem;
		height: 2.75rem;
		border: 0;
		border-radius: 50%;
		background: color-mix(in srgb, var(--text-hi) 8%, transparent);
		color: var(--text-hi);
		cursor: pointer;
	}
	.burger {
		position: relative;
		width: 1.1rem;
		height: 0.7rem;
	}
	.burger i {
		position: absolute;
		left: 0;
		right: 0;
		height: 1.6px;
		border-radius: 1px;
		background: currentColor;
		transition: transform 0.35s var(--ease-out);
	}
	.burger i:first-child {
		top: 0;
	}
	.burger i:last-child {
		bottom: 0;
	}
	.open .burger i:first-child {
		transform: translateY(0.3rem) rotate(45deg);
	}
	.open .burger i:last-child {
		transform: translateY(-0.3rem) rotate(-45deg);
	}
	.m-only {
		display: none;
	}
	@media (prefers-reduced-motion: reduce) {
		.txt,
		.burger i {
			transition: none;
		}
	}

	/* ---------- desktop: one line from 1021 px, tighter until 1280 px ---------- */
	@media (min-width: 1021px) {
		.nav a {
			white-space: nowrap;
		}
	}
	@media (min-width: 1021px) and (max-width: 1279px) {
		.capsule {
			gap: var(--sp-3);
		}
		.nav a {
			padding-inline: 0.7rem;
		}
		.lang {
			padding-inline: 0.55rem;
		}
		.go {
			padding: 0 0.85rem 0 0.95rem;
		}
	}

	/* ---------- compact: full-screen menu ---------- */
	@media (max-width: 1020px) {
		.menu {
			display: inline-grid;
		}
		.nav {
			position: fixed;
			inset: 0;
			z-index: -1;
			display: block;
			padding: 6.5rem clamp(1.25rem, 6vw, 3rem) 2rem;
			background: color-mix(in srgb, var(--bg-0) 96%, transparent);
			backdrop-filter: blur(20px);
			-webkit-backdrop-filter: blur(20px);
			opacity: 0;
			visibility: hidden;
			transition:
				opacity 0.35s var(--ease-out),
				visibility 0s 0.35s;
			pointer-events: auto;
		}
		.open .nav {
			opacity: 1;
			visibility: visible;
			transition: opacity 0.35s var(--ease-out);
		}
		ul {
			flex-direction: column;
			gap: 0;
		}
		.hl {
			display: none;
		}
		.nav a {
			padding: 0.85rem 0;
			border-radius: 0;
			border-bottom: 1px solid var(--line);
			font-size: clamp(1.7rem, 7vw, 2.6rem);
			font-weight: 720;
			font-stretch: 112%;
			letter-spacing: -0.02em;
			color: var(--text-hi);
			overflow: visible;
		}
		.nav a.hot .txt {
			color: var(--text-hi);
		}
			.nav a[aria-current='page']::after {
			display: none;
		}
		.open .nav li {
			animation: menu-in 0.5s var(--ease-out) both;
			animation-delay: calc(var(--i) * 45ms + 60ms);
		}
		.m-only {
			display: block;
		}
		.m-only a {
			color: var(--text);
			font-size: clamp(1.2rem, 5vw, 1.6rem);
		}
	}
	@keyframes menu-in {
		from {
			opacity: 0;
			transform: translate3d(0, 1rem, 0);
		}
	}
	@media (max-width: 1020px) and (prefers-reduced-motion: reduce) {
		.open .nav li {
			animation: none;
		}
	}
	@media (max-width: 560px) {
		.go {
			display: none;
		}
		.capsule {
			padding-left: 0.9rem;
		}
	}
</style>
