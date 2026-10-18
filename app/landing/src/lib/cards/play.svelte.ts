/**
 * Enter-view playback that can only enhance the final state.
 *
 * At rest (`on` false: SSR, no JS, reduced motion, before and after a play) every consumer renders
 * the final measured state. A play starts when the node enters the viewport (once; again on
 * `replay()`): `arm` is true for the first painted frames so CSS can show the start state with
 * transitions off, then it drops and the transitions run to the final state. `on` stays true for
 * `ms` (JS-driven animations read it), then the play ends.
 *
 * Any interruption ends the play at once on the final state: the node leaves the viewport (fast
 * scroll), the tab is hidden, the page comes back from the bfcache. A late observer callback (busy
 * main thread: the node has already been on screen for a while) does not start a play at all.
 */
import { reducedMotion } from '$lib/fx/motion';

/** An observer callback older than this means the node has been on screen already: no intro. */
const LATE_MS = 350;

export class Play {
	/** A play is running (JS-driven animations play while true, show the final state otherwise). */
	on = $state(false);
	/** First frames of a play: the start state, transitions off. */
	arm = $state(false);
	/** Plays so far; a key for restarting JS timelines. */
	n = $state(0);
	#ms: () => number;
	#end = 0;
	#unarm = 0;
	#raf = 0;
	#inView = false;

	/** `ms`: the longest animation of the scene, delays included (a function when it depends on data). */
	constructor(ms: number | (() => number)) {
		this.#ms = typeof ms === 'number' ? () => ms : ms;
	}

	stop = () => {
		clearTimeout(this.#end);
		clearTimeout(this.#unarm);
		cancelAnimationFrame(this.#raf);
		this.arm = false;
		this.on = false;
	};

	#start() {
		this.stop();
		if (reducedMotion() || document.hidden) return;
		this.arm = true;
		this.on = true;
		this.n++;
		// two frames so the start state is painted; the timeout releases it if rAF is throttled
		this.#raf = requestAnimationFrame(() => (this.#raf = requestAnimationFrame(() => (this.arm = false))));
		this.#unarm = window.setTimeout(() => (this.arm = false), 120);
		this.#end = window.setTimeout(this.stop, this.#ms() + 200);
	}

	/** Play again (replay buttons): only while the scene is on screen. */
	replay = () => {
		if (this.#inView) this.#start();
	};

	/** Action: play the first time the node enters the viewport; finish early on any interruption. */
	view = (node: Element, opts?: { threshold?: number }) => {
		let played = false;
		const at = opts?.threshold ?? 0.15;
		const io = new IntersectionObserver(
			([e]) => {
				this.#inView = e.isIntersecting;
				// fully out of view (scrolled past): finish now
				if (!e.isIntersecting) {
					if (this.on) this.stop();
					return;
				}
				if (played || e.intersectionRatio < at) return;
				played = true;
				if (performance.now() - e.time < LATE_MS) this.#start();
			},
			{ threshold: [0, at] }
		);
		io.observe(node);
		const hide = () => document.hidden && this.stop();
		const show = (e: PageTransitionEvent) => e.persisted && this.stop();
		document.addEventListener('visibilitychange', hide);
		window.addEventListener('pageshow', show);
		return {
			destroy: () => {
				io.disconnect();
				document.removeEventListener('visibilitychange', hide);
				window.removeEventListener('pageshow', show);
				this.stop();
			}
		};
	};
}
