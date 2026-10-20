<script lang="ts">
	/**
	 * A maker's AI-generated product render (vendor.ts `RENDER`), decorative; its edges fade out. The
	 * caller drops the photo's studio black with `mix-blend-mode: lighten` on its own outermost
	 * wrapper (`.x:has(> .render)`): a transformed wrapper isolates its children, so the blend must
	 * sit on the element that moves. No render for this maker/kind, or the image fails to load:
	 * `fallback` (the SVG GpuArt) renders instead.
	 */
	import type { Snippet } from 'svelte';
	import { renderSet, type RenderKind } from './vendor';

	let { vendor, kind, sizes, eager = false, fallback }: { vendor: string; kind: RenderKind; sizes: string; eager?: boolean; fallback?: Snippet } = $props();

	const avif = $derived(renderSet(vendor, kind, 'avif'));
	const webp = $derived(renderSet(vendor, kind, 'webp'));
	let failed = $state(false);
</script>

{#if webp && !failed}
	<picture class="render render--{kind}">
		{#if avif}<source type="image/avif" srcset={avif} {sizes} />{/if}
		<img srcset={webp} {sizes} src={webp.split(' ')[0]} alt="" width="1024" height="688" loading={eager ? 'eager' : 'lazy'} decoding="async" draggable="false" onerror={() => (failed = true)} />
	</picture>
{:else}
	{@render fallback?.()}
{/if}

<style>
	.render {
		display: block;
	}
	.render img {
		display: block;
		width: 100%;
		height: auto;
		-webkit-mask-image: radial-gradient(72% 70% at 50% 50%, #000 55%, transparent 100%);
		mask-image: radial-gradient(72% 70% at 50% 50%, #000 55%, transparent 100%);
		user-select: none;
	}
</style>
