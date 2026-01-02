<script lang="ts">
	import { Chat } from '$lib/components/chat';
	import { columns } from '$lib/components/document-table/Column';
	import type { AnalysisResult } from '$lib/components/documents/AnalysisResult';
	import Documents from '$lib/components/documents/documents.svelte';
	import { AnalysisProgress } from '$lib/components/analysis';
	import { OrganizePreview, OrganizeResult } from '$lib/components/organize';

	import { Button } from '$lib/components/ui/button/index.js';
	import { Input } from '$lib/components/ui/input/index.js';
	import { Spinner } from '$lib/components/ui/spinner';
	import { wrappedFetch } from '$lib/network/index.js';

	import type {
		AnalyzeResponse,
		FolderStructureResponse,
		ApplyStructureResponse
	} from '$lib/types/api';

	let { data } = $props();

	// Existing state
	let files = $state<AnalysisResult['files']>([]);
	let path: string = $state('');

	// New state for analysis
	let analysisJobId = $state<string | null>(null);
	let isAnalyzing = $state(false);
	let statusMessage = $state<{ type: 'error' | 'info'; text: string } | null>(null);

	// New state for organization
	let organizeStructure = $state<FolderStructureResponse | null>(null);
	let organizeResult = $state<ApplyStructureResponse | null>(null);
	let isGeneratingStructure = $state(false);
	let isApplyingStructure = $state(false);

	// View state
	type ViewState = 'files' | 'analyzing' | 'organize-preview' | 'organize-result';
	let activeView = $state<ViewState>('files');

	// List files (existing behavior, renamed for clarity)
	const listFiles = async (event: SubmitEvent) => {
		event.preventDefault();
		try {
			const response = await wrappedFetch<AnalysisResult>(
				`${import.meta.env.VITE_API_BASE_URL}/files?root_path=${path}`
			);
			files = response.files;
			activeView = 'files';
		} catch (e) {
			console.error('+page - listFiles - error=', e);
		}
	};

	// Start folder analysis
	const startAnalysis = async () => {
		if (!path) return;
		isAnalyzing = true;
		statusMessage = null;
		activeView = 'analyzing';
		try {
			const response = await wrappedFetch<AnalyzeResponse>(
				`${import.meta.env.VITE_API_BASE_URL}/analyze/folder`,
				{
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ root_path: path })
				}
			);

			// If no files to analyze, show message and return to files view
			if (response.files_queued === 0) {
				statusMessage = {
					type: 'info',
					text: response.message || 'No files to analyze (all files may already have .ruga metadata)'
				};
				isAnalyzing = false;
				activeView = 'files';
				return;
			}

			analysisJobId = response.job_id;
		} catch (e) {
			console.error('+page - startAnalysis - error=', e);
			statusMessage = {
				type: 'error',
				text: e instanceof Error ? e.message : 'Failed to start analysis. Is the backend running?'
			};
			isAnalyzing = false;
			activeView = 'files';
		}
	};

	// Handle analysis complete
	const onAnalysisComplete = async () => {
		isAnalyzing = false;
		analysisJobId = null;
		// Refresh file list to show updated .ruga status
		try {
			const response = await wrappedFetch<AnalysisResult>(
				`${import.meta.env.VITE_API_BASE_URL}/files?root_path=${path}`
			);
			files = response.files;
		} catch (e) {
			console.error('+page - onAnalysisComplete - error=', e);
		}
		activeView = 'files';
	};

	// Start organize flow (step 1: generate structure)
	const startOrganize = async () => {
		if (!path) return;
		isGeneratingStructure = true;
		try {
			const response = await wrappedFetch<FolderStructureResponse>(
				`${import.meta.env.VITE_API_BASE_URL}/organize/generate`,
				{
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ root_path: path })
				}
			);
			organizeStructure = response;
			activeView = 'organize-preview';
		} catch (e) {
			console.error('+page - startOrganize - error=', e);
		} finally {
			isGeneratingStructure = false;
		}
	};

	// Apply organization (step 2)
	const applyOrganization = async () => {
		if (!organizeStructure) return;
		isApplyingStructure = true;
		try {
			const response = await wrappedFetch<ApplyStructureResponse>(
				`${import.meta.env.VITE_API_BASE_URL}/organize/apply`,
				{
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ structure_id: organizeStructure.structure_id })
				}
			);
			organizeResult = response;
			activeView = 'organize-result';
		} catch (e) {
			console.error('+page - applyOrganization - error=', e);
		} finally {
			isApplyingStructure = false;
		}
	};

	// Cancel organize
	const cancelOrganize = () => {
		organizeStructure = null;
		activeView = 'files';
	};

	// Dismiss result
	const dismissResult = () => {
		organizeResult = null;
		organizeStructure = null;
		activeView = 'files';
	};

	// Derived state for file analysis status
	const filesWithoutRuga = $derived(files.filter((f) => !f.is_directory && !f.has_ruga));
	const filesWithRuga = $derived(files.filter((f) => !f.is_directory && f.has_ruga));
	const allFilesAnalyzed = $derived(files.length > 0 && filesWithoutRuga.length === 0);
	const noFilesAnalyzed = $derived(filesWithRuga.length === 0);
	const isAlreadyOrganized = $derived(path.toLowerCase().includes('_organized'));

	// Derived state for button states
	const canAnalyze = $derived(
		path.length > 2 && !isAnalyzing && !isGeneratingStructure && !allFilesAnalyzed
	);
	const canOrganize = $derived(
		path.length > 2 &&
			filesWithRuga.length > 0 &&
			!isAnalyzing &&
			!isGeneratingStructure &&
			!isAlreadyOrganized
	);

	// Button labels based on state
	const analyzeButtonLabel = $derived(
		allFilesAnalyzed ? 'All Analyzed' : `Analyze All (${filesWithoutRuga.length})`
	);
	const organizeButtonLabel = $derived(
		isAlreadyOrganized
			? 'Already Organized'
			: noFilesAnalyzed
				? 'Organize (analyze first)'
				: `Organize (${filesWithRuga.length})`
	);
