<script>
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import Sparkles from '$lib/components/icons/Sparkles.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	export let statusHistory = [];
	export let expand = false;

	let showHistory = false;
	let history = [];
	let status = null;

	$: showHistory = expand ? true : showHistory;
	$: history = statusHistory ?? [];
	$: status = history.length > 0 ? history.at(-1) : null;
	$: visibleHistory = history.filter((item) => item?.hidden !== true);
	$: activeLabel = (() => {
		if (!status) return 'Thinking';
		if (status?.done) return 'Completed';
		if (status?.action === 'web_search') return 'Researching';
		if (status?.action === 'knowledge_search') return 'Reviewing knowledge';
		if (status?.action === 'queries_generated' || status?.action === 'web_search_queries_generated') return 'Planning searches';
		if (status?.action === 'sources_retrieved') return 'Collecting sources';
		return 'Thinking';
	})();
</script>

{#if visibleHistory.length > 0}
	<div class="mb-3 rounded-2xl border border-violet-200/60 dark:border-violet-900/40 bg-gradient-to-br from-violet-50/80 via-white to-slate-50/80 dark:from-violet-950/20 dark:via-black/20 dark:to-slate-950/20 overflow-hidden">
		<button
			class="w-full text-left px-4 py-3"
			aria-label={$i18n.t('Toggle status history')}
			aria-expanded={showHistory}
			on:click={() => {
				showHistory = !showHistory;
			}}
		>
			<div class="flex items-start gap-3">
				<div class="mt-0.5 flex h-8 w-8 items-center justify-center rounded-xl bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300">
					{#if status?.done}
						<Sparkles className="size-4" />
					{:else}
						<Spinner className="size-4" />
					{/if}
				</div>
				<div class="min-w-0 flex-1">
					<div class="flex items-center gap-2 flex-wrap">
						<div class="text-xs font-semibold uppercase tracking-[0.18em] text-violet-700 dark:text-violet-300">
							Hermes {activeLabel}
						</div>
						<div class="rounded-full bg-white/90 dark:bg-black/30 border border-violet-200/70 dark:border-violet-900/30 px-2 py-0.5 text-[11px] text-violet-700 dark:text-violet-300">
							{visibleHistory.length} step{visibleHistory.length === 1 ? '' : 's'}
						</div>
					</div>
					<div class="mt-1 text-sm text-slate-700 dark:text-slate-200 leading-relaxed">
						{status?.description ?? 'Hermes is thinking through the request.'}
					</div>
					<div class="mt-2 text-xs text-slate-500 dark:text-slate-400">
						{showHistory ? 'Hide live reasoning timeline' : 'Show live reasoning timeline'}
					</div>
				</div>
				<div class="pt-1 text-violet-400 text-sm transition-transform {showHistory ? 'rotate-180' : ''}">
					⌄
				</div>
			</div>
		</button>

		{#if showHistory}
			<div class="border-t border-violet-200/60 dark:border-violet-900/30 px-4 py-3 bg-white/50 dark:bg-black/10">
				<div class="space-y-3">
					{#each visibleHistory as item, idx}
						<div class="flex gap-3">
							<div class="flex flex-col items-center pt-1">
								<div class="size-2 rounded-full {item?.done ? 'bg-emerald-500' : 'bg-violet-500 animate-pulse'}"></div>
								{#if idx !== visibleHistory.length - 1}
									<div class="mt-1 w-px flex-1 bg-violet-200 dark:bg-violet-900/40 min-h-5"></div>
								{/if}
							</div>
							<div class="min-w-0 flex-1 pb-1">
								<div class="flex items-center gap-2 flex-wrap">
									<div class="text-sm font-medium text-slate-800 dark:text-slate-100">
										{item?.description}
									</div>
									<div class="rounded-full px-2 py-0.5 text-[11px] border {item?.done ? 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/20 dark:text-emerald-300 dark:border-emerald-900/30' : 'bg-violet-50 text-violet-700 border-violet-200 dark:bg-violet-950/20 dark:text-violet-300 dark:border-violet-900/30'}">
										{item?.done ? 'done' : (item?.action ?? 'working')}
									</div>
								</div>
								{#if item?.query}
									<div class="mt-1 text-xs font-mono rounded-lg bg-slate-100/80 dark:bg-slate-900/60 px-2 py-1 text-slate-600 dark:text-slate-300 break-all">
										{item.query}
									</div>
								{/if}
								{#if item?.queries && item.queries.length > 0}
									<div class="mt-2 flex flex-wrap gap-1.5">
										{#each item.queries as query}
											<div class="rounded-full bg-slate-100 dark:bg-slate-900/60 px-2 py-1 text-[11px] text-slate-600 dark:text-slate-300">
												{query}
											</div>
										{/each}
									</div>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}
	</div>
{/if}
