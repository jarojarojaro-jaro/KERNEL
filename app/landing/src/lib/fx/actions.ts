/**
 * Svelte actions for the showcase interaction kit (design/REDESIGN.md §8).
 * All of them are no-ops under prefers-reduced-motion or on coarse pointers where noted.
 */
import type { Action } from 'svelte/action';
import { reducedMotion } from './motion';

const finePointer = () => typeof matchMedia !== 'undefined' && matchMedia('(hover: hover) and (pointer: fine)').matches;

/**
 * Hover tilt with glare. Sets --rx/--ry (deg) and --gx/--gy (%) on the node; the `.tilt` class in
 * showcase.css turns them into a 3D transform and a glare highlight.
 */
export const tilt: Action<HTMLElement, { max?: number } | undefined> = (node, opts) => {
	if (reducedMotion() || !finePointer()) return;
	const max = opts?.max ?? 6;
	node.classList.add('tilt');
	let frame = 0;
	const move = (e: PointerEvent) => {
		cancelAnimationFrame(frame);
		frame = requestAnimationFrame(() => {
			const r = node.getBoundingClientRect();
			const x = (e.clientX - r.left) / r.width;
			const y = (e.clientY - r.top) / r.height;
			node.style.setProperty('--ry', `${((x - 0.5) * 2 * max).toFixed(2)}deg`);
			node.style.setProperty('--rx', `${((0.5 - y) * 2 * max).toFixed(2)}deg`);
			node.style.setProperty('--gx', `${(x * 100).toFixed(1)}%`);
			node.style.setProperty('--gy', `${(y * 100).toFixed(1)}%`);
			node.dataset.hover = '';
		});
	};
	const leave = () => {
		cancelAnimationFrame(frame);
		node.style.setProperty('--rx', '0deg');
		node.style.setProperty('--ry', '0deg');
		delete node.dataset.hover;
	};
	node.addEventListener('pointermove', move);
	node.addEventListener('pointerleave', leave);
	return {
		destroy() {
			node.removeEventListener('pointermove', move);
			node.removeEventListener('pointerleave', leave);
		}
	};
};

/** Magnetic pull toward the cursor, at most `max` px. */
export const magnetic: Action<HTMLElement, { max?: number } | undefined> = (node, opts) => {
	if (reducedMotion() || !finePointer()) return;
	const max = opts?.max ?? 6;
	node.classList.add('magnetic');
	const move = (e: PointerEvent) => {
		const r = node.getBoundingClientRect();
		const dx = (e.clientX - (r.left + r.width / 2)) / (r.width / 2);
		const dy = (e.clientY - (r.top + r.height / 2)) / (r.height / 2);
		node.style.setProperty('--mx', `${(dx * max).toFixed(2)}px`);
		node.style.setProperty('--my', `${(dy * max).toFixed(2)}px`);
	};
	const leave = () => {
		node.style.setProperty('--mx', '0px');
		node.style.setProperty('--my', '0px');
	};
	node.addEventListener('pointermove', move);
	node.addEventListener('pointerleave', leave);
	return {
		destroy() {
			node.removeEventListener('pointermove', move);
			node.removeEventListener('pointerleave', leave);
		}
	};
};

/**
 * Reveal once when the node enters the viewport: sets `data-in`. CSS (`[data-reveal]` in
 * showcase.css) hides the node only when JS runs (`html.js`), so content is never lost without JS.
 * `onin` fires at the same moment for JS-driven animations (counters, races).
 */
export const reveal: Action<HTMLElement, { threshold?: number; onin?: () => void } | undefined> = (node, opts) => {
	node.dataset.reveal = node.dataset.reveal ?? '';
	if (reducedMotion() || typeof IntersectionObserver === 'undefined') {
		node.dataset.in = '';
		opts?.onin?.();
		return;
	}
	const io = new IntersectionObserver(
		(entries) => {
			for (const e of entries)
				if (e.isIntersecting) {
					node.dataset.in = '';
					opts?.onin?.();
					io.disconnect();
				}
		},
		{ threshold: opts?.threshold ?? 0.2 }
	);
	io.observe(node);
	return { destroy: () => io.disconnect() };
};

/** True while the node is (partly) visible; `cb` gets the state. Used to pause loops offscreen. */
export const visible: Action<HTMLElement, (on: boolean) => void> = (node, cb) => {
	if (typeof IntersectionObserver === 'undefined') {
		cb(true);
		return;
	}
	const io = new IntersectionObserver(([e]) => cb(e.isIntersecting), { threshold: 0 });
	io.observe(node);
	return { destroy: () => io.disconnect() };
};
