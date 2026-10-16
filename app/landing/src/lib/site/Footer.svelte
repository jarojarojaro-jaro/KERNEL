<script lang="ts">
	import { BRAND } from '$lib/brand';
	import { currentLang, href } from '$lib/i18n';
	import { consent } from './consent.svelte';
	import { copy } from './copy';
	import Logo from './Logo.svelte';

	const lang = $derived(currentLang());
	const t = $derived(copy[lang]);
	const legal = ['terms', 'privacy', 'cookies', 'ai', 'imprint'] as const;
</script>

<footer class="site-footer">
	<div class="container grid">
		<div class="about stack">
			<Logo />
			<p class="mute small">{t.footer.tagline}</p>
			<p class="source">{t.footer.credit}</p>
		</div>
		<nav aria-labelledby="f-product">
			<h2 id="f-product" class="overline">{t.footer.product}</h2>
			<ul>
				<li><a href={href(lang, '/#how')}>{t.nav.how}</a></li>
				<li><a href={href(lang, '/#results')}>{t.nav.results}</a></li>
				<li><a href={href(lang, '/methodology')}>{t.nav.methodology}</a></li>
				<li><a href={href(lang, '/scan')}>{t.privacy.scanLink}</a></li>
				<li><a href={href(lang, '/start')}>{t.nav.start}</a></li>
				<li><a href={href(lang, '/app')}>{t.footer.prototype}</a></li>
			</ul>
		</nav>
		<nav aria-labelledby="f-legal">
			<h2 id="f-legal" class="overline">{t.footer.legal}</h2>
			<ul>
				{#each legal as d (d)}
					<li><a href={href(lang, `/legal/${d}`)}>{t.footer.legalLinks[d]}</a></li>
				{/each}
				<li><button class="linklike" type="button" onclick={() => (consent.open = true)}>{t.footer.cookieSettings}</button></li>
			</ul>
		</nav>
	</div>
	<div class="container base">
		<p>{t.footer.draftNote} {t.footer.company}</p>
		<p>{t.footer.name} © 2026 {BRAND.company.legalName ?? BRAND.name}</p>
	</div>
</footer>

<style>
	.site-footer {
		border-top: 1px solid var(--line);
		background: var(--bg-1);
		padding-block: var(--sp-16) var(--sp-8);
		margin-top: var(--sp-16);
	}
	.grid {
		display: grid;
		grid-template-columns: 2fr 1fr 1fr;
		gap: var(--sp-10);
	}
	.about {
		--stack: var(--sp-3);
		max-width: 22rem;
	}
	ul {
		list-style: none;
		padding: 0;
		margin: var(--sp-4) 0 0;
		display: grid;
		gap: var(--sp-2);
	}
	a,
	.linklike {
		color: var(--text);
		text-decoration: none;
		font-size: var(--fs-sm);
	}
	a:hover,
	.linklike:hover {
		color: var(--text-hi);
		text-decoration: underline;
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
	.base {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		gap: var(--sp-3);
		margin-top: var(--sp-12);
		padding-top: var(--sp-6);
		border-top: 1px solid var(--line);
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	@media (max-width: 720px) {
		.grid {
			grid-template-columns: 1fr 1fr;
		}
		.about {
			grid-column: 1 / -1;
		}
	}
</style>
