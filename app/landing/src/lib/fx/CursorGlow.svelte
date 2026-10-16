<script lang="ts">
	/** One soft warm light that follows a fine pointer (screen blend). Off for touch and reduced motion. */
	import { onMount } from 'svelte';
	import { reducedMotion } from './motion';

	let el: HTMLDivElement | undefined = $state();
	let on = $state(false);

	onMount(() => {
		if (reducedMotion() || !matchMedia('(hover: hover) and (pointer: fine)').matches) return;
		let frame = 0;
		const move = (e: PointerEvent) => {
			cancelAnimationFrame(frame);
			frame = requestAnimationFrame(() => {
				if (el) el.style.transform = `translate3d(${e.clientX}px, ${e.clientY}px, 0)`;
				on = true;
			});
		};
		const leave = () => (on = false);
		addEventListener('pointermove', move, { passive: true });
		document.documentElement.addEventListener('pointerleave', leave);
		return () => {
			cancelAnimationFrame(frame);
			removeEventListener('pointermove', move);
			document.documentElement.removeEventListener('pointerleave', leave);
		};
	});
</script>

<div bind:this={el} class="cursor-glow" class:on aria-hidden="true"></div>
