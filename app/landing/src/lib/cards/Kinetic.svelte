<script lang="ts">
	/** Kinetic headline (showcase.css `.kin`): glyphs rise and widen in; the accessible name is the plain text. */
	let {
		lines,
		tag = 'h1',
		class: cls = 'mega',
		id,
		wide = -1,
		heat = -1,
		delay = 0
	}: { lines: string[]; tag?: 'h1' | 'h2'; class?: string; id?: string; wide?: number; heat?: number; delay?: number } = $props();
</script>

<svelte:element this={tag} class={cls} {id} aria-label={lines.join(' ')}>
	{#each lines as line, li (li)}
		{@const words = line.split(' ')}
		<span class="kin" class:kin--wide={li === wide} class:hot={li === heat} style="--line-delay:{delay + li * 220}ms;--n:{line.length}" aria-hidden="true">
			{#each words as word, wi (wi)}
				{@const at = words.slice(0, wi).join(' ').length + (wi ? 1 : 0)}
				{#if wi}{' '}{/if}<span class="w">{#each [...word] as ch, i (i)}<span class="ch" style="--i:{at + i}">{ch}</span>{/each}</span>
			{/each}
		</span>
	{/each}
</svelte:element>

<style>
	.w {
		display: inline-block;
		white-space: nowrap;
	}
	/* Explorer headlines: glyphs rise into place with transform and opacity only (composited; no
	   per-glyph font-weight/width animation, which costs layout on every frame), and they start at
	   0.01 opacity so the headline counts as painted from the first frame (LCP). The width contrast
	   stays in the static type: line 2 is set wide. */
	@media (prefers-reduced-motion: no-preference) {
		:global(html.js) .kin .ch {
			animation: kin-rise 0.8s var(--ease-out) both;
			animation-delay: calc(var(--line-delay, 0ms) + var(--i) * 28ms);
		}
	}
	.kin--wide {
		font-stretch: 125%;
	}
	@keyframes kin-rise {
		from {
			opacity: 0.01;
			transform: translate3d(0, 0.35em, 0);
		}
		to {
			opacity: 1;
			transform: none;
		}
	}
	/* One heat ramp across the whole line, sliced per glyph (each glyph is its own box). */
	.hot .ch {
		background: var(--heat-ramp-hot);
		background-size: calc(var(--n) * 100%) 100%;
		background-position: calc(var(--i) / max(1, var(--n) - 1) * 100%) 0;
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
	}
</style>
