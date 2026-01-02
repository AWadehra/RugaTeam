import type { AnalysisDoc } from '$lib/components/documents/AnalysisResult';

export const setDraggedDocument = (doc: AnalysisDoc) => {
  localStorage.setItem('draggedDocument', JSON.stringify(doc));
}
export const getDraggedDocument = (): AnalysisDoc => {
  const doc = localStorage.getItem('draggedDocument');
  return JSON.parse(doc!) as AnalysisDoc;
}
