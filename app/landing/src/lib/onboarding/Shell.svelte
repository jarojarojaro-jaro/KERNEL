<script lang="ts">
	/**
	 * Onboarding frame: a heat-progress rail (01 Konto → 02 Droga → 03 Wynik), a small prototype
	 * chip, and a centred stage that slides in with a glow on every step. The rail fills from the
	 * previous step to this one; under reduced motion everything renders in its final state.
	 */
	import type { Snippet } from 'svelte';
	import { onMount } from 'svelte';
	import { currentLang } from '$lib/i18n';
	import { ob } from './copy';
	import { loadSession, session } from './session.svelte';

	let {
		step,
		title,
		lead,
		wide = false,
		children
	}: { step: 1 | 2 | 3; title: string; lead: string; wide?: boolean; children: Snippet } = $props();
	const lang = $derived(currentLang());
	const t = $derived(ob[lang]);
	const fill = $derived((step - 1) / 2);
	const from = $derived(Math.max(0, step - 2) / 2);

	onMount(loadSession);
</script>

<svelte:head><meta name="description" content={lead} /></svelte:head>

<div class="shell">
	<div class="aura" aria-hidden="true"></div>
	<div class="container top">
		<nav class="rail" aria-label={t.stepOf(step, 3)} style="--fill:{fill}; --from:{from}">
			<div class="track" aria-hidden="true"><i></i></div>
			<ol>
				{#each t.steps as label, i (label)}
					<li class:done={i + 1 < step} class:current={i + 1 === step} aria-current={i + 1 === step ? 'step' : undefined} style="--x:{i / 2}">
						<span class="dot mono">{#if i + 1 < step}<span aria-hidden="true">✓</span>{:else}{String(i + 1).padStart(2, '0')}{/if}</span>
						<span class="lbl">{label}</span>
					</li>
				{/each}
			</ol>
		</nav>
		<div class="meta">
			<details class="proto">
				<summary><span class="pdot" aria-hidden="true"></span>{t.protoChip}</summary>
				<p>{t.prototype}</p>
			</details>
			{#if session.account}
				<p class="who">{t.account.signedAs} <strong>{session.account.email ?? session.account.method}</strong></p>
			{/if}
		</div>
	</div>

	<div class="stage container" class:wide>
		<header class="head">
			<p class="eyebrow">{t.stepOf(step, 3)}</p>
			<h1 class="giga title">{title}</h1>
			<p class="lede">{lead}</p>
		</header>
		<div class="body">
			{@render children()}
		</div>
	</div>
</div>

<style>
	.shell {
		position: relative;
		padding-block: var(--sp-8) var(--sp-20);
		overflow-x: clip;
		isolation: isolate;
	}
	/* slow ember field behind the stage */
	.aura {
		position: absolute;
		inset: -10% -20% auto;
		height: 46rem;
		z-index: -1;
		pointer-events: none;
		background:
			radial-gradient(38% 42% at 50% 18%, color-mix(in srgb, var(--heat-3) 20%, transparent), transparent 70%),
			radial-gradient(30% 30% at 22% 40%, color-mix(in srgb, var(--heat-2) 12%, transparent), transparent 70%),
			radial-gradient(26% 30% at 80% 34%, color-mix(in srgb, var(--heat-4) 10%, transparent), transparent 70%);
	}
	:global(:root[data-theme='light']) .aura {
		opacity: 0.7;
	}
	@media (prefers-reduced-motion: no-preference) {
		.aura {
			animation: aura 14s var(--ease-in-out) infinite alternate;
		}
	}
	@keyframes aura {
		to {
			transform: translate3d(2%, 3%, 0) scale(1.06);
		}
	}

	/* ---------- rail ---------- */
	.top {
		display: grid;
		gap: var(--sp-4);
		justify-items: center;
	}
	.rail {
		position: relative;
		width: min(100%, 34rem);
		padding-top: 0.2rem;
	}
	.track {
		position: absolute;
		left: 1.25rem;
		right: 1.25rem;
		top: calc(0.2rem + 1.25rem - 1.5px);
		height: 3px;
		border-radius: var(--r-pill);
		background: var(--bg-3);
		overflow: hidden;
	}
	.track i {
		position: absolute;
		inset: 0;
		border-radius: inherit;
		background: var(--heat-ramp-hot);
		transform-origin: left;
		transform: scaleX(var(--fill));
		box-shadow: 0 0 14px color-mix(in srgb, var(--heat-3) 80%, transparent);
	}
	@media (prefers-reduced-motion: no-preference) {
		.track i {
			animation: rail-fill 1.1s var(--ease-out) 0.15s both;
		}
	}
	@keyframes rail-fill {
		from {
			transform: scaleX(var(--from));
		}
	}
	.rail ol {
		position: relative;
		display: flex;
		justify-content: space-between;
		list-style: none;
		margin: 0;
		padding: 0;
	}
	.rail li {
		display: grid;
		justify-items: center;
		gap: var(--sp-2);
		width: 5rem;
		margin-inline: -1.25rem;
		color: var(--text-mute);
		font-size: var(--fs-sm);
	}
	.dot {
		display: grid;
		place-items: center;
		width: 2.5rem;
		height: 2.5rem;
		border-radius: 50%;
		border: 1px solid var(--line-strong);
		background: var(--bg-1);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
		transition:
			background-color var(--dur-3) var(--ease-out),
			box-shadow var(--dur-3) var(--ease-out);
	}
	.done .dot {
		border-color: transparent;
		background: linear-gradient(135deg, var(--heat-2), var(--heat-3));
		color: #120702;
		font-size: var(--fs-sm);
		font-weight: 700;
	}
	.current .dot {
		border-color: transparent;
		background: var(--heat-ramp-hot);
		color: #120702;
		font-weight: 600;
		box-shadow:
			0 0 0 4px color-mix(in srgb, var(--heat-3) 22%, transparent),
			0 0 26px color-mix(in srgb, var(--heat-3) 70%, transparent);
	}
	@media (prefers-reduced-motion: no-preference) {
		.current .dot {
			animation: pulse 2.4s var(--ease-in-out) 1.2s infinite;
		}
	}
	@keyframes pulse {
		50% {
			box-shadow:
				0 0 0 8px color-mix(in srgb, var(--heat-3) 10%, transparent),
				0 0 38px color-mix(in srgb, var(--heat-3) 85%, transparent);
		}
	}
	.current .lbl {
		color: var(--text-hi);
		font-weight: 600;
	}
	.done .lbl {
		color: var(--text);
	}

	/* ---------- prototype chip ---------- */
	.meta {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		align-items: center;
		gap: var(--sp-2) var(--sp-4);
	}
	.proto {
		position: relative;
		font-size: var(--fs-xs);
	}
	.proto summary {
		list-style: none;
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.3rem 0.8rem;
		border: 1px solid color-mix(in srgb, var(--heat-3) 45%, var(--line));
		border-radius: var(--r-pill);
		background: color-mix(in srgb, var(--heat-3) 7%, transparent);
		color: var(--text);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		font-stretch: 87.5%;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		cursor: pointer;
	}
	.proto summary::-webkit-details-marker {
		display: none;
	}
	.pdot {
		width: 0.45rem;
		height: 0.45rem;
		border-radius: 50%;
		background: var(--heat-3);
		box-shadow: 0 0 8px var(--heat-3);
	}
	.proto p {
		position: absolute;
		z-index: 5;
		left: 50%;
		top: calc(100% + 0.5rem);
		transform: translateX(-50%);
		width: min(22rem, 86vw);
		padding: var(--sp-3) var(--sp-4);
		border: 1px solid var(--line-strong);
		border-radius: var(--r-lg);
		background: var(--bg-2);
		box-shadow: var(--shadow-2);
		color: var(--text);
		line-height: 1.5;
	}
	.who {
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.who strong {
		color: var(--text-hi);
		font-weight: 600;
	}

	/* ---------- stage ---------- */
	.stage {
		display: grid;
		justify-items: center;
		gap: var(--sp-10);
		margin-top: clamp(2.5rem, 1.5rem + 3vw, 4.5rem);
	}
	.head {
		display: grid;
		justify-items: center;
		gap: var(--sp-4);
		text-align: center;
		max-width: 46rem;
	}
	.title {
		position: relative;
		padding-bottom: var(--sp-4);
	}
	.title::after {
		content: '';
		position: absolute;
		left: 50%;
		bottom: 0;
		width: 4.5rem;
		height: 3px;
		margin-left: -2.25rem;
		border-radius: var(--r-pill);
		background: var(--heat-ramp-hot);
		box-shadow: 0 0 18px color-mix(in srgb, var(--heat-3) 70%, transparent);
	}
	.head .lede {
		max-width: 40ch;
		margin-inline: auto;
	}
	.body {
		width: min(100%, 40rem);
	}
	.wide .body {
		width: min(100%, 68rem);
	}
	@media (prefers-reduced-motion: no-preference) {
		.head,
		.body {
			animation: stage-in 0.85s var(--ease-out) both;
		}
		.body {
			animation-delay: 0.12s;
		}
	}
	@keyframes stage-in {
		from {
			opacity: 0.01;
			transform: translate3d(3rem, 0, 0);
		}
	}
	@media (max-width: 520px) {
		.rail li {
			font-size: var(--fs-xs);
		}
		.stage {
			gap: var(--sp-8);
		}
	}
</style>
