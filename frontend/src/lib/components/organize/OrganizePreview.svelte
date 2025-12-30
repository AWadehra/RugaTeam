<script lang="ts">
	import type { FolderStructureResponse } from '$lib/types/api';
	import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Spinner } from '$lib/components/ui/spinner';
	import { Folder, FileText, ArrowRight } from '@lucide/svelte';

	interface Props {
		structure: FolderStructureResponse;
		onApply: () => void;
		onCancel: () => void;
		loading?: boolean;
	}

	let { structure, onApply, onCancel, loading = false }: Props = $props();
</script>

<Card class="w-full">
	<CardHeader>
		<CardTitle class="flex items-center justify-between">
			<div class="flex items-center gap-2">
				<Folder class="h-5 w-5" />
				Organization Preview
			</div>
			<Badge variant="secondary">
				{structure.total_files} files
			</Badge>
		</CardTitle>
	</CardHeader>
	<CardContent class="space-y-4">
		<!-- Root folder name -->
		<div class="p-3 bg-muted rounded-md">
			<div class="text-sm text-muted-foreground mb-1">New folder will be created:</div>
			<div class="font-mono font-medium">{structure.structure.root_folder_name}</div>
		</div>

		<!-- Organization rationale -->
		<div class="p-3 border rounded-md">
			<div class="text-sm font-medium mb-1">Organization Strategy</div>
			<p class="text-sm text-muted-foreground">
				{structure.structure.organization_rationale}
			</p>
		</div>

		<!-- Folder structure -->
		<div>
			<div class="text-sm font-medium mb-2">Folders to create ({structure.structure.folders.length})</div>
			<div class="max-h-32 overflow-y-auto border rounded-md p-2">
				{#each structure.structure.folders as folder}
					<div class="flex items-center gap-2 py-1 text-sm font-mono">
						<Folder class="h-4 w-4 text-blue-500" />
						{folder}
					</div>
				{/each}
			</div>
		</div>

		<!-- File moves table -->
		<div>
			<div class="text-sm font-medium mb-2">File moves ({structure.structure.file_moves.length})</div>
			<div class="max-h-60 overflow-y-auto border rounded-md">
				<table class="w-full text-sm">
					<thead class="sticky top-0 bg-background border-b">
						<tr>
							<th class="text-left p-2">Source</th>
							<th class="text-left p-2 w-8"></th>
							<th class="text-left p-2">Destination</th>
						</tr>
					</thead>
					<tbody>
						{#each structure.structure.file_moves as move}
							<tr class="border-b last:border-b-0 hover:bg-muted/50">
								<td class="p-2">
									<div class="flex items-center gap-1 truncate max-w-xs" title={move.source_path}>
										<FileText class="h-4 w-4 shrink-0 text-gray-400" />
										<span class="truncate">{move.source_path}</span>
									</div>
								</td>
								<td class="p-2">
									<ArrowRight class="h-4 w-4 text-gray-400" />
								</td>
								<td class="p-2">
									<div class="truncate max-w-xs text-green-600" title={move.destination_path}>
										{move.destination_path}
									</div>
									{#if move.reason}
										<div class="text-xs text-muted-foreground truncate" title={move.reason}>
											{move.reason}
										</div>
									{/if}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		</div>
	</CardContent>
	<CardFooter class="flex justify-end gap-2">
		<Button variant="outline" onclick={onCancel} disabled={loading}>
			Cancel
		</Button>
		<Button onclick={onApply} disabled={loading}>
			{#if loading}
				<Spinner class="h-4 w-4 mr-2" />
				Applying...
			{:else}
				Apply Organization
			{/if}
		</Button>
	</CardFooter>
</Card>
