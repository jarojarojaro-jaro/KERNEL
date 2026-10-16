<script lang="ts">
	import { page } from '$app/state';
	import { currentLang, href, num } from '$lib/i18n';
	import { T } from './i18n';
	import { SCREENS } from './nav';
	import { DEMO } from './demo';
	import Icon from './Icon.svelte';

	let { id, open = false }: { id: string; open?: boolean } = $props();

	const lang = $derived(currentLang());
	const t = $derived(T[lang]);
	const items = $derived([
		{ label: t.nav.overview, url: href(lang, '/app'), icon: 'overview' as const },
		...SCREENS.filter((s) => s.sidebar).map((s) => ({ label: t.nav[s.key], url: href(lang, s.path), icon: s.icon }))
	]);
	const current = (url: string) => page.url.pathname === url || page.url.pathname === url.replace(/\/$/, '');
</script>

<nav {id} class="sidebar" class:open aria-label={t.shell.navLabel}>
	<ul>
		{#each items as it (it.url)}
			<li>
				<a href={it.url} aria-current={current(it.url) ? 'page' : undefined}>
					<Icon name={it.icon} size={18} />
					<span>{it.label}</span>
				</a>
			</li>
		{/each}
	</ul>

	<div class="machine">
		<p class="overline">{t.shell.machine}</p>
		<p class="gpu">{t.shell.machineGpu}</p>
		<p class="mem num">{t.shell.machineMem(num(DEMO.vramGiB, lang), num(DEMO.ramGiB, lang))}</p>
		<a class="site small" href={href(lang, '/')}>{t.shell.backToSite}</a>
	</div>
</nav>

<style>
	.sidebar {
		display: flex;
		flex-direction: column;
		justify-content: space-between;
		gap: var(--sp-6);
		padding: var(--sp-4) var(--sp-3);
		background: var(--bg-1);
		border-right: 1px solid var(--line);
		overflow-y: auto;
	}
	ul {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 2px;
	}
	a[href] {
		text-decoration: none;
	}
	li a {
		position: relative;
		display: flex;
		align-items: center;
		gap: var(--sp-3);
		padding: 0.55rem var(--sp-3);
		border-radius: var(--r-sm);
		color: var(--text);
		font-size: var(--fs-sm);
		font-weight: var(--fw-medium);
		transition: background-color var(--dur-1) var(--ease-out);
	}
	li a:hover {
		background: var(--bg-3);
		color: var(--text-hi);
	}
	li a[aria-current='page'] {
		background: var(--bg-3);
		color: var(--text-hi);
	}
	li a[aria-current='page']::before {
		content: '';
		position: absolute;
		left: calc(-1 * var(--sp-3));
		top: 0.4rem;
		bottom: 0.4rem;
		width: 3px;
		border-radius: 0 var(--r-xs) var(--r-xs) 0;
		background: var(--text-hi);
	}
	li a[aria-current='page'] :global(svg) {
		color: var(--text-hi);
	}
	.machine {
		display: grid;
		gap: var(--sp-1);
		padding: var(--sp-4);
		border: 1px solid var(--line);
		border-radius: var(--r-md);
		background: var(--bg-2);
	}
	.gpu {
		color: var(--text-hi);
		font-weight: var(--fw-medium);
		font-size: var(--fs-sm);
	}
	.mem {
		color: var(--text-mute);
		font-size: var(--fs-xs);
	}
	.site {
		margin-top: var(--sp-2);
		color: var(--text-hi);
		text-decoration: underline;
	}

	@media (max-width: 720px) {
		.sidebar {
			display: none;
			border-right: 0;
			border-bottom: 1px solid var(--line);
		}
		.sidebar.open {
			display: flex;
		}
	}
</style>
