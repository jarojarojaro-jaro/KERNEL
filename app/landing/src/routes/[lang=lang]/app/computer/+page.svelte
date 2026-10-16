<script lang="ts">
	import { currentLang, num } from '$lib/i18n';
	import { M } from '$lib/data/measurements';
	import { T } from '$lib/desktop/i18n';
	import { OBSERVED } from '$lib/desktop/demo';
	import ScreenHead from '$lib/desktop/ScreenHead.svelte';
	import SpecList from '$lib/desktop/SpecList.svelte';
	import ScanFacts from '$lib/desktop/ScanFacts.svelte';
	import Src from '$lib/desktop/Src.svelte';
	import Icon from '$lib/desktop/Icon.svelte';

	const lang = $derived(currentLang());
	const t = $derived(T[lang]);
	const c = $derived(t.computer);

	const backends = $derived([
		{ name: 'ROCm (HIP)', ok: true, ...pair(c.bk.rocm) },
		{ name: 'Vulkan (RADV)', ok: true, ...pair(c.bk.vulkan) },
		{ name: 'CPU (AVX2)', ok: true, ...pair(c.bk.cpu) },
		{ name: 'CUDA', ok: false, ...pair(c.bk.cuda) },
		{ name: 'Metal', ok: false, ...pair(c.bk.metal) }
	]);
	function pair([state, note]: string[]) {
		return { state, note };
	}
	const asleep = M.bacoAsleep;
	const awake = M.bacoAwake;
	const range = (r: { lo: number; hi: number }) => `${r.lo}–${r.hi}`;
</script>

<svelte:head>
	<title>{t.shell.title(c.title)}</title>
</svelte:head>

<ScreenHead overline={c.overline} title={c.title} lead={c.lead} />

<div class="layout">
	<section aria-labelledby="spec-h" class="block">
		<h2 id="spec-h" class="overline">{c.specTitle}</h2>
		<SpecList />
	</section>

	<section aria-labelledby="warn-h" class="block">
		<h2 id="warn-h" class="overline">{c.warningsTitle}</h2>
		<div class="warns">
			<article class="hud baco" aria-labelledby="baco-h">
				<div class="baco-head">
					<span class="warn-ic"><Icon name="alert" size={20} /></span>
					<h3 id="baco-h" class="h3">{c.baco.title}</h3>
					<span class="badge badge--ok">{c.baco.fixed}</span>
				</div>
				<p class="small">{c.baco.body}</p>
				<div class="cmp">
					<div class="cmp-row">
						<span class="cmp-k">{c.baco.asleep}</span>
						<div class="bar bar--before bar--tall" aria-hidden="true"><i style="--v: {asleep.value / awake.value}"></i></div>
						<span class="cmp-v num">{num(asleep.value, lang)} <span class="u">t/s</span></span>
					</div>
					<div class="cmp-row">
						<span class="cmp-k">{c.baco.awake}</span>
						<div class="bar bar--tall" aria-hidden="true"><i style="--v: 1"></i></div>
						<span class="cmp-v num">{num(awake.value, lang, 0)} <span class="u">t/s</span></span>
					</div>
				</div>
				<p class="small">{c.baco.fix}</p>
				<p class="small mute">{asleep.method[lang]}</p>
				<Src m={[asleep, awake]} />
			</article>

			<article class="card thermal" aria-labelledby="therm-h">
				<div class="baco-head">
					<span class="info-ic"><Icon name="thermo" size={20} /></span>
					<h3 id="therm-h" class="h3">{c.thermal.title}</h3>
					<span class="badge badge--measured">{t.common.measured}</span>
				</div>
				<p class="small">
					{c.thermal.body(
						num(OBSERVED.powerW, lang, 0),
						range(OBSERVED.junction),
						range(OBSERVED.edge),
						num(OBSERVED.fansRpm, lang, 0)
					)}
				</p>
				<p class="small mute">{c.thermal.note}</p>
				<Src src={OBSERVED.source} />
			</article>
		</div>
	</section>

	<section aria-labelledby="bk-h" class="block">
		<h2 id="bk-h" class="overline">{c.backendsTitle}</h2>
		<div class="table-wrap">
			<table class="table">
				<caption>{c.backendsCaption}</caption>
				<thead>
					<tr>
						<th scope="col">{c.bkCol.name}</th>
						<th scope="col">{c.bkCol.state}</th>
						<th scope="col">{c.bkCol.note}</th>
					</tr>
				</thead>
				<tbody>
					{#each backends as b (b.name)}
						<tr>
							<th scope="row">{b.name}</th>
							<td><span class="badge {b.ok ? 'badge--ok' : 'badge--soon'}">{b.state}</span></td>
							<td>{b.note}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
		<Src m={[M.qwenOursMtp, M.qwenUpstreamVulkanPlain]} />
	</section>

	<ScanFacts />
</div>

<style>
	.layout {
		display: grid;
		gap: var(--sp-8);
	}
	.block {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: var(--sp-3);
	}
	.warns {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr));
		gap: var(--sp-4);
		align-items: start;
	}
	.baco,
	.thermal {
		display: grid;
		gap: var(--sp-3);
		padding: var(--sp-6);
	}
	.baco {
		--hud-c: var(--warn-ink);
	}
	.baco-head {
		display: grid;
		grid-template-columns: auto 1fr auto;
		align-items: start;
		gap: var(--sp-3);
	}
	.warn-ic {
		color: var(--warn-ink);
	}
	.info-ic {
		color: var(--info-ink);
	}
	.cmp {
		display: grid;
		gap: var(--sp-3);
		padding: var(--sp-4);
		border-radius: var(--r-sm);
		background: var(--bg-1);
	}
	.cmp-row {
		display: grid;
		grid-template-columns: 7.5rem 1fr 5.5rem;
		align-items: center;
		gap: var(--sp-3);
	}
	.cmp-k {
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	.cmp-v {
		text-align: right;
		color: var(--text-hi);
		font-size: var(--fs-md);
	}
	.u {
		font-size: var(--fs-xs);
		color: var(--text-mute);
	}
	@media (max-width: 480px) {
		.cmp-row {
			grid-template-columns: 1fr auto;
		}
		.cmp-row .bar {
			grid-column: 1 / -1;
			grid-row: 2;
		}
	}
</style>
