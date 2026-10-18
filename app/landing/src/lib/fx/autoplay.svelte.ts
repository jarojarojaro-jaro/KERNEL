/**
 * A scene timeline played when the scene enters the viewport (no scroll scrubbing). `p` STARTS AT 1:
 * the server HTML and any frame before the scene is seen show the final state. Once the scene is
 * actually in view, `p` replays 0 → 1 over `duration` seconds. If it leaves the viewport mid-play,
 * the tab is hidden or the page returns from the bfcache, it jumps to 1. Reduced motion: always 1.
 *
 *   const tl = new Autoplay(4);
 *   <div use:tl.view style="--p:{tl.p}"> … <Replay onclick={tl.replay} /> </div>
 */
import { onFinish, onFrame, reducedMotion } from './motion';

export class Autoplay {
	p = $state(1);
	playing = $state(false);
	#stop: (() => void) | null = null;
	#duration: number;
	#margin: string;

	/** `margin`: IntersectionObserver rootMargin (default: start a quarter into the viewport). */
	constructor(duration: number, margin = '0px 0px -25% 0px') {
		this.#duration = duration;
		this.#margin = margin;
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
		let seen = false;
		const io = new IntersectionObserver(
			([e]) => {
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
