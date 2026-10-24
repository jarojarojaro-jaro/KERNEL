<script lang="ts">
	import type { Candidate } from '../../shared/types';
	import Headline from '../components/Headline.svelte';
	import ScreenHead from '../components/ScreenHead.svelte';
	import { api } from '../lib/api';
	import { engineName } from '../lib/bench';
	import { num, pct } from '../lib/i18n';
	import { candidateText } from '../lib/reasons';
	import { store } from '../lib/store.svelte';

	const t = $derived(store.t.opt);
	const lang = $derived(store.lang);
	const s = $derived(store.state);
	const base = $derived(s?.baseline ?? null);
	const now = $derived(s?.best ?? s?.baseline ?? null);
	const cands = $derived<Candidate[]>(s?.candidates ?? []);
	const live = $derived(s?.phase === 'optimize');
	const prog = $derived(s?.progress && s.progress.phase === 'optimize' ? s.progress : null);
	const MARK: Record<Candidate['status'], string> = { pending: '·', running: '', kept: '✓', rejected: '×', failed: '!' };

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

<section class="screen" aria-labelledby="opt-title">
	<ScreenHead id="opt-title" overline={t.overline} title={t.title} accent={t.titleAccent} lead={t.lead} />

	{#if base && now}
		<div class="hl">
			<div class="hl-head">
				<h2 class="panel-title">{t.headline}</h2>
				<p class="eng num">
					{#if engineName(base, store.t) === engineName(now, store.t)}
						<span class="cur">{engineName(now, store.t)}</span>
					{:else}
						<span class="before">{engineName(base, store.t)}</span> → <span class="cur">{engineName(now, store.t)}</span>
					{/if}
				</p>
			</div>
			<Headline {base} {now} />
		</div>
	{/if}

	<div class="panel">
		<h2 class="panel-title">{t.candidates}</h2>
		{#if cands.length === 0}
			<p class="empty">{t.empty}</p>
		{:else}
			<ol class="cands">
				{#each cands as c (c.id)}
					<li class="cand {c.status}">
						<span class="m" aria-hidden="true">{#if c.status === 'running'}<span class="ring"></span>{:else}{MARK[c.status]}{/if}</span>
						<div class="body">
							<p class="top">
								<span class="lbl">{c.label[lang]}</span>
								<span class="st">{c.status === 'pending' && c.result ? t.measured : t.status[c.status]}</span>
							</p>
							<p class="desc">{c.desc[lang]}</p>
							{#if c.status === 'running' && prog}
								<p class="now num">{store.t.base.phases[prog.label] ?? prog.label}{prog.total > 1 ? ` · ${prog.done}/${prog.total}` : ''}</p>
							{/if}
							{#if c.result || c.decodePct !== undefined || c.prefillPct !== undefined || c.sameOutput !== undefined}
								<ul class="chips res">
									{#if c.result}
										<li class="chip chip--mono">{num(c.result.decode.tps, lang, 1)} t/s</li>
									{/if}
									{#if c.decodePct !== undefined}
										<li class="chip chip--mono" class:up={c.decodePct >= 0.5} class:down={c.decodePct <= -0.5}>{t.decodeShort} {pct(c.decodePct, lang)}</li>
									{/if}
									{#if c.prefillPct !== undefined}
										<li class="chip chip--mono" class:up={c.prefillPct >= 0.5} class:down={c.prefillPct <= -0.5}>{t.prefillShort} {pct(c.prefillPct, lang)}</li>
									{/if}
									{#if c.sameOutput !== undefined}
										<li class="chip" title={c.sameOutput ? undefined : t.diffHint}>{c.sameOutput ? `✓ ${t.same}` : `≠ ${t.diff}`}</li>
									{/if}
								</ul>
							{/if}
							{#if c.sameOutput === false}<p class="hint">{t.diffHint}</p>{/if}
							{#if c.reason}<p class="reason">{candidateText(c.reason, lang, (id) => cands.find((x) => x.id === id)?.label[lang] ?? id)}</p>{/if}
						</div>
					</li>
				{/each}
			</ol>
		{/if}
	</div>

	{#if live}
		<div class="actions">
			<button class="btn btn--secondary" type="button" onclick={cancel} disabled={cancelling}>{cancelling ? store.t.cancelling : store.t.cancel}</button>
		</div>
	{/if}
</section>

<style>
	.hl {
		display: grid;
		gap: var(--sp-4);
	}
	.hl-head {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		justify-content: space-between;
		gap: var(--sp-2) var(--sp-6);
	}
	.eng {
		margin: 0;
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.eng .before {
		color: var(--before);
	}
	.eng .cur {
		color: var(--text-hi);
	}
	.panel {
		display: grid;
		gap: var(--sp-4);
	}
	.empty {
		color: var(--text-mute);
	}
	.cands {
		display: grid;
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.cand {
		display: flex;
		gap: var(--sp-4);
		padding: var(--sp-4) 0;
		border-top: 1px solid var(--line);
	}
	.cand:first-child {
		border-top: 0;
		padding-top: 0;
	}
	.m {
		display: grid;
		place-items: center;
		flex: none;
		width: 1.9rem;
		height: 1.9rem;
		border-radius: 50%;
		border: 1px solid var(--line-strong);
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.m .ring {
		width: 0.85rem;
		height: 0.85rem;
		color: var(--text-hi);
	}
	.kept .m {
		background: var(--text-hi);
		border-color: var(--text-hi);
		color: var(--text-inv);
		font-weight: 700;
	}
	.rejected .m {
		color: var(--text-mute);
	}
	.failed .m {
		border-color: var(--danger-ink);
		color: var(--danger-ink);
	}
	.running .m {
		border-color: var(--text-hi);
	}
	.body {
		display: grid;
		gap: 0.35rem;
		min-width: 0;
		flex: 1;
	}
	.top {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: var(--sp-2) var(--sp-4);
		margin: 0;
	}
	.lbl {
		color: var(--text-hi);
		font-weight: 650;
	}
	.pending .lbl {
		color: var(--text);
	}
	.st {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: 0.1em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.kept .st {
		color: var(--ok-ink);
	}
	.failed .st {
		color: var(--danger-ink);
	}
	.running .st {
		color: var(--text-hi);
	}
	.desc {
		font-size: var(--fs-sm);
		color: var(--text-mute);
	}
	.now {
		font-size: var(--fs-xs);
		color: var(--text);
	}
	.res .chip {
		min-height: 1.6rem;
	}
	.chip.up {
		color: var(--accent-ink);
		border-color: color-mix(in srgb, var(--heat-3) 55%, var(--line-strong));
	}
	.chip.down {
		color: var(--danger-ink);
	}
	.reason {
		font-size: var(--fs-sm);
		color: var(--text);
	}
</style>
