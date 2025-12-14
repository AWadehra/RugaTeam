"""
Pydantic schemas for API requests and responses.
"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum
from uuid import UUID


class AnalysisStatus(str, Enum):
    """Status of file analysis."""
    ANALYZED = "analyzed"
    IN_PROCESS = "in_process"
    ERROR = "error"
    NOT_FOUND = "not_found"
    PENDING = "pending"


class JobType(str, Enum):
    """Type of analysis job."""
    FOLDER = "folder"
    FILE = "file"


class FileInfo(BaseModel):
    """Information about a file."""
    path: str
    is_directory: bool
    has_ruga: bool
    ruga_content: Optional[Dict[str, Any]] = None
    size: Optional[int] = None


class FileListResponse(BaseModel):
    """Response for listing files."""
    root_path: str
    files: List[FileInfo]


class AnalyzeFolderRequest(BaseModel):
    """Request to start folder analysis."""
    root_path: str


class AnalyzeFileRequest(BaseModel):
    """Request to start file analysis."""
    absolute_path: str  # Absolute path to the file
    root_path: Optional[str] = None  # Optional root directory (if not provided, uses parent of file)


class AnalyzeResponse(BaseModel):
    """Response from starting analysis."""
    job_id: str
    message: str
    job_type: JobType
    root_path: str
    target_path: str  # The folder or file being analyzed
    files_queued: int
    file_paths: List[str]


class StatusResponse(BaseModel):
    """Response for file status."""
    file_path: str
    root_path: str
    status: AnalysisStatus
    error_message: Optional[str] = None


class JobInfo(BaseModel):
    """Information about an analysis job."""
    job_id: str
    job_type: JobType
    root_path: str
    target_path: str
    status: AnalysisStatus
    files_queued: int
    files_processed: int
    files_failed: int
    created_at: str
    error_message: Optional[str] = None


class JobListResponse(BaseModel):
    """Response for listing jobs."""
    jobs: List[JobInfo]
