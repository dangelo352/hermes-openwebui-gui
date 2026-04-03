<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');
	const ADAPTER_BASE = 'http://127.0.0.1:8001';
	const API_KEY = 'hermes-local';

	type CommandResult = {
		name: string;
		content: string;
	};

	let loading = true;
	let busy = false;
	let health: any = null;
	let sessionMap: any = null;
	let commandInput = '/gateway status';
	let results: CommandResult[] = [];

	const quickActions = [
		{ label: 'Gateway Status', command: '/gateway status', section: 'Overview' },
		{ label: 'Gateway Restart', command: '/gateway restart', section: 'Overview' },
		{ label: 'Gateway Setup', command: '/gateway setup', section: 'Channels' },
		{ label: 'Sessions List', command: '/sessions list', section: 'Sessions' },
		{ label: 'Cron List', command: '/cron list', section: 'Automation' },
		{ label: 'Skills List', command: '/skills list', section: 'Agent' },
		{ label: 'Config', command: '/config', section: 'Config' },
		{ label: 'Doctor', command: '/doctor', section: 'Config' }
	];

	async function fetchJson(path: string) {
		const res = await fetch(`${ADAPTER_BASE}${path}`, {
			headers: { Authorization: `Bearer ${API_KEY}` }
		});
		if (!res.ok) throw new Error(await res.text());
		return await res.json();
	}

	async function runCommand(command: string, label?: string) {
		busy = true;
		try {
			const res = await fetch(`${ADAPTER_BASE}/v1/chat/completions`, {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${API_KEY}`,
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					model: 'hermes-gui',
					messages: [{ role: 'user', content: command }],
					stream: false
				})
			});
			if (!res.ok) {
				throw new Error(await res.text());
			}
			const data = await res.json();
			results = [
				{ name: label ?? command, content: data?.choices?.[0]?.message?.content ?? 'No response' },
				...results
			].slice(0, 10);
			if (command.includes('/gateway') || command.includes('/session')) {
				await refresh();
			}
		} catch (err) {
			toast.error(`${err}`);
		} finally {
			busy = false;
		}
	}

	async function refresh() {
		loading = true;
		try {
			const [healthRes, sessionRes] = await Promise.all([
				fetchJson('/health'),
				fetchJson('/v1/session-map')
			]);
			health = healthRes;
			sessionMap = sessionRes?.data ?? {};
		} catch (err) {
			toast.error(`${err}`);
		} finally {
			loading = false;
		}
	}

	onMount(async () => {
		await refresh();
	});
</script>

<svelte:head>
	<title>{$i18n.t('Gateway')} • Hermes Workspace</title>
</svelte:head>

{#if loading}
	<div class="flex items-center justify-center h-full py-20">
		<Spinner className="size-6" />
	</div>
{:else}
	<div class="max-w-7xl mx-auto py-4 md:py-6 space-y-6">
		<div class="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
			<div>
				<div class="text-2xl font-semibold text-gray-900 dark:text-gray-100">Hermes Gateway</div>
				<div class="text-sm text-gray-500 dark:text-gray-400 mt-1">
					Workspace control surface for Hermes gateway, sessions, config, and operator actions.
				</div>
			</div>
			<div class="flex gap-2">
				<button class="px-4 py-2 rounded-xl bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-sm" on:click={refresh}>Refresh</button>
				<button class="px-4 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm" on:click={() => runCommand('/gateway status', 'Gateway Status')}>Check Status</button>
			</div>
		</div>

		<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
			<div class="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
				<div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Adapter</div>
				<div class="mt-2 text-lg font-semibold text-gray-900 dark:text-gray-100">{health?.status ?? 'unknown'}</div>
				<div class="mt-1 text-sm text-gray-500 dark:text-gray-400">Model: {health?.model ?? 'unknown'}</div>
			</div>
			<div class="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
				<div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Mapped Chats</div>
				<div class="mt-2 text-lg font-semibold text-gray-900 dark:text-gray-100">{Object.keys(sessionMap ?? {}).length}</div>
				<div class="mt-1 text-sm text-gray-500 dark:text-gray-400">Open WebUI chat → Hermes session mappings</div>
			</div>
			<div class="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
				<div class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Recommended Repair</div>
				<div class="mt-2 text-sm text-gray-700 dark:text-gray-200 font-mono">scripts/fix_all.sh</div>
				<div class="mt-1 text-sm text-gray-500 dark:text-gray-400">or scripts\fix_all.bat on Windows</div>
			</div>
		</div>

		<div class="grid grid-cols-1 xl:grid-cols-[1.1fr,0.9fr] gap-6">
			<div class="space-y-6">
				<div class="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
					<div class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">Quick Actions</div>
					<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
						{#each quickActions as action}
							<button
								class="text-left rounded-2xl border border-gray-200 dark:border-gray-800 hover:border-blue-400 dark:hover:border-blue-700 p-4 transition"
								on:click={() => runCommand(action.command, action.label)}
							>
								<div class="flex items-center justify-between gap-3">
									<div class="font-medium text-gray-900 dark:text-gray-100">{action.label}</div>
									<div class="text-[10px] uppercase tracking-wide rounded-full px-2 py-1 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300">{action.section}</div>
								</div>
								<div class="mt-2 text-xs text-gray-500 dark:text-gray-400 font-mono">{action.command}</div>
							</button>
						{/each}
					</div>
				</div>

				<div class="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
					<div class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">Channels & Setup</div>
					<div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm text-gray-600 dark:text-gray-300">
						<div class="rounded-xl bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-800 p-4">
							<div class="font-medium text-gray-900 dark:text-gray-100 mb-2">Platform setup</div>
							<div>Use <code>/gateway setup</code> to configure Telegram, Discord, Slack, WhatsApp, Signal, Email, Matrix, and more.</div>
						</div>
						<div class="rounded-xl bg-gray-50 dark:bg-gray-950 border border-gray-200 dark:border-gray-800 p-4">
							<div class="font-medium text-gray-900 dark:text-gray-100 mb-2">Service control</div>
							<div>Use the Gateway actions above for status, restart, start, and stop from a GUI card instead of raw CLI.</div>
						</div>
					</div>
				</div>

				<div class="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
					<div class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">Run Custom Hermes Command</div>
					<div class="flex flex-col gap-3 md:flex-row">
						<input bind:value={commandInput} class="flex-1 rounded-xl border border-gray-200 dark:border-gray-800 bg-transparent px-4 py-3 text-sm" placeholder="/gateway status" />
						<button class="px-4 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm disabled:opacity-50" disabled={busy} on:click={() => runCommand(commandInput, 'Custom Command')}>
							{busy ? 'Running…' : 'Run'}
						</button>
					</div>
				</div>
			</div>

			<div class="space-y-6">
				<div class="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
					<div class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">Mapped Sessions</div>
					{#if Object.keys(sessionMap ?? {}).length === 0}
						<div class="text-sm text-gray-500 dark:text-gray-400">No Open WebUI chats are currently mapped to Hermes sessions.</div>
					{:else}
						<div class="space-y-3 max-h-80 overflow-y-auto">
							{#each Object.entries(sessionMap) as [key, value]}
								<div class="rounded-xl border border-gray-200 dark:border-gray-800 p-3 bg-gray-50 dark:bg-gray-950">
									<div class="font-mono text-xs text-gray-500 dark:text-gray-400">{key}</div>
									<div class="mt-1 text-sm text-gray-900 dark:text-gray-100 font-medium">{value.session_id}</div>
									<div class="mt-1 text-xs text-gray-500 dark:text-gray-400">Updated: {new Date(value.updated_at * 1000).toLocaleString()}</div>
								</div>
							{/each}
						</div>
					{/if}
				</div>

				<div class="rounded-2xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-4">
					<div class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">Recent Command Output</div>
					{#if results.length === 0}
						<div class="text-sm text-gray-500 dark:text-gray-400">Run a quick action or custom command to populate this panel.</div>
					{:else}
						<div class="space-y-4 max-h-[40rem] overflow-y-auto">
							{#each results as result}
								<div class="rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
									<div class="px-4 py-2 text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-950">{result.name}</div>
									<div class="p-4">
										<pre class="whitespace-pre-wrap break-words text-xs md:text-sm text-gray-800 dark:text-gray-100 font-mono">{result.content}</pre>
									</div>
								</div>
							{/each}
						</div>
					{/if}
				</div>
			</div>
		</div>
	</div>
{/if}
