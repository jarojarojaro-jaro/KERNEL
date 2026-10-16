<script lang="ts">
	/**
	 * A speed bar. The track holds the full heat ramp; a cover slides away (transform only) to reveal
	 * it up to `value / max`, so a longer bar is literally hotter. `cold` bars (upstream / before) use
	 * the steel colour instead. Animates when `value` changes; reduced motion jumps to the end.
	 */
	import Odometer from './Odometer.svelte';

	let {
		value,
		max,
		label,
		sub = '',
		cold = false,
		lang,
		decimals = 1,
		unit = 't/s',
		delay = 0,
		/** Optional redline on the same scale as `max` (a thin red mark across the track). */
		redline
	}: { value: number; max: number; label: string; sub?: string; cold?: boolean; lang: 'pl' | 'en'; decimals?: number; unit?: string; delay?: number; redline?: number } = $props();

	const f = $derived(Math.max(0, Math.min(1, value / max)));
</script>

<div class="hb" class:cold style="--f:{f}; --d:{delay}ms">
	<div class="meta">
		<span class="label">{label}{#if sub}<span class="sub">{sub}</span>{/if}</span>
		<span class="val"><Odometer {value} {decimals} {lang} minInt={1} /> <span class="unit">{unit}</span></span>
	</div>
	<div class="track" aria-hidden="true">
		<div class="ramp"></div>
		<div class="cover"></div>
		{#if redline}<span class="rl" style="--r:{redline / max}"></span>{/if}
	</div>
</div>

<style>
	.hb {
		display: grid;
		gap: var(--sp-2);
	}
	.meta {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: var(--sp-3);
	}
	.label {
		color: var(--text-hi);
		font-weight: 600;
	}
	.cold .label {
		color: var(--text);
		font-weight: 500;
	}
	.sub {
		display: block;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
		font-weight: 400;
		letter-spacing: 0.04em;
	}
	.val {
		font-size: var(--fs-xl);
		color: var(--text-hi);
		white-space: nowrap;
	}
	.cold .val {
		color: var(--before);
	}
	.unit {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.track {
		position: relative;
		height: 0.875rem;
		border-radius: var(--r-pill);
		background: var(--bg-3);
		overflow: hidden;
	}
	.ramp {
		position: absolute;
		inset: 0;
		background: var(--heat-ramp);
	}
	.cold .ramp {
		background: linear-gradient(90deg, #2a3038, var(--before));
	}
	.cover {
		position: absolute;
		inset: 0;
		background: var(--bg-3);
		transform: translate3d(calc(var(--f) * 100%), 0, 0);
		transition: transform 1.1s var(--ease-out) var(--d);
	}
	/* glowing leading edge rides on the cover, so it moves with the same transform */
	.cover::before {
		content: '';
		position: absolute;
		top: -50%;
		bottom: -50%;
		left: -1.5rem;
		width: 1.5rem;
		background: radial-gradient(closest-side at 100% 50%, rgb(255 243 214 / 0.85), transparent);
		opacity: calc(var(--f) * 20);
	}
	.cold .cover::before {
		display: none;
	}
	@media (prefers-reduced-motion: reduce) {
		.cover {
			transition: none;
		}
	}
	.rl {
		position: absolute;
		top: 0;
		bottom: 0;
		left: calc(var(--r) * 100%);
		width: 2px;
		background: var(--heat-2);
		box-shadow: 0 0 6px rgb(226 64 28 / 0.8);
	}
</style>
