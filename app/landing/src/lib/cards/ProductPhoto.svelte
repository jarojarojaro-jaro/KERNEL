<script lang="ts">
	/**
	 * A product photo (vendor.ts `PHOTO`): AVIF with a WebP fallback at 480/800/1200 px, transparent
	 * background, intrinsic 1200×800 so the box is reserved before it loads. Decorative by default
	 * (`alt` empty: the name is in the text next to it). If the image fails to load, `fallback`
	 * (the SVG GpuArt) renders instead.
	 */
	import type { Snippet } from 'svelte';
	import { PHOTO_H, PHOTO_W, photoSet, type PhotoId } from './vendor';

	let { id, sizes, eager = false, alt = '', fallback }: { id: PhotoId; sizes: string; eager?: boolean; alt?: string; fallback?: Snippet } = $props();

	let failed = $state(false);
</script>

{#if failed}
	{@render fallback?.()}
{:else}
	<picture class="photo">
		<source type="image/avif" srcset={photoSet(id, 'avif')} {sizes} />
		<img
			srcset={photoSet(id, 'webp')}
			{sizes}
			src="/media/cards/{id}-800.webp"
			{alt}
			width={PHOTO_W}
			height={PHOTO_H}
			loading={eager ? 'eager' : 'lazy'}
			fetchpriority={eager ? 'high' : 'auto'}
			decoding="async"
			draggable="false"
			onerror={() => (failed = true)}
		/>
	</picture>
{/if}

<style>
	.photo {
		display: block;
	}
	.photo img {
		display: block;
		width: 100%;
		height: auto;
		/* a soft contact shadow under the product, so it sits on any surface */
		filter: drop-shadow(0 1.2rem 1.6rem rgb(0 0 0 / 0.45)) drop-shadow(0 0.2rem 0.35rem rgb(0 0 0 / 0.35));
		user-select: none;
	}
</style>
