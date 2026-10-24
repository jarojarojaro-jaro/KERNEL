<script lang="ts">
	/** Copies `text`; the result is announced through a polite live region. */
	import { store } from '../lib/store.svelte';

	let { text, label }: { text: string; label?: string } = $props();
	const t = $derived(store.t.ready);
	let status = $state<'idle' | 'ok' | 'fail'>('idle');
	let timer: number | undefined;

	async function copy() {
		let ok = false;
		try {
			await navigator.clipboard.writeText(text);
			ok = true;
		} catch {
			// Older webviews: the selection-based fallback.
			const ta = document.createElement('textarea');
			ta.value = text;
			ta.setAttribute('readonly', '');
			ta.style.position = 'fixed';
			ta.style.opacity = '0';
			document.body.append(ta);
			ta.select();
			ok = document.execCommand('copy');
			ta.remove();
		}
		status = ok ? 'ok' : 'fail';
		clearTimeout(timer);
		timer = window.setTimeout(() => (status = 'idle'), 1800);
	}
</script>

<button type="button" class="copy" onclick={copy} aria-label={label ? `${t.copy}: ${label}` : t.copy}>
	{#if status === 'ok'}
		<svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true"><path d="M3 8.5l3 3 7-7" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" /></svg>
	{:else}
		<svg width="14" height="14" viewBox="0 0 16 16" aria-hidden="true"><rect x="5" y="5" width="8.5" height="8.5" rx="1.6" fill="none" stroke="currentColor" stroke-width="1.5" /><path d="M10.5 3.2V3a1.5 1.5 0 0 0-1.5-1.5H3A1.5 1.5 0 0 0 1.5 3v6A1.5 1.5 0 0 0 3 10.5h.2" fill="none" stroke="currentColor" stroke-width="1.5" /></svg>
	{/if}
	<span>{status === 'ok' ? t.copied : status === 'fail' ? t.copyFailed : t.copy}</span>
</button>
<span class="sr-only" aria-live="polite">{status === 'ok' ? t.copied : status === 'fail' ? t.copyFailed : ''}</span>

<style>
	.copy {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		flex: none;
		height: 2rem;
		padding: 0 0.75rem;
		border: 1px solid var(--line-strong);
		border-radius: var(--r-pill);
		background: var(--bg-2);
		color: var(--text-hi);
		font: inherit;
		font-family: var(--font-sans);
		font-size: var(--fs-xs);
		font-weight: 600;
		letter-spacing: 0;
		text-transform: none;
		cursor: pointer;
		transition: border-color var(--dur-2) var(--ease-out);
	}
	.copy:hover {
		border-color: var(--text-hi);
	}
</style>
