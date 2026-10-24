<script lang="ts">
	import ProgressRow from '../components/ProgressRow.svelte';
	import ScreenHead from '../components/ScreenHead.svelte';
	import { api } from '../lib/api';
	import { duration, gb, num, STEPS, type Step } from '../lib/i18n';
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
	/** The step running now (engine, model or checksum), shown as one big number. */
	const cur = $derived(live && store.state?.progress?.phase === 'download' ? store.state.progress : null);
	const curPct = $derived(cur && cur.total > 0 ? Math.min(100, (cur.done / cur.total) * 100) : null);
	const curName = $derived(cur ? (cur.label === 'model' ? t.model : cur.label === 'verify' ? t.verify : cur.label === 'extract' ? t.extract : cur.label.startsWith('reuse') ? t.reused : t.engine) : '');

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

	{#if curPct !== null && cur}
		<div class="big-prog">
			<p class="bp-num num"><span class="v">{num(curPct, lang, curPct < 10 ? 1 : 0)}</span><span class="u">%</span></p>
			<p class="bp-meta">
				<span class="bp-name">{curName}</span>
				{#if cur.rate}<span class="num">{num(cur.rate / 1e6, lang, 1)} MB/s</span>{/if}
				{#if cur.etaS}<span class="num">{t.eta} {duration(cur.etaS)}</span>{/if}
			</p>
		</div>
	{/if}
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
	.big-prog {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-end;
		gap: var(--sp-2) var(--sp-8);
	}
	.bp-num {
		margin: 0;
		line-height: 0.9;
	}
	.bp-num .v {
		font-size: clamp(3.4rem, 2rem + 5vw, 6.5rem);
		font-weight: 560;
		letter-spacing: -0.05em;
		color: var(--text-hi);
	}
	.bp-num .u {
		font-size: var(--fs-xl);
		color: var(--text-mute);
	}
	.bp-meta {
		display: grid;
		gap: 0.2rem;
		margin: 0 0 0.6rem;
		font-size: var(--fs-sm);
		color: var(--text-mute);
	}
	.bp-name {
		color: var(--text-hi);
		font-weight: 650;
		font-size: var(--fs-md);
	}
	.rows {
		display: grid;
	}
</style>
