<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { WEBUI_NAME } from '$lib/stores';
	import {
		getHermesOverview,
		runHermesCommand,
		getHermesConfigFiles,
		updateHermesEnvKey,
		updateHermesConfigPath
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
	let channelQuery = '';
	let skillsQuery = 'calendar';
	let skillsSource = 'clawhub';
	let skillsLimit = 20;
	let skillsResult: CommandResult | null = null;
	let installIdentifier = '';
	let selectedChannel = 'discord';

	const quickActions = [
		{ label: 'Gateway Status', command: '/gateway status' },
		{ label: 'Gateway Restart', command: '/gateway restart' },
		{ label: 'Doctor', command: '/doctor' },
		{ label: 'Sessions List', command: '/sessions list' },
		{ label: 'Cron List', command: '/cron list' },
		{ label: 'Config', command: '/config' }
	];

	const refresh = async () => {
		loading = true;
		try {
			const [overviewPayload, configPayload] = await Promise.all([getHermesOverview(), getHermesConfigFiles()]);
			overview = overviewPayload;
			configFiles = configPayload;
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
		await runCommand(`skills search ${JSON.stringify(skillsQuery)} --source ${skillsSource} --limit ${skillsLimit}`, { target: 'skills', refreshAfter: false });
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
				<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
					<div class="rounded-2xl border border-gray-100 dark:border-gray-850 bg-white dark:bg-black/20 p-4"><div class="text-xs uppercase tracking-wide text-gray-500">Adapter</div><div class="mt-2 text-lg font-semibold">{overview.health?.status ?? 'unknown'}</div><div class="mt-1 text-sm text-gray-500 break-all">{overview.health?.model}</div></div>
					<div class="rounded-2xl border border-gray-100 dark:border-gray-850 bg-white dark:bg-black/20 p-4"><div class="text-xs uppercase tracking-wide text-gray-500">Gateway</div><div class="mt-2 text-lg font-semibold">{overview.gateway?.exit_code === 0 ? 'Running' : 'Needs Attention'}</div><div class="mt-1 text-sm text-gray-500">Exit code: {overview.gateway?.exit_code}</div></div>
					<div class="rounded-2xl border border-gray-100 dark:border-gray-850 bg-white dark:bg-black/20 p-4"><div class="text-xs uppercase tracking-wide text-gray-500">Session Map</div><div class="mt-2 text-lg font-semibold">{overview.session_map_count}</div><div class="mt-1 text-sm text-gray-500">Mapped Open WebUI chats</div></div>
					<div class="rounded-2xl border border-gray-100 dark:border-gray-850 bg-white dark:bg-black/20 p-4"><div class="text-xs uppercase tracking-wide text-gray-500">Profiles/Auth</div><div class="mt-2 text-lg font-semibold">{overview.profiles?.exit_code === 0 ? 'Ready' : 'Check'}</div><div class="mt-1 text-sm text-gray-500">CLI control plane status</div></div>
				</div>

				<div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
					<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4"><div class="flex items-center justify-between gap-2"><div class="text-sm font-semibold">Gateway Status</div><Badge>{overview.gateway?.exit_code === 0 ? 'online' : 'degraded'}</Badge></div><pre class="mt-3 text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900 rounded-xl p-3 overflow-x-auto">{overview.gateway?.stdout || overview.gateway?.stderr || overview.gateway?.rendered}</pre></div>
					<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4"><div class="text-sm font-semibold">Gateway Log Tail</div><pre class="mt-3 text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900 rounded-xl p-3 overflow-x-auto">{configFiles?.gateway_log_tail || 'No gateway log output yet.'}</pre></div>
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
							<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4">
								<div class="text-sm font-semibold mb-3">Environment</div>
								<div class="space-y-3">
									{#each selectedChannelDef().envKeys as envKey}
										<div class="rounded-xl bg-gray-50 dark:bg-gray-900 p-3">
											<div class="text-xs uppercase tracking-wide text-gray-500">{envKey}</div>
											<input class="mt-2 w-full rounded-xl border border-gray-100 dark:border-gray-800 bg-transparent px-3 py-2 text-sm outline-hidden" value={getEnvValue(envKey)} placeholder={getEnvMaskedValue(envKey)} on:change={(e) => saveEnv(envKey, e.currentTarget.value)} disabled={saving} />
										</div>
									{/each}
								</div>
							</div>
							<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4">
								<div class="text-sm font-semibold mb-3">Config Paths</div>
								<div class="space-y-3">
									{#if selectedChannelDef().configPaths.length === 0}
										<div class="text-sm text-gray-500">No structured config paths defined for this channel yet.</div>
									{/if}
									{#each selectedChannelDef().configPaths as configPath}
										<div class="rounded-xl bg-gray-50 dark:bg-gray-900 p-3">
											<div class="text-xs uppercase tracking-wide text-gray-500">{configPath}</div>
											<input class="mt-2 w-full rounded-xl border border-gray-100 dark:border-gray-800 bg-transparent px-3 py-2 text-sm outline-hidden" value={String(getConfigValue(configPath) ?? '')} on:change={(e) => saveConfig(configPath, e.currentTarget.value)} disabled={saving} />
										</div>
									{/each}
								</div>
							</div>
						</div>

						<div class="mt-4 rounded-2xl border border-gray-100 dark:border-gray-850 p-4">
							<div class="text-sm font-semibold">Discovered Channels / Directory</div>
							<pre class="mt-3 text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900 rounded-xl p-3 overflow-x-auto">{JSON.stringify(configFiles?.channel_directory ?? {}, null, 2)}</pre>
						</div>
					</div>
				</div>
			{:else if activeTab === 'skills'}
				<div class="grid grid-cols-1 xl:grid-cols-[1.1fr,0.9fr] gap-4">
					<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4">
						<div class="text-sm font-semibold">Search / Browse Skills</div>
						<div class="mt-3 grid grid-cols-1 md:grid-cols-[1fr,180px,120px] gap-2">
							<input class="rounded-xl border border-gray-100 dark:border-gray-800 bg-transparent px-3 py-2 text-sm outline-hidden" bind:value={skillsQuery} placeholder="calendar" />
							<select class="rounded-xl border border-gray-100 dark:border-gray-800 bg-transparent px-3 py-2 text-sm outline-hidden" bind:value={skillsSource}>
								<option value="all">all</option><option value="official">official</option><option value="clawhub">clawhub</option><option value="skills-sh">skills-sh</option><option value="github">github</option><option value="lobehub">lobehub</option>
							</select>
							<input class="rounded-xl border border-gray-100 dark:border-gray-800 bg-transparent px-3 py-2 text-sm outline-hidden" bind:value={skillsLimit} type="number" min="1" max="50" />
						</div>
						<div class="mt-3 flex gap-2 flex-wrap">
							<button class="px-3 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black text-xs transition" on:click={runSkillsSearch} disabled={runningCommand}>Search</button>
							<button class="px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 text-xs transition" on:click={runSkillsBrowse} disabled={runningCommand}>Browse</button>
							<button class="px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 text-xs transition" on:click={() => runCommand('skills list', { target: 'skills', refreshAfter: false })} disabled={runningCommand}>Installed</button>
							<button class="px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 text-xs transition" on:click={() => runCommand('skills check', { target: 'skills', refreshAfter: false })} disabled={runningCommand}>Check Updates</button>
						</div>
						<pre class="mt-4 text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900 rounded-xl p-3 overflow-x-auto">{renderPanel(skillsResult, 'Search ClawHub, official, skills.sh, GitHub or LobeHub-backed skills here.')}</pre>
					</div>
					<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4"><div class="text-sm font-semibold">Inspect / Install Skill</div><div class="mt-3 space-y-3"><input class="w-full rounded-xl border border-gray-100 dark:border-gray-800 bg-transparent px-3 py-2 text-sm outline-hidden" bind:value={installIdentifier} placeholder="official/security/1password" /><div class="flex gap-2 flex-wrap"><button class="px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 text-xs transition" on:click={runSkillInspect} disabled={runningCommand}>Inspect</button><button class="px-3 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black text-xs transition" on:click={runSkillInstall} disabled={runningCommand}>Install</button><button class="px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 text-xs transition" on:click={() => runCommand(`skills uninstall ${installIdentifier.trim()}`, { target: 'skills', refreshAfter: true })} disabled={runningCommand || !installIdentifier.trim()}>Uninstall</button></div><div class="text-xs text-gray-500">Use the full identifier when search results are ambiguous. ClawHub-backed discovery is integrated here through Hermes skills sources.</div></div></div>
				</div>
			{:else if activeTab === 'ops'}
				<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4"><div class="text-sm font-semibold">Run Hermes Command</div><div class="mt-3 flex gap-2 flex-wrap"><input class="flex-1 min-w-[280px] rounded-xl border border-gray-100 dark:border-gray-800 bg-transparent px-3 py-2 text-sm outline-hidden" bind:value={commandInput} placeholder="/gateway status" /><button class="px-4 py-2 rounded-xl bg-black text-white dark:bg-white dark:text-black text-sm font-medium" on:click={() => runCommand(commandInput)} disabled={runningCommand}>Run</button></div>{#if runningCommand}<div class="mt-3 flex items-center gap-2 text-sm text-gray-500"><Spinner className="size-4" /> Running...</div>{/if}<pre class="mt-4 text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900 rounded-xl p-3 overflow-x-auto">{renderPanel(commandResult)}</pre></div>
			{:else if activeTab === 'access'}
				<div class="grid grid-cols-1 xl:grid-cols-3 gap-4"><div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4"><div class="text-sm font-semibold">Pairing</div><pre class="mt-3 text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900 rounded-xl p-3 overflow-x-auto">{overview.pairing?.stdout || overview.pairing?.rendered}</pre></div><div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4"><div class="text-sm font-semibold">Auth Pools</div><pre class="mt-3 text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900 rounded-xl p-3 overflow-x-auto">{overview.auth?.stdout || overview.auth?.rendered}</pre></div><div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4"><div class="text-sm font-semibold">Webhooks</div><pre class="mt-3 text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900 rounded-xl p-3 overflow-x-auto">{overview.webhooks?.stdout || overview.webhooks?.rendered}</pre></div></div>
			{:else if activeTab === 'profiles'}
				<div class="grid grid-cols-1 xl:grid-cols-3 gap-4"><div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4"><div class="text-sm font-semibold">Profiles</div><pre class="mt-3 text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900 rounded-xl p-3 overflow-x-auto">{overview.profiles?.stdout || overview.profiles?.rendered}</pre></div><div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4"><div class="text-sm font-semibold">Plugins</div><pre class="mt-3 text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900 rounded-xl p-3 overflow-x-auto">{overview.plugins?.stdout || overview.plugins?.rendered}</pre></div><div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4"><div class="text-sm font-semibold">Per-platform Tools</div><pre class="mt-3 text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900 rounded-xl p-3 overflow-x-auto">{overview.tools?.stdout || overview.tools?.rendered}</pre></div></div>
			{:else if activeTab === 'config'}
				<div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
					<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4"><div class="text-sm font-semibold">Hermes Config</div><div class="mt-3 text-xs text-gray-500">{configFiles?.config?.path}</div><pre class="mt-3 text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900 rounded-xl p-3 overflow-x-auto">{configFiles?.config?.raw || overview.config?.stdout || overview.config?.rendered}</pre></div>
					<div class="rounded-2xl border border-gray-100 dark:border-gray-850 p-4"><div class="text-sm font-semibold">Hermes .env</div><div class="mt-3 text-xs text-gray-500">{configFiles?.env?.path}</div><pre class="mt-3 text-xs whitespace-pre-wrap break-words bg-gray-50 dark:bg-gray-900 rounded-xl p-3 overflow-x-auto">{configFiles?.env?.raw || 'No .env data loaded'}</pre></div>
				</div>
			{/if}
		{/if}
	</div>
{/if}
