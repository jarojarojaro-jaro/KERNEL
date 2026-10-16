<script lang="ts">
	import { onMount, tick } from 'svelte';
	import { BRAND } from '$lib/brand';
	import { currentLang } from '$lib/i18n';
	import { T } from '$lib/desktop/i18n';
	import ScreenHead from '$lib/desktop/ScreenHead.svelte';
	import CopyButton from '$lib/ui/CopyButton.svelte';
	import Icon from '$lib/desktop/Icon.svelte';
	import Src from '$lib/desktop/Src.svelte';

	const lang = $derived(currentLang());
	const t = $derived(T[lang]);
	const d = $derived(t.dev);

	const BASE = `http://127.0.0.1:${BRAND.apiPort}`;
	const ENV = `${BRAND.ascii.toUpperCase()}_TOKEN`;
	const MODEL = 'qwen3.8-27b';

	// ---------- token (random, client-side, never a real secret) ----------
	let token = $state('');
	let reveal = $state(false);
	let regenMsg = $state('');
	function newToken() {
		const bytes = crypto.getRandomValues(new Uint8Array(24));
		return `${BRAND.ascii}_${Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('')}`;
	}
	onMount(() => (token = newToken()));
	const masked = $derived(token ? `${token.slice(0, BRAND.ascii.length + 1)}${'•'.repeat(20)}${token.slice(-4)}` : '…');
	function regenerate() {
		token = newToken();
		regenMsg = d.regenDone;
	}

	// ---------- examples ----------
	const examples = $derived([
		{
			id: 'curl',
			label: 'curl',
			code: `curl ${BASE}/v1/chat/completions \\
  -H "Authorization: Bearer $${ENV}" \\
  -H "Content-Type: application/json" \\
  -d '{"model": "${MODEL}", "messages": [{"role": "user", "content": "${d.samplePrompt}"}]}'`
		},
		{
			id: 'python',
			label: 'Python',
			code: `import os
from openai import OpenAI

client = OpenAI(base_url="${BASE}/v1", api_key=os.environ["${ENV}"])
reply = client.chat.completions.create(
    model="${MODEL}",
    messages=[{"role": "user", "content": "${d.samplePrompt}"}],
)
print(reply.choices[0].message.content)`
		},
		{
			id: 'js',
			label: 'JavaScript',
			code: `const res = await fetch('${BASE}/v1/chat/completions', {
  method: 'POST',
  headers: {
    Authorization: \`Bearer \${process.env.${ENV}}\`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    model: '${MODEL}',
    messages: [{ role: 'user', content: '${d.samplePrompt}' }]
  })
});
const data = await res.json();
console.log(data.choices[0].message.content);`
		}
	]);
	let tab = $state(0);
	const tabEls: HTMLButtonElement[] = $state([]);
	async function onTabKey(e: KeyboardEvent) {
		const n = examples.length;
		let next = tab;
		if (e.key === 'ArrowRight') next = (tab + 1) % n;
		else if (e.key === 'ArrowLeft') next = (tab - 1 + n) % n;
		else if (e.key === 'Home') next = 0;
		else if (e.key === 'End') next = n - 1;
		else return;
		e.preventDefault();
		tab = next;
		await tick();
		tabEls[next]?.focus();
	}

	// ---------- trusted hosts ----------
	let hosts = $state<string[]>([]);
	let draft = $state('');
	let invalid = $state(false);
	function addHost(e: SubmitEvent) {
		e.preventDefault();
		const v = draft.trim().replace(/\/$/, '');
		invalid = !/^https?:\/\/(\[[0-9a-f:]+\]|[a-z0-9.-]+)(:\d{1,5})?$/i.test(v);
		if (invalid) return;
		if (!hosts.includes(v)) hosts.push(v);
		draft = '';
	}

	const cliRows = $derived([
		[`${BRAND.cli} api status`, d.cli.status],
		[`${BRAND.cli} api token show`, d.cli.show],
		[`${BRAND.cli} api token rotate`, d.cli.rotate],
		[`${BRAND.cli} api trust http://localhost:5173`, d.cli.trust],
		[`${BRAND.cli} models list`, d.cli.models],
		[`${BRAND.cli} chat`, d.cli.chat],
		[`${BRAND.cli} tune --overnight --resume`, d.cli.tune]
	]);
	const cliText = $derived(cliRows.map(([c]) => c).join('\n'));
