<script lang="ts">
	import { onMount } from 'svelte';
	import { currentLang, href } from '$lib/i18n';
	import { ob } from '$lib/onboarding/copy';
	import Shell from '$lib/onboarding/Shell.svelte';

	type Os = 'windows' | 'linux' | 'macos';
	const lang = $derived(currentLang());
	const t = $derived(ob[lang].download);
	const list: Os[] = ['windows', 'linux', 'macos'];
	let detected = $state<Os | null>(null);

	onMount(() => {
		const ua = navigator.userAgent;
		detected = /Mac OS X/.test(ua) ? 'macos' : /Linux/.test(ua) && !/Android/.test(ua) ? 'linux' : 'windows';
	});
</script>

<svelte:head><title>{t.title}</title></svelte:head>

<Shell step={3} title={t.title} lead={t.lead}>
	<ul class="oses" role="list">
		{#each list as o (o)}
			<li class="card os" class:det={detected === o}>
				<div class="cluster between">
					<h2 class="h3">{t.os[o]}</h2>
					{#if detected === o}<span class="badge badge--progress">{t.detected}</span>{/if}
				</div>
				<p class="small mute">{t.notes[o]}</p>
				<button class="btn btn--secondary btn--block" type="button" disabled aria-describedby="dl-{o}">{t.button}</button>
				<p class="source" id="dl-{o}"><span class="badge badge--soon">{t.notYet}</span> · {t.target}</p>
			</li>
		{/each}
	</ul>
	<section class="card card--inset after" aria-labelledby="after-title">
		<h2 id="after-title" class="h3">{t.after}</h2>
		<ol>{#each t.afterSteps as s (s)}<li>{s}</li>{/each}</ol>
		<figure class="device">
			<div class="code num" aria-hidden="true">WDJB-MJHT</div>
			<figcaption class="source">{t.codeExample} · RFC 8628</figcaption>
		</figure>
		<a class="btn btn--ghost" href={href(lang, '/start/terminal')}>{ob[lang].result.toTerminal} →</a>
	</section>
</Shell>

<style>
	.oses {
		list-style: none;
		padding: 0;
		margin: 0;
		display: grid;
		grid-template-columns: repeat(3, minmax(0, 1fr));
		gap: var(--sp-4);
	}
	@media (max-width: 860px) {
		.oses {
			grid-template-columns: 1fr;
		}
	}
	.os {
		display: grid;
		gap: var(--sp-3);
		align-content: start;
	}
	.os.det {
		border-color: color-mix(in srgb, var(--info-ink) 60%, var(--line));
	}
	.between {
		justify-content: space-between;
	}
	.after {
		display: grid;
		gap: var(--sp-4);
		max-width: 48rem;
	}
	.after ol {
		margin: 0;
		padding-left: 1.3em;
		display: grid;
		gap: var(--sp-2);
	}
	.device {
		margin: 0;
		display: grid;
		gap: var(--sp-2);
		justify-items: start;
	}
	.code {
		font-size: var(--fs-2xl);
		letter-spacing: 0.14em;
		color: var(--text-hi);
		padding: var(--sp-3) var(--sp-5);
		border: 1px dashed var(--line-strong);
		border-radius: var(--r-md);
		background: var(--bg-2);
	}
</style>
