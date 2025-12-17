<style>
  :global(.badge) {
    background-color: var(--color-surface-tonal);
    color: var(--color-on-surface-variant);
  }
  .answer {
    max-height: 35vh;
    overflow-y: scroll;
  }
</style>
<script lang="ts">
  import { Button } from "$lib/components/ui/button/index.js";
  import { Textarea } from "$lib/components/ui/textarea/index.js";
  import { Badge } from "$lib/components/ui/badge/index.js";
  import BadgeCheckIcon from "@lucide/svelte/icons/badge-check";
  import { getDraggedDocument } from "$lib/store";
  import type { ChangeEventHandler } from "svelte/elements";
  import type { AnalysisDoc } from "../documents/AnalysisResult";
  import { Spinner } from "../ui/spinner";

  let error: string | null = null;
  let answer: string = $state("");
  let chatInput: string = $state("");
  let documentsInContext: AnalysisDoc[] = $state([]);

  let loading: boolean = $state(false);

  const onDropHandler = (event: DragEvent) => {
    event.preventDefault();
    const draggedDocumentFromStorage = getDraggedDocument();
    console.log('chat - draggedDocumentFromStorage=', draggedDocumentFromStorage);

    if (!documentsInContext.find(doc => doc.path === draggedDocumentFromStorage?.path)) {
      documentsInContext = [...documentsInContext, draggedDocumentFromStorage!];
    }
  };

  const onChatInputChange: ChangeEventHandler<HTMLTextAreaElement> = (event) => {
    event.preventDefault();
    const target = event.target as HTMLTextAreaElement;
    chatInput = target.value;
  };

  const onSubmit = async (event: SubmitEvent) => {
    answer = "";
    event.preventDefault();
    loading = true;
    try {
      const response = await fetch("/api/ask", {
        method: "POST",
        headers: {
          "Accept": "text/event-stream",
        },
        body: JSON.stringify({ question: "What is Svelte?" })
      });

      if (!response.ok) throw new Error(`Error: ${response.status}`);
      const reader = response?.body?.getReader();
      while (true && reader) {
        const { done, value } = await reader.read();
        if (done) {
          loading = false;
          break;
        }
        const chunk = new TextDecoder().decode(value);
        answer += chunk;
      }
      chatInput = "";
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
      console.error("Failed to submit ask:", error);
    }
  };
</script>
<form class="flex w-full flex-col gap-2 justify-center" onsubmit={onSubmit}>
    <Textarea class="min-h-0 field-sizing-fixed" rows={10} onchange={onChatInputChange} value={chatInput} placeholder="Start chatting here" ondragover={(event) => event.preventDefault()} ondrop={onDropHandler} />
    <div class="flex gap-1 flex-wrap">
      {#each documentsInContext as document (document.path)}
        <Badge variant="secondary" class="badge">
          <BadgeCheckIcon />
          {document.path}
        </Badge>
      {/each}
    </div>
    <Button type="submit">Chat</Button>
 
    <div class="flex flex-col gap-6">
    {#if loading}
      <div class="flex items-center gap-6">
        <Spinner class="spinner size-6" />
      </div>
    {/if}
    {#if answer}
      <div class="answer grid gap-2">
        {#each answer.replaceAll('\"', '').split('\\n') as line}
          <p>{line}</p>
        {/each}
      </div>
    {/if}
    </div>
</form>
