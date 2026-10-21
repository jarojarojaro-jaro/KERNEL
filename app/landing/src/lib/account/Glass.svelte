<script lang="ts">
	/** Glass card with a slowly travelling ember border (16 s loop; reduced motion: static border). */
	import type { Snippet } from 'svelte';

	interface Props {
		/** max inline size, CSS length */
		width: string;
		children: Snippet;
	}
	let { width, children }: Props = $props();
</script>

<div class="glass in" style="--w:{width}; --d:40ms">
	{@render children()}
</div>

<style>
	@property --spin {
		syntax: '<angle>';
		inherits: false;
		initial-value: 0deg;
	}
	.glass {
		position: relative;
		width: min(100%, var(--w));
		border-radius: 1.5rem;
		background: color-mix(in srgb, var(--bg-1) 72%, transparent);
		backdrop-filter: blur(18px) saturate(1.3);
		-webkit-backdrop-filter: blur(18px) saturate(1.3);
		box-shadow:
			var(--shadow-2),
			0 40px 120px -60px color-mix(in srgb, var(--heat-3) 70%, transparent);
	}
	.glass::before {
		content: '';
		position: absolute;
		inset: 0;
		z-index: 1;
		padding: 1px;
		border-radius: inherit;
		pointer-events: none;
		background:
			conic-gradient(from var(--spin), transparent 0 52%, color-mix(in srgb, var(--heat-2) 90%, transparent) 66%, var(--heat-4) 76%, transparent 90%),
			linear-gradient(var(--line-strong), var(--line-strong));
		-webkit-mask:
			linear-gradient(#000 0 0) content-box,
			linear-gradient(#000 0 0);
		mask:
			linear-gradient(#000 0 0) content-box,
			linear-gradient(#000 0 0);
		-webkit-mask-composite: xor;
		mask-composite: exclude;
	}
	@media (prefers-reduced-motion: no-preference) {
		.glass::before {
			animation: spin 16s linear infinite;
		}
		.in {
			animation: rise 0.36s var(--ease-out) var(--d) both;
		}
	}
	@keyframes spin {
		to {
			--spin: 360deg;
		}
	}
	@keyframes rise {
		from {
			opacity: 0.01;
			transform: translate3d(0, 0.75rem, 0);
		}
	}
	:global(:root[data-theme='light']) .glass {
		background: color-mix(in srgb, #ffffff 78%, transparent);
	}
	@media (max-width: 600px) {
		.glass {
			border-radius: 1.25rem;
		}
	}
</style>
