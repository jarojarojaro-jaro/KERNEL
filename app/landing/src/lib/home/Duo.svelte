<script lang="ts">
	/**
	 * Two-line headline: the copy's `|` splits the lead from the payoff, both in the same heavy cut.
	 * One or two key words marked *…* in the copy carry the ember accent (`.hx-accent`, via Hl); only `burn`
	 * headings (the final section) set the whole payoff in the heat gradient with a bloom.
	 */
	import { reveal } from '$lib/fx/actions';
	import Hl from './Hl.svelte';

	let {
		text,
		tag = 'h2',
		id,
		size = 'giga',
		/** 'duo' = condensed lead + wide payoff (kept for 2–3 key moments); 'plain' = one cut, one width. */
		mode = 'duo',
		burn = false
	}: { text: string; tag?: 'h1' | 'h2' | 'h3'; id?: string; size?: 'giga' | 'scene' | 'mega' | 'sub'; mode?: 'duo' | 'plain'; burn?: boolean } = $props();
	const parts = $derived(text.split('|'));
</script>

<svelte:element this={tag} {id} class="duo duo--{size} duo--{mode}" use:reveal={{ threshold: 0.4 }}>
	{#if mode === 'plain'}<Hl text={parts.join(' ')} />{:else if parts.length > 1}<span class="lo"><Hl text={parts[0]} /></span>{' '}<span class="hi" class:burn><Hl text={parts[1]} /></span>{:else}<Hl {text} />{/if}
</svelte:element>

<style>
	.duo {
		font-family: var(--font-display);
		color: var(--text-hi);
		line-height: 0.92;
		letter-spacing: -0.035em;
		text-wrap: balance;
		margin: 0;
	}
	.duo--giga {
		font-size: clamp(2.6rem, 1rem + 5.6vw, 6.6rem);
	}
	.duo--mega {
		font-size: clamp(3rem, 1rem + 7.4vw, 8.75rem);
	}
	.duo--scene {
		font-size: clamp(2.1rem, 1rem + 3.4vw, 4.4rem);
	}
	.duo--sub {
		font-size: clamp(1.9rem, 1rem + 2.4vw, 3.4rem);
	}
	.duo--plain {
		font-weight: 780;
		font-stretch: 104%;
		letter-spacing: -0.03em;
		line-height: 1;
	}
	/* one face, one cut: the heavy display weight at one width; the payoff differs only in colour */
	.lo {
		display: block;
		font-weight: 800;
		font-stretch: 104%;
		letter-spacing: -0.035em;
		color: var(--text-hi);
	}
	.hi {
		display: block;
		font-weight: 800;
		font-stretch: 104%;
		letter-spacing: -0.035em;
		color: var(--text-hi);
		transform-origin: 0 50%;
	}
	/*
	 * The final section: the payoff itself burns, heat ramp drifting through the letters. The clipped
	 * background only paints inside the box, and the display line-height (0.92) is shorter than the
	 * glyphs: padding gives descenders (ę ą g y j p) and the last glyph's overhang their room, the
	 * negative margin keeps the layout where it was.
	 */
	.hi.burn {
		background: linear-gradient(90deg, var(--heat-2), var(--heat-3) 30%, var(--heat-4) 55%, var(--heat-5) 70%, var(--heat-3) 100%) 0 0 / 200% 100%;
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
		filter: drop-shadow(0 0 24px rgb(255 122 26 / 0.35));
		padding: 0.16em 0.1em 0.24em 0;
		margin: -0.16em -0.1em -0.24em 0;
	}
	/* inside the burning payoff the accent is the payoff itself */
	.hi.burn :global(.hx-accent) {
		background: none;
		color: inherit;
		padding: 0;
		margin: 0;
	}
	@media (prefers-reduced-motion: no-preference) {
		.hi.burn {
			animation: hi-drift 7s ease-in-out infinite alternate;
		}
		/* resting state final; entering view replays a stretch-in (transform only, no layout shift) */
		:global(html.js) .duo:global([data-in]) .hi {
			animation: hi-in 1.1s var(--ease-out) 0.15s backwards;
		}
		:global(html.js) .duo:global([data-in]) .hi.burn {
			animation:
				hi-in 1.1s var(--ease-out) 0.15s backwards,
				hi-drift 7s ease-in-out infinite alternate;
		}
	}
	@keyframes hi-in {
		from {
			transform: scaleX(0.8);
		}
	}
	@keyframes hi-drift {
		to {
			background-position: 100% 0;
		}
	}
</style>
