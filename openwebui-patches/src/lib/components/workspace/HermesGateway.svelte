<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { WEBUI_NAME } from '$lib/stores';
	import { getHermesOverview, runHermesCommand } from '$lib/apis/hermes';
	import Search from '../icons/Search.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Badge from '../common/Badge.svelte';

	const i18n = getContext('i18n');

	type CommandResult = {
		command?: string;
		mode?: string;
		rendered?: string;
		stdout?: string;
		stderr?: string;
		exit_code?: number;
	};

	let loaded = false;
	let loading = false;
	let runningCommand = false;
	let overview: any = null;
	let activeTab = 'overview';
	let commandInput = '/gateway status';
	let commandResult: CommandResult | null = null;
	let channelQuery = '';

	const refresh = async () => {
		loading = true;
		try {
			overview = await getHermesOverview();
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			loading = false;
			loaded = true;
		}
	};

	const runCommand = async (command: string) => {
		runningCommand = true;
		commandResult = null;
		try {
			commandResult = await runHermesCommand(command);
			if (command.includes('restart') || command.includes('start') || command.includes('stop') || command.includes('setup')) {
				await refresh();
			}
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			runningCommand = false;
		}
	};

	const quickActions = [
		{ label: 'Gateway Status', command: '/gateway status' },
		{ label: 'Gateway Restart', command: '/gateway restart' },
		{ label: 'Doctor', command: '/doctor' },
		{ label: 'Sessions List', command: '/sessions list' },
		{ label: 'Cron List', command: '/cron list' },
		{ label: 'Config', command: '/config' }
	];

	const filteredChannels = () => {
		const channels = overview?.supported_channels ?? [];
		const q = channelQuery.trim().toLowerCase();
		if (!q) return channels;
		return channels.filter((channel) => channel.name.toLowerCase().includes(q) || channel.id.toLowerCase().includes(q));
	};

	const channelConnected = (channelId: string) => {
		const text = `${overview?.gateway?.stdout ?? ''}\n${overview?.gateway?.stderr ?? ''}`.toLowerCase();
		return text.includes(channelId.toLowerCase());
	};

	onMount(async () => {
		await refresh();
	});
</script>

<svelte:head>
	<title>Hermes Gateway • { $WEBUI_NAME }</title>
</svelte:head>

