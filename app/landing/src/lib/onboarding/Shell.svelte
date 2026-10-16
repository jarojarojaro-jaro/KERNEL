<script lang="ts">
	import type { Snippet } from 'svelte';
	import { onMount } from 'svelte';
	import { currentLang } from '$lib/i18n';
	import { ob } from './copy';
	import { loadSession, session } from './session.svelte';

	let { step, title, lead, children }: { step: 1 | 2 | 3; title: string; lead: string; children: Snippet } = $props();
	const lang = $derived(currentLang());
	const t = $derived(ob[lang]);

	onMount(loadSession);
</script>

<svelte:head><meta name="description" content={lead} /></svelte:head>

<div class="shell container">
	<nav class="stepper" aria-label={t.stepOf(step, 3)}>
		<ol>
			{#each t.steps as label, i (label)}
				<li class:done={i + 1 < step} class:current={i + 1 === step} aria-current={i + 1 === step ? 'step' : undefined}>
					<span class="idx num">{String(i + 1).padStart(2, '0')}</span>
					<span>{label}</span>
				</li>
			{/each}
		</ol>
		{#if session.account}
			<p class="who small mute">{t.account.signedAs} <strong>{session.account.email ?? session.account.method}</strong></p>
		{/if}
	</nav>
	<div class="notice notice--prototype proto" role="note">
		<span class="notice__icon">i</span>
		<p><span class="badge badge--prototype">{lang === 'pl' ? 'prototyp' : 'prototype'}</span> {t.prototype}</p>
	</div>
	<header class="head">
		<p class="overline">{t.stepOf(step, 3)}</p>
		<h1 class="h1">{title}</h1>
		<p class="lead">{lead}</p>
	</header>
	{@render children()}
</div>

<style>
	.shell {
		padding-block: var(--sp-8) var(--sp-16);
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: var(--sp-8);
	}
	.stepper {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: var(--sp-4);
		flex-wrap: wrap;
	}
	.stepper ol {
		display: flex;
		gap: var(--sp-2);
		list-style: none;
		margin: 0;
		padding: 0;
		flex-wrap: wrap;
	}
	.stepper li {
		display: flex;
		align-items: center;
		gap: var(--sp-2);
		padding: 0.35rem 0.75rem 0.35rem 0.4rem;
		border: 1px solid var(--line);
		border-radius: var(--r-pill);
		font-size: var(--fs-sm);
		color: var(--text-mute);
	}
	.idx {
		display: inline-grid;
		place-items: center;
		width: 1.6rem;
		height: 1.6rem;
		border-radius: 50%;
		background: var(--bg-3);
		font-size: var(--fs-2xs);
	}
	.stepper li.current {
		color: var(--text-hi);
		border-color: var(--accent-ink);
	}
	.stepper li.current .idx {
		background: var(--accent);
		color: var(--on-accent);
	}
	.stepper li.done .idx {
		background: var(--ok-soft);
		color: var(--text-hi);
		box-shadow: inset 0 0 0 1px var(--ok-ink);
	}
	.head {
		display: grid;
		gap: var(--sp-3);
		max-width: 48rem;
	}
</style>
