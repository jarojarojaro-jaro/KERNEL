<script lang="ts">
	import { afterNavigate } from '$app/navigation';
	import { page } from '$app/state';
	import { magnetic } from '$lib/fx/actions';
	import { reducedMotion } from '$lib/fx/motion';
	import { cardsHref, currentLang, href, resultsHref, switchLangHref } from '$lib/i18n';
	import { tick } from 'svelte';
	import { copy } from './copy';
	import Logo from './Logo.svelte';
	import ThemeToggle from './ThemeToggle.svelte';

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
		root.dataset.theme = theme === 'light' || theme === 'dark' ? theme : matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
	});

	const links = $derived([
		{ label: t.how, to: href(lang, '/#how') },
		{ label: t.results, to: resultsHref(lang) },
		{ label: t.cards, to: cardsHref(lang) },
		{ label: t.quality, to: href(lang, '/#quality') },
		{ label: t.methodology, to: href(lang, '/methodology') }
	]);
	const current = (to: string) => !to.includes('#') && page.url.pathname.startsWith(to);

	/* Sliding highlight: one pill that glides to the hovered or focused item. */
	let list: HTMLUListElement | undefined = $state();
	let hl = $state({ x: 0, w: 0, on: false });
	function point(e: Event) {
		const a = (e.target as HTMLElement).closest('a');
		if (!a || !list || innerWidth <= 1020) return;
		const r = a.getBoundingClientRect();
		const l = list.getBoundingClientRect();
		hl = { x: r.left - l.left, w: r.width, on: true };
	}

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
	<div class="capsule">
		<a class="brand" href={href(lang)}>
			<Logo />
		</a>
		<nav aria-label={t.main} class="nav" id="site-nav">
			<!-- svelte-ignore a11y_mouse_events_have_key_events (focusin covers keyboard) -->
			<ul bind:this={list} onpointerover={point} onfocusin={point} onpointerleave={() => (hl.on = false)} onfocusout={() => (hl.on = false)}>
				<span class="hl" class:on={hl.on} style="transform: translate3d({hl.x}px, 0, 0); width: {hl.w}px" aria-hidden="true"></span>
				{#each links as l, i (l.to)}
					<li style="--i:{i}">
						<a href={l.to} aria-current={current(l.to) ? 'page' : undefined} onclick={() => (open = false)}>
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
			{#if !showcase}<ThemeToggle toDark={t.themeToDark} toLight={t.themeToLight} />{/if}
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
	.hl {
		position: absolute;
		top: 0;
		bottom: 0;
		left: 0;
		border-radius: var(--r-pill);
		background: color-mix(in srgb, var(--text-hi) 9%, transparent);
		opacity: 0;
		transition:
			transform 0.35s var(--ease-out),
			width 0.35s var(--ease-out),
			opacity 0.25s;
		pointer-events: none;
	}
	.hl.on {
		opacity: 1;
	}
	.nav a {
		position: relative;
		display: flex;
		align-items: baseline;
		gap: 0.4rem;
		padding: 0.55rem 0.85rem;
		border-radius: var(--r-pill);
		color: var(--text);
		font-size: var(--fs-sm);
		font-weight: 520;
		line-height: 1.25;
		text-decoration: none;
		overflow: hidden;
		transition: color var(--dur-2);
	}
	/* Rolling label: one text node, its shadow copy sits below and rolls up on hover. */
	.txt {
		display: inline-block;
		text-shadow: 0 2em 0 var(--text-hi);
		transition: transform 0.38s var(--ease-out);
	}
	.nav a:hover,
	.nav a:focus-visible,
	.nav a[aria-current='page'] {
		color: var(--text-hi);
	}
	.nav a:hover .txt {
		transform: translateY(-2em);
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
		.hl,
		.burger i {
			transition: none;
		}
		.nav a:hover .txt {
			transform: none;
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
		.txt {
			text-shadow: none;
		}
		.nav a:hover .txt {
			transform: none;
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
