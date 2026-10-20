<script lang="ts">
	import { BRAND } from '$lib/brand';
	import { cardsHref, currentLang, href } from '$lib/i18n';
	import { page } from '$app/state';
	import { consent } from './consent.svelte';
	import ThemeToggle from './ThemeToggle.svelte';
	import { copy } from './copy';
	import Logo from './Logo.svelte';

	const lang = $derived(currentLang());
	const t = $derived(copy[lang]);
	const legal = ['terms', 'privacy', 'cookies', 'ai', 'imprint'] as const;
</script>

<footer class="site-footer">
	<div class="wrap grid">
		<div class="about">
			<Logo />
			<p class="tag">{t.footer.tagline}</p>
			<p class="fine-print">{t.footer.credit}</p>
			<p class="fine-print">{t.footer.aiMedia}</p>
		</div>
		<nav aria-labelledby="f-product">
			<h2 id="f-product" class="lbl">{t.footer.product}</h2>
			<ul>
				<li><a href={href(lang, '/#how')}>{t.nav.how}</a></li>
				<li><a href={href(lang, '/#results')}>{t.nav.results}</a></li>
				<li><a href={cardsHref(lang)}>{t.nav.cards}</a></li>
				<li><a href={href(lang, '/methodology')}>{t.nav.methodology}</a></li>
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
				<!-- The theme switch lives here (not in the nav) so the nav is identical on every page;
				     the showcase pages are dark-only, so it is offered only elsewhere. -->
				{#if !page.url.pathname.match(/^\/(pl|en)\/((karty|cards|wyniki|results)\/.*)?$/)}<li class="theme"><ThemeToggle toDark={t.nav.themeToDark} toLight={t.nav.themeToLight} /></li>{/if}
			</ul>
		</nav>
	</div>
	<p class="word" aria-hidden="true">{BRAND.name}</p>
	<div class="wrap base">
		<p>{t.footer.draftNote} {t.footer.company}</p>
		<p>{t.footer.name} © 2026 {BRAND.company.legalName ?? BRAND.name}</p>
	</div>
</footer>

<style>
	.site-footer {
		position: relative;
		overflow: clip;
		border-top: 1px solid var(--line);
		background:
			radial-gradient(60% 50% at 50% 120%, rgb(255 122 26 / 0.12), transparent 70%),
			var(--bg-0);
		padding-block: var(--sp-16) var(--sp-8);
		margin-top: var(--sp-16);
	}
	:global([data-showcase]) .site-footer {
		margin-top: 0;
	}
	.wrap {
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
	}
	.grid {
		display: grid;
		grid-template-columns: 2fr 1fr 1fr;
		gap: var(--sp-10);
	}
	.about {
		display: grid;
		gap: var(--sp-4);
		align-content: start;
		max-width: 24rem;
	}
	.tag {
		font-size: var(--fs-md);
		color: var(--text);
		line-height: 1.45;
	}
	.fine-print {
		font-size: var(--fs-xs);
		color: var(--text-mute);
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
		margin: var(--sp-4) 0 0;
		display: grid;
		gap: var(--sp-2);
	}
	a,
	.linklike {
		color: var(--text);
		text-decoration: none;
		font-size: var(--fs-sm);
		transition: color var(--dur-2);
	}
	a:hover,
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
	/* giant outlined wordmark, a nameplate above the legal line */
	.word {
		/* the clipped fill needs the glyphs' full height: line-height 0.8 is shorter than the ę and
		   the accents, so the box is padded and the margins give the space back */
		margin: calc(var(--sp-12) - 0.08em) 0 calc(var(--sp-6) - 0.24em);
		padding: 0.08em 0.06em 0.24em;
		text-align: center;
		font-family: var(--font-display);
		/* ~4em wide: 20vw keeps it inside the gutters down to 320 px */
		font-size: clamp(3rem, 20vw, 22rem);
		font-weight: 860;
		font-stretch: 125%;
		letter-spacing: -0.06em;
		line-height: 0.8;
		color: transparent;
		-webkit-text-stroke: 1px color-mix(in srgb, var(--text-hi) 16%, transparent);
		background: linear-gradient(180deg, color-mix(in srgb, var(--text-hi) 7%, transparent), transparent 85%);
		-webkit-background-clip: text;
		background-clip: text;
		user-select: none;
		white-space: nowrap;
	}
	.base {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		gap: var(--sp-3);
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
