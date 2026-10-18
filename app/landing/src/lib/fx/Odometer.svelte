<script lang="ts">
	/**
	 * Rolling odometer. Digits are drums that turn continuously: the last digit spins, higher ones
	 * roll over only on carry, like a mechanical counter. A new `value` is tweened over `duration` ms
	 * (0 = follow the value directly, e.g. when a parent animates it every frame).
	 * Screen readers and copy/paste get the final value as one visually hidden text; the drums are
 * aria-hidden and not selectable.
	 */
	import { onMount, untrack } from 'svelte';
	import { easeOutExpo, onFinish, onFrame, reducedMotion } from './motion';

	let {
		value,
		decimals = 1,
		lang = 'pl',
		duration = 1400,
		/** Minimum integer digits (keeps width stable while counting up). */
		minInt = 1,
		label = '',
		/** easeOutBack strength: > 0 counts past the value and settles back onto it (0 = no overshoot). */
		overshoot = 0,
		/** Keep leading drums' width (they fade instead of collapsing): the counter never changes size. */
		pad = false,
		/** Bump to count up again from 0 (e.g. when the counter enters the viewport); rests on `value`. */
		replay = 0
	}: { value: number; decimals?: number; lang?: 'pl' | 'en'; duration?: number; minInt?: number; label?: string; overshoot?: number; pad?: boolean; replay?: number } = $props();

	const ease = (k: number) => (overshoot > 0 ? 1 + (overshoot + 1) * (k - 1) ** 3 + overshoot * (k - 1) ** 2 : easeOutExpo(k));

	// svelte-ignore state_referenced_locally
	let shown = $state(value);
	let from = 0;
	let target = 0;
	let t0 = 0;
	let stop: (() => void) | null = null;
	let first = true;
	let lastReplay = 0;

	// a hidden tab or a bfcache restore: rest on the exact value at once
	onMount(() =>
		onFinish(() => {
			stop?.();
			stop = null;
			shown = Math.round(value * 10 ** decimals) / 10 ** decimals;
		})
	);

	$effect(() => {
		// The drums can only rest on whole digits: round the target to the shown precision.
		const v = Math.round(value * 10 ** decimals) / 10 ** decimals;
		const r = replay;
		const again = r !== lastReplay;
		lastReplay = r;
		if (again && !reducedMotion() && duration > 0) {
			first = false;
			untrack(() => (shown = 0));
		}
		else if (first || duration === 0 || reducedMotion()) {
			first = false;
			stop?.();
			shown = v;
			from = target = v;
			return;
		}
		from = untrack(() => shown);
		target = v;
		t0 = performance.now();
		stop?.();
		stop = onFrame((_, now) => {
			const k = Math.min(1, (now - t0) / duration);
			shown = from + (target - from) * ease(k);
			// the long easing tail would show the last digit one short (77,9 for 78,0): within one unit
			// of the target (and past any overshoot) it lands exactly on it
			if (k >= 1 || ((overshoot === 0 || k > 0.8) && Math.abs(target - shown) < 1 / 10 ** decimals)) {
				shown = target;
				stop = null;
				return false;
			}
		});
		// rAF can be throttled (background tab, busy main thread): the rest value is always exact
		const settle = setTimeout(() => {
			stop?.();
			stop = null;
			shown = target;
		}, duration + 120);
		return () => {
			clearTimeout(settle);
			stop?.();
		};
	});

	const sep = $derived(lang === 'pl' ? ',' : '.');
	const scale = $derived(10 ** decimals);
	/** Number of integer digits to render. */
	const intDigits = $derived(Math.max(minInt, String(Math.floor(Math.max(Math.abs(value), Math.abs(shown)))).length));
	/**
	 * Drum positions, most significant first. x = shown × 10^decimals as a continuous number.
	 * Like a mechanical counter, a drum rests on a whole digit and only turns during the last 35%
	 * of each unit (`snap`), so a frame caught mid-roll shows a readable digit almost always;
	 * higher drums turn with the same snapped carry from the digits below them.
	 */
	const snap = (f: number) => {
		const t = Math.min(1, Math.max(0, (f - 0.65) / 0.35));
		return Math.round(t * t * (3 - 2 * t) * 100) / 100;
	};
	const drums = $derived.by(() => {
		const x = Math.max(0, shown) * scale;
		const total = intDigits + decimals;
		const out: { pos: number; lead: boolean }[] = [];
		for (let k = total - 1; k >= 0; k--) {
			const p = 10 ** k;
			const below = x % p;
			const carry = k === 0 ? snap(x - Math.floor(x)) : below > p - 1 ? snap(below - (p - 1)) : 0;
			const pos = (Math.floor(x / p) % 10) + carry;
			out.push({ pos: pos % 10, lead: k >= decimals + 1 && x < p * 0.999 });
		}
		return out;
	});
	const text = $derived(value.toLocaleString(lang === 'pl' ? 'pl-PL' : 'en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals }));
</script>

<span class="odo" aria-label={label ? `${label}: ${text}` : undefined} role={label ? 'img' : undefined}>
	<!-- the one real value: read by screen readers and the only text copied with a selection -->
	<span class="sr-only">{text}</span>
	<span class="drums" aria-hidden="true">
		{#each drums as d, i (i)}
			{#if decimals > 0 && i === drums.length - decimals}<span class="sep">{sep}</span>{/if}
			<span class="drum" class:lead={d.lead && !pad} class:ghost={d.lead && pad}>
				<span class="strip" style="transform: translate3d(0, {-d.pos}em, 0)">
					{#each [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0] as n, j (j)}<span>{n}</span>{/each}
				</span>
			</span>
		{/each}
	</span>
</span>

<style>
	.odo {
		display: inline-flex;
		font-family: var(--font-mono);
		font-variant-numeric: tabular-nums;
		line-height: 1;
	}
	/* the reels are decoration: never selectable, never copied */
	.drums {
		display: inline-flex;
		align-items: flex-end;
		-webkit-user-select: none;
		user-select: none;
	}
	.drum {
		display: inline-block;
		height: 1em;
		overflow: clip;
		width: 1ch;
		/* soft fade at the drum edges, like digits seen through a window */
		mask-image: linear-gradient(transparent, #000 12%, #000 88%, transparent);
	}
	.drum.lead {
		width: 0;
		transition: width 0.4s var(--ease-out);
	}
	.drum.ghost {
		opacity: 0;
	}
	.strip {
		display: flex;
		flex-direction: column;
		will-change: transform;
	}
	.strip span {
		display: block;
		height: 1em;
		text-align: center;
	}
	/* Martian Mono's comma is a full 1ch cell: centre it in a narrower, clipped slot */
	.sep {
		display: inline-flex;
		justify-content: center;
		width: 0.5ch;
		overflow: clip;
		line-height: 1;
	}
</style>
