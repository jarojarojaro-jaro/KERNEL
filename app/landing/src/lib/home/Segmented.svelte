<script lang="ts" generics="T extends string">
	/**
	 * Tactile segmented control with radio-group semantics: one tab stop, arrow keys / Home / End
	 * move and select (WAI-ARIA radio group pattern). A bone thumb slides under the choice.
	 */
	import { tick } from 'svelte';
	import type { ModelKey } from '$lib/data/measurements';
	import ModelMark from '$lib/ModelMark.svelte';

	let {
		options,
		value = $bindable(),
		label,
		size = 'md'
	}: { options: { id: T; label: string; sub?: string; mark?: ModelKey }[]; value: T; label: string; size?: 'md' | 'lg' } = $props();

	let root: HTMLDivElement | undefined = $state();
	const idx = $derived(Math.max(0, options.findIndex((o) => o.id === value)));

	async function key(e: KeyboardEvent) {
		const n = options.length;
		const move: Record<string, number> = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 };
		let next = idx;
		if (e.key in move) next = (idx + move[e.key] + n) % n;
		else if (e.key === 'Home') next = 0;
		else if (e.key === 'End') next = n - 1;
		else return;
		e.preventDefault();
		value = options[next].id;
		await tick();
		root?.querySelectorAll<HTMLElement>('[role="radio"]')[next]?.focus();
	}
</script>

<div bind:this={root} class="seg seg--{size}" role="radiogroup" aria-label={label} tabindex="-1" onkeydown={key} style="--n:{options.length}; --i:{idx}; --col:{idx % 2}; --row:{Math.floor(idx / 2)}">
	<span class="thumb" aria-hidden="true"></span>
	{#each options as o, i (o.id)}
		<button type="button" role="radio" aria-checked={i === idx} tabindex={i === idx ? 0 : -1} onclick={() => (value = o.id)}>
			<span class="l">{#if o.mark}<ModelMark model={o.mark} size="0.7em" />{' '}{/if}{o.label}</span>
			{#if o.sub}<span class="s">{o.sub}</span>{/if}
		</button>
	{/each}
</div>

<style>
	.seg {
		position: relative;
		display: grid;
		grid-template-columns: repeat(var(--n), minmax(0, 1fr));
		padding: 5px;
		border: 1px solid var(--line);
		border-radius: var(--r-lg);
		background: var(--bg-1);
		box-shadow: inset 0 2px 10px rgb(0 0 0 / 0.6);
		isolation: isolate;
	}
	.seg:focus {
		outline: none;
	}
	.thumb {
		position: absolute;
		top: 5px;
		bottom: 5px;
		left: 5px;
		width: calc((100% - 10px) / var(--n));
		border-radius: calc(var(--r-lg) - 4px);
		/* selected = bone fill: heat colour is reserved for speed */
		background: linear-gradient(180deg, #f4f1ea, #dcd8cf);
		box-shadow:
			0 1px 0 rgb(255 255 255 / 0.6) inset,
			0 8px 22px -10px rgb(237 234 227 / 0.45),
			0 2px 6px rgb(0 0 0 / 0.6);
		transform: translate3d(calc(var(--i) * 100%), 0, 0);
		transition: transform 0.45s var(--ease-spring);
		z-index: -1;
	}
	button {
		display: grid;
		justify-items: center;
		align-content: center;
		gap: 0.15rem;
		min-height: 3rem;
		padding: 0.55rem 0.6rem;
		border: 0;
		border-radius: calc(var(--r-lg) - 4px);
		background: transparent;
		color: var(--text);
		font: inherit;
		cursor: pointer;
		transition:
			color var(--dur-2),
			transform var(--dur-1);
		text-align: center;
	}
	button:hover {
		color: var(--text-hi);
	}
	button:active {
		transform: scale(0.96);
	}
	button[aria-checked='true'] {
		color: var(--text-inv);
	}
	button[aria-checked='true']:focus-visible {
		outline-color: var(--text-hi);
	}
	button:focus-visible {
		outline: 2px solid var(--focus);
		outline-offset: 2px;
	}
	.l {
		font-weight: 700;
		font-stretch: 110%;
		font-size: var(--fs-base);
		letter-spacing: -0.01em;
		line-height: 1.15;
	}
	.seg--lg .l {
		font-size: clamp(1rem, 0.8rem + 0.8vw, 1.4rem);
	}
	.s {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.04em;
		color: var(--text-mute);
	}
	button[aria-checked='true'] .s {
		color: rgb(5 5 6 / 0.62);
	}
	@media (max-width: 640px) {
		.seg--lg {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
		.seg--lg .thumb {
			width: calc((100% - 10px) / 2);
			height: calc((100% - 10px) / 2);
			bottom: auto;
			transform: translate3d(calc(var(--col) * 100%), calc(var(--row) * 100%), 0);
		}
		/* long model names: stack the options vertically */
		.seg--md {
			grid-template-columns: minmax(0, 1fr);
		}
		.seg--md button {
			grid-auto-flow: column;
			justify-content: space-between;
			min-height: 2.75rem;
			padding-inline: 0.9rem;
		}
		.seg--md .thumb {
			width: calc(100% - 10px);
			height: calc((100% - 10px) / var(--n));
			bottom: auto;
			transform: translate3d(0, calc(var(--i) * 100%), 0);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.thumb {
			transition: none;
		}
	}
</style>
