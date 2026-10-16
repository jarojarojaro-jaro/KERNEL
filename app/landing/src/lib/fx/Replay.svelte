<script lang="ts">
	/** Small round "play the scene again" button for auto-played scenes. */
	let { onclick, lang, disabled = false }: { onclick: () => void; lang: 'pl' | 'en'; disabled?: boolean } = $props();
	const label = $derived(lang === 'pl' ? 'Odtwórz ponownie' : 'Play again');
</script>

<button type="button" class="replay" {onclick} {disabled} aria-label={label} title={label}>
	<svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true"><path d="M3 8a5 5 0 1 0 1.6-3.7M3 2.5v2.8h2.8" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linecap="round" /></svg>
</button>

<style>
	.replay {
		display: inline-grid;
		place-items: center;
		width: 2.5rem;
		height: 2.5rem;
		border-radius: 50%;
		border: 1px solid var(--line-strong);
		background: var(--bg-2);
		color: var(--text-hi);
		cursor: pointer;
		transition:
			background var(--dur-2),
			opacity var(--dur-2),
			transform var(--dur-1);
	}
	.replay:hover {
		background: var(--bg-3);
	}
	.replay:active {
		transform: scale(0.94);
	}
	.replay:disabled {
		opacity: 0.35;
		cursor: default;
	}
</style>
