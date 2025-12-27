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
from fastapi.responses import StreamingResponse
from pathlib import Path
from typing import List, Dict, Any, Optional
import sys
import asyncio
import json
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
from services.folder_organization_service import FolderOrganizationService
from services.vector_store_service import VectorStoreService
from services.chat_service import ChatService
from models.schemas import (
    FileInfo,
    FileListResponse,
    AnalyzeFolderRequest,
    AnalyzeFileRequest,
    AnalyzeResponse,
    JobInfo,
    JobListResponse,
    AnalysisStatus,
    JobType,
    ChatRequest,
    ChatMessage,
)
from models.folder_structure_schemas import (
    GenerateStructureRequest,
    FolderStructureResponse,
    ApplyStructureRequest,
    ApplyStructureResponse,
    OrganizeAllRequest,
    OrganizeAllResponse,
)

# Global services
file_service: Optional[FileService] = None
analysis_service: Optional[AnalysisService] = None
job_service: Optional[JobService] = None
folder_org_service: Optional[FolderOrganizationService] = None
vector_store_service: Optional[VectorStoreService] = None
chat_service: Optional[ChatService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup services."""
    global file_service, analysis_service, job_service, folder_org_service, vector_store_service, chat_service
    
    # Initialize services
    job_service = JobService()
    file_service = FileService()
    vector_store_service = VectorStoreService()
    analysis_service = AnalysisService(job_service=job_service, vector_store_service=vector_store_service)
    folder_org_service = FolderOrganizationService(vector_store_service=vector_store_service)
    chat_service = ChatService(vector_store_service=vector_store_service)
    
    print(f"✓ Vector store initialized with {vector_store_service.get_document_count()} documents")
    
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
            "GET /jobs": "List all analysis jobs (folder and file jobs)",
            "GET /jobs/{job_id}": "Get detailed job information with file statuses",
            "POST /organize/generate": "Generate organized folder structure using LLM",
            "POST /organize/apply": "Apply folder structure by copying files",
            "POST /organize/all": "Analyze, generate structure, and apply in one call",
            "POST /chat": "Chat with documents using RAG (streaming)",
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
async def list_jobs(include_file_statuses: bool = False):
    """
    List all analysis jobs with their status.
    
    Returns all jobs (both folder and file analysis jobs) with their current status.
    You can see both folder analysis jobs and file analysis jobs here.
    
    Query Parameters:
    - include_file_statuses: If True, includes individual file statuses for each job (default: False)
    """
    try:
        jobs = await job_service.list_jobs(include_file_statuses=include_file_statuses)
        return JobListResponse(jobs=jobs)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing jobs: {str(e)}")


@app.get("/jobs/{job_id}", response_model=JobInfo)
async def get_job(job_id: str):
    """
    Get detailed information about a specific job, including individual file statuses.
    
    This is useful for checking the status of all files in a folder analysis job.
    """
    try:
        job = await job_service.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        
        # Get file statuses for this job
        file_statuses = await job_service.get_job_files_status(job_id)
        job.file_statuses = file_statuses
        
        return job
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting job: {str(e)}")


@app.post("/organize/generate", response_model=FolderStructureResponse)
async def generate_folder_structure(request: GenerateStructureRequest):
    """
    Generate an organized folder structure suggestion using LLM with structured output.
    
    Analyzes all .ruga files in the root path and suggests a new folder organization
    based on category, dates, topics, and tags. The structure is organized by
    academic year and category.
    
    Request Body:
    - root_path: Path to the root directory containing .ruga files
    """
    try:
        root = Path(request.root_path)
        if not root.exists():
            raise HTTPException(status_code=404, detail=f"Root path does not exist: {request.root_path}")
        if not root.is_dir():
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {request.root_path}")
        
        # Generate structure
        structure_id, structure = await folder_org_service.generate_folder_structure(root)
        
        # Count total files
        total_files = len(structure.file_moves)
        
        return FolderStructureResponse(
            structure_id=structure_id,
            root_path=str(root.absolute()),
            structure=structure,
            total_files=total_files,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating folder structure: {str(e)}")


@app.post("/organize/apply", response_model=ApplyStructureResponse)
async def apply_folder_structure(request: ApplyStructureRequest):
    """
    Apply a folder structure by creating folders and copying files.
    
    Creates a new root folder with UUID prefix and copies all files to their
    suggested locations. Each application creates a new folder so you can
    compare different organization attempts.
    
    Request Body:
    - structure_id: UUID of the structure to apply (from /organize/generate)
    - dry_run: If true, only show what would be done without actually copying
    """
    try:
        structure_id = request.structure_id
        
        if structure_id not in folder_org_service.structures:
            raise HTTPException(status_code=404, detail=f"Structure not found: {structure_id}")
        
        # Get original root path
        original_root_str = folder_org_service.structure_roots.get(structure_id)
        if not original_root_str:
            raise HTTPException(status_code=404, detail=f"Root path not found for structure: {structure_id}")
        
        original_root = Path(original_root_str)
        if not original_root.exists():
            raise HTTPException(status_code=404, detail=f"Original root path no longer exists: {original_root_str}")
        
        # Apply structure
        new_root_path, files_copied, folders_created, errors = await folder_org_service.apply_folder_structure(
            structure_id, original_root, dry_run=request.dry_run
        )
        
        return ApplyStructureResponse(
            structure_id=structure_id,
            new_root_path=new_root_path,
            files_copied=files_copied,
            folders_created=folders_created,
            errors=errors,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error applying folder structure: {str(e)}")


@app.post("/organize/all", response_model=OrganizeAllResponse)
async def organize_all(request: OrganizeAllRequest):
    """
    Convenience endpoint that chains three operations:
    1. Analyze all files in the folder (POST /analyze/folder)
    2. Generate organized folder structure (POST /organize/generate)
    3. Apply the folder structure (POST /organize/apply)
    
    Returns the new root path with organized folders and files.
    This is designed for frontend simplicity - one call does everything.
    """
    errors = []
    analysis_job_id = None
    structure_id = None
    new_root_path = None
    files_analyzed = 0
    files_organized = 0
    folders_created = 0
    analysis_status = "unknown"
    
    try:
        root = Path(request.root_path)
        if not root.exists():
            raise HTTPException(status_code=404, detail=f"Root path does not exist: {request.root_path}")
        if not root.is_dir():
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {request.root_path}")
        
        # Step 1: Analyze folder
        try:
            analyze_request = AnalyzeFolderRequest(root_path=request.root_path)
            analyze_response = await analyze_folder(analyze_request)
            analysis_job_id = analyze_response.job_id
            files_analyzed = analyze_response.files_queued
            
            # Wait for analysis to complete if requested
            if request.wait_for_analysis and files_analyzed > 0:
                import time
                start_time = time.time()
                while time.time() - start_time < request.max_wait_seconds:
                    job = await job_service.get_job(analysis_job_id)
                    if not job:
                        errors.append("Analysis job not found")
                        break
                    
                    if job.status == AnalysisStatus.ANALYZED:
                        analysis_status = "analyzed"
                        break
                    elif job.status == AnalysisStatus.ERROR:
                        analysis_status = "error"
                        if job.error_message:
                            errors.append(f"Analysis error: {job.error_message}")
                        break
                    
                    # Wait a bit before checking again
                    await asyncio.sleep(2)
                else:
                    # Timeout
                    analysis_status = "timeout"
                    errors.append(f"Analysis did not complete within {request.max_wait_seconds} seconds")
            elif files_analyzed == 0:
                # No files to analyze, check if files already have .ruga
                analysis_status = "already_analyzed"
            else:
                analysis_status = "started"
        except Exception as e:
            errors.append(f"Error in analysis step: {str(e)}")
            if not analysis_job_id:
                raise HTTPException(status_code=500, detail=f"Failed to start analysis: {str(e)}")
        
        # Step 2: Generate folder structure
        try:
            generate_request = GenerateStructureRequest(root_path=request.root_path)
            generate_response = await generate_folder_structure(generate_request)
            structure_id = generate_response.structure_id
        except Exception as e:
            errors.append(f"Error in structure generation step: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to generate structure: {str(e)}")
        
        # Step 3: Apply folder structure
        try:
            apply_request = ApplyStructureRequest(structure_id=structure_id, dry_run=False)
            apply_response = await apply_folder_structure(apply_request)
            new_root_path = apply_response.new_root_path
            files_organized = apply_response.files_copied
            folders_created = apply_response.folders_created
            errors.extend(apply_response.errors)
        except Exception as e:
            errors.append(f"Error in structure application step: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to apply structure: {str(e)}")
        
        return OrganizeAllResponse(
            analysis_job_id=analysis_job_id or "",
            structure_id=structure_id or "",
            new_root_path=new_root_path or "",
            files_analyzed=files_analyzed,
            files_organized=files_organized,
            folders_created=folders_created,
            analysis_status=analysis_status,
            errors=errors,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in organize all: {str(e)}")


@app.post("/chat")
async def chat(request: ChatRequest):
    """
    Chat with documents using RAG. Streams responses in real-time.
    
    This endpoint uses the vector store to retrieve relevant documents and
    generates responses using a LangChain agent. Responses are streamed
    using Server-Sent Events (SSE).
    
    Request Body:
    - message: The user's message/query
    - conversation_history: Optional list of previous messages for context
    """
    try:
        if not chat_service:
            raise HTTPException(status_code=500, detail="Chat service not initialized")
        
        # Get the agent
        agent = chat_service.get_agent()
        
        # Build messages from request
        messages = []
        
        # Add conversation history if provided
        if request.conversation_history:
            for msg in request.conversation_history:
                messages.append({"role": msg.role, "content": msg.content})
        
        # Add current user message
        messages.append({"role": "user", "content": request.message})
        
        # Create async generator for streaming
        async def generate_stream():
            """Generate streaming response from agent."""
            try:
                # Run agent.stream in executor since it's synchronous
                loop = asyncio.get_event_loop()
                
                def run_agent():
                    """Run agent stream synchronously in executor."""
                    steps = []
                    for step in agent.stream(
                        {"messages": messages},
                        stream_mode="values",
                    ):
                        steps.append(step)
                    return steps
                
                # Execute in thread pool
                steps = await loop.run_in_executor(None, run_agent)
                
                # Stream the results
                for step in steps:
                    messages_list = step.get("messages", [])
                    if messages_list:
                        last_message = messages_list[-1]
                        
                        # Extract content from message
                        content = ""
                        msg_type = "ai"
                        
                        # Handle different message types
                        if hasattr(last_message, 'content'):
                            content = last_message.content or ""
                            if hasattr(last_message, 'type'):
                                msg_type = last_message.type
                        elif isinstance(last_message, dict):
                            content = last_message.get("content", "")
                            msg_type = last_message.get("type", "ai")
                        else:
                            content = str(last_message)
                        
                        # Only send non-empty content
                        if content:
                            # Format as JSON for SSE
                            data = {
                                "type": msg_type,
                                "content": content,
                            }
                            
                            # Send as SSE
                            yield f"data: {json.dumps(data)}\n\n"
                
                # Send done signal
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                
            except Exception as e:
                # Send error
                error_data = {
                    "type": "error",
                    "content": str(e),
                }
                yield f"data: {json.dumps(error_data)}\n\n"
        
        # Return streaming response
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable buffering for nginx
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in chat: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
