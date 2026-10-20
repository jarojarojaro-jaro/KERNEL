<script lang="ts">
	/**
	 * Onboarding frame: an optional quiet back link, the step rail (Konto → Droga → Sprzęt → Wynik),
	 * the step's big headline (*accent* words via Hl) with a one-line lede, the step content, and a
	 * small prototype chip under it. The stage slides in once; under reduced motion it renders in its
	 * final state.
	 */
	import type { Snippet } from 'svelte';
	import { onMount } from 'svelte';
	import Hl from '$lib/home/Hl.svelte';
	import { currentLang, href } from '$lib/i18n';
	import { ob } from './copy';
	import { loadSession, session } from './session.svelte';

	let {
		title,
		lead,
		/** 1-based position in `ob[lang].steps`: account 1, paths 2, hardware/download/terminal 3, result 4. */
		step,
		wide = false,
		/** Path of the previous step (e.g. '/start/paths'); omitted on the first step. */
		back,
		children
	}: { title: string; lead: string; step: number; wide?: boolean; back?: string; children: Snippet } = $props();
	const lang = $derived(currentLang());
	const t = $derived(ob[lang]);

	onMount(loadSession);
</script>

<svelte:head><meta name="description" content={lead} /></svelte:head>

<div class="shell heat-scope">
	<div class="aura" aria-hidden="true"></div>
	<div class="stage container" class:wide>
		{#if back}<a class="back" href={href(lang, back)}><span aria-hidden="true">←</span> {t.back}</a>{/if}
		<header class="head">
			<nav class="rail" aria-label={t.progress}>
				<ol role="list">
					{#each t.steps as name, i (name)}
						<li class:done={i + 1 < step} class:now={i + 1 === step} aria-current={i + 1 === step ? 'step' : undefined}>
							<span class="seg" aria-hidden="true"><i></i></span>
							<span class="lbl"><span class="n mono" aria-hidden="true">{String(i + 1).padStart(2, '0')}</span><span class="sr-only">{t.stepOf(i + 1, t.steps.length)}: </span><span class="name">{name}</span></span>
						</li>
					{/each}
				</ol>
			</nav>
			<h1 class="giga title"><Hl text={title} /></h1>
			<p class="lede">{lead}</p>
		</header>
		<div class="body">
			{@render children()}
		</div>
		<div class="meta">
			<details class="proto">
				<summary><span class="pdot" aria-hidden="true"></span>{t.protoChip}</summary>
				<p>{t.prototype}</p>
			</details>
			{#if session.account}
				<p class="who">{session.account.method === 'waitlist' ? t.account.listedAs : t.account.signedAs} <strong>{session.account.email ?? session.account.method}</strong></p>
			{/if}
		</div>
	</div>
</div>

<style>
	.shell {
		position: relative;
		padding-block: clamp(2.5rem, 1.5rem + 4vw, 5.5rem) var(--sp-20);
		overflow-x: clip;
		isolation: isolate;
	}
	/* slow ember field behind the headline */
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
	/* on bone, only the bright end of the ramp: amber and orange light, never rust */
	:global(:root[data-theme='light']) .aura {
		background:
			radial-gradient(38% 40% at 50% 16%, color-mix(in srgb, var(--heat-4) 30%, transparent), transparent 70%),
			radial-gradient(28% 30% at 24% 38%, color-mix(in srgb, var(--heat-3) 11%, transparent), transparent 70%),
			radial-gradient(26% 30% at 78% 32%, color-mix(in srgb, var(--heat-5) 70%, transparent), transparent 70%);
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

	.stage {
		display: grid;
		/* a wide child (TUI preview) must scroll, not widen the column */
		grid-template-columns: minmax(0, 1fr);
		justify-items: center;
		gap: var(--sp-10);
	}
	.back {
		justify-self: start;
		margin-bottom: calc(-1 * var(--sp-6));
		color: var(--text-mute);
		text-decoration: none;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.1em;
		text-transform: uppercase;
	}
	.back:hover {
		color: var(--text-hi);
	}
	.head {
		display: grid;
		justify-items: center;
		gap: var(--sp-4);
		text-align: center;
		max-width: 46rem;
	}
	/* ---------- step rail: four segments, heat fills up to the current step ---------- */
	.rail {
		width: min(100%, 30rem);
		margin-bottom: var(--sp-2);
	}
	.rail ol {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: var(--sp-2);
	}
	.rail li {
		display: grid;
		gap: var(--sp-2);
		justify-items: start;
		color: var(--text-mute);
		font-size: var(--fs-xs);
		text-align: left;
	}
	.seg {
		position: relative;
		width: 100%;
		height: 3px;
		border-radius: var(--r-pill);
		background: var(--line);
		overflow: hidden;
	}
	.seg i {
		position: absolute;
		inset: 0;
		border-radius: inherit;
		background: linear-gradient(90deg, var(--heat-2), var(--heat-3) 70%, var(--heat-4));
		transform: scaleX(0);
		transform-origin: left;
	}
	.done .seg i,
	.now .seg i {
		transform: none;
	}
	.now .seg {
		box-shadow: 0 0 14px color-mix(in srgb, var(--heat-3) 60%, transparent);
	}
	.lbl {
		display: inline-flex;
		align-items: baseline;
		gap: 0.4rem;
		white-space: nowrap;
	}
	.n {
		font-size: var(--fs-2xs);
		letter-spacing: 0.06em;
	}
	.done .n {
		color: var(--accent-ink);
	}
	.now {
		color: var(--text-hi);
		font-weight: 600;
	}
	.now .n {
		color: var(--accent-ink);
	}
	@media (prefers-reduced-motion: no-preference) {
		.now .seg i {
			animation: rail-fill 1.1s var(--ease-out) 0.35s both;
		}
	}
	@keyframes rail-fill {
		from {
			transform: scaleX(0);
		}
	}
	/* narrow phones: only the current step keeps its name; numbers and segments carry the rest */
	@media (max-width: 480px) {
		.rail li:not(.now) .name {
			position: absolute;
			width: 1px;
			height: 1px;
			overflow: hidden;
			clip-path: inset(50%);
			white-space: nowrap;
		}
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
		background: linear-gradient(90deg, var(--heat-2), var(--heat-3) 55%, var(--heat-4));
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

	/* ---------- prototype chip (under the content) ---------- */
	.meta {
		display: flex;
		flex-wrap: wrap;
		justify-content: center;
		align-items: center;
		gap: var(--sp-2) var(--sp-4);
		margin-top: calc(-1 * var(--sp-4));
	}
	.proto {
		position: relative;
	}
	.proto summary {
		list-style: none;
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.3rem 0.8rem;
		border: 1px solid var(--line);
		border-radius: var(--r-pill);
		color: var(--text-mute);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.08em;
		text-transform: uppercase;
		cursor: pointer;
	}
	.proto summary:hover {
		color: var(--text-hi);
		border-color: var(--line-strong);
	}
	.proto summary::-webkit-details-marker {
		display: none;
	}
	.pdot {
		width: 0.4rem;
		height: 0.4rem;
		border-radius: 50%;
		background: var(--heat-3);
	}
	.proto p {
		position: absolute;
		z-index: 5;
		left: 50%;
		bottom: calc(100% + 0.5rem);
		transform: translateX(-50%);
		width: min(22rem, 86vw);
		padding: var(--sp-3) var(--sp-4);
		border: 1px solid var(--line-strong);
		border-radius: var(--r-lg);
		background: var(--bg-2);
		box-shadow: var(--shadow-2);
		color: var(--text);
		font-size: var(--fs-xs);
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
	@media (max-width: 520px) {
		.stage {
			gap: var(--sp-8);
		}
		.back {
			margin-bottom: calc(-1 * var(--sp-4));
		}
	}
</style>
