"""
FastAPI server for Ruga file analysis and management.

Endpoints:
- GET /files: List all files and folders recursively, with .ruga status
- POST /analyze/folder: Start analyzing a folder (returns job ID)
- POST /analyze/file: Start analyzing a single file (returns job ID)
- GET /jobs: List all analysis jobs with their status
- GET /status/{file_path}: Get analysis status for a specific file
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from typing import List, Dict, Any, Optional
import sys
import asyncio
from contextlib import asynccontextmanager

# Add project root to path to import from examples
PROJECT_ROOT = Path(__file__).parent.parent
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

# Add backend to path for imports
BACKEND_DIR = Path(__file__).parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.file_service import FileService
from services.analysis_service import AnalysisService
from services.job_service import JobService
from models.schemas import (
    FileInfo,
    FileListResponse,
    AnalyzeFolderRequest,
    AnalyzeFileRequest,
    AnalyzeResponse,
    StatusResponse,
    JobListResponse,
    AnalysisStatus,
    JobType,
)

# Global services
file_service: Optional[FileService] = None
analysis_service: Optional[AnalysisService] = None
job_service: Optional[JobService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup services."""
    global file_service, analysis_service, job_service
    
    # Initialize services
    job_service = JobService()
    file_service = FileService()
    analysis_service = AnalysisService(job_service=job_service)
    
    yield
    
    # Cleanup (if needed)
    if analysis_service:
        await analysis_service.cleanup()


app = FastAPI(
    title="Ruga File Analysis API",
    description="API for managing file analysis and .ruga metadata generation",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Ruga File Analysis API",
        "version": "0.1.0",
        "endpoints": {
            "GET /files": "List all files and folders with .ruga status",
            "POST /analyze/folder": "Start analyzing a folder",
            "POST /analyze/file": "Start analyzing a single file",
            "GET /jobs": "List all analysis jobs",
            "GET /status/{file_path}": "Get analysis status for a file",
        },
    }


@app.get("/files", response_model=FileListResponse)
async def list_files(root_path: str):
    """
    List all files and folders recursively from a root path.
    
    Returns whether each file has a .ruga file associated, and if so, returns the content.
    """
    try:
        root = Path(root_path)
        if not root.exists():
            raise HTTPException(status_code=404, detail=f"Root path does not exist: {root_path}")
        if not root.is_dir():
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {root_path}")
        
        files = await file_service.list_files_recursive(root)
        return FileListResponse(root_path=str(root.absolute()), files=files)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")


