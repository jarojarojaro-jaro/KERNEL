<script lang="ts">
	/** Tacho mark (design/logo/mark.svg) + the site wordmark; the redline uses the theme-aware heat ink. */
	let { size = 28 }: { size?: number } = $props();
</script>

<span class="logo">
	<svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true" focusable="false">
		<path d="M8.22 24.78A11 11 0 1 1 23.78 24.78" stroke="currentColor" stroke-opacity=".38" stroke-width="3" stroke-linecap="round" />
		<path class="hot" d="M25.53 11.5A11 11 0 0 1 23.78 24.78" stroke-width="3" stroke-linecap="round" />
		<path class="hot" d="M16 17 22.13 11.86" stroke-width="3" stroke-linecap="round" />
		<circle cx="16" cy="17" r="2.6" fill="currentColor" />
	</svg>
	<span class="word">Enigma <span class="labz">LABZ</span></span>
</span>

<style>
	.logo {
		display: inline-flex;
		align-items: center;
		gap: 0.55rem;
		color: var(--text-hi);
	}
	.hot {
		stroke: var(--accent-ink);
	}
	.word {
		font-weight: 760;
		font-stretch: 118%;
		font-size: 1.125rem;
		letter-spacing: -0.02em;
		white-space: nowrap;
	}
	.labz {
		font-weight: 760;
	}
</style>
