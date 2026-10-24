<script lang="ts">
	import BenchSteps from '../components/BenchSteps.svelte';
	import ScreenHead from '../components/ScreenHead.svelte';
	import { api } from '../lib/api';
	import { engineName } from '../lib/bench';
	import { int, kTokens, num } from '../lib/i18n';
	import { store } from '../lib/store.svelte';

	const t = $derived(store.t.base);
	const lang = $derived(store.lang);
	const b = $derived(store.state?.baseline ?? null);
	const live = $derived(store.state?.phase === 'baseline');

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

<section class="screen" aria-labelledby="base-title">
	<ScreenHead id="base-title" overline={t.overline} title={t.title} accent={t.titleAccent} lead={t.lead} />

	{#if !b}
		<div class="panel panel--heat">
			<p class="eyebrow run">{t.running}</p>
			<BenchSteps phase="baseline" />
		</div>
		{#if live}
			<div class="actions">
				<button class="btn btn--secondary" type="button" onclick={cancel} disabled={cancelling}>{cancelling ? store.t.cancelling : store.t.cancel}</button>
			</div>
		{/if}
	{:else}
		<div class="panel panel--heat res">
			<div class="eng">
				<span class="badge badge--plain steel">{t.engine}</span>
				<span class="eng-name">{engineName(b, store.t)}</span>
				<span class="badge badge--measured">{t.measured}</span>
			</div>
			<dl class="stats">
				<div class="stat">
					<dt class="stat__label">{t.prefill}</dt>
					<dd class="stat__value">{num(b.prefill.tps, lang, 1)}<span class="stat__unit">t/s</span></dd>
					<dd class="foot num">{int(b.prefill.tokens, lang)} tok</dd>
				</div>
				<div class="stat">
					<dt class="stat__label">{t.decode}</dt>
					<dd class="stat__value">{num(b.decode.tps, lang, 1)}<span class="stat__unit">t/s</span></dd>
					<dd class="foot num">{int(b.decode.tokens, lang)} tok</dd>
				</div>
				<div class="stat">
					<dt class="stat__label">{t.ttft}</dt>
					<dd class="stat__value">{num(b.prefill.ttftS, lang, 2)}<span class="stat__unit">s</span></dd>
				</div>
				<div class="stat">
					<dt class="stat__label">{t.ctx}</dt>
					<dd class="stat__value">{int(b.config.ctx, lang)}<span class="stat__unit">tok</span></dd>
					<dd class="foot" class:ok={b.ctxOk} class:bad={!b.ctxOk}>{b.ctxOk ? `✓ ${t.ctxOk}` : `✗ ${t.ctxBad}`}</dd>
				</div>
			</dl>
			{#if b.deep}
				<div class="deep">
					<p class="eyebrow">{t.deep(kTokens(b.deep.ctxTokens))}</p>
					<p class="deep-nums num">
						<span><span class="dv">{num(b.deep.prefillTps, lang, 1)}</span> t/s {t.deepPrefill}</span>
						<span><span class="dv">{num(b.deep.decodeTps, lang, 1)}</span> t/s {t.deepDecode}</span>
					</p>
				</div>
			{/if}
			<p class="cfg num">
				-c {b.config.ctx} · KV {b.config.kvType} · -ub {b.config.ub} · -b {b.config.b}{b.config.flashAttn ? ' · -fa' : ''}{b.config.threads ? ` · -t ${b.config.threads}` : ''}
			</p>
		</div>
	{/if}
</section>

<style>
	.run {
		margin-bottom: var(--sp-3);
	}
	.res {
		display: grid;
		gap: var(--sp-8);
	}
	.eng {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-3);
	}
	.eng-name {
		color: var(--text-hi);
		font-weight: 680;
		font-size: var(--fs-md);
	}
	.steel {
		color: var(--before);
	}
	.stats {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 12rem), 1fr));
		gap: var(--sp-6);
		margin: 0;
	}
	.stats dd {
		margin: 0;
	}
	.stats .stat__value {
		font-size: clamp(2rem, 1.4rem + 2vw, 2.9rem);
		font-weight: 500;
		color: var(--text-hi);
		letter-spacing: -0.04em;
	}
	.stats .stat__label {
		order: -1;
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.12em;
		text-transform: uppercase;
	}
	.foot {
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.foot.ok {
		color: var(--ok-ink);
	}
	.foot.bad {
		color: var(--danger-ink);
	}
	.deep {
		display: grid;
		gap: var(--sp-2);
		padding-top: var(--sp-5);
		border-top: 1px solid var(--line);
	}
	.deep-nums {
		display: flex;
		flex-wrap: wrap;
		gap: var(--sp-3) var(--sp-8);
		margin: 0;
		color: var(--text-mute);
		font-size: var(--fs-sm);
	}
	.dv {
		font-size: var(--fs-xl);
		color: var(--text-hi);
	}
	.cfg {
		margin: 0;
		font-size: var(--fs-xs);
		color: var(--text-mute);
		overflow-wrap: anywhere;
	}
</style>
