<script lang="ts">
	import { currentLang } from '$lib/i18n';
	import { T } from './i18n';
	import Icon from './Icon.svelte';
	import SendPreview from './SendPreview.svelte';
	import Src from './Src.svelte';

	/** "Co wiemy o Twoim komputerze" (report 06 §2.2.1) with the send preview. */
	let { level = 2 }: { level?: 2 | 3 } = $props();
	const t = $derived(T[currentLang()]);
	const id = $props.id();
</script>

<section class="card facts" aria-labelledby="{id}-h">
	<svelte:element this={`h${level}`} id="{id}-h" class="h3">{t.scan.title}</svelte:element>
	<div class="cols">
		<div>
			<p class="overline">{t.scan.read}</p>
			<ul class="list">
				{#each t.scan.readItems as item (item)}
					<li><span class="ic ok"><Icon name="check" size={16} /></span>{item}</li>
				{/each}
			</ul>
		</div>
		<div>
			<p class="overline">{t.scan.never}</p>
			<ul class="list">
				{#each t.scan.neverItems as item (item)}
					<li><span class="ic no"><Icon name="close" size={16} /></span>{item}</li>
				{/each}
			</ul>
		</div>
	</div>
	<SendPreview />
	<Src src={t.scan.sourceNote} />
</section>

<style>
	.facts {
		display: grid;
		gap: var(--sp-5);
	}
	.cols {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(16rem, 1fr));
		gap: var(--sp-6);
	}
	.list {
		list-style: none;
		margin: var(--sp-3) 0 0;
		padding: 0;
		display: grid;
		gap: var(--sp-2);
		font-size: var(--fs-sm);
	}
	.list li {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: var(--sp-2);
		align-items: start;
	}
	.ic {
		margin-top: 0.15rem;
	}
	.ok {
		color: var(--ok-ink);
	}
	.no {
		color: var(--danger-ink);
	}
</style>
