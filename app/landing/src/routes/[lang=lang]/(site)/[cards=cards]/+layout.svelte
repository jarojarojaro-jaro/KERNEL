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
	.explorer {
		position: relative;
		overflow-x: clip;
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
