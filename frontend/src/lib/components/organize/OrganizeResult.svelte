<script lang="ts">
	import type { ApplyStructureResponse } from '$lib/types/api';
	import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { CheckCircle, XCircle, Folder, FileText } from '@lucide/svelte';

	interface Props {
		result: ApplyStructureResponse;
		onDismiss: () => void;
	}

	let { result, onDismiss }: Props = $props();

	const hasErrors = $derived(result.errors.length > 0);
</script>

<Card class="w-full">
	<CardHeader>
		<CardTitle class="flex items-center gap-2">
			{#if hasErrors}
				<XCircle class="h-5 w-5 text-yellow-500" />
				Organization Completed with Warnings
			{:else}
				<CheckCircle class="h-5 w-5 text-green-500" />
				Organization Complete
			{/if}
		</CardTitle>
	</CardHeader>
	<CardContent class="space-y-4">
		<!-- New folder path -->
		<div class="p-3 bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-md">
			<div class="text-sm text-muted-foreground mb-1">Files organized to:</div>
			<div class="font-mono font-medium text-green-700 dark:text-green-300 break-all">
				{result.new_root_path}
			</div>
		</div>

		<!-- Stats -->
		<div class="flex gap-4">
			<div class="flex items-center gap-2">
				<Folder class="h-5 w-5 text-blue-500" />
				<div>
					<div class="text-2xl font-bold">{result.folders_created}</div>
					<div class="text-xs text-muted-foreground">Folders created</div>
				</div>
			</div>
			<div class="flex items-center gap-2">
				<FileText class="h-5 w-5 text-green-500" />
				<div>
					<div class="text-2xl font-bold">{result.files_copied}</div>
					<div class="text-xs text-muted-foreground">Files copied</div>
				</div>
			</div>
		</div>

		<!-- Errors if any -->
		{#if hasErrors}
			<div class="border border-yellow-200 dark:border-yellow-800 rounded-md">
				<div class="p-2 bg-yellow-50 dark:bg-yellow-950 border-b border-yellow-200 dark:border-yellow-800">
					<Badge variant="outline" class="text-yellow-600">
						{result.errors.length} warning(s)
					</Badge>
				</div>
				<div class="max-h-32 overflow-y-auto p-2">
					{#each result.errors as error}
						<div class="text-sm text-yellow-600 dark:text-yellow-400 py-1">
							{error}
						</div>
					{/each}
				</div>
			</div>
		{/if}
	</CardContent>
	<CardFooter class="flex justify-end">
		<Button onclick={onDismiss}>
			Done
		</Button>
	</CardFooter>
</Card>
