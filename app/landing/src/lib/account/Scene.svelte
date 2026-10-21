<script lang="ts">
	/**
	 * One-screen stage of the account pages: slides under the translucent header and lays the hero's
	 * ember field behind the content, calmed in the middle (`focus` moves that calm spot: centre for
	 * sign-in, right for sign-up where the form sits).
	 */
	import type { Snippet } from 'svelte';
	import HeatField from '$lib/fx/HeatField.svelte';

	interface Props {
		labelledby: string;
		focus?: string;
		children: Snippet;
	}
	let { labelledby, focus = '50% 46%', children }: Props = $props();
</script>

<section class="acct heat-scope" aria-labelledby={labelledby} style="--focus:{focus}">
	<div class="bg" aria-hidden="true">
		<HeatField heat={0.55} />
		<div class="veil"></div>
	</div>
	{@render children()}
</section>

<style>
	.acct {
		position: relative;
		isolation: isolate;
		overflow: clip;
		margin-top: -4.2rem;
		padding: calc(4.2rem + clamp(0.5rem, 2.4vh, 2.5rem)) var(--gutter, 1rem) clamp(0.75rem, 3vh, 3rem);
		min-height: 100svh;
		display: grid;
		place-items: center;
	}
	.bg {
		position: absolute;
		inset: 0;
		z-index: -1;
	}
	.veil {
		position: absolute;
		inset: 0;
		background:
			radial-gradient(42% 56% at var(--focus), color-mix(in srgb, var(--bg-0) 88%, transparent), transparent 75%),
			linear-gradient(180deg, color-mix(in srgb, var(--bg-0) 70%, transparent), transparent 30%);
	}
	:global(:root[data-theme='light']) .bg :global(.heatfield) {
		display: none;
	}
	:global(:root[data-theme='light']) .veil {
		background:
			radial-gradient(40% 40% at 50% 20%, color-mix(in srgb, var(--heat-4) 30%, transparent), transparent 70%),
			radial-gradient(30% 30% at 18% 70%, color-mix(in srgb, var(--heat-3) 12%, transparent), transparent 70%),
			radial-gradient(30% 30% at 82% 64%, color-mix(in srgb, var(--heat-5) 80%, transparent), transparent 70%);
	}
</style>
