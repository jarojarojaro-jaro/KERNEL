<script lang="ts">
	/**
	 * Two-width headline: the copy's `|` splits a condensed lead (wdth 75, lighter) from a wide
	 * payoff (wdth 125, heavy). The width contrast is the brief's kinetic device; when the heading
	 * scrolls in, the payoff stretches from 75 to 125 (CSS only, reduced motion = final state).
	 */
	import { reveal } from '$lib/fx/actions';

	let {
		text,
		tag = 'h2',
		id,
		size = 'giga',
		/** 'duo' = condensed lead + wide payoff (kept for 2–3 key moments); 'plain' = one cut, one width. */
		mode = 'duo'
	}: { text: string; tag?: 'h1' | 'h2' | 'h3'; id?: string; size?: 'giga' | 'scene' | 'mega' | 'sub'; mode?: 'duo' | 'plain' } = $props();
	const parts = $derived(text.split('|'));
</script>

<svelte:element this={tag} {id} class="duo duo--{size} duo--{mode}" use:reveal={{ threshold: 0.4 }}>
	{#if mode === 'plain'}{parts.join(' ')}{:else if parts.length > 1}<span class="lo">{parts[0]}</span>{' '}<span class="hi">{parts[1]}</span>{:else}{text}{/if}
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
	.lo {
		display: block;
		font-weight: 560;
		font-stretch: 75%;
		color: var(--text);
		letter-spacing: -0.02em;
	}
	.hi {
		display: block;
		font-weight: 840;
		font-stretch: 125%;
		letter-spacing: -0.045em;
	}
	/* scene headings sit in a narrow column: a slightly narrower payoff avoids orphaned words */
	.duo--scene .hi {
		font-stretch: 112%;
	}
	@media (prefers-reduced-motion: no-preference) {
		:global(html.js) .duo:not([data-in]) .hi {
			font-stretch: 75%;
			opacity: 0.2;
		}
		.hi {
			transition:
				font-stretch 1.1s var(--ease-out) 0.15s,
				opacity 0.6s var(--ease-out) 0.15s;
		}
	}
</style>
