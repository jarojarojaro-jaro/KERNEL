<script lang="ts">
	/**
	 * The seven phases across the top. The backend's phase is the "current" step; finished steps (and
	 * steps whose data already exists) are buttons that open a read-only view of that step.
	 */
	import { STEPS, type Step } from '../lib/i18n';
	import { store } from '../lib/store.svelte';

	interface Props {
		/** The backend's step (for `error`, the step that failed). */
		current: Step;
		failed: boolean;
		/** The step on screen (null while the error screen is shown). */
		shown: Step | null;
		canOpen: (s: Step) => boolean;
		onselect: (s: Step) => void;
	}
	let { current, failed, shown, canOpen, onselect }: Props = $props();

	const t = $derived(store.t);
	const curIdx = $derived(STEPS.indexOf(current));
	const shownIdx = $derived(shown ? STEPS.indexOf(shown) : -1);
</script>

<nav class="stepper" aria-label={t.stepsLabel}>
	<ol style="--n:{STEPS.length}">
		{#each STEPS as s, i (s)}
			{@const state = i < curIdx || (i === curIdx && current === 'ready' && !failed) ? 'done' : i === curIdx ? (failed ? 'failed' : 'current') : 'todo'}
			<li class={state} class:shown={i === shownIdx}>
				{#if canOpen(s) && i !== shownIdx}
					<button type="button" onclick={() => onselect(s)} aria-current={i === curIdx ? 'step' : undefined}>
						<span class="dot" aria-hidden="true">{#if state === 'done'}✓{:else}{i + 1}{/if}</span>
						<span class="lbl">{t.steps[s]}</span>
						{#if state === 'done'}<span class="sr-only">({t.stepDone})</span>{/if}
					</button>
				{:else}
					<span class="item" aria-current={i === curIdx ? 'step' : undefined}>
						<span class="dot" aria-hidden="true">{#if state === 'done'}✓{:else if state === 'failed'}!{:else}{i + 1}{/if}</span>
						<span class="lbl">{t.steps[s]}</span>
						{#if state === 'done'}<span class="sr-only">({t.stepDone})</span>{/if}
					</span>
				{/if}
			</li>
		{/each}
	</ol>
</nav>

<style>
	.stepper {
		padding-top: var(--sp-6);
	}
	ol {
		display: grid;
		grid-template-columns: repeat(var(--n), minmax(0, 1fr));
		gap: 0;
		margin: 0;
		padding: 0;
		list-style: none;
	}
	li {
		position: relative;
		min-width: 0;
	}
	/* the rail between dots */
	li + li::before {
		content: '';
		position: absolute;
		top: 1.05rem;
		right: calc(50% + 1.1rem);
		left: calc(-50% + 1.1rem);
		height: 1px;
		background: var(--line);
	}
	li.done + li::before,
	li.done + li.current::before {
		background: color-mix(in srgb, var(--text-hi) 45%, transparent);
	}
	button,
	.item {
		display: grid;
		justify-items: center;
		gap: 0.5rem;
		width: 100%;
		padding: 0.15rem 0.25rem 0.6rem;
		border: 0;
		border-radius: var(--r-md);
		background: none;
		font: inherit;
		color: inherit;
		text-align: center;
	}
	button {
		cursor: pointer;
	}
	button:hover .lbl {
		color: var(--text-hi);
	}
	.dot {
		display: grid;
		place-items: center;
		width: 2.1rem;
		height: 2.1rem;
		border-radius: 50%;
		border: 1px solid var(--line-strong);
		background: var(--bg-1);
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		color: var(--text-mute);
		transition:
			background var(--dur-2) var(--ease-out),
			border-color var(--dur-2) var(--ease-out);
	}
	.lbl {
		font-size: var(--fs-xs);
		font-weight: 560;
		line-height: 1.25;
		color: var(--text-mute);
		text-wrap: balance;
	}
	.done .dot {
		background: var(--text-hi);
		border-color: var(--text-hi);
		color: var(--text-inv);
		font-weight: 700;
	}
	.done .lbl {
		color: var(--text);
	}
	.current .dot {
		border-color: var(--heat-3);
		color: var(--text-hi);
		box-shadow:
			0 0 0 3px color-mix(in srgb, var(--heat-3) 22%, transparent),
			0 0 18px -2px color-mix(in srgb, var(--heat-3) 55%, transparent);
	}
	.current .lbl {
		color: var(--text-hi);
	}
	.failed .dot {
		border-color: var(--danger-ink);
		color: var(--danger-ink);
		font-weight: 700;
	}
	.failed .lbl {
		color: var(--danger-ink);
	}
	.shown .lbl {
		color: var(--text-hi);
		text-decoration: underline;
		text-decoration-color: var(--heat-3);
		text-decoration-thickness: 2px;
		text-underline-offset: 0.4em;
	}
	@media (max-width: 760px) {
		.lbl {
			position: absolute;
			width: 1px;
			height: 1px;
			overflow: hidden;
			clip: rect(0 0 0 0);
			white-space: nowrap;
		}
		.dot {
			width: 1.9rem;
			height: 1.9rem;
		}
		li + li::before {
			top: 1.1rem;
			right: calc(50% + 1rem);
			left: calc(-50% + 1rem);
		}
		button,
		.item {
			padding-bottom: 0.15rem;
		}
	}
</style>
