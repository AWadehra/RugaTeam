export type AnalysisDoc = {
  has_ruga: boolean;
  is_directory: boolean;
  path: string;
  ruga_content: boolean;
  size: number;
}
export type AnalysisResult = {
  root_path: string;
  files: AnalysisDoc[];
};