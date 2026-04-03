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

	function lineTone(line: string): string {
		if (line.startsWith('📞 Tool')) return 'call';
		if (line.startsWith('✅ Tool')) return 'done';
		if (line.startsWith('Args:')) return 'args';
		if (line.startsWith('Result:')) return 'result';
		if (line.startsWith('↻')) return 'resume';
		return 'plain';
	}

	function linePrompt(line: string): string {
		if (line.startsWith('📞 Tool')) return '[tool]';
		if (line.startsWith('✅ Tool')) return '[done]';
		if (line.startsWith('Args:')) return '[args]';
		if (line.startsWith('Result:')) return '[out ]';
		if (line.startsWith('↻')) return '[sess]';
		return '[log ]';
	}

	$: sections = (() => {
		const marker = 'Tool activity:\n';
		if (!content.includes(marker)) {
			return null;
		}
		const rest = content.split(marker)[1] ?? '';
		const [tracePart, resultPartRaw] = rest.split('\n\nResult:\n');
		const trace = (tracePart ?? '').trim();
		const result = (resultPartRaw ?? '').trim();
		const traceLines = splitTrace(trace);
		return {
			trace,
			traceLines,
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
			<span class="rounded-full bg-slate-100 text-slate-700 dark:bg-slate-900 dark:text-slate-300 px-2.5 py-1">{sections.traceLines.length} log lines</span>
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
						Live tool calls and progress log. Collapse this when you just want the final answer.
					</div>
				</div>
				<div class="text-xs text-slate-500 group-open:rotate-180 transition">⌄</div>
			</summary>

			<div class="px-4 py-3">
				<div class="rounded-xl border border-slate-800 bg-black/70 overflow-hidden">
					<div class="flex items-center justify-between gap-3 px-3 py-2 border-b border-slate-800 bg-slate-900/80">
						<div class="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-slate-400">
							<span class="inline-block h-2 w-2 rounded-full bg-emerald-400 {sections.isLive ? 'animate-pulse' : ''}"></span>
							stream.log
						</div>
						<div class="text-[11px] text-slate-500 font-mono">tail -f hermes</div>
					</div>
					<div class="max-h-80 overflow-y-auto px-3 py-3 font-mono text-xs leading-6">
						{#each sections.traceLines as line}
							<div class="grid grid-cols-[auto,1fr] gap-3 border-b border-slate-900/70 last:border-b-0 py-1.5">
								<div class="text-[10px] uppercase tracking-[0.18em]
									{lineTone(line) === 'call' ? 'text-sky-300' : ''}
									{lineTone(line) === 'done' ? 'text-emerald-300' : ''}
									{lineTone(line) === 'args' ? 'text-amber-300' : ''}
									{lineTone(line) === 'result' ? 'text-violet-300' : ''}
									{lineTone(line) === 'resume' ? 'text-cyan-300' : ''}
									{lineTone(line) === 'plain' ? 'text-slate-500' : ''}
								">
									{linePrompt(line)}
								</div>
								<pre class="whitespace-pre-wrap break-words overflow-x-auto
									{lineTone(line) === 'call' ? 'text-sky-100' : ''}
									{lineTone(line) === 'done' ? 'text-emerald-100' : ''}
									{lineTone(line) === 'args' ? 'text-amber-100' : ''}
									{lineTone(line) === 'result' ? 'text-violet-100' : ''}
									{lineTone(line) === 'resume' ? 'text-cyan-100' : ''}
									{lineTone(line) === 'plain' ? 'text-slate-200' : ''}
								">{line}</pre>
							</div>
						{/each}
						{#if sections.isLive}
							<div class="flex items-center gap-2 pt-2 text-slate-400">
								<span class="inline-block h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
								<span>Streaming live from Hermes…</span>
							</div>
						{/if}
					</div>
				</div>
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
						<div class="mt-1 text-sm text-gray-500 dark:text-gray-400">Final answer, minimized from the live console log above.</div>
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
