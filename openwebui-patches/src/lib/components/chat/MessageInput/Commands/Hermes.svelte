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
		{ command: '/session', description: 'Show the mapped Hermes session for this chat', group: 'Session', backend: 'Hermes' },
		{ command: '/new', description: 'Clear the mapped Hermes session for this chat', group: 'Session', backend: 'Hermes' },
		{ command: '/resume ', description: 'Attach this chat to an existing Hermes session id', group: 'Session', backend: 'Hermes' },
		{ command: '/gateway status', description: 'Show Hermes gateway status', group: 'Gateway', backend: 'Hermes' },
		{ command: '/gateway restart', description: 'Restart the Hermes gateway service', group: 'Gateway', backend: 'Hermes' },
		{ command: '/sessions list', description: 'List Hermes sessions', group: 'Sessions', backend: 'Hermes' },
		{ command: '/skills list', description: 'List installed Hermes skills', group: 'Knowledge', backend: 'Hermes' },
		{ command: '/cron list', description: 'List Hermes cron jobs', group: 'Automation', backend: 'Hermes' },
		{ command: '/config', description: 'Show Hermes config summary', group: 'Ops', backend: 'Hermes' },
		{ command: '/doctor', description: 'Run Hermes diagnostics', group: 'Ops', backend: 'Hermes' },
		{ command: '/memory --help', description: 'Show Hermes memory CLI help', group: 'Memory', backend: 'Hermes' },
		{ command: '/hermes ', description: 'Run arbitrary non-interactive Hermes CLI args', group: 'Advanced', backend: 'Hermes' }
	];

	$: {
		const q = query.toLowerCase();
		filteredItems = items.filter((item) => {
			return (
				item.command.toLowerCase().includes(q) ||
				item.description.toLowerCase().includes(q) ||
				item.group.toLowerCase().includes(q)
			);
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

<div class="px-3 py-2 border-b border-gray-100 dark:border-gray-800">
	<div class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
		<Terminal className="size-3" />
		<span class="font-semibold uppercase tracking-wide">Hermes Commands</span>
		<span class="rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 px-2 py-0.5">Backend: Hermes</span>
	</div>
	<div class="mt-1 text-[11px] text-gray-500 dark:text-gray-400">
		Run gateway/session/admin actions inline. Follow-up chat continues on the mapped Hermes session.
	</div>
</div>

{#if filteredItems.length > 0}
	<div class="space-y-1 scrollbar-hidden max-h-96 overflow-y-auto">
		{#each filteredItems as item, idx}
			<Tooltip content={item.description} placement="top-start">
				<button
					class="px-3 py-2 rounded-xl w-full text-left border {idx === selectedIdx
						? 'bg-gray-50 dark:bg-gray-800 selected-command-option-button border-blue-200 dark:border-blue-800'
						: 'border-transparent hover:border-gray-200 dark:hover:border-gray-700'}"
					type="button"
					on:click={() => onSelect({ type: 'hermes-command', data: item })}
					on:mousemove={() => {
						selectedIdx = idx;
					}}
					data-selected={idx === selectedIdx}
				>
					<div class="flex items-center justify-between gap-3">
						<div class="font-medium text-black dark:text-gray-100">{item.command}</div>
						<div class="flex items-center gap-1 text-[10px] uppercase tracking-wide">
							<span class="rounded-full bg-gray-100 dark:bg-gray-900 px-2 py-0.5 text-gray-600 dark:text-gray-300">{item.group}</span>
							<span class="rounded-full bg-blue-100 dark:bg-blue-900/40 px-2 py-0.5 text-blue-700 dark:text-blue-300">{item.backend}</span>
						</div>
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 line-clamp-2 mt-1">{item.description}</div>
				</button>
			</Tooltip>
		{/each}
	</div>
{:else}
	<div class="px-3 py-3 text-sm text-gray-500">{$i18n.t('No matching Hermes commands')}</div>
{/if}
