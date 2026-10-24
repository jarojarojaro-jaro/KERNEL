<script lang="ts">
	import ProgressRow from '../components/ProgressRow.svelte';
	import ScreenHead from '../components/ScreenHead.svelte';
	import { api } from '../lib/api';
	import { gb, STEPS, type Step } from '../lib/i18n';
	import { store } from '../lib/store.svelte';

	const t = $derived(store.t.dl);
	const lang = $derived(store.lang);
	const chosen = $derived(store.state?.chosen ?? null);
	const live = $derived(store.state?.phase === 'download');
	/** Opened from the stepper after the download finished: progress events from before this page load are gone. */
	const past = $derived(STEPS.indexOf((store.state?.phase ?? 'license') as Step) > STEPS.indexOf('download'));

	const engine = $derived(store.prog('download', 'engine'));
	const extract = $derived(store.prog('download', 'extract'));
	const model = $derived(store.prog('download', 'model'));
	const verify = $derived(store.prog('download', 'verify'));
	const engineReused = $derived(store.prog('download', 'reuse:engine') !== null);
	const modelReused = $derived(store.prog('download', 'reuse:model') !== null);

	let cancelling = $state(false);
	async function cancel() {
		cancelling = true;
		try {
			await api.cancel();
		} finally {
			cancelling = false;
		}
	}
</script>

<section class="screen" aria-labelledby="dl-title">
	<ScreenHead id="dl-title" overline={t.overline} title={t.title} accent={t.titleAccent} lead={t.lead} />

	<div class="panel panel--heat rows">
		<ProgressRow title={t.engine} detail="llama.cpp" p={engine} reused={engineReused} done={past} />
		{#if extract}<ProgressRow title={t.extract} p={extract} unit="steps" />{/if}
		<ProgressRow
			title={t.model}
			detail={chosen ? `${chosen.name} · ${chosen.quant} · ${gb(chosen.file.sizeBytes, lang)} GB` : undefined}
			p={model}
			reused={modelReused}
			done={past}
			totalHint={chosen?.file.sizeBytes}
		/>
		{#if verify || chosen?.file.sha256}
			<ProgressRow title={t.verify} detail={chosen?.file.sha256 ? `sha256 ${chosen.file.sha256.slice(0, 16)}…` : undefined} p={verify} totalHint={chosen?.file.sizeBytes} done={past} />
		{/if}
	</div>

	{#if live}
		<div class="actions">
			<button class="btn btn--secondary" type="button" onclick={cancel} disabled={cancelling}>{cancelling ? store.t.cancelling : store.t.cancel}</button>
		</div>
	{/if}
</section>

<style>
	.rows {
		display: grid;
	}
</style>
