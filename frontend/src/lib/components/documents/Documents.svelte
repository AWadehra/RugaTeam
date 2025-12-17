<script lang="ts" generics="TData, TValue">
   import {
     createSvelteTable,
     FlexRender,
   } from "$lib/components/ui/data-table/index.js";
   import { getCoreRowModel, type ColumnDef } from "@tanstack/table-core";

  import * as Table from "$lib/components/ui/table/index.js";
  import { setDraggedDocument } from "$lib/store";
  import type { AnalysisDoc } from "./AnalysisResult";
 
  type DataTableProps<TData, TValue> = {
    columns: ColumnDef<TData, TValue>[];
    data: TData[];
  };
  let { data, columns }: DataTableProps<TData, TValue> = $props();
 
  const onDragStart = (document: TData) => {
    console.log('documents - onDragStart - document=', document);
    setDraggedDocument(document as AnalysisDoc);
  };
  const table = createSvelteTable({
    get data() {
      return data;
    },
    columns,
    getCoreRowModel: getCoreRowModel(),
  });
</script>
<style>
  [draggable=true] {
    cursor: grab;
  }
  [draggable=true]:active {
    cursor: grabbing;
  }
  :global(.header) {
    background-color: var(--slate3);
  } 
</style>
<div class="rounded-md border shadow-md">
  <div class="h-[80vh] relative overflow-y-auto overflow-x-hidden">
    <Table.Root class="relative min-h-50">
      <Table.Body>
        {#each table.getRowModel().rows as row (row.id)}
          <Table.Row ondragstart={() => onDragStart(row.original)} class="draggable" draggable data-state={row.getIsSelected() && "selected"}>
            {#each row.getVisibleCells() as cell (cell.id)}
              <Table.Cell>
                <FlexRender
                  content={cell.column.columnDef.cell}
                  context={cell.getContext()}
                />
              </Table.Cell>
            {/each}
          </Table.Row>
        {:else}
          <Table.Row>
            <Table.Cell colspan={columns.length} class="h-24 text-center">
              No results.
            </Table.Cell>
          </Table.Row>
        {/each}
      </Table.Body>
    </Table.Root>
  </div>
</div>