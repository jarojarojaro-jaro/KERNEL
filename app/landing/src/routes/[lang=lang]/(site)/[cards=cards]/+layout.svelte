<script lang="ts">
	import { onNavigate } from '$app/navigation';
	import { reducedMotion } from '$lib/fx/motion';

	let { children } = $props();

	// Card tile → card page (and back) morphs through the View Transitions API: the GPU render and the
	// card name carry the same `view-transition-name` on both pages. Without the API (or with reduced
	// motion) navigation is instant and each page plays its own entrance.
	onNavigate((nav) => {
		if (!document.startViewTransition || reducedMotion() || nav.from?.url.pathname === nav.to?.url.pathname) return;
		return new Promise((resolve) => {
			document.startViewTransition(async () => {
				resolve();
				await nav.complete;
				// Capture the new page at its final scroll position (SvelteKit restores it a frame later).
				if (nav.type !== 'popstate' && !nav.to?.url.hash) scrollTo(0, 0);
			});
		});
	});
</script>

<div class="explorer">
	{@render children()}
</div>

<style>
	/*
	 * Explorer heat language: one warm vocabulary on every cards page (gallery, card, queue, compare).
	 * Glowing headings (.hx-h), heat-line dividers (.hx-bt / .hx-bb), lit numbers (.hx-num),
	 * a heat ring that rises on hover (.hx-ring) and slow embers drifting behind the page. Text keeps
	 * its AA colours: heat is added as glow, borders and backgrounds, and as amber ink (>= 10:1 dark,
	 * accent-ink >= 5.8:1 light). Model identity colours stay on their models.
	 */
	.explorer {
		--hx-ink: var(--heat-4);
		--hx-glow: rgb(255 122 26 / 0.42);
		--hx-line: linear-gradient(90deg, var(--heat-2), var(--heat-3) 35%, var(--heat-4) 65%, rgb(255 193 90 / 0) 100%);
		--hx-line-c: linear-gradient(90deg, rgb(226 64 28 / 0), var(--heat-2) 15%, var(--heat-3) 45%, var(--heat-4) 65%, rgb(255 193 90 / 0));
		position: relative;
		overflow-x: clip;
		isolation: isolate;
	}
	:global(:root[data-theme='light']) .explorer {
		--hx-ink: var(--accent-ink);
		--hx-glow: rgb(226 84 26 / 0.3);
	}
	/*
	 * Embers: one static, fixed layer of warm light behind every explorer page. It is promoted once
	 * (will-change) so scrolling never repaints it, and it does not animate: no per-frame compositing.
	 */
	.explorer::before {
		content: '';
		position: fixed;
		inset: 0;
		z-index: -1;
		pointer-events: none;
		background:
			radial-gradient(38vmax 26vmax at 12% 18%, rgb(226 64 28 / 0.13), transparent 70%),
			radial-gradient(44vmax 30vmax at 88% 62%, rgb(255 122 26 / 0.1), transparent 70%),
			radial-gradient(30vmax 22vmax at 55% 95%, rgb(255 193 90 / 0.06), transparent 70%);
		will-change: transform;
	}

	/* (utility classes are doubled for specificity over a component's own colour/background) */
	/* headings glow like a hot filament; the letters keep their bone colour */
	.explorer :global(.hx-h.hx-h) {
		color: var(--text-hi);
		text-shadow:
			0 0 0.45em var(--hx-glow),
			0 0 1.4em rgb(226 64 28 / 0.22);
	}
	/* heading that cools from bone into amber along its length */
	.explorer :global(.hx-grad.hx-grad) {
		background: linear-gradient(100deg, var(--text-hi) 35%, var(--hx-ink) 80%, var(--heat-3));
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
		text-shadow: none;
		filter: drop-shadow(0 0 0.35em var(--hx-glow));
	}
	:global(:root[data-theme='light']) .explorer :global(.hx-grad.hx-grad) {
		background: linear-gradient(100deg, var(--text-hi) 35%, var(--accent-ink));
		-webkit-background-clip: text;
		background-clip: text;
	}
	/* every eyebrow dash on these pages is a short heat line */
	.explorer :global(.eyebrow::before) {
		background: var(--hx-line);
		opacity: 1;
		height: 2px;
		border-radius: 1px;
	}
	/* lit numbers */
	.explorer :global(.hx-num.hx-num) {
		color: var(--hx-ink);
		text-shadow: 0 0 0.6em var(--hx-glow);
	}
	/* heat-line dividers: a top or bottom border on any block */
	.explorer :global(.hx-bt.hx-bt) {
		border-top: 1px solid transparent;
		border-image: var(--hx-line) 1;
	}
	.explorer :global(.hx-bb.hx-bb) {
		border-bottom: 1px solid transparent;
		border-image: var(--hx-line) 1;
	}
	/*
	 * Heat ring: a hot top edge cooling down the sides at rest; on hover/focus the whole rim lights
	 * and an ember shadow rises. The ring replaces the grey border (repeated class = specificity over
	 * the component's own border colour), drawn inside the box so `overflow: hidden` keeps it.
	 */
	.explorer :global(.hx-ring.hx-ring.hx-ring) {
		position: relative;
		border-color: transparent;
	}
	.explorer :global(.hx-ring::after) {
		content: '';
		position: absolute;
		inset: 0;
		z-index: 2;
		padding: 1px;
		border-radius: inherit;
		background: linear-gradient(180deg, rgb(255 140 50 / 0.9), rgb(226 64 28 / 0.4) 28%, rgb(255 122 26 / 0.14) 62%, rgb(255 122 26 / 0.1));
		-webkit-mask:
			linear-gradient(#000 0 0) content-box,
			linear-gradient(#000 0 0);
		mask:
			linear-gradient(#000 0 0) content-box,
			linear-gradient(#000 0 0);
		-webkit-mask-composite: xor;
		mask-composite: exclude;
		pointer-events: none;
	}
	.explorer :global(.hx-ring:is(:hover, :focus-within)) {
		box-shadow:
			0 0 0 1px rgb(255 122 26 / 0.6),
			0 0 28px -6px rgb(255 122 26 / 0.45),
			0 24px 60px -26px rgb(226 64 28 / 0.7);
	}
	/* warm panel surface: a dark ember gradient instead of flat grey */
	.explorer :global(.hx-surface.hx-surface) {
		background:
			radial-gradient(90% 60% at 0% 0%, rgb(255 122 26 / 0.09), transparent 60%),
			radial-gradient(70% 60% at 100% 100%, rgb(226 64 28 / 0.07), transparent 60%),
			linear-gradient(180deg, rgb(19 19 22 / 0.92), rgb(8 8 9 / 0.92));
	}
	:global(:root[data-theme='light']) .explorer :global(.hx-surface.hx-surface) {
		background:
			radial-gradient(90% 60% at 0% 0%, rgb(255 122 26 / 0.1), transparent 60%),
			radial-gradient(70% 60% at 100% 100%, rgb(226 64 28 / 0.06), transparent 60%),
			var(--bg-2);
	}
	:global(::view-transition-group(*)) {
		animation-duration: 0.6s;
		animation-timing-function: cubic-bezier(0.16, 1, 0.3, 1);
	}
	/* the card itself flies with a heavier curve and flares as it lands */
	:global(::view-transition-group(*.gpu)) {
		animation-duration: 0.8s;
		animation-timing-function: cubic-bezier(0.7, 0, 0.15, 1);
		z-index: 2;
	}
	:global(::view-transition-new(*.gpu)) {
		animation: vt-flare 0.8s cubic-bezier(0.16, 1, 0.3, 1) both;
	}
	:global(::view-transition-old(*.gpu)) {
		animation: vt-out 0.35s ease-out both;
	}
	@keyframes -global-vt-flare {
		from {
			opacity: 0;
			filter: brightness(2.2) saturate(1.4);
		}
		50% {
			opacity: 1;
		}
		to {
			filter: none;
		}
	}
	:global(::view-transition-old(root)) {
		animation: 0.2s ease-out both vt-out;
	}
	:global(::view-transition-new(root)) {
		animation: 0.45s cubic-bezier(0.16, 1, 0.3, 1) 0.1s both vt-in;
	}
	@keyframes -global-vt-out {
		to {
			opacity: 0;
		}
	}
	@keyframes -global-vt-in {
		from {
			opacity: 0;
			transform: translateY(12px);
		}
	}
</style>