</script>

<svelte:head>
	<title>{t.shell.title(d.title)}</title>
</svelte:head>

<ScreenHead overline={d.overline} title={d.title} lead={d.lead} />

<div class="grid">
	<section class="card endpoint" aria-labelledby="ep-h">
		<h2 id="ep-h" class="overline">{d.endpoint}</h2>
		<div class="ep-row">
			<code class="ep">{BASE}</code>
			<CopyButton text={BASE} label={d.endpoint} />
		</div>
		<div class="table-wrap">
			<table class="table">
				<caption>{d.compatCaption}</caption>
				<thead>
					<tr>
						<th scope="col">{d.compatCol.api}</th>
						<th scope="col">{d.compatCol.path}</th>
						<th scope="col">{d.compatCol.note}</th>
					</tr>
				</thead>
				<tbody>
					<tr>
						<th scope="row">OpenAI</th>
						<td><code>/v1/chat/completions</code><br /><code>/v1/responses</code><br /><code>/v1/models</code></td>
						<td>{d.compat.openai}</td>
					</tr>
					<tr>
						<th scope="row">Anthropic</th>
						<td><code>/v1/messages</code></td>
						<td>{d.compat.anthropic}</td>
					</tr>
					<tr>
						<th scope="row">Ollama</th>
						<td><code>/api/*</code></td>
						<td>{d.compat.ollama}</td>
					</tr>
				</tbody>
			</table>
		</div>
		<Src src={['PLAN §6', lang === 'pl' ? 'raport 03 §3.5' : 'report 03 §3.5']} />
	</section>

	<section class="card token" aria-labelledby="tok-h">
		<h2 id="tok-h" class="h3">{d.tokenTitle}</h2>
		<div class="field">
			<label class="label" for="token">{d.tokenLabel}</label>
			<input id="token" class="input input--mono" readonly value={reveal ? token : masked} aria-describedby="tok-note" />
		</div>
		<div class="cluster">
			<button type="button" class="btn btn--secondary btn--sm" aria-pressed={reveal} onclick={() => (reveal = !reveal)}>
				<Icon name={reveal ? 'eyeOff' : 'eye'} size={16} />{reveal ? d.hide : d.show}
			</button>
			<CopyButton text={token} label={d.tokenTitle} />
			<button type="button" class="btn btn--ghost btn--sm" onclick={regenerate}>
				<Icon name="refresh" size={16} />{d.regen}
			</button>
		</div>
		<p class="small ok-msg" role="status">{regenMsg}</p>
		<p id="tok-note" class="notice notice--prototype"><span class="notice__icon" aria-hidden="true">i</span><span>{d.tokenNote}</span></p>
	</section>
</div>

<section class="block" aria-labelledby="ex-h">
	<h2 id="ex-h" class="overline">{d.examplesTitle}</h2>
	<div class="tabs" role="tablist" aria-label={d.examplesLabel}>
		{#each examples as ex, i (ex.id)}
			<button
				type="button"
				role="tab"
				id="tab-{ex.id}"
				aria-selected={tab === i}
				aria-controls="panel-{ex.id}"
				tabindex={tab === i ? 0 : -1}
				bind:this={tabEls[i]}
				onclick={() => (tab = i)}
				onkeydown={onTabKey}>{ex.label}</button
			>
		{/each}
	</div>
	{#each examples as ex, i (ex.id)}
		<div role="tabpanel" id="panel-{ex.id}" aria-labelledby="tab-{ex.id}" hidden={tab !== i}>
			<div class="codeblock">
				<div class="codeblock__head"><span>{ex.label}</span><CopyButton text={ex.code} label={ex.label} /></div>
				<!-- svelte-ignore a11y_no_noninteractive_tabindex (scrollable region must be keyboard-reachable, WCAG 2.1.1) -->
				<pre tabindex="0"><code>{ex.code}</code></pre>
			</div>
		</div>
	{/each}
	<p class="small mute">{d.envNote(ENV)}</p>
</section>

<div class="grid">
	<section class="card" aria-labelledby="sec-h">
		<h2 id="sec-h" class="h3">{d.securityTitle}</h2>
		<ul class="sec">
			{#each d.security as s (s)}
				<li><span class="sec-ic"><Icon name="check" size={16} /></span>{s}</li>
			{/each}
		</ul>
		<Src src={lang === 'pl' ? 'raport 03 §3.5; PLAN §6' : 'report 03 §3.5; PLAN §6'} />
	</section>

	<section class="card trusted" aria-labelledby="tr-h">
		<h2 id="tr-h" class="h3">{d.trustedTitle}</h2>
		<form class="tr-form" onsubmit={addHost} novalidate>
			<div class="field">
				<label class="label" for="origin">{d.trustedLabel}</label>
				<input
					id="origin"
					class="input input--mono"
					bind:value={draft}
					placeholder="http://localhost:5173"
					autocomplete="off"
					spellcheck="false"
					aria-invalid={invalid}
					aria-describedby="origin-hint{invalid ? ' origin-err' : ''}"
				/>
				<p id="origin-hint" class="hint">{d.trustedHint}</p>
				{#if invalid}<p id="origin-err" class="error-text">{d.trustedInvalid}</p>{/if}
			</div>
			<button type="submit" class="btn btn--secondary btn--sm"><Icon name="plus" size={16} />{d.trustedAdd}</button>
		</form>
		{#if hosts.length === 0}
			<p class="small mute">{d.trustedEmpty}</p>
		{:else}
			<ul class="hosts">
				{#each hosts as h (h)}
					<li>
						<code>{h}</code>
						<button
							type="button"
							class="icon-btn rm"
							aria-label={d.trustedRemove(h)}
							onclick={() => (hosts = hosts.filter((x) => x !== h))}><Icon name="close" size={14} /></button
						>
					</li>
				{/each}
			</ul>
		{/if}
	</section>
</div>

<section class="block" aria-labelledby="cli-h">
	<h2 id="cli-h" class="overline">{d.cliTitle}</h2>
	<div class="codeblock">
		<div class="codeblock__head"><span>{BRAND.cli}</span><CopyButton text={cliText} label={d.cliTitle} /></div>
		<!-- svelte-ignore a11y_no_noninteractive_tabindex (scrollable region must be keyboard-reachable, WCAG 2.1.1) -->
		<pre tabindex="0"><code>{#each cliRows as [cmd, what] (cmd)}<span class="prompt">$ </span>{cmd}<span class="cm">  # {what}</span>
{/each}</code></pre>
	</div>
	<p class="small mute">{d.cliNote}</p>
</section>

<style>
	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 22rem), 1fr));
		gap: var(--sp-4);
		align-items: start;
	}
	.grid + .block,
	.block + .grid {
		margin-top: var(--sp-6);
	}
	.endpoint,
	.token,
	.trusted {
		display: grid;
		gap: var(--sp-4);
	}
	.ep-row {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		justify-content: space-between;
		gap: var(--sp-3);
		padding: var(--sp-3) var(--sp-4);
		border: 1px solid var(--line);
		border-radius: var(--r-md);
		background: var(--bg-1);
	}
	.ep {
		font-size: var(--fs-md);
		color: var(--accent-ink);
		overflow-wrap: anywhere;
	}
	td code {
		color: var(--text-hi);
		font-size: var(--fs-xs);
	}
	.ok-msg:empty {
		display: none;
	}
	.ok-msg {
		color: var(--ok-ink);
	}
	.block {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		gap: var(--sp-3);
	}
	.cm {
		color: var(--text-mute);
	}
	.sec {
		list-style: none;
		margin: var(--sp-4) 0 0;
		padding: 0;
		display: grid;
		gap: var(--sp-3);
		font-size: var(--fs-sm);
	}
	.sec li {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: var(--sp-2);
	}
	.sec-ic {
		color: var(--ok-ink);
		margin-top: 0.15rem;
	}
	.tr-form {
		display: grid;
		gap: var(--sp-3);
		justify-items: start;
	}
	.tr-form .field {
		width: 100%;
	}
	.hosts {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: var(--sp-2);
	}
	.hosts li {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: var(--sp-2);
		padding: var(--sp-2) var(--sp-2) var(--sp-2) var(--sp-4);
		border: 1px solid var(--line);
		border-radius: var(--r-sm);
		background: var(--bg-1);
	}
	.hosts code {
		overflow-wrap: anywhere;
	}
	.rm {
		width: 2rem;
		height: 2rem;
	}
</style>
