<style>
	:global(.badge) {
		background-color: var(--color-surface-tonal);
		color: var(--color-on-surface-variant);
	}
	.messages {
		max-height: 50vh;
		overflow-y: auto;
	}
	.user-message {
		background-color: var(--clr-primary-a50, #e3e8ff);
		border-radius: 0.75rem 0.75rem 0 0.75rem;
	}
	.assistant-message {
		background-color: var(--clr-surface-tonal-a20, #f3f4f6);
		border-radius: 0.75rem 0.75rem 0.75rem 0;
	}
</style>

<script lang="ts">
	import { Button } from '$lib/components/ui/button/index.js';
	import { Textarea } from '$lib/components/ui/textarea/index.js';
	import { Badge } from '$lib/components/ui/badge/index.js';
	import BadgeCheckIcon from '@lucide/svelte/icons/badge-check';
	import { getDraggedDocument } from '$lib/store';
	import type { AnalysisDoc } from '../documents/AnalysisResult';
	import { Spinner } from '../ui/spinner';
	import type { ChatMessage, ChatStreamEvent } from '$lib/types/api';

	let error: string | null = $state(null);
	let chatInput: string = $state('');
	let documentsInContext: AnalysisDoc[] = $state([]);
	let conversationHistory: ChatMessage[] = $state([]);
	let streamingResponse: string = $state('');
	let loading: boolean = $state(false);

	const onDropHandler = (event: DragEvent) => {
		event.preventDefault();
		const draggedDocumentFromStorage = getDraggedDocument();

		if (!documentsInContext.find((doc) => doc.path === draggedDocumentFromStorage?.path)) {
			documentsInContext = [...documentsInContext, draggedDocumentFromStorage!];
		}
	};

	const onSubmit = async (event: SubmitEvent) => {
		event.preventDefault();
		if (!chatInput.trim()) return;

		error = null;
		loading = true;
		streamingResponse = '';

		const userMessage = chatInput.trim();

		// Add user message to history
		conversationHistory = [...conversationHistory, { role: 'user', content: userMessage }];

		try {
			const response = await fetch('/api/ask', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Accept: 'text/event-stream'
				},
				body: JSON.stringify({
					message: userMessage,
					conversation_history: conversationHistory.slice(0, -1) // Exclude current message
				})
			});

			// Check if response is JSON error instead of SSE stream
			const contentType = response.headers.get('content-type') || '';
			if (contentType.includes('application/json')) {
				const errorData = await response.json();
				throw new Error(errorData.content || `Error: ${response.status}`);
			}

			if (!response.ok) {
				throw new Error(`Error: ${response.status}`);
			}

			const reader = response.body?.getReader();
			const decoder = new TextDecoder();
			let buffer = '';

			while (reader) {
				const { done, value } = await reader.read();
				if (done) break;

				buffer += decoder.decode(value, { stream: true });
				const lines = buffer.split('\n');
				buffer = lines.pop() || '';

				for (const line of lines) {
					if (line.startsWith('data: ')) {
						const jsonStr = line.slice(6);
						try {
							const data = JSON.parse(jsonStr);
							console.log('SSE data received:', data);

							// Helper to extract string content
							const extractContent = (content: unknown): string => {
								if (typeof content === 'string') return content;
								if (Array.isArray(content)) {
									return content
										.map((c) => (typeof c === 'string' ? c : c.text || c.content || ''))
										.join('');
								}
								if (typeof content === 'object' && content !== null) {
									const obj = content as Record<string, unknown>;
									return String(obj.text || obj.content || JSON.stringify(content));
								}
								return String(content);
							};

							if ((data.type === 'ai' || data.type === 'tool') && data.content) {
								// Accumulate responses (tool results + AI response)
								const content = extractContent(data.content);
								if (data.type === 'ai') {
									// AI response - this is the main answer
									streamingResponse = content;
								} else if (data.type === 'tool') {
									// Tool result - show as context/sources (optional: you can hide this)
									// For now, we'll skip tool messages and only show the AI response
									console.log('Tool result (sources):', content.substring(0, 200) + '...');
								}
							} else if (data.type === 'done') {
								loading = false;
							} else if (data.type === 'error') {
								error = extractContent(data.content) || 'Unknown error';
								loading = false;
							}
						} catch {
							// Skip malformed JSON
						}
					}
				}
			}

			// Add assistant response to history
			if (streamingResponse) {
				conversationHistory = [
					...conversationHistory,
					{ role: 'assistant', content: streamingResponse }
				];
				streamingResponse = '';
			}

			chatInput = '';
		} catch (e) {
			error = e instanceof Error ? e.message : String(e);
			// Remove the failed user message from history
			conversationHistory = conversationHistory.slice(0, -1);
		} finally {
			loading = false;
		}
	};

	const clearHistory = () => {
		conversationHistory = [];
		error = null;
	};
</script>

<div class="flex w-full flex-col gap-4">
	<!-- Conversation history -->
	{#if conversationHistory.length > 0}
		<div class="messages flex flex-col gap-3 p-2 border rounded-md">
			{#each conversationHistory as msg}
				<div
					class="{msg.role === 'user'
						? 'user-message ml-8'
						: 'assistant-message mr-8'} p-3 text-sm"
				>
					<div class="text-xs text-muted-foreground mb-1 capitalize">{msg.role}</div>
					<div class="whitespace-pre-wrap">{msg.content}</div>
				</div>
			{/each}
			{#if streamingResponse}
				<div class="assistant-message mr-8 p-3 text-sm">
					<div class="text-xs text-muted-foreground mb-1">Assistant</div>
					<div class="whitespace-pre-wrap">{streamingResponse}</div>
				</div>
			{/if}
			{#if loading && !streamingResponse}
				<div class="flex items-center gap-2 p-3">
					<Spinner class="h-4 w-4" />
					<span class="text-sm text-muted-foreground">Thinking...</span>
				</div>
			{/if}
		</div>
		<Button variant="ghost" size="sm" onclick={clearHistory} class="self-end">
			Clear History
		</Button>
	{/if}

	<!-- Error display -->
	{#if error}
		<div class="text-red-500 text-sm p-2 border border-red-200 rounded-md">
			Error: {error}
		</div>
	{/if}

	<!-- Input form -->
	<form class="flex flex-col gap-2" onsubmit={onSubmit}>
		<Textarea
			class="min-h-0 field-sizing-fixed"
			rows={4}
			bind:value={chatInput}
			placeholder="Ask a question about your documents..."
			ondragover={(event) => event.preventDefault()}
			ondrop={onDropHandler}
			disabled={loading}
		/>

		<!-- Documents in context -->
		{#if documentsInContext.length > 0}
			<div class="flex gap-1 flex-wrap">
				{#each documentsInContext as document (document.path)}
					<Badge variant="secondary" class="badge">
						<BadgeCheckIcon />
						{document.path}
					</Badge>
				{/each}
			</div>
		{/if}

		<Button type="submit" disabled={loading || !chatInput.trim()}>
			{#if loading}
				<Spinner class="h-4 w-4 mr-2" />
				Sending...
			{:else}
				Send
			{/if}
		</Button>
	</form>
</div>
