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

	$: sections = (() => {
		const marker = 'Tool activity:\n';
		if (!content.includes(marker)) {
			return null;
		}
		const rest = content.split(marker)[1] ?? '';
		const [tracePart, resultPartRaw] = rest.split('\n\nResult:\n');
		const trace = (tracePart ?? '').trim();
		const result = (resultPartRaw ?? '').trim();
		return {
			trace,
			traceLines: splitTrace(trace),
			result,
			files: extractFiles(`${trace}\n${result}`)
		};
	})();
</script>

{#if sections}
	<div class="flex flex-col gap-3">
		<div class="flex flex-wrap gap-2 text-[11px] uppercase tracking-wide">
			<span class="rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 px-2 py-1">Hermes coding trace</span>
			<span class="rounded-full bg-gray-100 text-gray-700 dark:bg-gray-900 dark:text-gray-300 px-2 py-1">Model: {model?.name ?? 'hermes-gui'}</span>
			<span class="rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300 px-2 py-1">{sections.traceLines.length} activity lines</span>
		</div>

		<div class="rounded-2xl border border-blue-200/60 dark:border-blue-900/50 bg-blue-50/70 dark:bg-blue-950/20 p-3">
			<div class="text-xs font-semibold uppercase tracking-wide text-blue-700 dark:text-blue-300 mb-2">
				Tool activity
			</div>
			<div class="space-y-2">
				{#each sections.traceLines as line}
					<div class="rounded-xl bg-white/70 dark:bg-black/20 border border-blue-100 dark:border-blue-900/40 px-3 py-2">
						<pre class="text-xs whitespace-pre-wrap break-words text-blue-950 dark:text-blue-100 font-mono overflow-x-auto">{line}</pre>
					</div>
				{/each}
			</div>
		</div>

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
			<div class="rounded-2xl border border-gray-200 dark:border-gray-800 p-1.5">
				<div class="px-2 pt-2 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
					Result
				</div>
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
			</div>
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
