<script lang="ts">
	/**
	 * Tacho mark, inlined from KERNEL/app/design/logo/mark.svg. The redline and needle use
	 * `--accent-ink` instead of the file's fixed heat orange so the mark keeps its contrast on light surfaces.
	 */
	let { size = 22 }: { size?: number } = $props();
</script>

<svg class="mark" width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true" focusable="false">
	<path d="M8.22 24.78A11 11 0 1 1 23.78 24.78" stroke="currentColor" stroke-opacity=".38" stroke-width="3" stroke-linecap="round" />
	<path class="red" d="M25.53 11.5A11 11 0 0 1 23.78 24.78" stroke-width="3" stroke-linecap="round" />
	<path class="red" d="M16 17 22.13 11.86" stroke-width="3" stroke-linecap="round" />
	<circle cx="16" cy="17" r="2.6" fill="currentColor" />
</svg>

<style>
	.mark {
		flex: none;
		color: var(--text-hi);
	}
	.red {
		stroke: var(--accent-ink);
	}
</style>
