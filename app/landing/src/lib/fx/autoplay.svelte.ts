/**
 * A scene timeline played when the scene enters the viewport (no scroll scrubbing). `p` STARTS AT 1:
 * the server HTML and any frame before the scene is seen show the final state. Once the scene is
 * actually in view, `p` replays 0 → 1 over `duration` seconds. If it leaves the viewport mid-play,
 * the tab is hidden or the page returns from the bfcache, it jumps to 1. Reduced motion: always 1.
 *
 * `arm`: a scene still entirely below the fold when it mounts is set to its start state (`p` = 0)
 * at once, so scrolling to it never shows the final state first and then jumps back (counters
 * would flash their end values). A scene already on screen at mount stays final and does not replay.
 *
 *   const tl = new Autoplay(4);
 *   <div use:tl.view style="--p:{tl.p}"> … <Replay onclick={tl.replay} /> </div>
 */
import { onFinish, onFrame, reducedMotion } from './motion';

export class Autoplay {
	p = $state(1);
	playing = $state(false);
	/** The node is inside the observed area (rootMargin applied). */
	inView = $state(false);
	#stop: (() => void) | null = null;
	#duration: number;
	#margin: string;
	#arm: boolean;

	/** `margin`: IntersectionObserver rootMargin (default: start a quarter into the viewport). */
	constructor(duration: number, margin = '0px 0px -25% 0px', { arm = false }: { arm?: boolean } = {}) {
		this.#duration = duration;
		this.#margin = margin;
		this.#arm = arm;
	}

	replay = () => {
		this.#stop?.();
		if (reducedMotion()) {
			this.p = 1;
			return;
		}
		this.p = 0;
		this.playing = true;
		let t = 0;
		this.#stop = onFrame((dt) => {
			t += dt;
			this.p = Math.min(1, t / this.#duration);
			if (this.p >= 1) {
				this.playing = false;
				this.#stop = null;
				return false;
			}
		});
	};

	finish = () => {
		this.#stop?.();
		this.#stop = null;
		this.p = 1;
		this.playing = false;
	};

	/** Action: play the first time the node enters the viewport (see `margin`); finish when it leaves. */
	view = (node: HTMLElement) => {
		if (reducedMotion() || typeof IntersectionObserver === 'undefined') return;
		const below = node.getBoundingClientRect().top >= innerHeight;
		// armed: below the fold → start state now and play on entry; already on screen → stay final
		let seen = this.#arm && !below;
		if (this.#arm && below) this.p = 0;
		const io = new IntersectionObserver(
			([e]) => {
				this.inView = e.isIntersecting;
				if (e.isIntersecting) {
					if (!seen) {
						seen = true;
						this.replay();
					}
				} else if (this.playing) this.finish();
			},
			{ rootMargin: this.#margin }
		);
		io.observe(node);
		const off = onFinish(this.finish);
		return {
			destroy: () => {
				io.disconnect();
				off();
				this.#stop?.();
			}
		};
	};
}
