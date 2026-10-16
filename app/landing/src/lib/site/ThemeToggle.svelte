<script lang="ts">
	import { onMount } from 'svelte';

	let { toDark, toLight }: { toDark: string; toLight: string } = $props();
	let theme = $state<'dark' | 'light'>('dark');

	onMount(() => {
		theme = document.documentElement.dataset.theme === 'light' ? 'light' : 'dark';
	});

	function toggle() {
		theme = theme === 'dark' ? 'light' : 'dark';
		document.documentElement.dataset.theme = theme;
		document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? '#050506' : '#f4f2ee');
		try {
			localStorage.setItem('theme', theme);
		} catch {
			/* storage blocked: theme applies to this page view only */
		}
	}
</script>

<button class="icon-btn" type="button" onclick={toggle} aria-label={theme === 'dark' ? toLight : toDark} title={theme === 'dark' ? toLight : toDark}>
	{#if theme === 'dark'}
		<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></svg>
	{:else}
		<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 14.5A8.5 8.5 0 0 1 9.5 4a8.5 8.5 0 1 0 10.5 10.5Z" /></svg>
	{/if}
</button>
