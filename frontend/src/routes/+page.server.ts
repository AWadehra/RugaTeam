import { wrappedFetch } from "$lib/network";
import type { KnowledgeDocument } from "$lib/components/documents";

export async function load() {
  const documents = (await wrappedFetch<{default: KnowledgeDocument[]}>(`${import.meta.env.VITE_API_BASE_URL}/list`)).default;
  return {
    documents: documents,
  };
}