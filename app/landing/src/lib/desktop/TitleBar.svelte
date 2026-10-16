<script lang="ts">
	import { onMount } from 'svelte';
	import { BRAND } from '$lib/brand';
	import { currentLang, href, switchLangHref, LANGS } from '$lib/i18n';
	import { T } from './i18n';
	import Icon from './Icon.svelte';
	import Mark from './Mark.svelte';

	let { navOpen = $bindable(false), navId }: { navOpen?: boolean; navId: string } = $props();

	const lang = $derived(currentLang());
	const t = $derived(T[lang]);

	let theme = $state<'dark' | 'light'>('dark');
	onMount(() => {
		theme = document.documentElement.dataset.theme === 'light' ? 'light' : 'dark';
	});
	function toggleTheme() {
		theme = theme === 'dark' ? 'light' : 'dark';
		document.documentElement.dataset.theme = theme;
		try {
			localStorage.setItem('theme', theme);
		} catch {
			/* storage blocked: the choice lasts for this page view */
		}
	}
</script>

<header class="titlebar" data-tauri-drag-region>
	<div class="brand">
		<a class="home" href={href(lang, '/app')} aria-label={BRAND.name}>
			<Mark size={22} />
			<span class="name">{BRAND.name}</span>
		</a>
		<span class="badge badge--prototype proto" title={t.shell.protoTitle}>
			<span class="long">{t.shell.protoLong}</span>
			<span class="short">{t.shell.protoShort}</span>
		</span>
	</div>

	<div class="tools">
		<nav class="langs" aria-label={t.shell.langLabel}>
			{#each LANGS as l (l)}
				<a
					href={switchLangHref(l)}
					hreflang={l}
					lang={l}
					aria-current={l === lang ? 'true' : undefined}
					data-sveltekit-noscroll>{l.toUpperCase()}</a
				>
			{/each}
		</nav>
		<button
			type="button"
			class="icon-btn tool"
			onclick={toggleTheme}
			aria-label={theme === 'dark' ? t.shell.themeToLight : t.shell.themeToDark}
		>
			<Icon name={theme === 'dark' ? 'sun' : 'moon'} size={18} />
		</button>
		<button
			type="button"
			class="icon-btn tool menu"
			aria-expanded={navOpen}
			aria-controls={navId}
			aria-label={navOpen ? t.shell.menuClose : t.shell.menuOpen}
			onclick={() => (navOpen = !navOpen)}
		>
			<Icon name={navOpen ? 'close' : 'menu'} size={18} />
		</button>
		<!-- Decorative window controls of the desktop mock; the real ones come from Tauri. -->
		<div class="winctl" aria-hidden="true">
			<span><Icon name="minimize" size={14} /></span>
			<span><Icon name="maximize" size={14} /></span>
			<span><Icon name="close" size={14} /></span>
		</div>
	</div>
</header>

<style>
	.titlebar {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--sp-4);
		min-height: 2.875rem;
		padding: 0 0 0 var(--sp-4);
		background: var(--bg-1);
		border-bottom: 1px solid transparent;
		border-image: linear-gradient(90deg, transparent, var(--heat-3) 30%, var(--heat-4) 50%, var(--heat-2) 70%, transparent) 1;
		user-select: none;
	}
	.brand {
		display: flex;
		align-items: center;
		gap: var(--sp-4);
		min-width: 0;
	}
	.home {
		display: inline-flex;
		align-items: center;
		gap: var(--sp-2);
		color: var(--text-hi);
		text-decoration: none;
		font-weight: var(--fw-semibold);
		letter-spacing: var(--tracking-tight);
		white-space: nowrap;
	}
	.proto {
		min-width: 0;
		overflow: hidden;
		text-overflow: ellipsis;
	}
	.short {
		display: none;
	}
	.tools {
		display: flex;
		align-items: center;
		gap: var(--sp-2);
		align-self: stretch;
	}
	.langs {
		display: flex;
		gap: 2px;
		padding: 2px;
		border: 1px solid var(--line);
		border-radius: var(--r-sm);
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
	}
	.langs a {
		padding: 0.2rem 0.5rem;
		border-radius: var(--r-xs);
		color: var(--text-mute);
		text-decoration: none;
	}
	.langs a:hover {
		color: var(--text-hi);
	}
	.langs a[aria-current='true'] {
		background: var(--bg-3);
		color: var(--text-hi);
	}
	.tool {
		width: 2.25rem;
		height: 2.25rem;
		border-color: transparent;
	}
	.menu {
		display: none;
	}
	.winctl {
		display: flex;
		align-self: stretch;
		margin-left: var(--sp-2);
		border-left: 1px solid var(--line);
	}
	.winctl span {
		display: grid;
		place-items: center;
		width: 2.75rem;
		color: var(--text-mute);
	}

	@media (max-width: 1180px) {
		.long {
			display: none;
		}
		.short {
			display: inline;
		}
	}
	@media (max-width: 720px) {
		.titlebar {
			padding-right: var(--sp-2);
		}
		.winctl {
			display: none;
		}
		.menu {
			display: inline-grid;
		}
	}
	@media (max-width: 400px) {
		.name {
			display: none;
		}
	}
</style>
