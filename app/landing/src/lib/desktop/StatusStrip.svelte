<script lang="ts">
	import { BRAND } from '$lib/brand';
	import { currentLang } from '$lib/i18n';
	import { T } from './i18n';
	import { ACTIVE } from './demo';

	const t = $derived(T[currentLang()]);
</script>

<footer class="status" aria-label={t.shell.statusLabel}>
	<dl>
		<div class="item">
			<dt>{t.shell.backend}</dt>
			<dd>{ACTIVE.backend}</dd>
		</div>
		<div class="item">
			<dt>{t.shell.gpu}</dt>
			<dd class="ok"><span class="led" aria-hidden="true"></span>{t.shell.gpuOk}</dd>
		</div>
		<div class="item">
			<dt>{t.shell.model}</dt>
			<dd>{ACTIVE.model} {ACTIVE.quant}</dd>
		</div>
		<div class="item">
			<dt>{t.shell.api}</dt>
			<dd>127.0.0.1:{BRAND.apiPort}</dd>
		</div>
		<div class="item proto">
			<dt>{t.shell.engine}</dt>
			<dd>{t.shell.engineProto}</dd>
		</div>
	</dl>
	<p class="protoline">{t.shell.protoLong}</p>
</footer>

<style>
	.status {
		border-top: 1px solid var(--line);
		background: var(--bg-1);
		font-family: var(--font-mono);
		font-size: var(--fs-xs);
	}
	dl {
		display: flex;
		flex-wrap: wrap;
		margin: 0;
	}
	.item {
		display: flex;
		align-items: center;
		gap: var(--sp-2);
		padding: 0.45rem var(--sp-4);
		border-right: 1px solid var(--line);
		white-space: nowrap;
	}
	.proto {
		margin-left: auto;
		border-right: 0;
		border-left: 1px solid var(--line);
	}
	dt {
		font-size: var(--fs-2xs);
		letter-spacing: var(--tracking-overline);
		text-transform: uppercase;
		color: var(--text-mute);
	}
	dd {
		margin: 0;
		color: var(--text-hi);
		display: inline-flex;
		align-items: center;
		gap: var(--sp-2);
	}
	.ok {
		color: var(--ok-ink);
	}
	.led {
		width: 0.5rem;
		height: 0.5rem;
		border-radius: 50%;
		background: var(--ok);
		box-shadow: 0 0 0 3px var(--ok-soft);
	}
	.proto dd {
		color: var(--text-mute);
	}
	.protoline {
		display: none;
		padding: var(--sp-2) var(--sp-4);
		border-top: 1px solid var(--line);
		color: var(--info-ink);
	}
	@media (max-width: 1180px) {
		.protoline {
			display: block;
		}
	}
	@media (max-width: 720px) {
		.item {
			flex: 1 1 50%;
			border-bottom: 1px solid var(--line);
			white-space: normal;
		}
		.proto {
			margin-left: 0;
			border-left: 0;
		}
	}
</style>
