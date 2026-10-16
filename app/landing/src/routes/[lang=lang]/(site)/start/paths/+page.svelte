<script lang="ts">
	import { onMount } from 'svelte';
	import { currentLang, href } from '$lib/i18n';
	import { ob } from '$lib/onboarding/copy';
	import Shell from '$lib/onboarding/Shell.svelte';

	const lang = $derived(currentLang());
	const t = $derived(ob[lang].paths);
	let suggested = $state<string | null>(null);

	onMount(() => {
		// Hint only: a terminal user on Linux, everyone else the app. Never blocks a choice.
		suggested = /Linux/.test(navigator.userAgent) && !/Android/.test(navigator.userAgent) ? 'terminal' : 'download';
	});
</script>

<svelte:head><title>{t.title}</title></svelte:head>

<Shell step={2} title={t.title} lead={t.lead}>
	<ul class="paths" role="list">
		{#each t.items as p (p.id)}
			<li>
				<a class="card card--interactive path" href={href(lang, `/start/${p.id}`)} class:suggested={suggested === p.id}>
					<span class="step-index">{p.k}</span>
					<span class="h3 title">{p.title}</span>
					<span class="body">{p.body}</span>
					{#if suggested === p.id}<span class="badge badge--progress">{t.recommended}</span>{/if}
					<span class="go">{p.cta} <span class="arrow" aria-hidden="true">→</span></span>
				</a>
			</li>
		{/each}
	</ul>
</Shell>

<style>
	.paths {
		list-style: none;
		padding: 0;
		margin: 0;
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: var(--sp-4);
	}
	@media (max-width: 860px) {
		.paths {
			grid-template-columns: 1fr;
		}
	}
	.path {
		display: grid;
		gap: var(--sp-3);
		align-content: start;
		height: 100%;
		text-decoration: none;
		color: var(--text);
	}
	.path.suggested {
		border-color: var(--text-hi);
	}
	.title {
		color: var(--text-hi);
		font-weight: var(--fw-semibold);
	}
	.body {
		font-size: var(--fs-sm);
	}
	.path .badge {
		justify-self: start;
	}
	.go {
		margin-top: var(--sp-2);
		color: var(--text-hi);
		font-weight: var(--fw-semibold);
		font-size: var(--fs-sm);
	}
	.path:hover .arrow {
		display: inline-block;
		transform: translateX(3px);
	}
</style>
