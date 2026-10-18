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

<Shell title={t.title} lead={t.lead} wide back="/start/paths">
	<ul class="oses" role="list">
		{#each list as o (o)}
			<li class="card os" class:det={detected === o} class:heat-card={detected === o}>
				<span class="osic" aria-hidden="true">
					{#if o === 'windows'}
						<svg viewBox="0 0 24 24" fill="currentColor"><path d="M3 5.5 10.5 4.4v7.1H3zM11.5 4.3 21 3v8.5h-9.5zM3 12.5h7.5v7.1L3 18.5zM11.5 12.5H21V21l-9.5-1.3z" /></svg>
					{:else if o === 'linux'}
						<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"><path d="M12 3c-2.2 0-3.4 1.9-3.4 4.4 0 1.6-.6 2.8-1.8 4.4C5.4 13.6 4.5 15.4 5 17.5c.4 1.8 2.6 2.4 4 2.5h6c1.4-.1 3.6-.7 4-2.5.5-2.1-.4-3.9-1.8-5.7-1.2-1.6-1.8-2.8-1.8-4.4C15.4 4.9 14.2 3 12 3Z" /><circle cx="10.3" cy="8" r=".8" fill="currentColor" /><circle cx="13.7" cy="8" r=".8" fill="currentColor" /></svg>
					{:else}
						<svg viewBox="0 0 24 24" fill="currentColor"><path d="M16.4 12.6c0-2.4 2-3.5 2-3.6-1.1-1.6-2.8-1.8-3.4-1.8-1.4-.2-2.8.8-3.5.8s-1.8-.8-3-.8C7 7.3 5.5 8.2 4.7 9.7c-1.7 2.9-.4 7.2 1.2 9.6.8 1.2 1.7 2.4 3 2.4 1.2-.1 1.6-.8 3-.8s1.8.8 3 .8c1.3 0 2.1-1.2 2.9-2.3.9-1.3 1.3-2.6 1.3-2.7 0 0-2.6-1-2.7-4.1ZM14.1 5.4c.6-.8 1.1-1.9 1-3-.9 0-2.1.6-2.7 1.4-.6.7-1.1 1.8-1 2.8 1.1.1 2.1-.5 2.7-1.2Z" /></svg>
					{/if}
				</span>
				<div class="cluster between">
					<h2 class="h3">{t.os[o]}</h2>
					{#if detected === o}<span class="badge badge--measured badge--plain">{t.detected}</span>{/if}
				</div>
				<p class="small mute">{t.notes[o]}</p>
				<button class="btn btn--secondary btn--block" type="button" disabled aria-describedby="dl-{o}">{t.button}</button>
				<p class="source" id="dl-{o}"><span class="badge badge--soon">{t.notYet}</span> · {t.target}</p>
			</li>
		{/each}
	</ul>
	<section class="card card--inset heat-wash after" aria-labelledby="after-title">
		<h2 id="after-title" class="h3">{t.after}</h2>
		<ol>{#each t.afterSteps as s, i (s)}<li><span class="n mono">{String(i + 1).padStart(2, '0')}</span><span>{s}</span></li>{/each}</ol>
		<figure class="device">
			<div class="code mono heat-num" aria-hidden="true">WDJB-MJHT</div>
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
		gap: var(--sp-5);
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
		padding: var(--sp-6);
	}
	.osic {
		display: grid;
		place-items: center;
		width: 3.5rem;
		height: 3.5rem;
		margin-bottom: var(--sp-2);
		border: 1px solid var(--line-strong);
		border-radius: var(--r-lg);
		color: var(--text-hi);
	}
	.osic svg {
		width: 1.6rem;
		height: 1.6rem;
	}
	.det .osic {
		color: var(--accent-ink);
		border-color: color-mix(in srgb, var(--heat-3) 60%, transparent);
		box-shadow: 0 0 30px -6px color-mix(in srgb, var(--heat-3) 70%, transparent);
	}
	.between {
		justify-content: space-between;
	}
	.after {
		display: grid;
		gap: var(--sp-5);
		margin-top: var(--sp-6);
		padding: var(--sp-8);
		overflow: hidden;
	}
	.after ol {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(14rem, 1fr));
		gap: var(--sp-4);
	}
	.after li {
		display: grid;
		gap: var(--sp-2);
		padding-top: var(--sp-3);
		border-top: 2px solid transparent;
		border-image: linear-gradient(90deg, var(--heat-2), var(--heat-4)) 1;
		font-size: var(--fs-sm);
	}
	.n {
		font-size: var(--fs-xs);
		color: var(--accent-ink);
	}
	.device {
		margin: 0;
		display: grid;
		gap: var(--sp-2);
		justify-items: start;
	}
	.code {
		font-size: clamp(1.75rem, 1.2rem + 2vw, 2.75rem);
		font-weight: 500;
		letter-spacing: 0.14em;
		padding: var(--sp-3) var(--sp-6);
		border: 1px dashed color-mix(in srgb, var(--heat-3) 60%, var(--line-strong));
		border-radius: var(--r-lg);
	}
</style>
