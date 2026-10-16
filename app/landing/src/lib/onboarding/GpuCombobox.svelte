<script lang="ts">
	import { GPUS, type Gpu } from '$lib/estimator';

	let {
		value = $bindable<Gpu | null>(null),
		label,
		placeholder,
		hint,
		none,
		error = null
	}: { value?: Gpu | null; label: string; placeholder: string; hint: string; none: string; error?: string | null } = $props();

	let query = $state('');
	let open = $state(false);
	let active = $state(0);
	let input: HTMLInputElement | undefined = $state();

	$effect(() => {
		// Keep the text in sync when the value is set from outside (scan code).
		if (value && value.name !== query) query = value.name;
	});

	const results = $derived.by(() => {
		const q = query.toLowerCase().replace(/geforce|radeon|nvidia|amd/g, '').trim();
		if (!q) return GPUS.slice(0, 12);
		const parts = q.split(/\s+/);
		return GPUS.filter((g) => parts.every((p) => g.name.toLowerCase().includes(p) || g.id.includes(p))).slice(0, 12);
	});

	function choose(g: Gpu) {
		value = g;
		query = g.name;
		open = false;
	}

	function onKey(e: KeyboardEvent) {
		if (e.key === 'ArrowDown') {
			e.preventDefault();
			if (!open) open = true;
			else active = Math.min(active + 1, results.length - 1);
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			active = Math.max(active - 1, 0);
		} else if (e.key === 'Enter' && open && results[active]) {
			e.preventDefault();
			choose(results[active]);
		} else if (e.key === 'Escape') {
			open = false;
		}
	}

	const tag = (g: Gpu) => (g.unified ? 'unified' : g.cpuOnly ? 'CPU' : `${g.vram} GB`);
</script>

<div class="field combo">
	<label for="gpu-input">{label}</label>
	<div class="wrap">
		<input
			bind:this={input}
			id="gpu-input"
			class="input"
			type="text"
			role="combobox"
			autocomplete="off"
			spellcheck="false"
			aria-autocomplete="list"
			aria-expanded={open}
			aria-controls="gpu-list"
			aria-activedescendant={open && results[active] ? `gpu-opt-${results[active].id}` : undefined}
			aria-describedby="gpu-hint{error ? ' gpu-err' : ''}"
			aria-invalid={!!error}
			{placeholder}
			bind:value={query}
			oninput={() => {
				open = true;
				active = 0;
				if (value && value.name !== query) value = null;
			}}
			onfocus={() => (open = true)}
			onblur={() => setTimeout(() => (open = false), 120)}
			onkeydown={onKey}
		/>
		{#if open}
			<ul id="gpu-list" role="listbox" aria-label={label}>
				{#each results as g, i (g.id)}
					<li
						id="gpu-opt-{g.id}"
						role="option"
						aria-selected={i === active}
						class:active={i === active}
						onmousedown={(e) => {
							e.preventDefault();
							choose(g);
						}}
					>
						<span class="n">{g.name}</span>
						<span class="m num">{tag(g)}</span>
						{#if g.lab === 'measured'}<span class="badge badge--measured">lab</span>{/if}
					</li>
				{:else}
					<li class="empty" role="option" aria-selected="false" aria-disabled="true">{none}</li>
				{/each}
			</ul>
		{/if}
	</div>
	<span class="hint" id="gpu-hint">{hint}</span>
	{#if error}<span class="error-text" id="gpu-err">{error}</span>{/if}
</div>

<style>
	.wrap {
		position: relative;
	}
	ul {
		position: absolute;
		z-index: 20;
		inset: calc(100% + 4px) 0 auto 0;
		margin: 0;
		padding: var(--sp-1);
		list-style: none;
		max-height: 18rem;
		overflow: auto;
		background: var(--bg-2);
		border: 1px solid var(--line-strong);
		border-radius: var(--r-md);
		box-shadow: var(--shadow-2);
	}
	li {
		display: flex;
		align-items: center;
		gap: var(--sp-3);
		padding: 0.55rem 0.7rem;
		border-radius: var(--r-sm);
		cursor: pointer;
		font-size: var(--fs-sm);
	}
	li.active {
		background: var(--bg-3);
		color: var(--text-hi);
		box-shadow: inset 2px 0 0 var(--text-hi);
	}
	.n {
		flex: 1;
	}
	.m {
		color: var(--text-mute);
		font-size: var(--fs-xs);
	}
	.empty {
		color: var(--text-mute);
		cursor: default;
	}
</style>
