<script lang="ts">
	import { afterNavigate } from '$app/navigation';
	import TitleBar from '$lib/desktop/TitleBar.svelte';
	import Sidebar from '$lib/desktop/Sidebar.svelte';
	import StatusStrip from '$lib/desktop/StatusStrip.svelte';
	import { currentLang } from '$lib/i18n';
	import { T } from '$lib/desktop/i18n';

	let { children } = $props();
	const lang = $derived(currentLang());
	const t = $derived(T[lang]);
	// hooks.server sets <html lang> for the prerendered page; keep it right after client-side switches.
	$effect(() => {
		document.documentElement.lang = lang;
	});
	const navId = 'app-nav';
	let navOpen = $state(false);
	let main: HTMLElement | undefined = $state();

	afterNavigate(({ from }) => {
		navOpen = false;
		// The window scrolls inside <main>; start each screen at the top like a real app view.
		if (from) main?.scrollTo({ top: 0 });
	});
</script>

<svelte:head>
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="desk bg-grid">
	<a class="skip-link" href="#app-main">{t.shell.skip}</a>
	<div class="window">
		<TitleBar bind:navOpen {navId} />
		<div class="frame">
			<Sidebar id={navId} open={navOpen} />
			<main id="app-main" tabindex="-1" bind:this={main}>
				<div class="content">
					{@render children()}
				</div>
			</main>
		</div>
		<StatusStrip />
	</div>
</div>

<style>
	.desk {
		min-height: 100dvh;
		padding: var(--sp-5);
		background-color: var(--bg-0);
	}
	.window {
		display: grid;
		grid-template-rows: auto minmax(0, 1fr) auto;
		height: calc(100dvh - 2 * var(--sp-5));
		min-height: 36rem;
		max-width: 100rem;
		margin-inline: auto;
		border: 1px solid var(--line-strong);
		border-radius: var(--r-lg);
		background: var(--bg-1);
		box-shadow: var(--shadow-2);
		overflow: hidden;
	}
	.frame {
		display: grid;
		grid-template-columns: 15rem minmax(0, 1fr);
		min-height: 0;
	}
	main {
		min-width: 0;
		overflow-y: auto;
		background: var(--bg-0);
		outline: none;
	}
	.content {
		max-width: 76rem;
		margin-inline: auto;
		padding: var(--sp-8) var(--sp-8) var(--sp-12);
	}

	@media (max-width: 1100px) {
		.desk {
			padding: var(--sp-3);
		}
		.window {
			height: calc(100dvh - 2 * var(--sp-3));
		}
		.frame {
			grid-template-columns: 13rem minmax(0, 1fr);
		}
		.content {
			padding: var(--sp-6) var(--sp-6) var(--sp-10);
		}
	}
	@media (max-width: 720px) {
		.desk {
			padding: 0;
		}
		.window {
			height: auto;
			min-height: 100dvh;
			border: 0;
			border-radius: 0;
			box-shadow: none;
			overflow: visible;
		}
		.frame {
			grid-template-columns: minmax(0, 1fr);
			grid-template-rows: auto 1fr;
		}
		main {
			overflow: visible;
		}
		.content {
			padding: var(--sp-5) var(--sp-4) var(--sp-10);
		}
	}
</style>
