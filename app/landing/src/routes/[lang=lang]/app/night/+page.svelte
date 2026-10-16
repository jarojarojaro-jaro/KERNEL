<script lang="ts">
	import { BRAND } from '$lib/brand';
	import { currentLang, num } from '$lib/i18n';
	import { T } from '$lib/desktop/i18n';
	import { OBSERVED, HISTORY } from '$lib/desktop/demo';
	import ScreenHead from '$lib/desktop/ScreenHead.svelte';
	import Src from '$lib/desktop/Src.svelte';
	import Icon from '$lib/desktop/Icon.svelte';
	import CopyButton from '$lib/ui/CopyButton.svelte';

	const lang = $derived(currentLang());
	const t = $derived(T[lang]);
	const n = $derived(t.night);

	let run = $state<'idle' | 'run' | 'pause'>('idle');
	let acOnly = $state(true);
	let idleOnly = $state(true);
	let windowOnly = $state(false);
	let quiet = $state(false);
	const LIMITS = [80, 90, 100] as const;
	let tempLimit = $state<number>(80);
	const hotOver = $derived(OBSERVED.junction.hi > tempLimit);

	let undone = $state<Record<'engine' | 'baco', boolean>>({ engine: false, baco: false });

	const range = (r: { lo: number; hi: number }) => `${r.lo}–${r.hi}`;
	const cli = `${BRAND.cli} tune --overnight --resume\n${BRAND.cli} tune status`;
</script>

<svelte:head>
	<title>{t.shell.title(n.title)}</title>
</svelte:head>

<ScreenHead overline={n.overline} title={n.title} lead={n.lead} />

