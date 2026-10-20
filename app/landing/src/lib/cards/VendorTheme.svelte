<script lang="ts">
	/**
	 * Wraps a cards page in its maker's colours (vendor.ts): sets the --v* properties, re-tints the
	 * explorer's heat language (rings, surfaces, glowing headings, dividers, amber ink) and, outside
	 * AMD, the heat tokens themselves (vendorHeat), so the whole page reads in the maker's family:
	 * the page glow, bars, the ×N, the render's light strip. AMD keeps the site's heat (red family).
	 */
	import type { Snippet } from 'svelte';
	import { vendorHeat, vendorVars } from './vendor';

	let { vendor, children }: { vendor: string; children: Snippet } = $props();
</script>

<div class="vend" style="{vendorVars(vendor)}; {vendorHeat(vendor)}">
	{@render children()}
</div>

<style>
	.vend {
		--hx-ink: var(--v-hi);
		--hx-glow: rgb(var(--v) / 0.42);
		--hx-line: linear-gradient(90deg, rgb(var(--v)), rgb(var(--v) / 0.5) 55%, rgb(var(--v) / 0) 100%);
		--hx-line-c: linear-gradient(90deg, rgb(var(--v) / 0), rgb(var(--v)) 30%, rgb(var(--v) / 0.6) 70%, rgb(var(--v) / 0));
	}
	/*
	 * The page's light in the maker's family: one fixed layer over the explorer's warm embers (it
	 * paints after them in the same stacking context), static and promoted once, like the embers.
	 */
	.vend::before {
		content: '';
		position: fixed;
		inset: 0;
		z-index: -1;
		pointer-events: none;
		background:
			radial-gradient(38vmax 26vmax at 12% 18%, rgb(var(--v) / 0.13), transparent 70%),
			radial-gradient(44vmax 30vmax at 88% 62%, rgb(var(--v) / 0.1), transparent 70%),
			radial-gradient(30vmax 22vmax at 55% 95%, rgb(var(--v) / 0.06), transparent 70%),
			var(--bg-0);
		will-change: transform;
	}
	:global(:root[data-theme='light']) .vend {
		--hx-ink: color-mix(in srgb, rgb(var(--v)) 62%, #000);
		--hx-glow: rgb(var(--v) / 0.25);
	}
	.vend :global(.hx-ring.hx-ring::after) {
		background: linear-gradient(180deg, rgb(var(--v) / 0.9), rgb(var(--v) / 0.4) 28%, rgb(var(--v) / 0.14) 62%, rgb(var(--v) / 0.1));
	}
	.vend :global(.hx-ring.hx-ring:is(:hover, :focus-within)) {
		box-shadow:
			0 0 0 1px rgb(var(--v) / 0.6),
			0 0 28px -6px rgb(var(--v) / 0.45),
			0 24px 60px -26px rgb(var(--v) / 0.55);
	}
	.vend :global(.hx-surface.hx-surface.hx-surface) {
		background:
			radial-gradient(90% 60% at 0% 0%, rgb(var(--v) / 0.1), transparent 60%),
			radial-gradient(70% 60% at 100% 100%, rgb(var(--v) / 0.06), transparent 60%),
			linear-gradient(180deg, rgb(19 19 22 / 0.92), rgb(8 8 9 / 0.92));
	}
	:global(:root[data-theme='light']) .vend :global(.hx-surface.hx-surface.hx-surface) {
		background:
			radial-gradient(90% 60% at 0% 0%, rgb(var(--v) / 0.1), transparent 60%),
			radial-gradient(70% 60% at 100% 100%, rgb(var(--v) / 0.06), transparent 60%),
			var(--bg-2);
	}
	.vend :global(.hx-h.hx-h.hx-h) {
		text-shadow:
			0 0 0.45em var(--hx-glow),
			0 0 1.4em rgb(var(--v) / 0.2);
	}
	/* clipped gradient headings: the background box gets room for descenders (ę ą j g) and the last
	   glyph's overhang; the negative margin keeps the layout */
	.vend :global(.hx-grad.hx-grad.hx-grad) {
		background: linear-gradient(100deg, var(--text-hi) 35%, var(--hx-ink) 85%);
		-webkit-background-clip: text;
		background-clip: text;
		padding: 0.14em 0.08em 0.2em 0;
		margin: -0.14em -0.08em -0.2em 0;
	}
	.vend :global(.eyebrow::before) {
		background: var(--hx-line);
	}
</style>
