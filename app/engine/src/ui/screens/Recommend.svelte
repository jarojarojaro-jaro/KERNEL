<script lang="ts">
	import type { Backend, Option } from '../../shared/types';
	import MemBar from '../components/MemBar.svelte';
	import ScreenHead from '../components/ScreenHead.svelte';
	import { api, ApiError } from '../lib/api';
	import { gb, int, kTokens, num } from '../lib/i18n';
	import { rejectedText, whyText } from '../lib/reasons';
	import { store } from '../lib/store.svelte';

	let { onlicense, onhw }: { onlicense: () => void; onhw: () => void } = $props();

	const t = $derived(store.t.rec);
	const lang = $derived(store.lang);
	const rec = $derived(store.state?.recommendation ?? null);
	const hw = $derived(store.state?.hw ?? null);
	const licensed = $derived(store.state?.license?.valid === true);
	const phase = $derived(store.state?.phase ?? 'license');
	/** Picking a model only makes sense before the pipeline runs (or after it failed). */
	const canStart = $derived(phase === 'license' || phase === 'scan' || phase === 'recommend' || phase === 'error');
	const options = $derived(rec ? (rec.pick ? [rec.pick, ...rec.alternatives] : rec.alternatives) : []);

	let picked = $state<string | null>(null);
	const selected = $derived<Option | null>(options.find((o) => o.id === picked) ?? rec?.pick ?? null);
	const BACKEND: Record<Backend, string> = { cuda: 'CUDA', rocm: 'ROCm', vulkan: 'Vulkan', metal: 'Metal', cpu: 'CPU' };

	let busy = $state(false);
	let error = $state('');

	async function start() {
		if (!selected) return;
		busy = true;
		error = '';
		try {
			await api.start(selected.id);
		} catch (e) {
			error = e instanceof ApiError && e.status === 403 ? t.needLicense : e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
		}
	}

	const mainGpu = $derived(hw ? [...hw.gpus].sort((a, b) => b.vramGiB - a.vramGiB)[0] : undefined);
</script>

