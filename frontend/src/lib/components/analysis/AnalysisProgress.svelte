<script lang="ts">
	import { onDestroy } from 'svelte';
	import type { JobInfo, AnalysisStatus } from '$lib/types/api';
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { Spinner } from '$lib/components/ui/spinner';
	import { CheckCircle, XCircle, Clock, Loader2 } from '@lucide/svelte';

	interface Props {
		jobId: string;
		onComplete?: () => void;
	}

	let { jobId, onComplete }: Props = $props();

	let job = $state<JobInfo | null>(null);
	let error = $state<string | null>(null);
	let intervalId: ReturnType<typeof setInterval> | null = null;

	const statusIcons: Record<AnalysisStatus, typeof CheckCircle> = {
		analyzed: CheckCircle,
		in_process: Loader2,
		pending: Clock,
		error: XCircle,
		not_found: XCircle
	};

	const statusColors: Record<AnalysisStatus, string> = {
		analyzed: 'text-green-500',
		in_process: 'text-blue-500',
		pending: 'text-gray-400',
		error: 'text-red-500',
		not_found: 'text-red-500'
	};

	async function fetchJobStatus() {
		try {
			const response = await fetch(`/api/jobs/${jobId}`);
			if (!response.ok) {
				const text = await response.text();
				throw new Error(`Failed to fetch job status (${response.status}): ${text}`);
			}
			job = await response.json();

			// Stop polling if job is complete or errored
			if (job && (job.status === 'analyzed' || job.status === 'error')) {
				stopPolling();
				onComplete?.();
			}
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
			stopPolling();
			// If we can't reach the backend, also call onComplete to return to files view
			onComplete?.();
		}
	}

	function startPolling() {
		fetchJobStatus();
		intervalId = setInterval(fetchJobStatus, 2000);
	}

	function stopPolling() {
		if (intervalId) {
			clearInterval(intervalId);
			intervalId = null;
		}
	}

	$effect(() => {
		if (jobId) {
			startPolling();
		}
		return () => stopPolling();
	});

	onDestroy(() => {
		stopPolling();
	});

	const progressPercent = $derived(
		job ? Math.round((job.files_processed / job.files_queued) * 100) : 0
	);
</script>

<Card class="w-full">
	<CardHeader>
		<CardTitle class="flex items-center gap-2">
			{#if job?.status === 'in_process' || job?.status === 'pending'}
				<Spinner class="h-5 w-5" />
			{/if}
			Analysis Progress
		</CardTitle>
	</CardHeader>
	<CardContent>
		{#if error}
			<div class="text-red-500 mb-4">
				Error: {error}
			</div>
		{:else if job}
			<!-- Progress bar -->
			<div class="mb-4">
				<div class="flex justify-between text-sm mb-1">
					<span>{job.files_processed} / {job.files_queued} files</span>
					<span>{progressPercent}%</span>
				</div>
				<div class="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
					<div
						class="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
						style="width: {progressPercent}%"
					></div>
				</div>
			</div>

			<!-- Status summary -->
			<div class="flex gap-4 mb-4 text-sm">
				<Badge variant="secondary">
					Processed: {job.files_processed}
				</Badge>
				{#if job.files_failed > 0}
					<Badge variant="destructive">
						Failed: {job.files_failed}
					</Badge>
				{/if}
				<Badge variant="outline">
					Status: {job.status}
				</Badge>
			</div>

			<!-- File status list -->
			{#if job.file_statuses}
				<div class="max-h-60 overflow-y-auto border rounded-md">
					<table class="w-full text-sm">
						<thead class="sticky top-0 bg-background border-b">
							<tr>
								<th class="text-left p-2">File</th>
								<th class="text-left p-2 w-24">Status</th>
							</tr>
						</thead>
						<tbody>
							{#each Object.entries(job.file_statuses) as [filePath, status]}
								{@const Icon = statusIcons[status]}
								<tr class="border-b last:border-b-0">
									<td class="p-2 truncate max-w-md" title={filePath}>
										{filePath}
									</td>
									<td class="p-2">
										<div class="flex items-center gap-1 {statusColors[status]}">
											<Icon class="h-4 w-4 {status === 'in_process' ? 'animate-spin' : ''}" />
											<span class="capitalize">{status.replace('_', ' ')}</span>
										</div>
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
		{:else}
			<div class="flex items-center gap-2">
				<Spinner class="h-5 w-5" />
				<span>Loading job status...</span>
			</div>
		{/if}
	</CardContent>
</Card>