</script>

<style>
	.page {
		flex-direction: column;
	}
	.docs-and-chat {
		flex-direction: row;
	}

	@media (max-width: 600px) {
		.docs-and-chat {
			flex-direction: column;
		}
	}
</style>

<div class="page p-4 flex justify-center items-center h-full w-full gap-8">
	<!-- Path input + action buttons row -->
	<form onsubmit={listFiles} class="flex w-full items-center space-x-2">
		<Input bind:value={path} placeholder="Path to your folder" class="flex-1" />
		<Button type="submit" variant="outline">List Files</Button>
		<Button type="button" onclick={startAnalysis} disabled={!canAnalyze}>
			{#if isAnalyzing}
				<Spinner class="h-4 w-4 mr-2" />
				Analyzing...
			{:else}
				{analyzeButtonLabel}
			{/if}
		</Button>
		<Button type="button" onclick={startOrganize} disabled={!canOrganize}>
			{#if isGeneratingStructure}
				<Spinner class="h-4 w-4 mr-2" />
				Loading...
			{:else}
				{organizeButtonLabel}
			{/if}
		</Button>
	</form>

	<!-- Status message -->
	{#if statusMessage}
		<div
			class="w-full p-4 rounded-md {statusMessage.type === 'error'
				? 'bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300'
				: 'bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300'}"
		>
			{statusMessage.text}
		</div>
	{/if}

	<!-- Conditional content based on activeView -->
	{#if activeView === 'analyzing' && analysisJobId}
		<div class="w-full max-w-2xl">
			<AnalysisProgress jobId={analysisJobId} onComplete={onAnalysisComplete} />
		</div>
	{:else if activeView === 'organize-preview' && organizeStructure}
		<div class="w-full max-w-4xl">
			<OrganizePreview
				structure={organizeStructure}
				onApply={applyOrganization}
				onCancel={cancelOrganize}
				loading={isApplyingStructure}
			/>
		</div>
	{:else if activeView === 'organize-result' && organizeResult}
		<div class="w-full max-w-2xl">
			<OrganizeResult result={organizeResult} onDismiss={dismissResult} />
		</div>
	{:else if files.length > 0}
		<div class="docs-and-chat flex w-full gap-8">
			<Documents data={files} {columns} />
			<Chat />
		</div>
	{/if}
</div>
