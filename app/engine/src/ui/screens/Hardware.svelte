<script lang="ts">
	import type { Backend, Hw } from '../../shared/types';
	import GpuArt from '../components/GpuArt.svelte';
	import ScreenHead from '../components/ScreenHead.svelte';
	import { api } from '../lib/api';
	import { num, time } from '../lib/i18n';
	import { store } from '../lib/store.svelte';

	let { onnext }: { onnext: (() => void) | null } = $props();

	const t = $derived(store.t.hw);
	const lang = $derived(store.lang);
	const hw = $derived<Hw | null>(store.state?.hw ?? null);
	const gpus = $derived(hw ? [...hw.gpus].sort((a, b) => b.vramGiB - a.vramGiB) : []);
	const main = $derived(gpus[0] ?? null);
	const OS: Record<Hw['os'], string> = { linux: 'Linux', windows: 'Windows', macos: 'macOS' };
	const BACKEND: Record<Backend, string> = { cuda: 'CUDA', rocm: 'ROCm', vulkan: 'Vulkan', metal: 'Metal', cpu: 'CPU' };

	let busy = $state(false);
	let error = $state('');

	async function rescan() {
		busy = true;
		error = '';
		try {
			await api.scan();
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
		} finally {
			busy = false;
		}
	}
</script>

<section class="screen" aria-labelledby="hw-title">
	<ScreenHead id="hw-title" overline={t.overline} title={t.title} accent={t.titleAccent} lead={t.lead} />

	{#if !hw}
		<div class="panel busy" role="status"><span class="ring" aria-hidden="true"></span>{t.scanning}</div>
	{:else}
		<div class="hwhero">
			<p class="hw-name">{main ? main.name : hw.cpu.name}</p>
			<p class="hw-num num">
				<span class="big">{num(main ? main.vramGiB : hw.ramGiB, lang, 0)}</span>
				<span class="unit">GB {main ? (main.unified ? t.unified : 'VRAM') : 'RAM'}</span>
			</p>
		</div>
		<div class="panel panel--heat scan">
			<div class="visual">
				<GpuArt gpu={main} cpuName={hw.cpu.name} />
			</div>
			<div class="list">
				{#if gpus.length === 0}
					<p class="notice notice--warn"><span class="notice__icon" aria-hidden="true">!</span><span>{t.noGpu}</span></p>
				{/if}
				{#each gpus as g, i (i)}
					{#if gpus.length > 1}<p class="eyebrow gpu-n">{t.gpuN(i + 1)}</p>{/if}
					<dl class="facts">
						<div><dt>{t.gpu}</dt><dd>{g.name}{#if g.arch}<span class="sub">{g.arch}</span>{/if}</dd></div>
						<div>
							<dt>{t.vram}</dt>
							<dd><span class="num">{num(g.vramGiB, lang, g.vramGiB % 1 ? 1 : 0)} GB</span>{#if g.unified}<span class="sub">{t.unified}</span>{/if}</dd>
						</div>
						{#if g.driver}<div><dt>{t.driver}</dt><dd>{g.driver}</dd></div>{/if}
						<div>
							<dt>{t.backends}</dt>
							<dd>
								<ul class="chips">
									{#each g.backends as b (b)}<li class="chip chip--mono">{BACKEND[b]}</li>{/each}
								</ul>
							</dd>
						</div>
					</dl>
				{/each}
				<dl class="facts" class:sys={gpus.length > 0}>
					<div><dt>{t.cpu}</dt><dd>{hw.cpu.name}<span class="sub">{t.cores(hw.cpu.cores, hw.cpu.threads)}</span></dd></div>
					<div><dt>{t.ram}</dt><dd class="num">{num(hw.ramGiB, lang, 0)} GB</dd></div>
					<div><dt>{t.disk}</dt><dd class="num">{num(hw.diskFreeGiB, lang, 0)} GB</dd></div>
					<div><dt>{t.system}</dt><dd>{OS[hw.os]} · {hw.arch}<span class="sub">{t.scannedAt} {time(hw.scannedAt, lang)}</span></dd></div>
				</dl>
			</div>
		</div>
		{#if error}<p class="error-text" role="alert">{error}</p>{/if}
		<div class="actions">
			{#if onnext}
				<button class="go" type="button" onclick={onnext}>{t.next} <span class="arrow" aria-hidden="true">→</span></button>
			{/if}
			<button class="btn btn--secondary" type="button" onclick={rescan} disabled={busy}>
				{#if busy}<span class="ring" aria-hidden="true"></span>{/if}{t.rescan}
			</button>
		</div>
	{/if}
</section>

<style>
	.hwhero {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		justify-content: space-between;
		gap: var(--sp-2) var(--sp-8);
	}
	.hw-name {
		margin: 0;
		font-size: clamp(1.8rem, 1.1rem + 2.6vw, 3.2rem);
		font-weight: 780;
		font-stretch: 106%;
		letter-spacing: -0.03em;
		line-height: 1.05;
		color: var(--text-hi);
	}
	.hw-num {
		display: flex;
		align-items: baseline;
		gap: 0.5rem;
		margin: 0;
	}
	.hw-num .big {
		font-size: clamp(3rem, 1.8rem + 4.6vw, 5.6rem);
		font-weight: 560;
		line-height: 0.9;
		letter-spacing: -0.05em;
		background: linear-gradient(180deg, #ffffff, #b9b5ad);
		-webkit-background-clip: text;
		background-clip: text;
		color: transparent;
	}
	:global(:root[data-theme='light']) .hw-num .big {
		background: none;
		color: var(--text-hi);
	}
	.hw-num .unit {
		font-size: var(--fs-xs);
		letter-spacing: 0.12em;
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.scan {
		display: grid;
		grid-template-columns: minmax(0, 1.15fr) minmax(0, 1fr);
		gap: var(--sp-8);
		align-items: center;
	}
	.list {
		display: grid;
		gap: var(--sp-4);
	}
	.gpu-n {
		margin: 0;
	}
	.sys {
		padding-top: var(--sp-2);
		border-top: 1px solid var(--line-strong);
	}
	.sys > div:first-child > * {
		border-top: 0;
	}
	.facts dd.num {
		font-family: var(--font-mono);
		font-weight: 500;
	}
	@media (max-width: 900px) {
		.scan {
			grid-template-columns: 1fr;
			gap: var(--sp-6);
		}
	}
</style>