<div class="top">
	<section class="card start" aria-labelledby="start-h">
		<h2 id="start-h" class="sr-only">{n.startBtn}</h2>
		<span class="moon"><Icon name="night" size={28} /></span>
		<blockquote class="quote">{n.startQuote}</blockquote>
		<p class="source">{t.common.uxExample('§2.1.4')}</p>
		<div class="cluster">
			{#if run === 'idle'}
				<button type="button" class="btn btn--primary" onclick={() => (run = 'run')}>
					<Icon name="play" size={16} />{n.startBtn}
				</button>
			{:else}
				<button type="button" class="btn btn--secondary" onclick={() => (run = 'idle')}>
					<Icon name="close" size={16} />{n.stopBtn}
				</button>
			{/if}
		</div>
		<p class="small mute">{t.common.protoAction}</p>
	</section>

	<section class="card cond" aria-labelledby="cond-h">
		<h2 id="cond-h" class="h3">{n.conditionsTitle}</h2>
		<div class="sw">
			<label class="switch"><input type="checkbox" role="switch" bind:checked={acOnly} aria-describedby="ac-h" />{n.acOnly}</label>
			<p id="ac-h" class="hint">{n.acHint}</p>
		</div>
		<div class="sw">
			<label class="switch"><input type="checkbox" role="switch" bind:checked={idleOnly} aria-describedby="idle-h" />{n.idleOnly}</label>
			<p id="idle-h" class="hint">{n.idleHint}</p>
		</div>
		<div class="sw">
			<label class="switch"><input type="checkbox" role="switch" bind:checked={windowOnly} />{n.windowOnly}</label>
		</div>
		<div class="sw">
			<label class="switch"><input type="checkbox" role="switch" bind:checked={quiet} />{n.quiet}</label>
		</div>
		<div class="field">
			<label class="label" for="temp">{n.tempLimit}</label>
			<select id="temp" class="select" bind:value={tempLimit} aria-describedby="temp-h">
				{#each LIMITS as l (l)}<option value={l}>{l} °C</option>{/each}
			</select>
			<p id="temp-h" class="hint">{n.tempHint}</p>
		</div>
		{#if hotOver}
			<p class="notice notice--warn">
				<span class="notice__icon" aria-hidden="true">!</span>
				<span>{n.tempWarn(range(OBSERVED.junction), String(tempLimit))}<br /><span class="source">{t.common.source}: {OBSERVED.source}</span></span>
			</p>
		{/if}
	</section>
</div>

<section class="hud live" data-state={run} aria-labelledby="live-h">
	<header class="live-head">
		<h2 id="live-h" class="live-title"><span class="led" aria-hidden="true"></span>{n.liveTitle}</h2>
		<span class="badge {run === 'run' ? 'badge--progress' : 'badge--soon'}" role="status">{n.state[run]}</span>
		{#if run !== 'idle'}
			<button type="button" class="btn btn--secondary btn--sm" onclick={() => (run = run === 'run' ? 'pause' : 'run')}>
				<Icon name={run === 'run' ? 'pause' : 'play'} size={16} />{run === 'run' ? n.pause : n.resume}
			</button>
		{/if}
	</header>

	{#if run === 'idle'}<p class="small mute">{n.notStarted}</p>{/if}
	{#if run === 'pause'}<p class="small">{n.pausedByYou}</p>{/if}

	<div class="prog">
		<div class="prog-top">
			<p class="prog-text num">{n.progress}</p>
			<span class="badge badge--prototype">{t.common.layoutExample('§2.1.4')}</span>
		</div>
		<div class="track" aria-hidden="true"><i style="--v: {42 / 180}"></i></div>
	</div>

	<dl class="tiles">
		<div class="tile">
			<dt><Icon name="bolt" size={14} />{n.tiles.power}</dt>
			<dd class="val num">{OBSERVED.powerW}<span class="u"> W</span></dd>
			<dd class="bar" aria-hidden="true"><i style="--v: {OBSERVED.powerW / OBSERVED.capW}"></i></dd>
			<dd class="lim">{n.limitOf(`${OBSERVED.capW} W`)}</dd>
		</div>
		<div class="tile" class:over={hotOver}>
			<dt><Icon name="thermo" size={14} />{n.tiles.junction}</dt>
			<dd class="val num">{range(OBSERVED.junction)}<span class="u"> °C</span></dd>
			<dd class="bar bar--range" aria-hidden="true"><i style="--v: {OBSERVED.junction.hi / 110}"></i></dd>
			<dd class="lim">{hotOver ? n.overLimit : n.limitOf(`${tempLimit} °C`)}</dd>
		</div>
		<div class="tile">
			<dt><Icon name="thermo" size={14} />{n.tiles.edge}</dt>
			<dd class="val num">{range(OBSERVED.edge)}<span class="u"> °C</span></dd>
			<dd class="bar bar--range" aria-hidden="true"><i style="--v: {OBSERVED.edge.hi / 110}"></i></dd>
		</div>
		<div class="tile">
			<dt><Icon name="thermo" size={14} />{n.tiles.mem}</dt>
			<dd class="val num">{OBSERVED.second.mem}<span class="u"> °C</span></dd>
			<dd class="bar" aria-hidden="true"><i style="--v: {OBSERVED.second.mem / 110}"></i></dd>
		</div>
		<div class="tile">
			<dt><Icon name="fan" size={14} />{n.tiles.fans}</dt>
			<dd class="val num">~{num(OBSERVED.fansRpm, lang, 0)}<span class="u"> RPM</span></dd>
		</div>
	</dl>
	<p class="small mute">{n.liveNote}</p>
	<Src src={[OBSERVED.source, OBSERVED.second.source]} />
</section>

<div class="bottom">
	<section class="card hist" aria-labelledby="hist-h">
		<h2 id="hist-h" class="h3">{n.historyTitle}</h2>
		<p class="small mute">{n.historyNote}</p>
		<ul class="hist-list">
			<li class="hist-row empty">
				<span class="date num">—</span>
				<div class="hist-body"><p class="small">{n.nightEmpty}</p></div>
				<span class="badge badge--soon">{t.common.soon}</span>
			</li>
			<li class="hist-row" class:is-undone={undone.engine}>
				<span class="date num">{HISTORY.engine.date}</span>
				<div class="hist-body">
					<p class="h-title">{n.hist.engine.title}</p>
					<p class="small num">{n.hist.engine.detail(num(HISTORY.engine.m.value, lang))}</p>
					<Src m={HISTORY.engine.m} />
				</div>
				<button type="button" class="btn btn--ghost btn--sm" aria-pressed={undone.engine} onclick={() => (undone.engine = !undone.engine)}>
					<Icon name={undone.engine ? 'refresh' : 'undo'} size={16} />{undone.engine ? n.redo : n.undo}
					<span class="sr-only">: {n.hist.engine.title}</span>
				</button>
			</li>
			<li class="hist-row" class:is-undone={undone.baco}>
				<span class="date num">{HISTORY.baco.date}</span>
				<div class="hist-body">
					<p class="h-title">{n.hist.baco.title}</p>
					<p class="small num">{n.hist.baco.detail(num(HISTORY.baco.before.value, lang), num(HISTORY.baco.after.value, lang, 0))}</p>
					<Src m={[HISTORY.baco.before, HISTORY.baco.after]} />
				</div>
				<button type="button" class="btn btn--ghost btn--sm" aria-pressed={undone.baco} onclick={() => (undone.baco = !undone.baco)}>
					<Icon name={undone.baco ? 'refresh' : 'undo'} size={16} />{undone.baco ? n.redo : n.undo}
					<span class="sr-only">: {n.hist.baco.title}</span>
				</button>
			</li>
		</ul>
	</section>

	<section class="card safety" aria-labelledby="safe-h">
		<h2 id="safe-h" class="h3">{n.safetyTitle}</h2>
		<div>
			{#each n.safety as [title, body] (title)}
				<details class="disclosure">
					<summary>{title}</summary>
					<div class="disclosure__body small">{body}</div>
				</details>
			{/each}
		</div>
		<Src src={['PLAN §4.3', `${lang === 'pl' ? 'raport' : 'report'} 06 §2.1.4`]} />
		<div class="codeblock">
			<div class="codeblock__head"><span>{n.cliTitle}</span><CopyButton text={cli} label={n.cliTitle} /></div>
			<pre><code><span class="prompt">$ </span>{BRAND.cli} tune --overnight --resume
<span class="prompt">$ </span>{BRAND.cli} tune status</code></pre>
		</div>
	</section>
</div>

<style>
	.top {
		display: grid;
		grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr);
		gap: var(--sp-4);
		align-items: start;
	}
	.start {
		display: grid;
		gap: var(--sp-4);
		justify-items: start;
		background:
			radial-gradient(120% 120% at 0% 0%, var(--accent-soft), transparent 60%),
			var(--bg-2);
	}
	.moon {
		color: var(--accent-ink);
	}
	.quote {
		margin: 0;
		font-size: var(--fs-lg);
		line-height: var(--lh-snug);
		color: var(--text-hi);
		letter-spacing: var(--tracking-tight);
		max-width: 32rem;
	}
	.cond {
		display: grid;
		gap: var(--sp-4);
	}
	.sw {
		display: grid;
		gap: var(--sp-1);
	}
	.sw .hint {
		padding-left: calc(2.5rem + var(--sp-3));
	}
	.field {
		max-width: 16rem;
	}

	/* REACTOR-style live panel */
	.live {
		margin-top: var(--sp-4);
		padding: var(--sp-6);
		display: grid;
		gap: var(--sp-4);
		background:
			linear-gradient(var(--grid) 1px, transparent 1px) 0 0 / 100% 24px,
			var(--bg-2);
	}
	.live-head {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: var(--sp-3);
	}
	.live-title {
		display: inline-flex;
		align-items: center;
		gap: var(--sp-2);
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
		font-weight: var(--fw-medium);
		letter-spacing: var(--tracking-overline);
		text-transform: uppercase;
		color: var(--accent-ink);
		margin-right: auto;
	}
	.led {
		width: 0.55rem;
		height: 0.55rem;
		border-radius: 50%;
		border: 1px solid var(--text-mute);
	}
	.live[data-state='run'] .led {
		background: var(--accent);
		border-color: var(--accent);
		box-shadow: var(--accent-glow);
	}
	.live[data-state='pause'] .led {
		background: var(--warn);
		border-color: var(--warn);
	}
	.prog {
		display: grid;
		gap: var(--sp-2);
	}
	.prog-top {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: var(--sp-2);
	}
	.prog-text {
		color: var(--text-hi);
		font-size: var(--fs-sm);
	}
	.track {
		position: relative;
		height: 0.5rem;
		border-radius: var(--r-xs);
		background: var(--bg-3);
		overflow: hidden;
	}
	.track > i {
		position: absolute;
		inset: 0 auto 0 0;
		width: calc(var(--v) * 100%);
		background: var(--accent);
		border-radius: inherit;
		overflow: hidden;
	}
	.live:not([data-state='run']) .track > i {
		background: var(--before);
	}
	@media (prefers-reduced-motion: no-preference) {
		.live[data-state='run'] .track > i::after {
			content: '';
			position: absolute;
			inset: 0;
			background: linear-gradient(90deg, transparent, var(--accent-hover), transparent);
			animation: sweep 1.6s var(--ease-in-out) infinite;
		}
		.live[data-state='run'] .led {
			animation: blink 1.2s steps(1) infinite;
		}
	}
	@keyframes sweep {
		from {
			transform: translateX(-100%);
		}
		to {
			transform: translateX(100%);
		}
	}
	.tiles {
		margin: 0;
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
		gap: var(--sp-3);
	}
	.tile {
		display: grid;
		gap: var(--sp-2);
		align-content: start;
		padding: var(--sp-4);
		border: 1px solid var(--line);
		border-radius: var(--r-md);
		background: var(--bg-1);
	}
	.tile.over {
		border-color: var(--warn);
		background: var(--warn-soft);
	}
	.tile dt {
		display: inline-flex;
		align-items: center;
		gap: var(--sp-2);
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		letter-spacing: var(--tracking-overline);
		text-transform: uppercase;
		color: var(--text-mute);
	}
	.tile dd {
		margin: 0;
	}
	.val {
		font-size: var(--fs-xl);
		color: var(--text-hi);
		letter-spacing: -0.02em;
		line-height: 1;
	}
	.u {
		font-size: var(--fs-xs);
		color: var(--text-mute);
		letter-spacing: 0;
	}
	.tile .bar {
		height: 0.375rem;
	}
	.tile.over .bar > i {
		--bar-c: var(--warn);
	}
	.lim {
		font-family: var(--font-mono);
		font-size: var(--fs-2xs);
		color: var(--text-mute);
	}
	.tile.over .lim {
		color: var(--warn-ink);
	}
	.bottom {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 22rem), 1fr));
		gap: var(--sp-4);
		margin-top: var(--sp-4);
		align-items: start;
	}
	.hist,
	.safety {
		display: grid;
		gap: var(--sp-4);
	}
	.hist-list {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
	}
	.hist-row {
		display: grid;
		grid-template-columns: 6.5rem 1fr auto;
		gap: var(--sp-3);
		align-items: start;
		padding: var(--sp-4) 0;
		border-top: 1px solid var(--line);
	}
	.hist-row.is-undone .hist-body {
		opacity: 0.5;
		text-decoration: line-through;
	}
	.date {
		font-size: var(--fs-xs);
		color: var(--text-mute);
		padding-top: 0.15rem;
	}
	.h-title {
		color: var(--text-hi);
		font-weight: var(--fw-medium);
		font-size: var(--fs-sm);
	}
	.hist-body {
		min-width: 0;
	}

	@media (max-width: 900px) {
		.top {
			grid-template-columns: minmax(0, 1fr);
		}
	}
	@media (max-width: 480px) {
		.hist-row {
			grid-template-columns: 1fr auto;
		}
		.date {
			grid-column: 1 / -1;
		}
		.bottom {
			grid-template-columns: minmax(0, 1fr);
		}
	}
</style>
