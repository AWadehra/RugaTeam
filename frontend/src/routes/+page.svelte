<script lang="ts">
  import Chat from '$lib/components/chat/chat.svelte';
  import { columns } from '$lib/components/document-table/Column';
  import type { AnalysisResult } from '$lib/components/documents/AnalysisResult';
  import Documents from '$lib/components/documents/documents.svelte';


  import { Button } from "$lib/components/ui/button/index.js";
  import { Input } from "$lib/components/ui/input/index.js";
  import { wrappedFetch } from '$lib/network/index.js';

  let { data } = $props();
  console.log('+page - columns=', columns);
  console.log('+page - data=', data);

  let files = $state<AnalysisResult['files']>([]);

  let path: string = $state('');

  const analyzeFiles = async (event: SubmitEvent) => {
    event.preventDefault();
    try {
      const response = await wrappedFetch<AnalysisResult>(`${import.meta.env.VITE_API_BASE_URL}/files?root_path=${path}`);
      files = response.files;
    } catch (e) {
      console.error('+page - analyzeFiles - error=', e);
    }
  };

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
  <form onsubmit={analyzeFiles} class="flex w-full items-center space-x-2">
    <Input bind:value={path} placeholder="Path to your folder" />
    <Button type="submit">Analyze</Button>
  </form>
  {#if files.length > 0}
    <div class="docs-and-chat flex w-full gap-8">
      <Documents data={files} columns={columns} />
      <Chat />  
    </div>
  {/if}
</div>