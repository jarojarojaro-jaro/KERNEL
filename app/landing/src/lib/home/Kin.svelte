<script lang="ts">
	/**
	 * Kinetic headline (showcase.css `.kin`): every glyph is a `.ch` with its index `--i`; words are
	 * `.w` (no break inside a word), real spaces sit between them so lines wrap naturally.
	 * The text itself is plain HTML, painted on first frame by CSS only (it is the LCP element);
	 * `heat` lines colour each glyph along the heat ramp, left = red, right = white-hot.
	 */
	import { heatColor } from '$lib/fx/motion';

	let {
		lines,
		wide = [],
		heat = [],
		/** Lines in the cold-metal finish (steel chrome, a sheen passes once): the "same" lines. */
		cold = [],
		delays = [100, 350, 700]
	}: { lines: string[]; wide?: number[]; heat?: number[]; cold?: number[]; delays?: number[] } = $props();

	const rows = $derived(
		lines.map((line, li) => {
			const glyphs = [...line.replace(/\s+/g, '')].length;
			let i = 0;
			const words = line.split(/\s+/).map((w) =>
				[...w].map((ch) => {
					const k = i++;
					return { ch, k, color: heat.includes(li) ? heatColor(0.42 + (0.58 * k) / Math.max(1, glyphs - 1)) : '' };
				})
			);
			return { words, wide: wide.includes(li), heat: heat.includes(li), cold: cold.includes(li), delay: delays[li] ?? 0 };
		})
	);
</script>
{#each rows as r, li (li)}
	<span class="kin" class:kin--wide={r.wide} class:kin--heat={r.heat} class:kin--cold={r.cold} style="--line-delay:{r.delay}ms">
		<span class="sr-only">{lines[li]}</span>
		<span aria-hidden="true">{#each r.words as w, wi (wi)}{#if wi > 0}{' '}{/if}<span class="w">{#each w as g (g.k)}<span class="ch" style="--i:{g.k}{g.color ? `;color:${g.color}` : ''}">{g.ch}</span>{/each}</span>{/each}</span>
	</span>
{/each}
