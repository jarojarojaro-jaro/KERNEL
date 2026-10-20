<script lang="ts">
	import VendorPage from '$lib/cards/VendorPage.svelte';

	let { data } = $props();
</script>

<VendorPage vendor={data.vendor} />
