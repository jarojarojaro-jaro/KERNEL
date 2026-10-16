<script lang="ts">
	import '$design/tokens.css';
	import '$design/components.css';
	import '$design/showcase.css';
	import { afterNavigate } from '$app/navigation';

	let { children } = $props();

	/**
	 * Wide tables scroll horizontally on small screens. A scrolling region must be reachable by
	 * keyboard (WCAG 2.1.1), so every `.table-wrap` that actually overflows becomes a labelled,
	 * focusable region; it is re-evaluated after navigation and on resize.
	 */
	function markScrollRegions() {
		for (const el of document.querySelectorAll<HTMLElement>('.table-wrap')) {
			const scrolls = el.scrollWidth > el.clientWidth + 1;
			if (scrolls) {
				const noun = document.documentElement.lang === 'en' ? 'table' : 'tabela';
				const title = el.querySelector('caption')?.textContent?.trim() || el.closest('section, article')?.querySelector('h2, h3')?.textContent?.trim();
				// Suffix keeps the region name distinct from the enclosing section's name (landmark-unique).
				const label = title ? `${title} (${noun})` : noun;
				el.setAttribute('tabindex', '0');
				el.setAttribute('role', 'region');
				el.setAttribute('aria-label', label);
			} else if (el.getAttribute('role') === 'region') {
				el.removeAttribute('tabindex');
				el.removeAttribute('role');
				el.removeAttribute('aria-label');
			}
		}
	}

	afterNavigate(() => requestAnimationFrame(markScrollRegions));
</script>

<svelte:window onresize={markScrollRegions} />

{@render children()}
