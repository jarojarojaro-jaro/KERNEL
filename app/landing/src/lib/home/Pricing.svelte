<script lang="ts">
	/**
	 * Cennik as one statement and one instrument: a Free/Turbo toggle drives a giant price (the
	 * paid price literally widens: wdth 75 → 125), a rubber-stamp marks it as a hypothesis, and the
	 * waitlist runs underneath as a single strip.
	 */
	import { type Lang } from '$lib/i18n';
	import { copy } from '$lib/site/copy';
	import Waitlist from '$lib/site/Waitlist.svelte';
	import Duo from './Duo.svelte';
	import Segmented from './Segmented.svelte';

	let { lang }: { lang: Lang } = $props();
	const c = $derived(copy[lang].pricing);
	let plan = $state('turbo');
	const p = $derived(c.plans.find((x) => x.id === plan) ?? c.plans[0]);
	const options = $derived(c.plans.map((x) => ({ id: x.id, label: x.name })));
</script>

<section id="pricing" class="pricing" aria-labelledby="pricing-title">
	<div class="inner">
		<header class="head">
			<Duo text={c.title} id="pricing-title" mode="plain" />
			<p class="lede">{c.lead}</p>
		</header>
		<div class="instrument">
			<div class="toggle"><Segmented options={options} bind:value={plan} label={c.plan} /></div>
			<p class="price" class:paid={plan !== 'free'} aria-live="polite">
				<span class="amount">{p.price}</span>
				<span class="per">{p.per}</span>
			</p>
			<ul class="items">
				{#each p.items as it (it)}<li>{it}</li>{/each}
			</ul>
			<div class="stamp" role="note">
				<span class="st">{c.badge}</span>
				<span class="sb">{c.stamp}</span>
			</div>
		</div>
		<Waitlist />
	</div>
</section>

<style>
	.pricing {
		padding-block: clamp(3.5rem, 2.5rem + 3vw, 6rem);
		border-top: 1px solid var(--line);
		background:
			radial-gradient(50% 50% at 90% 10%, rgb(255 255 255 / 0.025), transparent 70%),
			var(--bg-1);
	}
	.inner {
		width: min(100% - 2 * var(--gutter), 90rem);
		margin-inline: auto;
		display: grid;
		gap: clamp(2.5rem, 5vw, 4.5rem);
	}
	.head {
		display: grid;
		gap: var(--sp-5);
	}
	.instrument {
		position: relative;
		display: grid;
		grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
		grid-template-areas:
			'toggle stamp'
			'price  price'
			'items  items';
		align-items: center;
		gap: var(--sp-6);
		padding-block: clamp(2rem, 4vw, 3rem);
		border-block: 1px solid var(--line);
	}
	.toggle {
		grid-area: toggle;
		width: min(100%, 22rem);
	}
	.price {
		grid-area: price;
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: var(--sp-2) var(--sp-6);
	}
	.amount {
		font-family: var(--font-display);
		font-size: clamp(4.5rem, 2rem + 11vw, 13rem);
		font-weight: 860;
		font-stretch: 75%;
		letter-spacing: -0.05em;
		line-height: 0.85;
		color: var(--text-hi);
		transition: font-stretch 0.8s var(--ease-out);
	}
	.paid .amount {
		font-stretch: 125%;
	}
	.per {
		font-family: var(--font-mono);
		font-size: var(--fs-sm);
		color: var(--text);
	}
	.items {
		grid-area: items;
		margin: 0;
		padding: 0;
		list-style: none;
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-2) var(--sp-6);
		font-size: var(--fs-md);
		color: var(--text);
	}
	.items li::before {
		content: '+ ';
		font-family: var(--font-mono);
		color: var(--text-mute);
	}
	/* a rubber stamp: the price is a hypothesis we are testing, not an offer */
	.stamp {
		grid-area: stamp;
		justify-self: end;
		display: grid;
		gap: 0.35rem;
		max-width: 19rem;
		padding: 0.8rem 1rem;
		border: 2px solid var(--text-hi);
		outline: 1px solid var(--text-hi);
		outline-offset: 3px;
		border-radius: 4px;
		transform: rotate(-4deg);
		color: var(--text-hi);
	}
	.st {
		font-family: var(--font-mono);
		font-weight: 700;
		font-size: var(--fs-sm);
		text-transform: uppercase;
		letter-spacing: 0.18em;
	}
	.sb {
		font-size: var(--fs-xs);
		line-height: 1.45;
		color: var(--text);
	}
	@media (max-width: 720px) {
		.instrument {
			grid-template-columns: minmax(0, 1fr);
			grid-template-areas: 'toggle' 'price' 'items' 'stamp';
		}
		.stamp {
			justify-self: start;
			transform: rotate(-2deg);
		}
		.items {
			display: grid;
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.amount {
			transition: none;
		}
	}
</style>
