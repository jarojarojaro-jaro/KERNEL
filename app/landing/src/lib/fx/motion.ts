/**
 * Motion kit for the showcase pages (design/REDESIGN.md §5). Everything here animates
 * transform/opacity or a canvas, respects prefers-reduced-motion, and stops when offscreen.
 */

export function reducedMotion(): boolean {
	return typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/** Heat ramp stops (tokens.css --heat-0..5). Colour means speed and nothing else. */
export const HEAT = ['#1e3448', '#7a2e1f', '#e2401c', '#ff7a1a', '#ffc15a', '#fff3d6'] as const;
export const COLD = '#7d8794';

const rgb = (h: string) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));

/** Colour on the heat ramp for t ∈ [0, 1] (0 = cold, 1 = white-hot). */
export function heatColor(t: number): string {
	const x = Math.min(1, Math.max(0, t)) * (HEAT.length - 1);
	const i = Math.min(HEAT.length - 2, Math.floor(x));
	const f = x - i;
	const a = rgb(HEAT[i]);
	const b = rgb(HEAT[i + 1]);
	return `rgb(${a.map((v, k) => Math.round(v + (b[k] - v) * f)).join(' ')})`;
}

export const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
export const easeOutExpo = (t: number) => (t >= 1 ? 1 : 1 - 2 ** (-10 * t));
export const easeInOutCubic = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);

/**
 * Damped spring that follows a target; `step` advances it by dt seconds and returns the position.
 * Stiffness/damping chosen for a needle: fast rise, one small overshoot.
 */
export class Spring {
	x: number;
	v = 0;
	target: number;
	constructor(
		x = 0,
		public stiffness = 140,
		public damping = 14
	) {
		this.x = x;
		this.target = x;
	}
	step(dt: number): number {
		// Semi-implicit Euler in sub-steps keeps it stable at low frame rates.
		const n = Math.max(1, Math.ceil(dt / 0.008));
		const h = dt / n;
		for (let i = 0; i < n; i++) {
			this.v += (this.stiffness * (this.target - this.x) - this.damping * this.v) * h;
			this.x += this.v * h;
		}
		return this.x;
	}
	get settled(): boolean {
		return Math.abs(this.target - this.x) < 1e-3 && Math.abs(this.v) < 1e-3;
	}
	snap(to = this.target) {
		this.x = this.target = to;
		this.v = 0;
	}
}

/**
 * One shared rAF loop. Callbacks receive dt (s) and run only while the tab is visible.
 * Return false from the callback to unsubscribe.
 */
type Tick = (dt: number, now: number) => boolean | void;
const ticks = new Set<Tick>();
let raf = 0;
let last = 0;
function loop(now: number) {
	const dt = Math.min(0.05, (now - last) / 1000);
	last = now;
	for (const t of [...ticks]) if (t(dt, now) === false) ticks.delete(t);
	raf = ticks.size ? requestAnimationFrame(loop) : 0;
}
export function onFrame(t: Tick): () => void {
	ticks.add(t);
	if (!raf) {
		last = performance.now();
		raf = requestAnimationFrame(loop);
	}
	return () => ticks.delete(t);
}

/**
 * Run `cb` once the page is idle after load (requestIdleCallback, with a fallback timeout) and no
 * earlier than `minDelay` ms after navigation start. Keeps WebGL setup and rAF loops out of
 * hydration and the LCP window. Returns a cancel function.
 */
export function whenIdle(cb: () => void, minDelay = 0): () => void {
	let idle = 0;
	let done = false;
	const run = () => {
		if (done) return;
		done = true;
		cb();
	};
	const timer = setTimeout(
		() => {
			if (typeof requestIdleCallback === 'function') idle = requestIdleCallback(run, { timeout: 1500 });
			else run();
		},
		Math.max(0, minDelay - performance.now())
	);
	return () => {
		done = true;
		clearTimeout(timer);
		if (idle && typeof cancelIdleCallback === 'function') cancelIdleCallback(idle);
	};
}
