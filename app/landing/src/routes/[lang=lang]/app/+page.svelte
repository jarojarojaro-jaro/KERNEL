<script lang="ts">
	import { currentLang, href } from '$lib/i18n';
	import { T } from '$lib/desktop/i18n';
	import { SCREENS } from '$lib/desktop/nav';
	import Icon from '$lib/desktop/Icon.svelte';
	import ScreenHead from '$lib/desktop/ScreenHead.svelte';

	const lang = $derived(currentLang());
	const t = $derived(T[lang]);
</script>

<svelte:head>
	<title>{t.shell.title(t.nav.overview)}</title>
</svelte:head>

<ScreenHead overline={t.overview.overline} title={t.overview.title} lead={t.overview.lead}>
	{#snippet actions()}
		<a class="btn btn--primary" href={href(lang, '/app/wizard')}>
			{t.overview.startWizard}<Icon name="arrowRight" size={16} />
		</a>
		<a class="btn btn--secondary" href={href(lang, '/app/chat')}>{t.overview.openChat}</a>
	{/snippet}
</ScreenHead>

<section aria-labelledby="screens-h">
	<h2 id="screens-h" class="overline">{t.overview.screensTitle}</h2>
	<ul class="screens">
		{#each SCREENS as s, i (s.key)}
			<li>
				<a class="card card--interactive tile" href={href(lang, s.path)}>
					<span class="top">
						<span class="ic"><Icon name={s.icon} size={20} /></span>
						<span class="idx num">{String(i + 1).padStart(2, '0')}</span>
					</span>
					<span class="h3 name">{t.nav[s.key]}</span>
					<span class="desc">{t.overview.desc[s.key]}</span>
				</a>
			</li>
		{/each}
	</ul>
</section>

<section class="notice notice--prototype rules" aria-labelledby="rules-h">
	<span class="notice__icon" aria-hidden="true">i</span>
	<div>
		<h2 id="rules-h" class="h3">{t.overview.rulesTitle}</h2>
		<ul>
			{#each t.overview.rules as r (r)}<li>{r}</li>{/each}
		</ul>
	</div>
</section>

<style>
	.screens {
		list-style: none;
		margin: var(--sp-4) 0 var(--sp-8);
		padding: 0;
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(16rem, 1fr));
		gap: var(--sp-4);
	}
	.tile {
		display: grid;
		gap: var(--sp-2);
		align-content: start;
		height: 100%;
		color: var(--text);
		text-decoration: none;
		padding: var(--sp-5);
	}
	.tile:hover .name {
		color: var(--accent-ink);
	}
	.top {
		display: flex;
		align-items: center;
		justify-content: space-between;
		margin-bottom: var(--sp-2);
	}
	.ic {
		display: grid;
		place-items: center;
		width: 2.5rem;
		height: 2.5rem;
		border-radius: var(--r-sm);
		background: var(--bg-3);
		color: var(--accent-ink);
	}
	.idx {
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.name {
		color: var(--text-hi);
		transition: color var(--dur-1) var(--ease-out);
	}
	.desc {
		font-size: var(--fs-sm);
	}
	.rules ul {
		margin: var(--sp-2) 0 0;
		padding-left: 1.1rem;
		display: grid;
		gap: var(--sp-1);
	}
</style>
