<script lang="ts">
	/**
	 * Speed lines behind the hero duel: light streaks flowing left → right, in two groups. The
	 * typical app's side (left; on phones the top) gets few, thin, steel streaks that drift slowly;
	 * our side (right; on phones the bottom) gets many hot streaks with a white-hot head that fly.
	 * Three depths per side (far: thin, dim, slower; near: thicker, brighter, faster) give the
	 * parallax. Every streak is its own composited layer moved by a CSS transform: no canvas, no
	 * per-frame script. The layout is seeded, so server and client render the same streaks.
	 * Off screen the animation pauses; reduced motion shows a static heat gradient instead.
	 */
	import { visible } from './actions';

	/** Deterministic PRNG (mulberry32): the same streaks on the server and the client. */
	function rng(seed: number) {
		let a = seed;
		return () => {
			a = (a + 0x6d2b79f5) | 0;
			let t = Math.imul(a ^ (a >>> 15), 1 | a);
			t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
			return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
		};
	}
	type Streak = { y: number; len: number; h: number; d: number; delay: number; o: number; k: number };
	/** depth 0 = far, 2 = near; `dur` = seconds to cross the side at depth 0. */
	function streaks(n: number, seed: number, dur: number, len: number, op: number): Streak[] {
		const r = rng(seed);
		return Array.from({ length: n }, (_, i) => {
			const depth = i % 3;
			const l = len * (0.6 + 0.5 * depth + 0.4 * r());
			const d = dur * (1 - 0.28 * depth) * (0.85 + 0.3 * r());
			return {
				y: 4 + 92 * r(),
				len: l,
				h: depth === 2 ? 2 : 1,
				d,
				delay: -d * r(),
				o: op * (0.45 + 0.3 * depth) * (0.8 + 0.4 * r()),
				// travel = the side's width + the streak's own, in units of its own width
				k: 100 / l
			};
		});
	}
	const cold = streaks(9, 7, 7.5, 16, 0.55);
	const hot = streaks(21, 11, 1.5, 26, 0.9);

	let onScreen = $state(false);
	const style = (s: Streak) =>
		`top:${s.y.toFixed(2)}%;width:${s.len.toFixed(2)}%;height:${s.h}px;opacity:${s.o.toFixed(3)};--k:${s.k.toFixed(3)};animation-duration:${s.d.toFixed(2)}s;animation-delay:${s.delay.toFixed(2)}s`;
</script>

<div class="speed" class:off={!onScreen} aria-hidden="true" use:visible={(v) => (onScreen = v)}>
	<div class="side cold">{#each cold as s, i (i)}<i style={style(s)}></i>{/each}</div>
	<div class="side hot">{#each hot as s, i (i)}<i style={style(s)}></i>{/each}</div>
</div>

<style>
	.speed {
		position: absolute;
		inset: 0;
		pointer-events: none;
		-webkit-mask-image: linear-gradient(180deg, transparent, #000 18%, #000 82%, transparent);
		mask-image: linear-gradient(180deg, transparent, #000 18%, #000 82%, transparent);
	}
	.side {
		position: absolute;
		top: 0;
		bottom: 0;
		overflow: hidden;
	}
	.cold {
		left: 0;
		width: 50%;
	}
	/* our side starts a little before the seam: the hot streaks pass behind the speed-up badge */
	.hot {
		left: 42%;
		right: 0;
		/* a faint heat floor under the streaks */
		background: radial-gradient(70% 60% at 60% 55%, rgb(255 122 26 / 0.07), transparent 70%);
	}
	i {
		position: absolute;
		left: 0;
		border-radius: 999px;
		transform: translate3d(-100%, 0, 0);
		animation-name: run;
		animation-timing-function: linear;
		animation-iteration-count: infinite;
		will-change: transform;
	}
	.cold i {
		background: linear-gradient(90deg, transparent, rgb(125 135 148 / 0.5) 70%, rgb(201 207 216 / 0.8));
	}
	.hot i {
		background: linear-gradient(90deg, transparent, rgb(226 64 28 / 0.55) 45%, var(--heat-3) 80%, var(--heat-5));
		box-shadow: 0 0 6px rgb(255 122 26 / 0.45);
	}
	@keyframes run {
		to {
			transform: translate3d(calc(var(--k) * 100%), 0, 0);
		}
	}
	.off i {
		animation-play-state: paused;
	}
	/* phones (the panes stack): our side below the typical one */
	@media (max-width: 720px) {
		.cold {
			width: 100%;
			bottom: 52%;
		}
		.hot {
			left: 0;
			top: 46%;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		i {
			display: none;
		}
		.hot {
			background:
				linear-gradient(90deg, transparent, rgb(255 122 26 / 0.08) 50%, rgb(255 193 90 / 0.1)),
				radial-gradient(70% 60% at 60% 55%, rgb(255 122 26 / 0.07), transparent 70%);
		}
	}
</style>
