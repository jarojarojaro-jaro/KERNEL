<script lang="ts">
	import { store } from '../lib/store.svelte';
	import Logo from './Logo.svelte';

	const t = $derived(store.t);
</script>

<header class="site-header">
	<div class="capsule">
		<span class="brand">
			<Logo />
			<span class="sub">{t.brandSub}</span>
			{#if store.state?.version}<span class="ver num">v{store.state.version}</span>{/if}
		</span>
		<div class="tools">
			<div class="lang" role="group" aria-label={t.langLabel}>
				<button type="button" class:cur={store.lang === 'pl'} aria-pressed={store.lang === 'pl'} lang="pl" onclick={() => store.setLang('pl')}>PL</button>
				<span class="sep" aria-hidden="true">/</span>
				<button type="button" class:cur={store.lang === 'en'} aria-pressed={store.lang === 'en'} lang="en" onclick={() => store.setLang('en')}>EN</button>
			</div>
			<button
				type="button"
				class="theme"
				aria-label={store.theme === 'dark' ? t.themeToLight : t.themeToDark}
				title={store.theme === 'dark' ? t.themeToLight : t.themeToDark}
				onclick={() => store.setTheme(store.theme === 'dark' ? 'light' : 'dark')}
			>
				{#if store.theme === 'dark'}
					<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true">
						<circle cx="12" cy="12" r="4.2" />
						<path d="M12 2.5v2.2M12 19.3v2.2M2.5 12h2.2M19.3 12h2.2M5.3 5.3l1.6 1.6M17.1 17.1l1.6 1.6M5.3 18.7l1.6-1.6M17.1 6.9l1.6-1.6" />
					</svg>
				{:else}
					<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" aria-hidden="true">
						<path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z" />
					</svg>
				{/if}
			</button>
		</div>
	</div>
</header>

<style>
	.site-header {
		position: sticky;
		top: 0;
		z-index: var(--z-header);
		padding: 0.6rem clamp(0.5rem, 1.5vw, 1rem) 0;
	}
	.capsule {
		display: flex;
		align-items: center;
		gap: var(--sp-4);
		height: 3.6rem;
		max-width: 92rem;
		margin-inline: auto;
		padding: 0 0.45rem 0 1.1rem;
		border: 1px solid color-mix(in srgb, var(--text-hi) 9%, transparent);
		border-radius: var(--r-pill);
		background: color-mix(in srgb, var(--bg-1) 78%, transparent);
		backdrop-filter: saturate(1.4) blur(18px);
		-webkit-backdrop-filter: saturate(1.4) blur(18px);
		box-shadow:
			0 1px 0 rgb(255 255 255 / 0.04) inset,
			0 12px 40px -18px rgb(0 0 0 / 0.8);
	}
	:global(:root[data-theme='light']) .capsule {
		box-shadow: var(--shadow-2);
	}
	.brand {
		display: inline-flex;
		align-items: center;
		gap: var(--sp-3);
		min-width: 0;
	}
	.sub {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-mute);
		padding-left: var(--sp-3);
		border-left: 1px solid var(--line);
		white-space: nowrap;
	}
	.ver {
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.tools {
		display: flex;
		align-items: center;
		gap: 0.25rem;
		margin-left: auto;
	}
	.lang {
		display: inline-flex;
		align-items: center;
	}
	.lang button {
		min-width: 2.25rem;
		height: 2.5rem;
		padding: 0 0.45rem;
		border: 0;
		border-radius: var(--r-pill);
		background: none;
		font-family: var(--font-mono);
		font-size: 0.72rem;
		letter-spacing: 0.08em;
		color: var(--text-mute);
		cursor: pointer;
	}
	.lang button:hover {
		color: var(--text-hi);
	}
	.lang button.cur {
		color: var(--text-hi);
		font-weight: 700;
	}
	.sep {
		color: var(--text-mute);
		opacity: 0.6;
		font-size: 0.72rem;
	}
	.theme {
		display: inline-grid;
		place-items: center;
		width: 2.6rem;
		height: 2.6rem;
		border-radius: var(--r-pill);
		border: 1px solid var(--line);
		background: var(--bg-2);
		color: var(--text-hi);
		cursor: pointer;
		transition: border-color var(--dur-2) var(--ease-out);
	}
	.theme:hover {
		border-color: var(--line-strong);
	}
	@media (max-width: 640px) {
		.sub,
		.ver {
			display: none;
		}
		.capsule {
			padding-left: 0.9rem;
		}
	}
</style>
