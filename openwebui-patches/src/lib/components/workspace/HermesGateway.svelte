<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { WEBUI_NAME } from '$lib/stores';
	import {
		getHermesOverview,
		runHermesCommand,
		getHermesConfigFiles,
		updateHermesEnvKey,
		updateHermesConfigPath,
		getHermesUpdateRebuildStatus,
		triggerHermesUpdateRebuild
	} from '$lib/apis/hermes';
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

	type ConfigFiles = {
		env: { path: string; raw: string; values: Record<string, string>; masked: Record<string, string> };
		config: { path: string; raw: string; values: Record<string, any> };
		channel_directory: Record<string, any>;
		gateway_log_tail: string;
	};

	const tabs = ['overview', 'channels', 'skills', 'ops', 'access', 'profiles', 'config'];
	const channelDocsBase = 'https://hermes-agent.nousresearch.com/docs/user-guide/messaging/';

	const channelDefinitions = [
		{
			id: 'discord',
			name: 'Discord',
			docsSlug: 'discord',
			envKeys: ['DISCORD_BOT_TOKEN', 'DISCORD_ALLOWED_USERS', 'DISCORD_HOME_CHANNEL', 'DISCORD_HOME_CHANNEL_NAME'],
			configPaths: ['platforms.discord.require_mention', 'platforms.discord.free_response_channels', 'platforms.discord.auto_thread', 'platforms.discord.reactions']
		},
		{
			id: 'telegram',
			name: 'Telegram',
			docsSlug: 'telegram',
			envKeys: ['TELEGRAM_BOT_TOKEN', 'TELEGRAM_ALLOWED_USERS', 'TELEGRAM_HOME_CHANNEL', 'TELEGRAM_HOME_CHANNEL_NAME'],
			configPaths: ['platforms.telegram.reply_to_mode', 'platforms.telegram.require_mention', 'platforms.telegram.free_response_chats']
		},
		{
			id: 'slack',
			name: 'Slack',
			docsSlug: 'slack',
			envKeys: ['SLACK_BOT_TOKEN', 'SLACK_APP_TOKEN', 'SLACK_ALLOWED_USERS', 'SLACK_HOME_CHANNEL', 'SLACK_HOME_CHANNEL_NAME'],
			configPaths: []
		},
		{
			id: 'whatsapp',
			name: 'WhatsApp',
			docsSlug: 'whatsapp',
			envKeys: ['WHATSAPP_ENABLED', 'WHATSAPP_MODE', 'WHATSAPP_ALLOWED_USERS'],
			configPaths: []
		},
		{
			id: 'signal',
			name: 'Signal',
			docsSlug: 'signal',
			envKeys: ['SIGNAL_HTTP_URL', 'SIGNAL_ACCOUNT', 'SIGNAL_ALLOWED_USERS', 'SIGNAL_GROUP_ALLOWED_USERS', 'SIGNAL_HOME_CHANNEL'],
			configPaths: ['platforms.signal.ignore_stories']
		},
		{
			id: 'matrix',
			name: 'Matrix',
			docsSlug: 'matrix',
			envKeys: ['MATRIX_HOMESERVER', 'MATRIX_ACCESS_TOKEN', 'MATRIX_USER_ID', 'MATRIX_PASSWORD', 'MATRIX_ALLOWED_USERS', 'MATRIX_HOME_ROOM'],
			configPaths: ['platforms.matrix.encryption']
		},
		{
			id: 'mattermost',
			name: 'Mattermost',
			docsSlug: 'mattermost',
			envKeys: ['MATTERMOST_URL', 'MATTERMOST_TOKEN', 'MATTERMOST_ALLOWED_USERS', 'MATTERMOST_HOME_CHANNEL'],
			configPaths: ['platforms.mattermost.reply_mode', 'platforms.mattermost.require_mention', 'platforms.mattermost.free_response_channels']
		},
		{
			id: 'email',
			name: 'Email',
			docsSlug: 'email',
			envKeys: ['EMAIL_ADDRESS', 'EMAIL_PASSWORD', 'EMAIL_IMAP_HOST', 'EMAIL_IMAP_PORT', 'EMAIL_SMTP_HOST', 'EMAIL_SMTP_PORT', 'EMAIL_ALLOWED_USERS', 'EMAIL_HOME_ADDRESS'],
			configPaths: []
		}
	];

	let loaded = false;
	let loading = false;
	let runningCommand = false;
	let saving = false;
	let overview: any = null;
	let configFiles: ConfigFiles | null = null;
	let activeTab = 'overview';
	let commandInput = '/gateway status';
	let commandResult: CommandResult | null = null;
	let updateStatus: any = null;
	let channelQuery = '';
	let skillsQuery = '';
	let skillsSource = 'official';
	let skillsLimit = 24;
	let skillsResult: CommandResult | null = null;
	let installIdentifier = '';
	let skillsTab = 'registry';
	let selectedChannel = 'discord';
	let configView = 'overview';
	let configExpandAll = false;
	let channelExpandAll = false;

	const quickActions = [
		{ label: 'Gateway Status', command: '/gateway status' },
		{ label: 'Gateway Restart', command: '/gateway restart' },
		{ label: 'Doctor', command: '/doctor' },
		{ label: 'Sessions List', command: '/sessions list' },
		{ label: 'Cron List', command: '/cron list' },
		{ label: 'Config', command: '/config' }
	];
	const skillsSources = [
		{ id: 'official', label: 'Official' },
		{ id: 'clawhub', label: 'ClawHub' },
		{ id: 'all', label: 'All' },
		{ id: 'skills-sh', label: 'skills.sh' },
		{ id: 'github', label: 'GitHub' },
		{ id: 'lobehub', label: 'LobeHub' }
	];

	const refresh = async () => {
		loading = true;
		try {
			const [overviewPayload, configPayload, updatePayload] = await Promise.all([getHermesOverview(), getHermesConfigFiles(), getHermesUpdateRebuildStatus()]);
			overview = overviewPayload;
			configFiles = configPayload;
			updateStatus = updatePayload;
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			loading = false;
			loaded = true;
		}
	};

	const runCommand = async (command: string, opts: { refreshAfter?: boolean; target?: 'main' | 'skills' } = {}) => {
		runningCommand = true;
		if ((opts.target ?? 'main') === 'main') commandResult = null;
		if ((opts.target ?? 'main') === 'skills') skillsResult = null;
		try {
			const result = await runHermesCommand(command);
			if ((opts.target ?? 'main') === 'skills') {
				skillsResult = result;
			} else {
				commandResult = result;
			}
			if (opts.refreshAfter ?? /(gateway|profile|webhook|pairing|plugins|tools |auth )/.test(command)) {
				await refresh();
			}
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			runningCommand = false;
		}
	};

	const runSkillsSearch = async () => {
		const query = skillsQuery.trim() || 'calendar';
		await runCommand(`skills search ${JSON.stringify(query)} --source ${skillsSource} --limit ${skillsLimit}`, { target: 'skills', refreshAfter: false });
	};

	const runSkillsBrowse = async () => {
		await runCommand(`skills browse --source ${skillsSource} --page 1 --size ${skillsLimit}`, { target: 'skills', refreshAfter: false });
	};

	const runSkillInspect = async () => {
		if (!installIdentifier.trim()) {
			toast.error('Enter a full skill identifier first');
			return;
		}
		await runCommand(`skills inspect ${installIdentifier.trim()}`, { target: 'skills', refreshAfter: false });
	};

	const runSkillInstall = async () => {
		if (!installIdentifier.trim()) {
			toast.error('Enter a full skill identifier first');
			return;
		}
		await runCommand(`skills install ${installIdentifier.trim()} --yes`, { target: 'skills', refreshAfter: true });
	};

	const startUpdateRebuild = async () => {
		runningCommand = true;
		try {
			updateStatus = await triggerHermesUpdateRebuild(true);
			toast.success('Update + rebuild started. Open WebUI may restart while the image rebuilds.');
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			runningCommand = false;
		}
	};

	const filteredChannels = () => {
		const channels = overview?.supported_channels ?? [];
		const q = channelQuery.trim().toLowerCase();
		if (!q) return channels;
		return channels.filter((channel) => channel.name.toLowerCase().includes(q) || channel.id.toLowerCase().includes(q));
	};

	const channelDetected = (channelId: string) => {
		const text = `${overview?.gateway?.stdout ?? ''}\n${overview?.gateway?.stderr ?? ''}`.toLowerCase();
		return text.includes(channelId.toLowerCase());
	};

	const renderPanel = (result: CommandResult | null, fallback = 'Run a command to populate this panel.') => {
		return result?.rendered || result?.stdout || result?.stderr || fallback;
	};

	const selectedChannelDef = () => channelDefinitions.find((item) => item.id === selectedChannel) ?? channelDefinitions[0];

	const getEnvValue = (key: string) => configFiles?.env?.values?.[key] ?? '';
	const getEnvMaskedValue = (key: string) => configFiles?.env?.masked?.[key] ?? '';

	const getConfigValue = (path: string) => {
		const parts = path.split('.');
		let current: any = configFiles?.config?.values ?? {};
		for (const part of parts) {
			current = current?.[part];
		}
		return current ?? '';
	};

	const saveEnv = async (key: string, value: string) => {
		saving = true;
		try {
			configFiles = await updateHermesEnvKey(key, value);
			toast.success(`Saved ${key}`);
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			saving = false;
		}
	};

	const saveConfig = async (path: string, value: any) => {
		saving = true;
		try {
			configFiles = await updateHermesConfigPath(path, value);
			toast.success(`Saved ${path}`);
		} catch (error) {
			toast.error(`${error}`);
		} finally {
			saving = false;
		}
	};

	const fileLineCount = (text: string) => (text ? text.split(/\r?\n/).filter((line, index, lines) => !(index === lines.length - 1 && line === '')).length : 0);

	const envEntries = () => Object.entries(configFiles?.env?.values ?? {});
	const topLevelConfigEntries = () => Object.entries((configFiles?.config?.values ?? {}) as Record<string, any>);
	const channelDirectoryEntries = () => Object.entries((configFiles?.channel_directory ?? {}) as Record<string, any>);

	const envGroups = () => {
		const groups: Record<string, Array<[string, string]>> = {};
		for (const [key, value] of envEntries()) {
			const prefix = key.includes('_') ? key.split('_')[0] : 'OTHER';
			(groups[prefix] ||= []).push([key, value]);
		}
		return Object.entries(groups).sort((a, b) => a[0].localeCompare(b[0]));
	};

	const markdownFence = (language: string, body: string) => `\`\`\`${language}\n${body || ''}\n\`\`\``;
	const stringifyBlock = (value: any) => (typeof value === 'string' ? value : JSON.stringify(value, null, 2));
	const summarizeValue = (value: any) => {
		if (Array.isArray(value)) return `${value.length} item${value.length === 1 ? '' : 's'}`;
		if (value && typeof value === 'object') return `${Object.keys(value).length} key${Object.keys(value).length === 1 ? '' : 's'}`;
		if (typeof value === 'boolean') return value ? 'true' : 'false';
		if (value === '' || value == null) return 'empty';
		return String(value);
	};

	const visibleEnvValue = (key: string) => getEnvMaskedValue(key) || getEnvValue(key) || 'Not set';
	const configViews = [
		{ id: 'overview', label: 'Overview' },
		{ id: 'config', label: 'config.yaml' },
		{ id: 'env', label: '.env' },
		{ id: 'channels', label: 'channel directory' },
		{ id: 'logs', label: 'gateway log' }
	];

	onMount(async () => {
		await refresh();
	});