<section class="screen" aria-labelledby="rec-title">
	<ScreenHead id="rec-title" overline={t.overline} title={t.title} accent={t.titleAccent} />

	{#if hw}
		<p class="hwline">
			<button type="button" class="hwbtn" onclick={onhw}>
				<span>{mainGpu ? `${mainGpu.name} · ${num(mainGpu.vramGiB, lang, 0)} GB` : hw.cpu.name} <span class="mute">· {num(hw.ramGiB, lang, 0)} GB RAM</span> <span aria-hidden="true">→</span></span>
			</button>
		</p>
	{/if}

	{#if !rec}
		<div class="panel busy" role="status"><span class="ring" aria-hidden="true"></span>{t.thinking}</div>
	{:else}
		{#if !rec.pick}
			<p class="notice notice--danger" role="alert">
				<span class="notice__icon" aria-hidden="true">!</span>
				<span>{t.none}<strong class="num">{int(rec.minCtx, lang)}</strong>{t.noneTail}</span>
			</p>
		{/if}

		{#if selected}
			{@const o = selected}
			<article class="panel panel--heat hero" aria-labelledby="pick-name">
				<div class="head">
					<p class="badge badge--plain tag">{o.id === rec.pick?.id ? t.pick : t.chosen}</p>
					<h2 id="pick-name" class="model">{o.name}</h2>
					<p class="meta">
						<span>{o.family}</span><span aria-hidden="true">·</span><span>{o.params}</span><span aria-hidden="true">·</span><span class="chip chip--mono">{o.quant}</span>
					</p>
				</div>

				<div class="ctx">
					<p class="ctx-fig">
						<span class="ctx-num num">{int(o.ctx, lang)}</span>
						<span class="ctx-unit">{t.ctx}</span>
					</p>
					<div class="ruler" aria-hidden="true">
						<i class="fill" style="width:{Math.min(100, (o.ctx / Math.max(o.ctxMax, o.ctx)) * 100)}%"></i>
						<i class="min" style="left:{Math.min(100, (rec.minCtx / Math.max(o.ctxMax, o.ctx)) * 100)}%"><span class="num">{kTokens(rec.minCtx)}</span></i>
					</div>
					<p class="ctx-note num">
						<span class="ok">✓ {t.ctxMin(int(rec.minCtx, lang))}</span>
						<span>{t.ctxMax(int(o.ctxMax, lang))}</span>
					</p>
				</div>

				{#if o.features.length}
					<ul class="chips feats" aria-label={t.featuresLabel}>
						{#each o.features as f (f)}<li class="chip">{t.features[f] ?? f}</li>{/each}
					</ul>
				{/if}

				<MemBar mem={o.mem} title={o.gpuIndex === null ? t.memRam : t.mem} />

				<div class="cols">
					{#if o.why.length}
						<div>
							<h3 class="eyebrow">{t.why}</h3>
							<ul class="why">
								{#each o.why as w, i (i)}<li>{whyText(w, lang)}</li>{/each}
							</ul>
						</div>
					{/if}
					<div>
						<h3 class="eyebrow">{t.spec}</h3>
						<dl class="facts spec">
							<div><dt>{t.file}</dt><dd class="mono">{o.file.path}<span class="sub">{o.file.repo}</span></dd></div>
							<div><dt>{t.size}</dt><dd class="mono">{gb(o.file.sizeBytes, lang)} GB</dd></div>
							<div><dt>{t.kvType}</dt><dd class="mono">{o.kvType}</dd></div>
							<div><dt>{t.ub}</dt><dd class="mono">{o.ub}</dd></div>
							<div><dt>{t.backend}</dt><dd class="mono">{BACKEND[o.backend]}</dd></div>
						</dl>
					</div>
				</div>
			</article>
		{/if}

		{#if options.length > 1}
			<fieldset class="alts">
				<legend class="eyebrow">{t.alternatives}</legend>
				<div class="alt-grid">
					{#each options as o (o.id)}
						<label class="alt" class:on={selected?.id === o.id}>
							<input type="radio" name="option" value={o.id} checked={selected?.id === o.id} onchange={() => (picked = o.id)} disabled={!canStart} />
							<span class="alt-top">
								<span class="alt-name">{o.name}</span>
								{#if o.id === rec.pick?.id}<span class="badge badge--plain mini">{t.pick}</span>{/if}
							</span>
							<span class="alt-q chip chip--mono">{o.quant}</span>
							<span class="alt-row num"><span class="big">{kTokens(o.ctx)}</span> <span class="mute">ctx</span></span>
							<span class="alt-row num mute">{num(o.mem.totalGiB, lang, 1)} / {num(o.mem.budgetGiB, lang, 1)} GB · KV {o.kvType}</span>
							{#if o.features.length}<span class="alt-row small mute">{o.features.map((f) => t.features[f]?.split(':')[0] ?? f).join(' · ')}</span>{/if}
						</label>
					{/each}
				</div>
			</fieldset>
		{/if}

		{#if rec.rejected.length}
			<details class="disclosure rejected" open={!rec.pick}>
				<summary>{t.rejected(rec.rejected.length)}</summary>
				<div class="disclosure__body">
					<p class="hint">{t.rejectedHint}</p>
					<ul class="rej">
						{#each rec.rejected as r, i (i)}
							<li><span class="mono">{r.modelId}</span> <span class="chip chip--mono">{r.quant}</span> <span class="why-r">{rejectedText(r.reason, lang)}</span></li>
						{/each}
					</ul>
				</div>
			</details>
		{/if}

		{#if selected && canStart}
			<div class="dock">
				<div class="dock-in">
					<p class="dock-sel">
						<span class="dock-name">{selected.name} <span class="mute">{selected.quant}</span></span>
						<span class="num mute">{int(selected.ctx, lang)} tok · {gb(selected.file.sizeBytes, lang)} GB</span>
					</p>
					{#if licensed}
						<button class="go" type="button" onclick={start} disabled={busy}>
							{#if busy}<span class="ring" aria-hidden="true"></span>{t.starting}{:else}{t.start} <span class="arrow" aria-hidden="true">→</span>{/if}
						</button>
					{:else}
						<p class="need">{t.needLicense}</p>
						<button class="btn btn--primary" type="button" onclick={onlicense}>{t.goLicense} <span class="arrow" aria-hidden="true">→</span></button>
					{/if}
				</div>
				{#if error}<p class="error-text" role="alert">{error}</p>{/if}
			</div>
		{/if}
	{/if}
</section>

<style>
	.hwline {
		margin: calc(-1 * var(--sp-4)) 0 0;
	}
	.hwbtn {
		display: inline-flex;
		flex-wrap: wrap;
		gap: 0.4rem;
		padding: 0.45rem 0.9rem;
		border: 1px solid var(--line);
		border-radius: var(--r-pill);
		background: var(--bg-1);
		color: var(--text-hi);
		font: inherit;
		font-size: var(--fs-xs);
		font-weight: 560;
		cursor: pointer;
	}
	.hwbtn:hover {
		border-color: var(--line-strong);
	}
	.mute {
		color: var(--text-mute);
	}
	.hero {
		display: grid;
		gap: var(--sp-8);
	}
	.head {
		display: grid;
		gap: var(--sp-2);
	}
	.tag {
		justify-self: start;
		margin: 0;
		color: var(--text-hi);
	}
	.model {
		font-size: clamp(1.8rem, 1.2rem + 2.2vw, 2.8rem);
		font-weight: 760;
		font-stretch: 106%;
		letter-spacing: -0.03em;
		line-height: 1.05;
	}
	.meta {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem;
		color: var(--text);
		font-size: var(--fs-sm);
	}
	.ctx {
		display: grid;
		gap: var(--sp-3);
	}
	.ctx-fig {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0.4rem 1rem;
		margin: 0;
	}
	.ctx-num {
		font-size: clamp(3rem, 1.6rem + 6vw, 6.25rem);
		font-weight: 560;
		line-height: 0.95;
		letter-spacing: -0.05em;
		color: var(--text-hi);
		background: linear-gradient(180deg, #ffffff, #b9b5ad);
		-webkit-background-clip: text;
		background-clip: text;
		-webkit-text-fill-color: transparent;
	}
	:global(:root[data-theme='light']) .ctx-num {
		background: none;
		-webkit-text-fill-color: currentColor;
	}
	.ctx-unit {
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.ruler {
		position: relative;
		height: 0.5rem;
		margin-top: 1.4rem;
		border-radius: var(--r-pill);
		background: var(--bg-3);
	}
	.ruler .fill {
		position: absolute;
		inset: 0 auto 0 0;
		border-radius: inherit;
		background: linear-gradient(90deg, color-mix(in srgb, var(--text-hi) 55%, transparent), var(--text-hi));
		transition: width var(--dur-4) var(--ease-out);
	}
	.ruler .min {
		position: absolute;
		top: -0.35rem;
		bottom: -0.35rem;
		width: 2px;
		margin-left: -1px;
		background: var(--warn-ink);
	}
	.ruler .min span {
		position: absolute;
		bottom: calc(100% + 0.2rem);
		left: 50%;
		transform: translateX(-50%);
		font-size: var(--fs-2xs);
		color: var(--warn-ink);
		font-style: normal;
	}
	.ctx-note {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		gap: var(--sp-2) var(--sp-6);
		margin: 0;
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.ctx-note .ok {
		color: var(--ok-ink);
	}
	.cols {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr));
		gap: var(--sp-8);
	}
	.cols h3 {
		margin-bottom: var(--sp-3);
	}
	.why {
		display: grid;
		gap: var(--sp-2);
		margin: 0;
		padding: 0;
		list-style: none;
	}
	.why li {
		position: relative;
		padding-left: 1.2rem;
		color: var(--text);
		font-size: var(--fs-sm);
	}
	.why li::before {
		content: '';
		position: absolute;
		left: 0;
		top: 0.6em;
		width: 0.5rem;
		height: 1px;
		background: var(--text-mute);
	}
	.mono {
		font-family: var(--font-mono);
		font-weight: 400;
		font-size: var(--fs-sm);
	}
	.spec dd .sub {
		overflow-wrap: anywhere;
	}
	.alts {
		margin: 0;
		padding: 0;
		border: 0;
		min-width: 0;
	}
	.alts legend {
		padding: 0;
		margin-bottom: var(--sp-4);
	}
	.alt-grid {
		display: grid;
		gap: var(--sp-4);
		grid-template-columns: repeat(auto-fill, minmax(min(100%, 15rem), 1fr));
	}
	.alt {
		position: relative;
		display: grid;
		gap: 0.45rem;
		align-content: start;
		padding: var(--sp-5);
		border: 1px solid var(--line);
		border-radius: var(--r-xl);
		background: var(--bg-2);
		cursor: pointer;
		transition:
			border-color var(--dur-2) var(--ease-out),
			box-shadow var(--dur-2) var(--ease-out);
	}
	.alt:hover {
		border-color: var(--line-strong);
	}
	.alt.on {
		border-color: var(--text-hi);
		box-shadow: 0 0 0 1px var(--text-hi);
	}
	.alt input {
		position: absolute;
		top: var(--sp-5);
		right: var(--sp-5);
		width: 1.1rem;
		height: 1.1rem;
		margin: 0;
		accent-color: var(--text-hi);
	}
	.alt:has(input:focus-visible) {
		outline: 2px solid var(--focus);
		outline-offset: 2px;
	}
	.alt:has(input:disabled) {
		cursor: default;
	}
	.alt-top {
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
		align-items: center;
		padding-right: 1.6rem;
	}
	.alt-name {
		color: var(--text-hi);
		font-weight: 680;
	}
	.mini {
		font-size: 0.6rem;
		color: var(--text-hi);
	}
	.alt-q {
		justify-self: start;
	}
	.alt-row {
		font-size: var(--fs-xs);
	}
	.alt-row .big {
		font-size: var(--fs-lg);
		color: var(--text-hi);
	}
	.rejected summary {
		font-weight: 600;
		color: var(--text-hi);
	}
	.rej {
		display: grid;
		gap: var(--sp-2);
		margin: var(--sp-3) 0 0;
		padding: 0;
		list-style: none;
		font-size: var(--fs-sm);
	}
	.rej li {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem;
		padding-block: 0.45rem;
		border-top: 1px solid var(--line);
	}
	.why-r {
		color: var(--text-mute);
	}
	.dock {
		position: sticky;
		bottom: 3.4rem;
		z-index: 5;
		display: grid;
		gap: var(--sp-2);
		padding: var(--sp-3) var(--sp-3) var(--sp-3) var(--sp-6);
		border: 1px solid var(--line-strong);
		border-radius: var(--r-pill);
		background: color-mix(in srgb, var(--bg-1) 88%, transparent);
		backdrop-filter: blur(16px);
		-webkit-backdrop-filter: blur(16px);
		box-shadow: var(--shadow-2);
	}
	.dock-in {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-3) var(--sp-6);
	}
	.dock-sel {
		display: grid;
		gap: 0.1rem;
		margin: 0 auto 0 0;
		min-width: 0;
	}
	.dock-name {
		color: var(--text-hi);
		font-weight: 680;
	}
	.dock-sel .num {
		font-size: var(--fs-xs);
	}
	.need {
		font-size: var(--fs-sm);
		color: var(--warn-ink);
	}
	@media (max-width: 600px) {
		.dock {
			border-radius: 1.25rem;
			padding: var(--sp-3);
		}
		.dock-sel {
			display: none;
		}
		.dock .go,
		.dock .btn {
			width: 100%;
		}
	}
</style>
