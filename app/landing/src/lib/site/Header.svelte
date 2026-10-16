<script lang="ts">
	import { currentLang, href, switchLangHref } from '$lib/i18n';
	import { copy } from './copy';
	import Logo from './Logo.svelte';
	import ThemeToggle from './ThemeToggle.svelte';

	const lang = $derived(currentLang());
	const t = $derived(copy[lang].nav);
	const other = $derived(lang === 'pl' ? 'en' : 'pl');
	let open = $state(false);

	const links = $derived([
		{ label: t.how, to: '/#how' },
		{ label: t.results, to: '/#results' },
		{ label: t.bits, to: '/#bits' },
		{ label: t.hardware, to: '/#hardware' },
		{ label: t.pricing, to: '/#pricing' },
		{ label: t.methodology, to: '/methodology' }
	]);
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && (open = false)} />

<a class="skip-link" href="#main">{t.skip}</a>
<header class="site-header">
	<div class="container header-bar">
		<a class="brand" href={href(lang)}>
			<Logo />
		</a>
		<nav aria-label={t.main} class="nav" class:open id="site-nav">
			<ul>
				{#each links as l (l.to)}
					<li><a href={href(lang, l.to)} onclick={() => (open = false)}>{l.label}</a></li>
				{/each}
			</ul>
		</nav>
		<div class="actions">
			<a class="lang" href={switchLangHref(other)} hreflang={other} title={t.langLabel} data-sveltekit-reload>
				{other.toUpperCase()}<span class="sr-only" lang={other}> – {t.lang}</span>
			</a>
			<ThemeToggle toDark={t.themeToDark} toLight={t.themeToLight} />
			<a class="btn btn--primary btn--sm cta" href={href(lang, '/start')}>{t.start}</a>
			<button
				class="icon-btn menu"
				type="button"
				aria-expanded={open}
				aria-controls="site-nav"
				aria-label={open ? t.close : t.menu}
				onclick={() => (open = !open)}
			>
				<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true">
					{#if open}<path d="M6 6l12 12M18 6 6 18" />{:else}<path d="M4 7h16M4 12h16M4 17h16" />{/if}
				</svg>
			</button>
		</div>
	</div>
</header>

<style>
	.site-header {
		position: sticky;
		top: 0;
		z-index: var(--z-header);
		background: color-mix(in srgb, var(--bg-0) 82%, transparent);
		backdrop-filter: saturate(1.4) blur(14px);
		-webkit-backdrop-filter: saturate(1.4) blur(14px);
		border-bottom: 1px solid var(--line);
	}
	.header-bar {
		display: flex;
		align-items: center;
		gap: var(--sp-6);
		height: 4rem;
	}
	.brand {
		text-decoration: none;
		flex: none;
	}
	.nav {
		flex: 1;
	}
	.nav ul {
		display: flex;
		gap: var(--sp-1);
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.nav a {
		display: block;
		padding: 0.45rem 0.7rem;
		border-radius: var(--r-sm);
		color: var(--text);
		font-size: var(--fs-sm);
		font-weight: var(--fw-medium);
		text-decoration: none;
	}
	.nav a:hover {
		color: var(--text-hi);
		background: var(--bg-3);
	}
	.actions {
		display: flex;
		align-items: center;
		gap: var(--sp-2);
		margin-left: auto;
	}
	.lang {
		display: inline-grid;
		place-items: center;
		height: 2.5rem;
		min-width: 2.5rem;
		padding: 0 0.5rem;
		border: 1px solid var(--line);
		border-radius: var(--r-sm);
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		font-weight: var(--fw-medium);
		letter-spacing: 0.08em;
		color: var(--text-hi);
		text-decoration: none;
	}
	.lang:hover {
		background: var(--bg-3);
	}
	.menu {
		display: none;
	}
	@media (max-width: 960px) {
		.menu {
			display: inline-grid;
		}
		.nav {
			display: none;
			position: absolute;
			inset: 4rem 0 auto 0;
			background: var(--bg-0);
			border-bottom: 1px solid var(--line);
			padding: var(--sp-3) var(--gutter) var(--sp-5);
		}
		.nav.open {
			display: block;
		}
		.nav ul {
			flex-direction: column;
		}
		.nav a {
			padding: 0.75rem 0.5rem;
			font-size: var(--fs-base);
		}
	}
	@media (max-width: 420px) {
		.cta {
			display: none;
		}
	}
</style>
