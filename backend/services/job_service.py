"""
Service for managing analysis jobs.
"""

from pathlib import Path
from typing import Dict, Optional, List
from uuid import UUID, uuid4
from datetime import datetime
import asyncio

# Add backend to path for imports
import sys
BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from models.schemas import JobType, AnalysisStatus, JobInfo


class JobService:
    """Service for managing analysis jobs."""
    
    def __init__(self):
        """Initialize the job service."""
        # Track jobs: job_id -> JobInfo
        self.jobs: Dict[str, JobInfo] = {}
        # Track job files: job_id -> List[file_path]
        self.job_files: Dict[str, List[str]] = {}
        # Track job file status: job_id -> file_path -> status
        self.job_file_status: Dict[str, Dict[str, AnalysisStatus]] = {}
        # Lock for thread safety
        self.lock = asyncio.Lock()
    
    def create_job(
        self,
        job_type: JobType,
        root_path: str,
        target_path: str,
        file_paths: List[str],
    ) -> str:
        """
        Create a new analysis job.
        
        Args:
            job_type: Type of job (folder or file)
            root_path: Root directory path
            target_path: The folder or file being analyzed
            file_paths: List of file paths to be analyzed
            
        Returns:
            Job ID (UUID as string)
        """
        job_id = str(uuid4())
        
        job_info = JobInfo(
            job_id=job_id,
            job_type=job_type,
            root_path=root_path,
            target_path=target_path,
            status=AnalysisStatus.PENDING,
            files_queued=len(file_paths),
            files_processed=0,
            files_failed=0,
            created_at=datetime.now().isoformat(),
        )
        
        self.jobs[job_id] = job_info
        self.job_files[job_id] = file_paths
        self.job_file_status[job_id] = {
            path: AnalysisStatus.PENDING for path in file_paths
        }
        
        return job_id
    
    async def update_job_file_status(
        self,
        job_id: str,
        file_path: str,
        status: AnalysisStatus,
        error_message: Optional[str] = None,
    ):
        """Update the status of a file within a job."""
        async with self.lock:
            if job_id not in self.jobs:
                return
            
            # Get previous status to avoid double-counting
            previous_status = self.job_file_status.get(job_id, {}).get(file_path)
            
            # Update file status
            if job_id not in self.job_file_status:
                self.job_file_status[job_id] = {}
            self.job_file_status[job_id][file_path] = status
            
            # Update job statistics (only if status changed to a final state)
            job = self.jobs[job_id]
            if status == AnalysisStatus.ANALYZED and previous_status != AnalysisStatus.ANALYZED:
                job.files_processed += 1
            elif status == AnalysisStatus.ERROR and previous_status != AnalysisStatus.ERROR:
                job.files_failed += 1
            
            # Update overall job status
            file_statuses = list(self.job_file_status[job_id].values())
            if all(s == AnalysisStatus.ANALYZED for s in file_statuses):
                job.status = AnalysisStatus.ANALYZED
            elif any(s == AnalysisStatus.IN_PROCESS for s in file_statuses):
                job.status = AnalysisStatus.IN_PROCESS
            elif any(s == AnalysisStatus.ERROR for s in file_statuses):
                if all(s in (AnalysisStatus.ANALYZED, AnalysisStatus.ERROR) for s in file_statuses):
                    job.status = AnalysisStatus.ERROR
                else:
                    job.status = AnalysisStatus.IN_PROCESS
            else:
                job.status = AnalysisStatus.PENDING
            
            if error_message:
                job.error_message = error_message
    
    async def get_job(self, job_id: str) -> Optional[JobInfo]:
        """Get job information by ID."""
        async with self.lock:
            return self.jobs.get(job_id)
    
    async def list_jobs(self, include_file_statuses: bool = False) -> List[JobInfo]:
        """
        List all jobs.
        
        Args:
            include_file_statuses: If True, include individual file statuses for each job
        """
        async with self.lock:
            jobs = list(self.jobs.values())
            if include_file_statuses:
                # Add file statuses to each job
                for job in jobs:
                    job.file_statuses = self.job_file_status.get(job.job_id, {}).copy()
            return jobs
    
    async def get_job_files_status(self, job_id: str) -> Dict[str, AnalysisStatus]:
        """Get status of all files in a job."""
        async with self.lock:
            return self.job_file_status.get(job_id, {}).copy()
