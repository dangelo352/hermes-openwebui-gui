<script lang="ts">
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Terminal from '$lib/components/icons/Terminal.svelte';
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	export let query = '';
	export let onSelect = (e) => {};
	export let filteredItems = [];

	let selectedIdx = 0;

	const items = [
		{ command: '/session', description: 'Show the mapped Hermes session for this chat' },
		{ command: '/new', description: 'Clear the mapped Hermes session for this chat' },
		{ command: '/resume ', description: 'Attach this chat to an existing Hermes session id' },
		{ command: '/gateway status', description: 'Show Hermes gateway status' },
		{ command: '/gateway restart', description: 'Restart the Hermes gateway service' },
		{ command: '/sessions list', description: 'List Hermes sessions' },
		{ command: '/skills list', description: 'List installed Hermes skills' },
		{ command: '/cron list', description: 'List Hermes cron jobs' },
		{ command: '/config', description: 'Show Hermes config summary' },
		{ command: '/doctor', description: 'Run Hermes diagnostics' },
		{ command: '/memory --help', description: 'Show Hermes memory CLI help' },
		{ command: '/hermes ', description: 'Run arbitrary non-interactive Hermes CLI args' }
	];

	$: {
		const q = query.toLowerCase();
		filteredItems = items.filter((item) => {
			return item.command.toLowerCase().includes(q) || item.description.toLowerCase().includes(q);
		});
		selectedIdx = Math.min(selectedIdx, Math.max(filteredItems.length - 1, 0));
	}

	export const selectUp = () => {
		selectedIdx = Math.max(0, selectedIdx - 1);
	};

	export const selectDown = () => {
		selectedIdx = Math.min(selectedIdx + 1, filteredItems.length - 1);
	};

	export const select = async () => {
		const item = filteredItems[selectedIdx];
		if (item) {
			onSelect({ type: 'hermes-command', data: item });
		}
	};
</script>

<div class="px-2 text-xs text-gray-500 py-1 flex items-center gap-1">
	<Terminal className="size-3" />
	<span>Hermes Commands</span>
</div>

{#if filteredItems.length > 0}
	<div class="space-y-0.5 scrollbar-hidden">
		{#each filteredItems as item, idx}
			<Tooltip content={item.description} placement="top-start">
				<button
					class="px-3 py-2 rounded-xl w-full text-left {idx === selectedIdx
						? 'bg-gray-50 dark:bg-gray-800 selected-command-option-button'
						: ''}"
					type="button"
					on:click={() => onSelect({ type: 'hermes-command', data: item })}
					on:mousemove={() => {
						selectedIdx = idx;
					}}
					data-selected={idx === selectedIdx}
				>
					<div class="font-medium text-black dark:text-gray-100">{item.command}</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 line-clamp-2">{item.description}</div>
				</button>
			</Tooltip>
		{/each}
	</div>
{:else}
	<div class="px-3 py-2 text-sm text-gray-500">{$i18n.t('No matching Hermes commands')}</div>
{/if}