{#if loaded}
	<div class="flex flex-col gap-4 px-1 mt-1.5 mb-3">
		<div class="flex justify-between items-center gap-3 flex-wrap">
			<div class="flex items-center md:self-center text-xl font-medium px-0.5 gap-2 shrink-0">
				<div>Hermes Gateway</div>
				{#if overview}
					<div class="text-lg font-medium text-gray-500 dark:text-gray-500">{overview.session_map_count}</div>
				{/if}
			</div>

			<div class="flex items-center gap-2 flex-wrap">
				<button class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-200 transition" on:click={refresh} disabled={loading}>
					<div class="self-center font-medium line-clamp-1">Refresh</div>
				</button>
				{#each quickActions as action}
					<button class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black transition" on:click={() => runCommand(action.command)} disabled={runningCommand}>
						<div class="self-center font-medium line-clamp-1">{action.label}</div>
					</button>
				{/each}
			</div>
		</div>

		<div class="flex gap-2 text-sm font-medium overflow-x-auto scrollbar-none">
			{#each ['overview', 'channels', 'ops', 'config'] as tab}
				<button class="px-3 py-1.5 rounded-full transition {activeTab === tab ? 'bg-black text-white dark:bg-white dark:text-black' : 'bg-gray-50 dark:bg-gray-850 text-gray-600 dark:text-gray-300'}" on:click={() => (activeTab = tab)}>
					{tab === 'ops' ? 'Operations' : tab.charAt(0).toUpperCase() + tab.slice(1)}
				</button>
			{/each}
		</div>

		{#if loading && !overview}
			<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-6 flex items-center justify-center">
				<Spinner className="size-5" />
			</div>
		{:else if overview}
			{#if activeTab === 'overview'}
				<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
					<div class="rounded-2xl border border-gray-100 dark:border-gray-850 bg-white dark:bg-black/20 p-4">
						<div class="text-xs uppercase tracking-wide text-gray-500">Adapter</div>
						<div class="mt-2 text-lg font-semibold">{overview.health?.status ?? 'unknown'}</div>
						<div class="mt-1 text-sm text-gray-500 break-all">{overview.health?.model}</div>
					</div>
					<div class="rounded-2xl border border-gray-100 dark:border-gray-850 bg-white dark:bg-black/20 p-4">
						<div class="text-xs uppercase tracking-wide text-gray-500">Gateway</div>
						<div class="mt-2 text-lg font-semibold">{overview.gateway?.exit_code === 0 ? 'Running' : 'Needs Attention'}</div>
						<div class="mt-1 text-sm text-gray-500">Exit code: {overview.gateway?.exit_code}</div>
					</div>
					<div class="rounded-2xl border border-gray-100 dark:border-gray-850 bg-white dark:bg-black/20 p-4">
						<div class="text-xs uppercase tracking-wide text-gray-500">Session Map</div>
						<div class="mt-2 text-lg font-semibold">{overview.session_map_count}</div>
						<div class="mt-1 text-sm text-gray-500">Mapped Open WebUI chats</div>
					</div>
					<div class="rounded-2xl border border-gray-100 dark:border-gray-850 bg-white dark:bg-black/20 p-4">
						<div class="text-xs uppercase tracking-wide text-gray-500">Diagnostics</div>
						<div class="mt-2 text-lg font-semibold">{overview.doctor?.exit_code === 0 ? 'Healthy' : 'Check Doctor Output'}</div>
						<div class="mt-1 text-sm text-gray-500">Hermes doctor summary</div>
					</div>
				</div>

				<div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
					<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4">
						<div class="flex items-center justify-between gap-2">
							<div class="text-sm font-semibold">Gateway Status</div>
							<Badge>{overview.gateway?.exit_code === 0 ? 'online' : 'degraded'}</Badge>
						</div>
						<pre class="mt-3 text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900 rounded-xl p-3 overflow-x-auto">{overview.gateway?.stdout || overview.gateway?.stderr || overview.gateway?.rendered}</pre>
					</div>
					<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4">
						<div class="text-sm font-semibold">Session Map</div>
						<pre class="mt-3 text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900 rounded-xl p-3 overflow-x-auto">{JSON.stringify(overview.session_map, null, 2)}</pre>
					</div>
				</div>
			{:else if activeTab === 'channels'}
				<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-3 flex items-center gap-2">
					<div class="text-gray-400"><Search className="size-3.5" /></div>
					<input class="w-full text-sm py-1 rounded-r-xl outline-hidden bg-transparent" bind:value={channelQuery} placeholder="Search channels" />
				</div>
				<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
					{#each filteredChannels() as channel}
						<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4 bg-white dark:bg-black/20">
							<div class="flex items-center justify-between gap-3">
								<div>
									<div class="font-semibold">{channel.name}</div>
									<div class="text-xs text-gray-500 mt-1">Setup via `hermes {channel.setup_command}`</div>
								</div>
								<Badge>{channelConnected(channel.id) ? 'detected' : 'available'}</Badge>
							</div>
							<div class="mt-3 text-xs text-gray-500">Docs</div>
							<a class="mt-1 text-sm underline break-all" href={`https://hermes-agent.nousresearch.com/docs/user-guide/messaging/${channel.docs_slug}`} target="_blank" rel="noreferrer">Open {channel.name} docs</a>
							<div class="mt-3 flex gap-2 flex-wrap">
								<button class="px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 text-xs transition" on:click={() => runCommand('/gateway status')}>Status</button>
								<button class="px-3 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black text-xs transition" on:click={() => runCommand('/gateway setup')}>Setup Flow</button>
							</div>
						</div>
					{/each}
				</div>
			{:else if activeTab === 'ops'}
				<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4">
					<div class="text-sm font-semibold">Run Hermes Command</div>
					<div class="mt-3 flex gap-2 flex-wrap">
						<input class="flex-1 min-w-[280px] rounded-xl border border-gray-100 dark:border-gray-800 bg-transparent px-3 py-2 text-sm outline-hidden" bind:value={commandInput} placeholder="/gateway status" />
						<button class="px-4 py-2 rounded-xl bg-black text-white dark:bg-white dark:text-black text-sm font-medium" on:click={() => runCommand(commandInput)} disabled={runningCommand}>Run</button>
					</div>
					{#if runningCommand}
						<div class="mt-3 flex items-center gap-2 text-sm text-gray-500"><Spinner className="size-4" /> Running...</div>
					{/if}
					{#if commandResult}
						<pre class="mt-4 text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900 rounded-xl p-3 overflow-x-auto">{commandResult.rendered || commandResult.stdout || commandResult.stderr}</pre>
					{/if}
				</div>
				<div class="grid grid-cols-1 xl:grid-cols-2 gap-4 mt-4">
					<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4">
						<div class="text-sm font-semibold">Sessions</div>
						<pre class="mt-3 text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900 rounded-xl p-3 overflow-x-auto">{overview.sessions?.stdout || overview.sessions?.rendered}</pre>
					</div>
					<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4">
						<div class="text-sm font-semibold">Cron Jobs</div>
						<pre class="mt-3 text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900 rounded-xl p-3 overflow-x-auto">{overview.cron?.stdout || overview.cron?.rendered}</pre>
					</div>
				</div>
			{:else if activeTab === 'config'}
				<div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
					<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4">
						<div class="text-sm font-semibold">Hermes Config</div>
						<pre class="mt-3 text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900 rounded-xl p-3 overflow-x-auto">{overview.config?.stdout || overview.config?.rendered}</pre>
					</div>
					<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4">
						<div class="text-sm font-semibold">Doctor Output</div>
						<pre class="mt-3 text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900 rounded-xl p-3 overflow-x-auto">{overview.doctor?.stdout || overview.doctor?.stderr || overview.doctor?.rendered}</pre>
					</div>
				</div>
			{/if}
		{/if}
	</div>
{/if}
