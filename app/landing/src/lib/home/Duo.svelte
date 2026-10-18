<script lang="ts">
	/**
	 * Two-line headline: the copy's `|` splits the lead from the payoff, both in the same heavy cut.
	 * The payoff carries an ember underline (heat in the divider, not the letters); only `burn`
	 * headings (the final section) set the payoff itself in the heat gradient with a bloom.
	 */
	import { reveal } from '$lib/fx/actions';

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
	{#if mode === 'plain'}{parts.join(' ')}{:else if parts.length > 1}<span class="lo">{parts[0]}</span>{' '}<span class="hi" class:burn><span class="ul">{parts[1]}</span></span>{:else}{text}{/if}
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
	/* heat in the underline: an ember stroke under the payoff, following every wrapped line */
	.ul {
		background: linear-gradient(90deg, var(--heat-2), var(--heat-3) 45%, var(--heat-4)) no-repeat 0 92% / 100% 0.075em;
		-webkit-box-decoration-break: clone;
		box-decoration-break: clone;
		padding-bottom: 0.06em;
	}
	/* the final section: the payoff itself burns, heat ramp drifting through the letters */
	.hi.burn {
		background: linear-gradient(90deg, var(--heat-2), var(--heat-3) 30%, var(--heat-4) 55%, var(--heat-5) 70%, var(--heat-3) 100%) 0 0 / 200% 100%;
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
		filter: drop-shadow(0 0 24px rgb(255 122 26 / 0.35));
	}
	.hi.burn .ul {
		background: none;
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
