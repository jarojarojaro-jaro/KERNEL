<script lang="ts" generics="T extends string">
	import type { ModelKey } from '$lib/data/measurements';
	import ModelMark from '$lib/ModelMark.svelte';
	/**
	 * Radio-group picker built on native radios: arrow keys move the choice, Tab leaves the group,
	 * the legend names it. Styled as tactile key caps; the checked cap glows.
	 */
	let {
		legend,
		name,
		options,
		value = $bindable(),
		size = 'md',
		hideLegend = false,
		/** Narrow screens: an even 2-column grid instead of ragged wrapping (nothing runs off the edge). */
		tight = false
	}: {
		legend: string;
		name: string;
		options: { value: T; label: string; sub?: string; disabled?: boolean; model?: ModelKey }[];
		value: T;
		size?: 'md' | 'lg';
		hideLegend?: boolean;
		tight?: boolean;
	} = $props();
</script>

<fieldset class="choice choice--{size}" class:tight>
	<legend class:sr-only={hideLegend}>{legend}</legend>
	<div class="caps">
		{#each options as o (o.value)}
			<label class="cap" class:on={value === o.value} class:off={o.disabled}>
				<input type="radio" {name} value={o.value} bind:group={value} disabled={o.disabled} />
				<span class="l">{#if o.model}<ModelMark model={o.model} /> {/if}{o.label}</span>
				{#if o.sub}<span class="s">{o.sub}</span>{/if}
			</label>
		{/each}
	</div>
</fieldset>

<style>
	.choice {
		border: 0;
		margin: 0;
		padding: 0;
		min-width: 0;
	}
	legend {
		padding: 0;
		margin-bottom: var(--sp-2);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		text-transform: uppercase;
		letter-spacing: 0.12em;
		color: var(--text-mute);
	}
	.caps {
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-2);
	}
	.cap {
		position: relative;
		display: inline-grid;
		align-content: center;
		gap: 0.1rem;
		min-height: 2.75rem;
		padding: 0.45rem 1rem;
		border: 1px solid var(--line);
		border-radius: var(--r-md);
		background: linear-gradient(180deg, var(--bg-3), var(--bg-2));
		box-shadow:
			0 1px 0 rgb(255 255 255 / 0.05) inset,
			0 2px 0 #000,
			0 6px 14px -8px #000;
		color: var(--text);
		cursor: pointer;
		user-select: none;
		transition:
			transform var(--dur-1) var(--ease-out),
			box-shadow var(--dur-2),
			border-color var(--dur-2),
			color var(--dur-2);
	}
	/* hover warms the key: heat rim and an ember underglow; selection itself stays bone */
	.cap:hover {
		border-color: var(--heat-3);
		color: var(--text-hi);
		box-shadow:
			0 1px 0 rgb(255 255 255 / 0.05) inset,
			0 2px 0 #000,
			0 10px 26px -12px rgb(255 122 26 / 0.7);
	}
	.cap:active {
		transform: translateY(2px);
		box-shadow:
			0 1px 0 rgb(255 255 255 / 0.04) inset,
			0 0 0 #000;
	}
	/* selected: bone outline and a lit key, never heat (heat means speed only) */
	.cap.on {
		color: var(--text-hi);
		border-color: var(--text-hi);
		background: linear-gradient(180deg, #2a2926, var(--bg-2));
		box-shadow:
			0 1px 0 rgb(255 255 255 / 0.1) inset,
			0 2px 0 #000,
			0 0 0 1px rgb(237 234 227 / 0.25),
			0 10px 30px -14px rgb(255 122 26 / 0.55);
	}
	.cap.on::before {
		content: '';
		position: absolute;
		top: 0.45rem;
		right: 0.45rem;
		width: 0.35rem;
		height: 0.35rem;
		border-radius: 50%;
		background: var(--text-hi);
	}
	.cap.off {
		opacity: 0.45;
		cursor: not-allowed;
	}
	.cap:has(input:focus-visible) {
		outline: 2px solid var(--focus);
		outline-offset: 3px;
	}
	input {
		position: absolute;
		opacity: 0;
		width: 1px;
		height: 1px;
		pointer-events: none;
	}
	.l {
		font-weight: 650;
		font-stretch: 108%;
		font-size: var(--fs-sm);
		white-space: nowrap;
	}
	.s {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
		letter-spacing: 0.04em;
		white-space: nowrap;
	}
	@media (max-width: 40rem) {
		.tight .caps {
			display: grid;
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}
		.tight .cap {
			padding-inline: 0.75rem;
			min-width: 0;
		}
		.choice.tight .l {
			font-size: var(--fs-sm);
			white-space: normal;
		}
		.tight .s {
			white-space: normal;
		}
	}
	.choice--lg .cap {
		min-height: 3.5rem;
		padding: 0.6rem 1.15rem 0.6rem 1rem;
	}
	.choice--lg .l {
		font-size: var(--fs-md);
	}
</style>
