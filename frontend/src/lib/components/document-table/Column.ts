import type { ColumnDef } from "@tanstack/table-core";
import type { AnalysisDoc } from "../documents/AnalysisResult";

export const columns: ColumnDef<AnalysisDoc>[] = [
  {
    accessorKey: "path",
    header: "Path",
  },
];