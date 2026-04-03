<script lang="ts">
	import ContentRenderer from '../ContentRenderer.svelte';

	export let chatId = '';
	export let messageId = '';
	export let history;
	export let selectedModels = [];
	export let content = '';
	export let model = null;
	export let editCodeBlock = true;
	export let topPadding = false;
	export let done = true;
	export let addMessages = () => {};
	export let onSave = () => {};
	export let onTaskClick = () => {};
	export let onSourceClick = () => {};

	type ToolEvent = {
		kind: 'tool';
		toolName: string;
		status: 'running' | 'done';
		callLine: string;
		args?: string;
		result?: string;
	};

	type LogEvent = {
		kind: 'log';
		line: string;
	};

	const FILE_PATTERN = /(?:[A-Za-z]:\\[^\s`'\"]+|\/(?:[^\s`'\"]+\/)*[^\s`'\"]+|(?:^|\s)(?:[\w.-]+\/)+[\w.-]+\.[A-Za-z0-9]{1,8})/g;

	function extractFiles(text: string): string[] {
		const matches = text.match(FILE_PATTERN) ?? [];
		return [...new Set(matches.map((m) => m.trim()).filter((m) => /[./\\]/.test(m)))].slice(0, 12);
	}

	function splitTrace(trace: string): string[] {
		return trace
			.split('\n')
			.map((line) => line.trim())
			.filter(Boolean);
	}

	function summarizeTool(line: string): string {
		const match = line.match(/Tool\s+\d+:\s+([^\(\s]+)/);
		return match?.[1] ?? 'tool';
	}

	function buildEvents(lines: string[]): Array<ToolEvent | LogEvent> {
		const events: Array<ToolEvent | LogEvent> = [];
		let pendingTool: ToolEvent | null = null;

		for (const line of lines) {
			if (line.startsWith('📞 Tool')) {
				if (pendingTool) events.push(pendingTool);
				pendingTool = {
					kind: 'tool',
					toolName: summarizeTool(line),
					status: 'running',
					callLine: line
				};
				continue;
			}

			if (line.startsWith('✅ Tool')) {
				if (pendingTool) {
					pendingTool.status = 'done';
					pendingTool.callLine = line;
					continue;
				}
				events.push({ kind: 'log', line });
				continue;
			}

			if (line.startsWith('Args:')) {
				if (pendingTool) {
					pendingTool.args = line.replace(/^Args:\s*/, '');
					continue;
				}
				events.push({ kind: 'log', line });
				continue;
			}

			if (line.startsWith('Result:')) {
				if (pendingTool) {
					pendingTool.result = line.replace(/^Result:\s*/, '');
					events.push(pendingTool);
					pendingTool = null;
					continue;
				}
				events.push({ kind: 'log', line });
				continue;
			}

			if (pendingTool) {
				events.push(pendingTool);
				pendingTool = null;
			}
			events.push({ kind: 'log', line });
		}

		if (pendingTool) events.push(pendingTool);
		return events;
	}

	function lineTone(line: string): string {
		if (line.startsWith('↻')) return 'resume';
		return 'plain';
	}

	$: sections = (() => {
		const marker = 'Tool activity:\n';
		if (!content.includes(marker)) return null;
		const rest = content.split(marker)[1] ?? '';
		const [tracePart, resultPartRaw] = rest.split('\n\nResult:\n');
		const trace = (tracePart ?? '').trim();
		const result = (resultPartRaw ?? '').trim();
		const traceLines = splitTrace(trace);
		return {
			trace,
			traceLines,
			events: buildEvents(traceLines),
			result,
			files: extractFiles(`${trace}\n${result}`),
			isLive: !done,
			hasResult: Boolean(result)
		};
	})();
</script>

{#if sections}
	<div class="flex flex-col gap-3">
		<div class="flex flex-wrap items-center gap-2 text-[11px] uppercase tracking-wide">
			<span class="rounded-full px-2.5 py-1 font-semibold {sections.isLive ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' : 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'}">
				{sections.isLive ? 'Live Hermes activity' : 'Hermes activity log'}
			</span>
			<span class="rounded-full bg-gray-100 text-gray-700 dark:bg-gray-900 dark:text-gray-300 px-2.5 py-1">Model: {model?.name ?? 'hermes-gui'}</span>
			<span class="rounded-full bg-slate-100 text-slate-700 dark:bg-slate-900 dark:text-slate-300 px-2.5 py-1">{sections.events.length} events</span>
			{#if sections.hasResult}
				<span class="rounded-full bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300 px-2.5 py-1">Result ready</span>
			{/if}
		</div>

		<details class="group rounded-2xl border border-slate-200/80 dark:border-slate-800 bg-gradient-to-b from-slate-950 via-slate-950 to-black text-slate-100 shadow-sm overflow-hidden" open>
			<summary class="list-none cursor-pointer px-4 py-3 flex items-center justify-between gap-3 border-b border-slate-800/80">
				<div class="min-w-0">
					<div class="flex items-center gap-2 flex-wrap">
						<div class="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-300">Hermes console</div>
						<div class="rounded-full border border-slate-700 bg-slate-900/80 px-2 py-0.5 text-[11px] text-slate-300">
							{sections.isLive ? 'streaming' : 'complete'}
						</div>
					</div>
					<div class="mt-1 text-sm text-slate-300">
						Compact tool cards and logs. Collapse this when you just want the final answer.
					</div>
				</div>
				<div class="text-xs text-slate-500 group-open:rotate-180 transition">⌄</div>
			</summary>

			<div class="px-4 py-3 space-y-3 max-h-[28rem] overflow-y-auto">
				{#each sections.events as event}
					{#if event.kind === 'tool'}
						<div class="rounded-xl border {event.status === 'done' ? 'border-emerald-800/70 bg-emerald-950/20' : 'border-sky-800/70 bg-sky-950/20'} overflow-hidden">
							<div class="flex items-center justify-between gap-3 px-3 py-2 border-b {event.status === 'done' ? 'border-emerald-900/60' : 'border-sky-900/60'}">
								<div class="flex items-center gap-2 min-w-0">
									<span class="inline-flex h-6 min-w-6 items-center justify-center rounded-md text-[11px] font-bold {event.status === 'done' ? 'bg-emerald-400/20 text-emerald-200' : 'bg-sky-400/20 text-sky-200'}">
										{event.status === 'done' ? '✓' : '>'}
									</span>
									<div>
										<div class="text-[11px] uppercase tracking-[0.18em] {event.status === 'done' ? 'text-emerald-300' : 'text-sky-300'}">{event.status === 'done' ? 'Tool completed' : 'Tool call'}</div>
										<div class="font-mono text-sm text-white break-all">{event.toolName}</div>
									</div>
								</div>
							</div>
							<div class="px-3 py-3 space-y-3 text-xs font-mono">
								{#if event.args}
									<div>
										<div class="mb-1 text-[10px] uppercase tracking-[0.18em] text-amber-300">Args</div>
										<pre class="whitespace-pre-wrap break-words overflow-x-auto rounded-lg border border-amber-900/40 bg-black/30 px-3 py-2 text-amber-100">{event.args}</pre>
									</div>
								{/if}
								{#if event.result}
									<div>
										<div class="mb-1 text-[10px] uppercase tracking-[0.18em] text-violet-300">Result</div>
										<pre class="whitespace-pre-wrap break-words overflow-x-auto rounded-lg border border-violet-900/40 bg-black/30 px-3 py-2 text-violet-100">{event.result}</pre>
									</div>
								{/if}
							</div>
						</div>
					{:else}
						<div class="rounded-xl border border-slate-800 bg-black/40 px-3 py-2 font-mono text-xs leading-6 {lineTone(event.line) === 'resume' ? 'text-cyan-100' : 'text-slate-200'}">
							{event.line}
						</div>
					{/if}
				{/each}
				{#if sections.isLive}
					<div class="flex items-center gap-2 pt-1 text-slate-400 text-sm">
						<span class="inline-block h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
						<span>Streaming live from Hermes…</span>
					</div>
				{/if}
			</div>
		</details>

		{#if sections.files.length > 0}
			<div class="rounded-2xl border border-amber-200/60 dark:border-amber-900/40 bg-amber-50/70 dark:bg-amber-950/20 p-3">
				<div class="text-xs font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-300 mb-2">
					Files referenced
				</div>
				<div class="flex flex-wrap gap-2">
					{#each sections.files as file}
						<span class="rounded-full bg-white/80 dark:bg-black/20 border border-amber-200 dark:border-amber-900/40 px-2 py-1 text-xs font-mono text-amber-900 dark:text-amber-100">{file}</span>
					{/each}
				</div>
			</div>
		{/if}

		{#if sections.result}
			<details class="group rounded-2xl border border-gray-200 dark:border-gray-800 p-1.5 bg-white dark:bg-black/20" open>
				<summary class="list-none cursor-pointer px-2 pt-2 pb-1 flex items-center justify-between gap-3">
					<div>
						<div class="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">Result</div>
						<div class="mt-1 text-sm text-gray-500 dark:text-gray-400">Final answer, separated from the live tool log above.</div>
					</div>
					<div class="text-xs text-gray-400 group-open:rotate-180 transition">⌄</div>
				</summary>
				<ContentRenderer
					id={`${chatId}-${messageId}-hermes-result`}
					{messageId}
					{history}
					{selectedModels}
					content={sections.result}
					sources={[]}
					floatingButtons={false}
					save={true}
					preview={true}
					{editCodeBlock}
					{topPadding}
					{done}
					{model}
					{addMessages}
					{onSave}
					{onTaskClick}
					{onSourceClick}
				/>
			</details>
		{/if}
	</div>
{:else}
	<ContentRenderer
		id={`${chatId}-${messageId}`}
		{messageId}
		{history}
		{selectedModels}
		{content}
		sources={[]}
		floatingButtons={false}
		save={true}
		preview={true}
		{editCodeBlock}
		{topPadding}
		{done}
		{model}
		{addMessages}
		{onSave}
		{onTaskClick}
		{onSourceClick}
	/>
{/if}
