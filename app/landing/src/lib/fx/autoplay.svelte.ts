/**
 * A scene timeline that plays once when the scene enters the viewport (no scroll scrubbing):
 * `p` runs 0 → 1 over `duration` seconds; `replay()` runs it again. Reduced motion jumps to p = 1.
 *
 *   const tl = new Autoplay(4);
 *   <div use:tl.view style="--p:{tl.p}"> … <Replay onclick={tl.replay} /> </div>
 */
import { onFrame, reducedMotion } from './motion';

export class Autoplay {
	p = $state(0);
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

	/** Action: start the timeline the first time the node enters the viewport (see `margin`). */
	view = (node: HTMLElement) => {
		if (reducedMotion()) this.p = 1;
		const io = new IntersectionObserver(
			([e]) => {
				if (!e.isIntersecting) return;
				io.disconnect();
				if (this.p < 1) this.replay();
			},
			{ rootMargin: this.#margin }
		);
		io.observe(node);
		return {
			destroy: () => {
				io.disconnect();
				this.#stop?.();
			}
		};
	};
}
