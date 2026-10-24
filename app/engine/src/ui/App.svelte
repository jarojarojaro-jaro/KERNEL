<script lang="ts">
	import { onMount, tick, untrack } from 'svelte';
	import type { Phase } from '../shared/types';
	import Header from './components/Header.svelte';
	import LogDrawer from './components/LogDrawer.svelte';
	import Stepper from './components/Stepper.svelte';
	import { api } from './lib/api';
	import { STEPS, type Step } from './lib/i18n';
	import { store } from './lib/store.svelte';
	import Baseline from './screens/Baseline.svelte';
	import Download from './screens/Download.svelte';
	import ErrorScreen from './screens/ErrorScreen.svelte';
	import Hardware from './screens/Hardware.svelte';
	import License from './screens/License.svelte';
	import Optimize from './screens/Optimize.svelte';
	import Ready from './screens/Ready.svelte';
	import Recommend from './screens/Recommend.svelte';

	const t = $derived(store.t);
	const s = $derived(store.state);
	const phase = $derived<Phase>(s?.phase ?? 'license');
	const failed = $derived(phase === 'error');
	/** The backend's step; for an error, the step that failed. */
	const current = $derived<Step>(failed ? (s?.error && s.error.phase !== 'error' ? s.error.phase : 'license') : (phase as Step));
	const curIdx = $derived(STEPS.indexOf(current));

	/** A step the user opened from the stepper; null follows the backend. */
	let view = $state<Step | null>(null);
	/** Keeps the welcome screen up for a moment after a valid key, so the plan badge is seen before the scan. */
	let hold = $state<Step | null>(null);
	const shown = $derived<Step | 'error'>(view ?? hold ?? (failed ? 'error' : current));

	// A new backend phase takes the screen back from whatever the user was looking at.
	let lastPhase: Phase | null = null;
	$effect(() => {
		const p = phase;
		untrack(() => {
			if (p !== lastPhase) {
				if (lastPhase === 'license' && view === null) {
					hold = 'license';
					setTimeout(() => (hold = null), 1400);
				}
				lastPhase = p;
				view = null;
			}
		});
	});

	function canOpen(step: Step): boolean {
		const i = STEPS.indexOf(step);
		switch (step) {
			case 'license':
				return true;
			case 'scan':
				return Boolean(s?.hw) || curIdx >= i;
			case 'recommend':
				return Boolean(s?.recommendation) || curIdx >= i;
			case 'baseline':
				return Boolean(s?.baseline) || curIdx >= i;
			case 'optimize':
				return (s?.candidates.length ?? 0) > 0 || curIdx >= i;
			case 'ready':
				return phase === 'ready';
			default:
				return curIdx >= i;
		}
	}

	function open(step: Step) {
		view = step === current && !failed ? null : step;
	}

	async function scanFirst() {
		view = 'scan';
		if (!s?.hw) await api.scan().catch(() => store.refresh());
	}

	async function showRecommendation() {
		view = 'recommend';
		if (!s?.recommendation) await api.recommend().catch(() => store.refresh());
	}

	// A recommend phase without a recommendation (e.g. after a restart): ask once.
	let asked = false;
	$effect(() => {
		if (phase === 'recommend' && s && !s.recommendation && !asked) {
			asked = true;
			void api.recommend().catch(() => (asked = false));
		}
	});

	// Screen change: back to the top and focus on the new heading (not on the first render).
	let first = true;
	$effect(() => {
		void shown;
		if (first) {
			first = false;
			return;
		}
		void tick().then(() => {
			scrollTo({ top: 0 });
			document.querySelector<HTMLElement>('[data-screen-title]')?.focus({ preventScroll: true });
		});
	});

	onMount(() => {
		void store.refresh();
		store.connect();
	});
</script>

<a class="skip-link" href="#main">{t.skip}</a>
<Header />

{#if s}
	<div class="wrap">
		<Stepper {current} {failed} shown={shown === 'error' ? null : shown} {canOpen} onselect={open} />
	</div>
{/if}

<main id="main" class="wrap">
	{#if store.online === false}
		{#if s}
			<p class="notice notice--warn conn" role="status"><span class="notice__icon" aria-hidden="true">!</span><span>{t.offline}</span></p>
		{:else}
			<section class="screen" aria-labelledby="off-title">
				<header class="screen-head">
					<h1 id="off-title" class="title" tabindex="-1">{t.offlineTitle}</h1>
					<p class="lede">{t.offlineBody}</p>
				</header>
				<div class="actions"><button class="btn btn--primary" type="button" onclick={() => store.connect()}>{t.retryNow}</button></div>
			</section>
		{/if}
	{/if}

	{#if !s}
		{#if store.online !== false}<p class="busy loading" role="status"><span class="ring" aria-hidden="true"></span>{t.connecting}</p>{/if}
	{:else}
		{#if view && (STEPS.indexOf(view) < curIdx || failed)}
			<div class="peek">
				<p>{t.viewingPast}</p>
				<button class="btn btn--secondary btn--sm" type="button" onclick={() => (view = null)}>{t.backToCurrent} <span class="arrow" aria-hidden="true">→</span></button>
			</div>
		{/if}
		{#if shown === 'error'}
			<ErrorScreen onview={open} />
		{:else if shown === 'license'}
			<License onscanfirst={scanFirst} onnext={() => ((view = null), (hold = null))} />
		{:else if shown === 'scan'}
			<Hardware onnext={showRecommendation} />
		{:else if shown === 'recommend'}
			<Recommend onlicense={() => open('license')} onhw={() => open('scan')} />
		{:else if shown === 'download'}
			<Download />
		{:else if shown === 'baseline'}
			<Baseline />
		{:else if shown === 'optimize'}
			<Optimize />
		{:else if shown === 'ready'}
			<Ready />
		{/if}
	{/if}
</main>

<LogDrawer />

<style>
	main {
		padding-bottom: 4.5rem;
		min-height: 60vh;
	}
	.loading {
		padding-block: var(--sp-16);
	}
	.conn {
		margin-top: var(--sp-6);
	}
	.peek {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: var(--sp-3);
		margin-top: var(--sp-6);
		padding: var(--sp-3) var(--sp-3) var(--sp-3) var(--sp-5);
		border: 1px dashed var(--line-strong);
		border-radius: var(--r-pill);
		color: var(--text);
		font-size: var(--fs-sm);
	}
	@media (max-width: 600px) {
		.peek {
			border-radius: var(--r-lg);
		}
	}
</style>