@app.post("/analyze/folder", response_model=AnalyzeResponse)
async def analyze_folder(request: AnalyzeFolderRequest):
    """
    Start analyzing all files in a folder and generating .ruga files as background tasks.
    
    Analyzes all files in the root_path that don't have .ruga files.
    """
    try:
        root = Path(request.root_path)
        if not root.exists():
            raise HTTPException(status_code=404, detail=f"Root path does not exist: {request.root_path}")
        if not root.is_dir():
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {request.root_path}")
        
        # Get all files without .ruga
        files_to_analyze = await file_service.get_files_without_ruga(root)
        
        # Debug: Check total files vs files without ruga
        all_files = list(root.rglob('*'))
        all_regular_files = [f for f in all_files if f.is_file() and f.suffix != '.ruga']
        
        if not files_to_analyze:
            # Check if there are any files at all
            if not all_regular_files:
                message = "No files found in folder"
            else:
                # All files already have .ruga metadata
                message = f"Found {len(all_regular_files)} file(s), but all already have .ruga metadata"
            
            # Create job even if no files to analyze
            job_id = job_service.create_job(
                job_type=JobType.FOLDER,
                root_path=str(root.absolute()),
                target_path=str(root.absolute()),
                file_paths=[],
            )
            return AnalyzeResponse(
                job_id=job_id,
                message=message,
                job_type=JobType.FOLDER,
                root_path=str(root.absolute()),
                target_path=str(root.absolute()),
                files_queued=0,
                file_paths=[],
            )
        
        # Create job
        queued_paths = [str(f.relative_to(root)) for f in files_to_analyze]
        job_id = job_service.create_job(
            job_type=JobType.FOLDER,
            root_path=str(root.absolute()),
            target_path=str(root.absolute()),
            file_paths=queued_paths,
        )
        
        # Queue files for analysis with job_id
        for file_path in files_to_analyze:
            analysis_service.queue_file_analysis(root, file_path, job_id=job_id)
        
        # Start background processing if not already running
        if analysis_service.processing_task is None or analysis_service.processing_task.done():
            analysis_service.processing_task = asyncio.create_task(analysis_service.process_queue())
        
        return AnalyzeResponse(
            job_id=job_id,
            message=f"Queued {len(queued_paths)} file(s) for analysis",
            job_type=JobType.FOLDER,
            root_path=str(root.absolute()),
            target_path=str(root.absolute()),
            files_queued=len(queued_paths),
            file_paths=queued_paths,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting folder analysis: {str(e)}")


@app.post("/analyze/file", response_model=AnalyzeResponse)
async def analyze_file(request: AnalyzeFileRequest):
    """
    Start analyzing a single file and generating a .ruga file as a background task.
    
    Provide the absolute path to the file. If root_path is not provided, 
    the parent directory of the file will be used as the root.
    """
    try:
        file_path = Path(request.absolute_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {request.absolute_path}")
        if not file_path.is_file():
            raise HTTPException(status_code=400, detail=f"Path is not a file: {request.absolute_path}")
        if file_path.suffix == ".ruga":
            raise HTTPException(status_code=400, detail="Cannot analyze .ruga files")
        
        # Determine root path
        if request.root_path:
            root = Path(request.root_path)
            if not root.exists():
                raise HTTPException(status_code=404, detail=f"Root path does not exist: {request.root_path}")
            if not root.is_dir():
                raise HTTPException(status_code=400, detail=f"Root path is not a directory: {request.root_path}")
            # Verify file is within root
            try:
                rel_path = str(file_path.relative_to(root))
            except ValueError:
                raise HTTPException(
                    status_code=400, 
                    detail=f"File {request.absolute_path} is not within root directory {request.root_path}"
                )
        else:
            # Use parent directory as root
            root = file_path.parent
            rel_path = file_path.name
        
        # Create job
        job_id = job_service.create_job(
            job_type=JobType.FILE,
            root_path=str(root.absolute()),
            target_path=rel_path,
            file_paths=[rel_path],
        )
        
        # Queue file for analysis with job_id
        analysis_service.queue_file_analysis(root, file_path, job_id=job_id)
        
        # Start background processing if not already running
        if analysis_service.processing_task is None or analysis_service.processing_task.done():
            analysis_service.processing_task = asyncio.create_task(analysis_service.process_queue())
        
        return AnalyzeResponse(
            job_id=job_id,
            message=f"Queued file for analysis",
            job_type=JobType.FILE,
            root_path=str(root.absolute()),
            target_path=rel_path,
            files_queued=1,
            file_paths=[rel_path],
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting file analysis: {str(e)}")


@app.get("/jobs", response_model=JobListResponse)
async def list_jobs():
    """
    List all analysis jobs with their status.
    
    Returns all jobs (both folder and file analysis jobs) with their current status.
    """
    try:
        jobs = await job_service.list_jobs()
        return JobListResponse(jobs=jobs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing jobs: {str(e)}")


@app.get("/status/{file_path:path}", response_model=StatusResponse)
async def get_status(file_path: str, root_path: str):
    """
    Get the analysis status for a specific file.
    
    Status can be: 'analyzed', 'in_process', 'error', or 'not_found'
    """
    try:
        root = Path(root_path)
        if not root.exists():
            raise HTTPException(status_code=404, detail=f"Root path does not exist: {root_path}")
        
        full_path = root / file_path
        if not full_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
        status, error_message = await analysis_service.get_file_status(root, full_path)
        
        return StatusResponse(
            file_path=file_path,
            root_path=str(root.absolute()),
            status=status,
            error_message=error_message,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
