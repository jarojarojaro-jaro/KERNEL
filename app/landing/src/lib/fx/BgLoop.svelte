<script lang="ts">
	/**
	 * A decorative background loop (AI-generated, static/media): the poster is plain HTML; the video
	 * gets its sources only once it enters the viewport and the page has loaded (lazy), plays muted and
	 * looped, pauses when it leaves the viewport and fades in over the poster when it actually plays.
	 * Reduced motion, or a hidden box (display: none, e.g. the light theme): poster only, no video
	 * downloaded. `src` is the path without extension: `<src>.webm` (VP9), `<src>.mp4` (H.264),
	 * `<src>-poster.webp`. The caller positions and tones the `.bgloop` box (opacity, blend, mask).
	 */
	import { onMount, tick } from 'svelte';
	import { reducedMotion } from './motion';

	let { src }: { src: string } = $props();

	let video = $state<HTMLVideoElement>();
	let attached = $state(false);
	let playing = $state(false);
	/** Resolves once the page's own resources have loaded: a loop never competes with first paint. */
	function pageLoaded(): Promise<void> {
		const { promise, resolve } = Promise.withResolvers<void>();
		if (document.readyState === 'complete') resolve();
		else addEventListener('load', () => resolve(), { once: true });
		return promise;
	}

	onMount(() => {
		const v = video;
		if (!v || reducedMotion() || typeof IntersectionObserver === 'undefined') return;
		let near = false;
		const io = new IntersectionObserver(
			async ([e]) => {
				near = e.isIntersecting;
				if (!near) {
					v.pause();
					return;
				}
				if (!attached) {
					await pageLoaded();
					if (attached || !near) return;
					attached = true;
					await tick();
					v.load();
				}
				v.play().catch(() => {});
			},
			{ rootMargin: '0px' }
		);
		io.observe(v);
		return () => io.disconnect();
	});
</script>

<div class="bgloop" aria-hidden="true">
	<img class="poster" src="{src}-poster.webp" alt="" loading="lazy" decoding="async" />
	<video bind:this={video} class:on={playing} muted playsinline loop autoplay preload="none" disablepictureinpicture tabindex="-1" onplaying={() => (playing = true)}>
		{#if attached}
			<source src="{src}.webm" type="video/webm" />
			<source src="{src}.mp4" type="video/mp4" />
		{/if}
	</video>
</div>

<style>
	.bgloop {
		position: absolute;
		inset: 0;
		overflow: hidden;
		pointer-events: none;
	}
	.poster,
	video {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		object-fit: cover;
	}
	video {
		opacity: 0;
		transition: opacity 1.2s var(--ease-out, ease-out);
	}
	video.on {
		opacity: 1;
	}
</style>