</script>

<svelte:head>
	<title>Hermes Gateway • {$WEBUI_NAME}</title>
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
				<button class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-200 transition" on:click={refresh} disabled={loading || saving}>
					<div class="self-center font-medium line-clamp-1">Refresh</div>
				</button>
				{#each quickActions as action}
					<button class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black transition" on:click={() => runCommand(action.command)} disabled={runningCommand || saving}>
						<div class="self-center font-medium line-clamp-1">{action.label}</div>
					</button>
				{/each}
				<button class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-emerald-600 text-white transition disabled:opacity-50" on:click={startUpdateRebuild} disabled={runningCommand || saving || updateStatus?.running}>
					<div class="self-center font-medium line-clamp-1">{updateStatus?.running ? 'Rebuilding…' : 'Update + Rebuild'}</div>
				</button>
			</div>
		</div>

		<div class="flex gap-2 text-sm font-medium overflow-x-auto scrollbar-none">
			{#each tabs as tab}
				<button class="px-3 py-1.5 rounded-full transition {activeTab === tab ? 'bg-black text-white dark:bg-white dark:text-black' : 'bg-gray-50 dark:bg-gray-850 text-gray-600 dark:text-gray-300'}" on:click={() => (activeTab = tab)}>
					{tab.charAt(0).toUpperCase() + tab.slice(1)}
				</button>
			{/each}
		</div>

		{#if loading && !overview}
			<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-6 flex items-center justify-center">
				<Spinner className="size-5" />
			</div>
		{:else if overview}
			{#if activeTab === 'overview'}
				<div class="rounded-3xl border border-gray-100 dark:border-gray-850 bg-gradient-to-br from-white via-white to-gray-50/80 dark:from-black/30 dark:via-black/20 dark:to-gray-950/20 p-5 shadow-sm">
					<div class="flex items-start justify-between gap-4 flex-wrap">
						<div>
							<div class="text-xs uppercase tracking-[0.22em] text-gray-500">Hermes Gateway Control Plane</div>
							<div class="mt-2 text-2xl font-semibold">Professional live gateway operations</div>
							<div class="mt-2 text-sm text-gray-500 max-w-3xl">Status, logs, config files, channel setup, and live Hermes controls in one place. The goal is a real admin console, not a raw command dump.</div>
						</div>
						<div class="rounded-2xl border border-gray-100 dark:border-gray-850 bg-white/80 dark:bg-black/30 px-4 py-3 min-w-[220px]">
							<div class="text-xs uppercase tracking-wide text-gray-500">Current health</div>
							<div class="mt-2 flex items-center gap-2"><span class="inline-block h-2.5 w-2.5 rounded-full {overview.gateway?.exit_code === 0 ? 'bg-emerald-500' : 'bg-amber-500'}"></span><span class="text-lg font-semibold">{overview.gateway?.exit_code === 0 ? 'Gateway online' : 'Needs attention'}</span></div>
							<div class="mt-1 text-sm text-gray-500">Adapter: {overview.health?.status ?? 'unknown'} · Model: {overview.health?.model}</div>
						</div>
						<div class="rounded-2xl border border-gray-100 dark:border-gray-850 bg-white/80 dark:bg-black/30 px-4 py-3 min-w-[220px]">
							<div class="text-xs uppercase tracking-wide text-gray-500">Updater</div>
							<div class="mt-2 flex items-center gap-2"><span class="inline-block h-2.5 w-2.5 rounded-full {updateStatus?.running ? 'bg-sky-500 animate-pulse' : 'bg-gray-400'}"></span><span class="text-lg font-semibold">{updateStatus?.running ? 'Rebuild running' : 'Idle'}</span></div>
							<div class="mt-1 text-sm text-gray-500 font-mono truncate">{updateStatus?.log_path ?? 'state/update-rebuild.log'}</div>
						</div>
					</div>
				</div>

				<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
					<div class="rounded-2xl border border-gray-100 dark:border-gray-850 bg-white dark:bg-black/20 p-4 shadow-sm"><div class="text-xs uppercase tracking-wide text-gray-500">Adapter</div><div class="mt-2 text-lg font-semibold">{overview.health?.status ?? 'unknown'}</div><div class="mt-1 text-sm text-gray-500 break-all">{overview.health?.model}</div></div>
					<div class="rounded-2xl border border-gray-100 dark:border-gray-850 bg-white dark:bg-black/20 p-4 shadow-sm"><div class="text-xs uppercase tracking-wide text-gray-500">Gateway</div><div class="mt-2 text-lg font-semibold">{overview.gateway?.exit_code === 0 ? 'Running' : 'Needs Attention'}</div><div class="mt-1 text-sm text-gray-500">Exit code: {overview.gateway?.exit_code}</div></div>
					<div class="rounded-2xl border border-gray-100 dark:border-gray-850 bg-white dark:bg-black/20 p-4 shadow-sm"><div class="text-xs uppercase tracking-wide text-gray-500">Session Map</div><div class="mt-2 text-lg font-semibold">{overview.session_map_count}</div><div class="mt-1 text-sm text-gray-500">Mapped Open WebUI chats</div></div>
					<div class="rounded-2xl border border-gray-100 dark:border-gray-850 bg-white dark:bg-black/20 p-4 shadow-sm"><div class="text-xs uppercase tracking-wide text-gray-500">Profiles/Auth</div><div class="mt-2 text-lg font-semibold">{overview.profiles?.exit_code === 0 ? 'Ready' : 'Check'}</div><div class="mt-1 text-sm text-gray-500">CLI control plane status</div></div>
				</div>

				<div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
					<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4 bg-white dark:bg-black/20 shadow-sm"><div class="flex items-center justify-between gap-2"><div><div class="text-sm font-semibold">Gateway status</div><div class="text-xs text-gray-500">Structured command output rendered in a terminal-style card.</div></div><Badge>{overview.gateway?.exit_code === 0 ? 'online' : 'degraded'}</Badge></div><pre class="mt-3 text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-950 rounded-2xl p-4 overflow-x-auto border border-gray-100 dark:border-gray-800 font-mono">{overview.gateway?.stdout || overview.gateway?.stderr || overview.gateway?.rendered}</pre></div>
					<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4 bg-white dark:bg-black/20 shadow-sm"><div class="flex items-center justify-between gap-2"><div><div class="text-sm font-semibold">Gateway live log</div><div class="text-xs text-gray-500">Console-style tail view for background activity and diagnostics.</div></div><Badge>{fileLineCount(configFiles?.gateway_log_tail || '')} lines</Badge></div><div class="mt-3 rounded-2xl border border-slate-800 bg-gradient-to-b from-slate-950 to-black text-slate-100 overflow-hidden"><div class="px-4 py-2 border-b border-slate-800 text-[11px] uppercase tracking-[0.18em] text-slate-400">gateway.log</div><pre class="px-4 py-4 text-xs whitespace-pre-wrap break-words overflow-x-auto max-h-[26rem] font-mono">{configFiles?.gateway_log_tail || 'No gateway log output yet.'}</pre></div></div>
				</div>
			{:else if activeTab === 'channels'}
				<div class="grid grid-cols-1 xl:grid-cols-[300px,1fr] gap-4">
					<div class="space-y-3">
						<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-3 flex items-center gap-2"><div class="text-gray-400"><Search className="size-3.5" /></div><input class="w-full text-sm py-1 rounded-r-xl outline-hidden bg-transparent" bind:value={channelQuery} placeholder="Search channels" /></div>
						<div class="space-y-2">
							{#each filteredChannels() as channel}
								<button class="w-full text-left rounded-2xl border border-gray-100 dark:border-gray-850 p-3 bg-white dark:bg-black/20 transition {selectedChannel === channel.id ? 'ring-2 ring-blue-500/60' : ''}" on:click={() => (selectedChannel = channel.id)}>
									<div class="flex items-center justify-between gap-3"><div class="font-semibold">{channel.name}</div><Badge>{channelDetected(channel.id) ? 'detected' : 'available'}</Badge></div>
									<div class="mt-1 text-xs text-gray-500">{channel.id}</div>
								</button>
							{/each}
						</div>
					</div>
					<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4 bg-white dark:bg-black/20">
						<div class="flex items-center justify-between gap-3 flex-wrap">
							<div>
								<div class="text-lg font-semibold">{selectedChannelDef().name}</div>
								<a class="text-sm underline text-gray-500" href={`${channelDocsBase}${selectedChannelDef().docsSlug}`} target="_blank" rel="noreferrer">Open docs</a>
							</div>
							<div class="flex gap-2 flex-wrap">
								<button class="px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 text-xs transition" on:click={() => runCommand('/gateway status')}>Status</button>
								<button class="px-3 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black text-xs transition" on:click={() => runCommand('/gateway setup')}>Setup Wizard</button>
							</div>
						</div>

						<div class="mt-5 grid grid-cols-1 lg:grid-cols-2 gap-4">
							<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4 bg-gradient-to-b from-white to-gray-50/60 dark:from-black/20 dark:to-black/5">
								<div class="flex items-center justify-between gap-3 mb-3">
									<div>
										<div class="text-sm font-semibold">Environment variables</div>
										<div class="text-xs text-gray-500">Organized setup fields for this channel.</div>
									</div>
									<button class="px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 text-xs transition" on:click={() => (channelExpandAll = !channelExpandAll)}>{channelExpandAll ? 'Collapse all' : 'Expand all'}</button>
								</div>
								<div class="space-y-3">
									{#each selectedChannelDef().envKeys as envKey}
										<details class="group rounded-2xl border border-gray-100 dark:border-gray-850 bg-white/90 dark:bg-black/20 overflow-hidden" open={channelExpandAll}>
											<summary class="list-none cursor-pointer px-4 py-3 flex items-center justify-between gap-3">
												<div>
													<div class="text-xs uppercase tracking-wide text-gray-500">{envKey}</div>
													<div class="mt-1 text-sm text-gray-700 dark:text-gray-300 line-clamp-1">{visibleEnvValue(envKey)}</div>
												</div>
												<div class="text-xs text-gray-400 group-open:rotate-180 transition">⌄</div>
											</summary>
											<div class="px-4 pb-4 pt-1 border-t border-gray-100 dark:border-gray-850 bg-gray-50/70 dark:bg-gray-950/30">
												<div class="text-xs text-gray-500 mb-2">Current value preview</div>
												<div class="rounded-xl bg-white dark:bg-black/30 border border-gray-100 dark:border-gray-800 px-3 py-2 text-xs font-mono break-all">{visibleEnvValue(envKey)}</div>
												<input class="mt-3 w-full rounded-xl border border-gray-100 dark:border-gray-800 bg-transparent px-3 py-2 text-sm outline-hidden" value={getEnvValue(envKey)} placeholder={getEnvMaskedValue(envKey)} on:change={(e) => saveEnv(envKey, e.currentTarget.value)} disabled={saving} />
											</div>
										</details>
									{/each}
								</div>
							</div>
							<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4 bg-gradient-to-b from-white to-gray-50/60 dark:from-black/20 dark:to-black/5">
								<div class="text-sm font-semibold mb-1">Structured config paths</div>
								<div class="text-xs text-gray-500 mb-3">Readable per-setting controls instead of a raw YAML wall.</div>
								<div class="space-y-3">
									{#if selectedChannelDef().configPaths.length === 0}
										<div class="rounded-2xl border border-dashed border-gray-200 dark:border-gray-800 px-4 py-6 text-sm text-gray-500 bg-gray-50/70 dark:bg-gray-950/20">No structured config paths defined for this channel yet.</div>
									{/if}
									{#each selectedChannelDef().configPaths as configPath}
										<details class="group rounded-2xl border border-gray-100 dark:border-gray-850 bg-white/90 dark:bg-black/20 overflow-hidden" open={channelExpandAll}>
											<summary class="list-none cursor-pointer px-4 py-3 flex items-center justify-between gap-3">
												<div>
													<div class="text-xs uppercase tracking-wide text-gray-500">{configPath}</div>
													<div class="mt-1 text-sm text-gray-700 dark:text-gray-300">{summarizeValue(getConfigValue(configPath))}</div>
												</div>
												<div class="text-xs text-gray-400 group-open:rotate-180 transition">⌄</div>
											</summary>
											<div class="px-4 pb-4 pt-1 border-t border-gray-100 dark:border-gray-850 bg-gray-50/70 dark:bg-gray-950/30">
												<div class="rounded-xl bg-white dark:bg-black/30 border border-gray-100 dark:border-gray-800 px-3 py-2 text-xs font-mono break-all">{String(getConfigValue(configPath) ?? '') || 'Not set'}</div>
												<input class="mt-3 w-full rounded-xl border border-gray-100 dark:border-gray-800 bg-transparent px-3 py-2 text-sm outline-hidden" value={String(getConfigValue(configPath) ?? '')} on:change={(e) => saveConfig(configPath, e.currentTarget.value)} disabled={saving} />
											</div>
										</details>
									{/each}
								</div>
							</div>
						</div>

						<div class="mt-4 rounded-2xl border border-gray-100 dark:border-gray-850 p-4 bg-white dark:bg-black/20">
							<div class="flex items-center justify-between gap-3 flex-wrap">
								<div>
									<div class="text-sm font-semibold">Discovered channels</div>
									<div class="text-xs text-gray-500">Structured overview plus raw JSON when needed.</div>
								</div>
								<Badge>{channelDirectoryEntries().length} entries</Badge>
							</div>
							<div class="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
								{#each channelDirectoryEntries() as [channelId, value]}
									<div class="rounded-2xl border border-gray-100 dark:border-gray-850 bg-gray-50/70 dark:bg-gray-950/20 p-4">
										<div class="flex items-center justify-between gap-3"><div class="font-semibold">{channelId}</div><Badge>{summarizeValue(value)}</Badge></div>
										<pre class="mt-3 text-xs whitespace-pre-wrap break-words bg-white dark:bg-black/30 rounded-xl p-3 overflow-x-auto border border-gray-100 dark:border-gray-800">{stringifyBlock(value)}</pre>
									</div>
								{/each}
							</div>
						</div>
					</div>
				</div>
			{:else if activeTab === 'skills'}
				<div class="space-y-5">
					<div class="rounded-3xl border border-gray-100 dark:border-gray-850 bg-gradient-to-br from-white via-white to-gray-50/80 dark:from-black/30 dark:via-black/20 dark:to-gray-950/20 p-5 shadow-sm">
						<div class="flex items-start justify-between gap-4 flex-wrap">
							<div>
								<div class="text-xs uppercase tracking-[0.22em] text-gray-500">Hermes Skills Registry</div>
								<div class="mt-2 text-2xl font-semibold">Discover official skills with a cleaner install workflow</div>
								<div class="mt-2 text-sm text-gray-500 max-w-3xl">This is now styled more like the OpenClaw registry flow: cleaner controls, official-first discovery, and a dedicated output panel instead of a raw command dump.</div>
							</div>
							<div class="rounded-2xl border border-gray-100 dark:border-gray-850 bg-white/80 dark:bg-black/30 px-4 py-3 min-w-[240px]">
								<div class="text-xs uppercase tracking-wide text-gray-500">Current source</div>
								<div class="mt-2 text-lg font-semibold">{skillsSources.find((source) => source.id === skillsSource)?.label ?? skillsSource}</div>
								<div class="mt-1 text-sm text-gray-500">Defaulted to official results first for cleaner discovery.</div>
							</div>
						</div>
					</div>

					<div class="flex gap-1 p-1 rounded-xl bg-gray-100 dark:bg-gray-900 w-fit">
						<button class="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-sm font-medium transition {skillsTab === 'registry' ? 'bg-white dark:bg-black text-black dark:text-white shadow-sm' : 'text-gray-500 hover:text-gray-900 dark:hover:text-gray-100'}" on:click={() => (skillsTab = 'registry')}>Official Registry</button>
						<button class="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-sm font-medium transition {skillsTab === 'installed' ? 'bg-white dark:bg-black text-black dark:text-white shadow-sm' : 'text-gray-500 hover:text-gray-900 dark:hover:text-gray-100'}" on:click={() => (skillsTab = 'installed')}>Installed / Updates</button>
					</div>

					{#if skillsTab === 'registry'}
						<div class="grid grid-cols-1 xl:grid-cols-[1.2fr,0.8fr] gap-4">
							<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-5 bg-white dark:bg-black/20 shadow-sm">
								<div class="flex items-start justify-between gap-3 flex-wrap">
									<div>
										<div class="text-sm font-semibold">Browse registry</div>
										<div class="text-xs text-gray-500 mt-1">Search official skills first, then fan out to other registries when needed.</div>
									</div>
									<div class="rounded-full border border-gray-200 dark:border-gray-800 px-3 py-1 text-xs text-gray-500">limit {skillsLimit}</div>
								</div>

								<div class="mt-4 space-y-4">
									<div class="relative">
										<div class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"><Search className="size-4" /></div>
										<input class="w-full rounded-2xl border border-gray-100 dark:border-gray-800 bg-transparent pl-10 pr-4 py-3 text-sm outline-hidden" bind:value={skillsQuery} placeholder="Search skills… try calendar, github, notion, docker" />
									</div>

									<div class="flex gap-2 flex-wrap">
										{#each skillsSources as source}
											<button class="px-3 py-1.5 rounded-full text-xs font-medium transition {skillsSource === source.id ? 'bg-black text-white dark:bg-white dark:text-black' : 'bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-300'}" on:click={() => (skillsSource = source.id)}>{source.label}</button>
										{/each}
									</div>

									<div class="grid grid-cols-1 md:grid-cols-[140px,1fr] gap-3">
										<div class="rounded-2xl border border-gray-100 dark:border-gray-800 px-3 py-3">
											<div class="text-xs uppercase tracking-wide text-gray-500 mb-2">Result limit</div>
											<input class="w-full rounded-xl border border-gray-100 dark:border-gray-800 bg-transparent px-3 py-2 text-sm outline-hidden" bind:value={skillsLimit} type="number" min="1" max="50" />
										</div>
										<div class="rounded-2xl border border-gray-100 dark:border-gray-800 px-3 py-3">
											<div class="text-xs uppercase tracking-wide text-gray-500 mb-2">Actions</div>
											<div class="flex gap-2 flex-wrap">
												<button class="px-3 py-2 rounded-xl bg-black text-white dark:bg-white dark:text-black text-sm font-medium transition" on:click={runSkillsSearch} disabled={runningCommand}>Search</button>
												<button class="px-3 py-2 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 text-sm font-medium transition" on:click={runSkillsBrowse} disabled={runningCommand}>Browse trending</button>
											</div>
										</div>
									</div>
								</div>

								<div class="mt-5 rounded-2xl border border-gray-100 dark:border-gray-850 bg-white dark:bg-black/20 shadow-sm overflow-hidden">
									<div class="px-4 py-3 border-b border-gray-100 dark:border-gray-850 flex items-center justify-between gap-3">
										<div>
											<div class="text-sm font-semibold">Search results console</div>
											<div class="text-xs text-gray-500">Live markdown/text output from Hermes skills search commands.</div>
										</div>
										<div class="rounded-full bg-gray-100 dark:bg-gray-900 px-3 py-1 text-xs text-gray-500 font-mono">skills {skillsSource}</div>
									</div>
									<div class="rounded-b-2xl border-t border-slate-800 bg-gradient-to-b from-slate-950 to-black text-slate-100 overflow-hidden">
										<div class="px-4 py-2 border-b border-slate-800 text-[11px] uppercase tracking-[0.18em] text-slate-400">registry-search.log</div>
										<pre class="px-4 py-4 text-xs whitespace-pre-wrap break-words overflow-x-auto max-h-[32rem] font-mono">{renderPanel(skillsResult, 'Search official skills, browse trending registries, or inspect a skill below.')}</pre>
									</div>
								</div>
							</div>

							<div class="space-y-4">
								<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-5 bg-white dark:bg-black/20 shadow-sm">
									<div class="text-sm font-semibold">Inspect / install skill</div>
									<div class="mt-1 text-xs text-gray-500">Use the full identifier for precise installs, just like the OpenClaw registry flow.</div>
									<div class="mt-4 space-y-3">
										<input class="w-full rounded-2xl border border-gray-100 dark:border-gray-800 bg-transparent px-4 py-3 text-sm outline-hidden" bind:value={installIdentifier} placeholder="official/security/1password" />
										<div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
											<button class="px-3 py-2 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 text-sm font-medium transition" on:click={runSkillInspect} disabled={runningCommand}>Inspect</button>
											<button class="px-3 py-2 rounded-xl bg-black text-white dark:bg-white dark:text-black text-sm font-medium transition" on:click={runSkillInstall} disabled={runningCommand}>Install</button>
											<button class="px-3 py-2 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 text-sm font-medium transition" on:click={() => runCommand(`skills uninstall ${installIdentifier.trim()}`, { target: 'skills', refreshAfter: true })} disabled={runningCommand || !installIdentifier.trim()}>Uninstall</button>
											<button class="px-3 py-2 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 text-sm font-medium transition" on:click={() => runCommand(`skills view ${installIdentifier.trim()}`, { target: 'skills', refreshAfter: false })} disabled={runningCommand || !installIdentifier.trim()}>Preview</button>
										</div>
									</div>
								</div>

								<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-5 bg-white dark:bg-black/20 shadow-sm">
									<div class="text-sm font-semibold">Quick actions</div>
									<div class="mt-4 grid grid-cols-1 gap-2">
										<button class="px-3 py-2 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 text-left text-sm transition" on:click={() => runCommand('skills list', { target: 'skills', refreshAfter: false })} disabled={runningCommand}>View installed skills</button>
										<button class="px-3 py-2 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 text-left text-sm transition" on:click={() => runCommand('skills check', { target: 'skills', refreshAfter: false })} disabled={runningCommand}>Check for updates</button>
										<button class="px-3 py-2 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 text-left text-sm transition" on:click={() => { skillsSource = 'official'; runSkillsBrowse(); }} disabled={runningCommand}>Browse official trending</button>
										<button class="px-3 py-2 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 text-left text-sm transition" on:click={() => { skillsSource = 'clawhub'; runSkillsBrowse(); }} disabled={runningCommand}>Browse ClawHub trending</button>
									</div>
								</div>
							</div>
						</div>
					{:else}
						<div class="grid grid-cols-1 xl:grid-cols-[0.9fr,1.1fr] gap-4">
							<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-5 bg-white dark:bg-black/20 shadow-sm">
								<div class="text-sm font-semibold">Installed / updates</div>
								<div class="mt-1 text-xs text-gray-500">Maintenance actions and installed-skill inspection in a cleaner admin layout.</div>
								<div class="mt-4 grid grid-cols-1 gap-2">
									<button class="px-3 py-2 rounded-xl bg-black text-white dark:bg-white dark:text-black text-left text-sm font-medium transition" on:click={() => runCommand('skills list', { target: 'skills', refreshAfter: false })} disabled={runningCommand}>List installed skills</button>
									<button class="px-3 py-2 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 text-left text-sm transition" on:click={() => runCommand('skills check', { target: 'skills', refreshAfter: false })} disabled={runningCommand}>Check updates</button>
									<button class="px-3 py-2 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 text-left text-sm transition" on:click={() => runCommand('skills browse --source official --page 1 --size 12', { target: 'skills', refreshAfter: false })} disabled={runningCommand}>Browse official recommendations</button>
								</div>
							</div>
							<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-5 bg-white dark:bg-black/20 shadow-sm overflow-hidden">
								<div class="px-0 pb-3 flex items-center justify-between gap-3"><div><div class="text-sm font-semibold">Installed skills console</div><div class="text-xs text-gray-500">Rendered command output in a readable terminal-style panel.</div></div></div>
								<div class="rounded-2xl border border-slate-800 bg-gradient-to-b from-slate-950 to-black text-slate-100 overflow-hidden">
									<div class="px-4 py-2 border-b border-slate-800 text-[11px] uppercase tracking-[0.18em] text-slate-400">skills-installed.log</div>
									<pre class="px-4 py-4 text-xs whitespace-pre-wrap break-words overflow-x-auto max-h-[34rem] font-mono">{renderPanel(skillsResult, 'Run Installed / Updates actions to view installed skills, update checks, and maintenance output here.')}</pre>
								</div>
							</div>
						</div>
					{/if}
				</div>
			{:else if activeTab === 'ops'}
				<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4"><div class="text-sm font-semibold">Run Hermes Command</div><div class="mt-3 flex gap-2 flex-wrap"><input class="flex-1 min-w-[280px] rounded-xl border border-gray-100 dark:border-gray-800 bg-transparent px-3 py-2 text-sm outline-hidden" bind:value={commandInput} placeholder="/gateway status" /><button class="px-4 py-2 rounded-xl bg-black text-white dark:bg-white dark:text-black text-sm font-medium" on:click={() => runCommand(commandInput)} disabled={runningCommand}>Run</button></div>{#if runningCommand}<div class="mt-3 flex items-center gap-2 text-sm text-gray-500"><Spinner className="size-4" /> Running...</div>{/if}<pre class="mt-4 text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900 rounded-xl p-3 overflow-x-auto">{renderPanel(commandResult)}</pre></div>
			{:else if activeTab === 'access'}
				<div class="grid grid-cols-1 xl:grid-cols-3 gap-4"><div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4"><div class="text-sm font-semibold">Pairing</div><pre class="mt-3 text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900 rounded-xl p-3 overflow-x-auto">{overview.pairing?.stdout || overview.pairing?.rendered}</pre></div><div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4"><div class="text-sm font-semibold">Auth Pools</div><pre class="mt-3 text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900 rounded-xl p-3 overflow-x-auto">{overview.auth?.stdout || overview.auth?.rendered}</pre></div><div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4"><div class="text-sm font-semibold">Webhooks</div><pre class="mt-3 text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900 rounded-xl p-3 overflow-x-auto">{overview.webhooks?.stdout || overview.webhooks?.rendered}</pre></div></div>
			{:else if activeTab === 'profiles'}
				<div class="grid grid-cols-1 xl:grid-cols-3 gap-4"><div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4"><div class="text-sm font-semibold">Profiles</div><pre class="mt-3 text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900 rounded-xl p-3 overflow-x-auto">{overview.profiles?.stdout || overview.profiles?.rendered}</pre></div><div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4"><div class="text-sm font-semibold">Plugins</div><pre class="mt-3 text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900 rounded-xl p-3 overflow-x-auto">{overview.plugins?.stdout || overview.plugins?.rendered}</pre></div><div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4"><div class="text-sm font-semibold">Per-platform Tools</div><pre class="mt-3 text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900 rounded-xl p-3 overflow-x-auto">{overview.tools?.stdout || overview.tools?.rendered}</pre></div></div>
			{:else if activeTab === 'config'}
				<div class="space-y-4">
					<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
						<div class="rounded-2xl border border-gray-100 dark:border-gray-850 bg-white dark:bg-black/20 p-4"><div class="text-xs uppercase tracking-wide text-gray-500">config.yaml</div><div class="mt-2 text-lg font-semibold">{topLevelConfigEntries().length}</div><div class="mt-1 text-sm text-gray-500">top-level sections</div></div>
						<div class="rounded-2xl border border-gray-100 dark:border-gray-850 bg-white dark:bg-black/20 p-4"><div class="text-xs uppercase tracking-wide text-gray-500">.env</div><div class="mt-2 text-lg font-semibold">{envEntries().length}</div><div class="mt-1 text-sm text-gray-500">environment keys</div></div>
						<div class="rounded-2xl border border-gray-100 dark:border-gray-850 bg-white dark:bg-black/20 p-4"><div class="text-xs uppercase tracking-wide text-gray-500">Channel Directory</div><div class="mt-2 text-lg font-semibold">{channelDirectoryEntries().length}</div><div class="mt-1 text-sm text-gray-500">tracked channel entries</div></div>
						<div class="rounded-2xl border border-gray-100 dark:border-gray-850 bg-white dark:bg-black/20 p-4"><div class="text-xs uppercase tracking-wide text-gray-500">Gateway Log</div><div class="mt-2 text-lg font-semibold">{fileLineCount(configFiles?.gateway_log_tail || '')}</div><div class="mt-1 text-sm text-gray-500">tail lines loaded</div></div>
					</div>

					<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4 bg-gradient-to-b from-white to-gray-50/60 dark:from-black/20 dark:to-black/5">
						<div class="flex items-start justify-between gap-3 flex-wrap">
							<div>
								<div class="text-lg font-semibold">Gateway config files</div>
								<div class="mt-1 text-sm text-gray-500">Readable cards, grouped metadata, and expandable raw views instead of a giant text dump.</div>
							</div>
							<div class="flex gap-2 flex-wrap">
								{#each configViews as view}
									<button class="px-3 py-1.5 rounded-xl text-xs transition {configView === view.id ? 'bg-black text-white dark:bg-white dark:text-black' : 'bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800'}" on:click={() => (configView = view.id)}>{view.label}</button>
								{/each}
								<button class="px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 text-xs transition" on:click={() => (configExpandAll = !configExpandAll)}>{configExpandAll ? 'Collapse all' : 'Expand all'}</button>
							</div>
						</div>
					</div>

					{#if configView === 'overview'}
						<div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
							<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4 bg-white dark:bg-black/20">
								<div class="flex items-center justify-between gap-3"><div><div class="text-sm font-semibold">config.yaml overview</div><div class="text-xs text-gray-500">{configFiles?.config?.path}</div></div><Badge>{fileLineCount(configFiles?.config?.raw || '')} lines</Badge></div>
								<div class="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
									{#each topLevelConfigEntries() as [key, value]}
										<div class="rounded-2xl border border-gray-100 dark:border-gray-850 bg-gray-50/70 dark:bg-gray-950/20 p-4"><div class="flex items-center justify-between gap-3"><div class="font-semibold">{key}</div><Badge>{summarizeValue(value)}</Badge></div><pre class="mt-3 text-xs whitespace-pre-wrap break-words bg-white dark:bg-black/30 rounded-xl p-3 overflow-x-auto border border-gray-100 dark:border-gray-800">{markdownFence('yaml', `${key}: ${stringifyBlock(value)}`)}</pre></div>
									{/each}
								</div>
							</div>
							<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4 bg-white dark:bg-black/20">
								<div class="flex items-center justify-between gap-3"><div><div class="text-sm font-semibold">.env overview</div><div class="text-xs text-gray-500">{configFiles?.env?.path}</div></div><Badge>{envGroups().length} groups</Badge></div>
								<div class="mt-4 space-y-3">
									{#each envGroups() as [group, entries]}
										<details class="group rounded-2xl border border-gray-100 dark:border-gray-850 bg-gray-50/70 dark:bg-gray-950/20 overflow-hidden" open={configExpandAll}>
											<summary class="list-none cursor-pointer px-4 py-3 flex items-center justify-between gap-3"><div><div class="font-semibold">{group}</div><div class="text-xs text-gray-500">{entries.length} keys</div></div><div class="text-xs text-gray-400 group-open:rotate-180 transition">⌄</div></summary>
											<div class="px-4 pb-4 pt-1 border-t border-gray-100 dark:border-gray-850 space-y-2 bg-white/70 dark:bg-black/10">
												{#each entries as [key]}
													<div class="rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-black/30 px-3 py-2"><div class="text-xs uppercase tracking-wide text-gray-500">{key}</div><div class="mt-1 text-xs font-mono break-all">{visibleEnvValue(key)}</div></div>
												{/each}
											</div>
										</details>
									{/each}
								</div>
							</div>
						</div>
					{:else if configView === 'config'}
						<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4 bg-white dark:bg-black/20">
							<div class="flex items-center justify-between gap-3 flex-wrap"><div><div class="text-sm font-semibold">Hermes config.yaml</div><div class="text-xs text-gray-500">{configFiles?.config?.path}</div></div><Badge>{fileLineCount(configFiles?.config?.raw || '')} lines</Badge></div>
							<details class="mt-4 group rounded-2xl border border-gray-100 dark:border-gray-850 bg-gray-50/70 dark:bg-gray-950/20 overflow-hidden" open={configExpandAll || true}>
								<summary class="list-none cursor-pointer px-4 py-3 flex items-center justify-between gap-3"><div><div class="font-semibold">Raw file</div><div class="text-xs text-gray-500">Full YAML, kept readable inside a file-style container.</div></div><div class="text-xs text-gray-400 group-open:rotate-180 transition">⌄</div></summary>
								<div class="px-4 pb-4 pt-1 border-t border-gray-100 dark:border-gray-850"><pre class="text-xs whitespace-pre-wrap break-words bg-white dark:bg-black/30 rounded-xl p-4 overflow-x-auto border border-gray-100 dark:border-gray-800">{markdownFence('yaml', configFiles?.config?.raw || overview.config?.stdout || overview.config?.rendered || '')}</pre></div>
							</details>
						</div>
					{:else if configView === 'env'}
						<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4 bg-white dark:bg-black/20">
							<div class="flex items-center justify-between gap-3 flex-wrap"><div><div class="text-sm font-semibold">Hermes .env</div><div class="text-xs text-gray-500">{configFiles?.env?.path}</div></div><Badge>{envEntries().length} keys</Badge></div>
							<div class="mt-4 space-y-3">
								{#each envGroups() as [group, entries]}
									<details class="group rounded-2xl border border-gray-100 dark:border-gray-850 bg-gray-50/70 dark:bg-gray-950/20 overflow-hidden" open={configExpandAll}>
										<summary class="list-none cursor-pointer px-4 py-3 flex items-center justify-between gap-3"><div><div class="font-semibold">{group}</div><div class="text-xs text-gray-500">{entries.length} keys</div></div><div class="text-xs text-gray-400 group-open:rotate-180 transition">⌄</div></summary>
										<div class="px-4 pb-4 pt-1 border-t border-gray-100 dark:border-gray-850 bg-white/70 dark:bg-black/10 space-y-2">
											{#each entries as [key]}
												<div class="rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-black/30 px-3 py-3"><div class="flex items-center justify-between gap-3"><div class="text-xs uppercase tracking-wide text-gray-500">{key}</div><Badge>{getEnvValue(key) ? 'set' : 'masked/empty'}</Badge></div><div class="mt-2 text-xs font-mono break-all">{visibleEnvValue(key)}</div></div>
											{/each}
											<pre class="mt-3 text-xs whitespace-pre-wrap break-words bg-white dark:bg-black/30 rounded-xl p-4 overflow-x-auto border border-gray-100 dark:border-gray-800">{markdownFence('bash', entries.map(([key]) => `${key}=${visibleEnvValue(key)}`).join('\n'))}</pre>
										</div>
									</details>
								{/each}
							</div>
						</div>
					{:else if configView === 'channels'}
						<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4 bg-white dark:bg-black/20">
							<div class="flex items-center justify-between gap-3 flex-wrap"><div><div class="text-sm font-semibold">Channel directory</div><div class="text-xs text-gray-500">Structured channel metadata from Hermes home.</div></div><Badge>{channelDirectoryEntries().length} entries</Badge></div>
							<div class="mt-4 grid grid-cols-1 lg:grid-cols-2 gap-3">
								{#each channelDirectoryEntries() as [channelId, value]}
									<details class="group rounded-2xl border border-gray-100 dark:border-gray-850 bg-gray-50/70 dark:bg-gray-950/20 overflow-hidden" open={configExpandAll}>
										<summary class="list-none cursor-pointer px-4 py-3 flex items-center justify-between gap-3"><div><div class="font-semibold">{channelId}</div><div class="text-xs text-gray-500">{summarizeValue(value)}</div></div><div class="text-xs text-gray-400 group-open:rotate-180 transition">⌄</div></summary>
										<div class="px-4 pb-4 pt-1 border-t border-gray-100 dark:border-gray-850"><pre class="text-xs whitespace-pre-wrap break-words bg-white dark:bg-black/30 rounded-xl p-4 overflow-x-auto border border-gray-100 dark:border-gray-800">{markdownFence('json', stringifyBlock(value))}</pre></div>
									</details>
								{/each}
							</div>
						</div>
					{:else if configView === 'logs'}
						<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4 bg-white dark:bg-black/20">
							<div class="flex items-center justify-between gap-3 flex-wrap"><div><div class="text-sm font-semibold">Gateway log tail</div><div class="text-xs text-gray-500">Recent adapter-visible gateway output.</div></div><Badge>{fileLineCount(configFiles?.gateway_log_tail || '')} lines</Badge></div>
							<details class="mt-4 group rounded-2xl border border-gray-100 dark:border-gray-850 bg-gray-50/70 dark:bg-gray-950/20 overflow-hidden" open={configExpandAll || true}>
								<summary class="list-none cursor-pointer px-4 py-3 flex items-center justify-between gap-3"><div><div class="font-semibold">Recent log output</div><div class="text-xs text-gray-500">Minimize or expand as needed.</div></div><div class="text-xs text-gray-400 group-open:rotate-180 transition">⌄</div></summary>
								<div class="px-4 pb-4 pt-1 border-t border-gray-100 dark:border-gray-850"><pre class="text-xs whitespace-pre-wrap break-words bg-white dark:bg-black/30 rounded-xl p-4 overflow-x-auto border border-gray-100 dark:border-gray-800">{markdownFence('text', configFiles?.gateway_log_tail || 'No gateway log output yet.')}</pre></div>
							</details>
						</div>
					{/if}
				</div>
			{/if}
		{/if}
	</div>
{/if}
