/**
 * TypeScript types matching backend Pydantic schemas.
 */

// Enums
export type AnalysisStatus = 'analyzed' | 'in_process' | 'error' | 'not_found' | 'pending';
export type JobType = 'folder' | 'file';

// File types
export interface FileInfo {
	path: string;
	is_directory: boolean;
	has_ruga: boolean;
	ruga_content?: Record<string, unknown> | null;
	size?: number | null;
}

export interface FileListResponse {
	root_path: string;
	files: FileInfo[];
}

// Analysis types
export interface AnalyzeFolderRequest {
	root_path: string;
}

export interface AnalyzeResponse {
	job_id: string;
	message: string;
	job_type: JobType;
	root_path: string;
	target_path: string;
	files_queued: number;
	file_paths: string[];
}

export interface JobInfo {
	job_id: string;
	job_type: JobType;
	root_path: string;
	target_path: string;
	status: AnalysisStatus;
	files_queued: number;
	files_processed: number;
	files_failed: number;
	created_at: string;
	error_message?: string | null;
	file_statuses?: Record<string, AnalysisStatus> | null;
}

export interface JobListResponse {
	jobs: JobInfo[];
}

// Organization types
export interface FileMove {
	source_path: string;
	destination_path: string;
	reason?: string | null;
}

export interface FolderStructure {
	root_folder_name: string;
	folders: string[];
	file_moves: FileMove[];
	organization_rationale: string;
}

export interface GenerateStructureRequest {
	root_path: string;
}

export interface FolderStructureResponse {
	structure_id: string;
	root_path: string;
	structure: FolderStructure;
	total_files: number;
}

export interface ApplyStructureRequest {
	structure_id: string;
	dry_run?: boolean;
}

export interface ApplyStructureResponse {
	structure_id: string;
	new_root_path: string;
	files_copied: number;
	folders_created: number;
	errors: string[];
}

// Chat types
export interface ChatMessage {
	role: 'user' | 'assistant';
	content: string;
}

export interface ChatRequest {
	message: string;
	conversation_history?: ChatMessage[];
}

export interface ChatStreamEvent {
	type: 'ai' | 'human' | 'tool' | 'done' | 'error';
	content?: string;
}
