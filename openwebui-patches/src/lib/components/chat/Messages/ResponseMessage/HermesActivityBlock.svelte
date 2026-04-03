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

	$: sections = (() => {
		const marker = 'Tool activity:\n';
		if (!content.includes(marker)) {
			return null;
		}
		const rest = content.split(marker)[1] ?? '';
		const [tracePart, resultPartRaw] = rest.split('\n\nResult:\n');
		return {
			trace: (tracePart ?? '').trim(),
			result: (resultPartRaw ?? '').trim()
		};
	})();
</script>

{#if sections}
	<div class="flex flex-col gap-3">
		<div class="rounded-2xl border border-blue-200/60 dark:border-blue-900/50 bg-blue-50/70 dark:bg-blue-950/20 p-3">
			<div class="text-xs font-semibold uppercase tracking-wide text-blue-700 dark:text-blue-300 mb-2">
				Tool activity
			</div>
			<pre class="text-xs whitespace-pre-wrap break-words text-blue-950 dark:text-blue-100 font-mono overflow-x-auto">{sections.trace}</pre>
		</div>

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
