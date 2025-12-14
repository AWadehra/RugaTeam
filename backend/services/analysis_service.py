"""
Service for file analysis operations.
"""

from pathlib import Path
from typing import Dict, Optional, Set
import asyncio
from datetime import datetime

# Import from examples
import sys
PROJECT_ROOT = Path(__file__).parent.parent.parent
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

# Add backend to path for imports
BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ruga_file_handler import has_ruga_metadata, save_ruga_metadata
from process_folder import process_file_for_metadata
from models.schemas import AnalysisStatus


class AnalysisService:
    """Service for managing file analysis tasks."""
    
    def __init__(self, job_service=None):
        """Initialize the analysis service."""
        # Track status: root_path -> file_path -> status
        self.status: Dict[str, Dict[str, AnalysisStatus]] = {}
        # Track errors: root_path -> file_path -> error_message
        self.errors: Dict[str, Dict[str, str]] = {}
        # Queue of files to process: (job_id, root_path, file_path, rel_path)
        self.queue: list[tuple[Optional[str], Path, Path, str]] = []
        # Set of files currently being processed
        self.processing: Set[tuple[str, str]] = set()
        # Lock for thread safety
        self.lock = asyncio.Lock()
        # Background task running flag
        self.processing_task: Optional[asyncio.Task] = None
        # Job service reference
        self.job_service = job_service
    
    def queue_file_analysis(
        self, root_path: Path, file_path: Path, job_id: Optional[str] = None
    ):
        """
        Queue a file for analysis.
        
        Args:
            root_path: Root directory path
            file_path: Full path to the file to analyze
            job_id: Optional job ID to track this file
        """
        root_str = str(root_path.absolute())
        rel_path = str(file_path.relative_to(root_path))
        
        # Initialize status tracking for this root if needed
        if root_str not in self.status:
            self.status[root_str] = {}
            self.errors[root_str] = {}
        
        # Set status to pending
        self.status[root_str][rel_path] = AnalysisStatus.PENDING
        
        # Add to queue with job_id
        self.queue.append((job_id, root_path, file_path, rel_path))
    
    async def process_queue(self):
        """Process the queue of files to analyze. Runs continuously."""
        while True:
            async with self.lock:
                if not self.queue:
                    # No files to process, wait a bit
                    await asyncio.sleep(1)
                    continue
                
                # Get next file from queue
                job_id, root_path, file_path, rel_path = self.queue.pop(0)
                root_str = str(root_path.absolute())
                key = (root_str, rel_path)
            
            # Skip if already processing or analyzed
            if key in self.processing:
                continue
            
            # Check if already has .ruga file
            if has_ruga_metadata(file_path):
                async with self.lock:
                    if root_str not in self.status:
                        self.status[root_str] = {}
                    self.status[root_str][rel_path] = AnalysisStatus.ANALYZED
                
                # Update job if exists
                if job_id and self.job_service:
                    await self.job_service.update_job_file_status(
                        job_id, rel_path, AnalysisStatus.ANALYZED
                    )
                continue
            
            # Mark as processing
            async with self.lock:
                self.processing.add(key)
                if root_str not in self.status:
                    self.status[root_str] = {}
                self.status[root_str][rel_path] = AnalysisStatus.IN_PROCESS
            
            # Update job status to in_process
            if job_id and self.job_service:
                await self.job_service.update_job_file_status(
                    job_id, rel_path, AnalysisStatus.IN_PROCESS
                )
            
            # Process in background (run in executor to avoid blocking)
            try:
                # Run the synchronous processing function in a thread pool
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    process_file_for_metadata,
                    file_path,
                    root_path,
                )
                
                async with self.lock:
                    if result:
                        # Success
                        self.status[root_str][rel_path] = AnalysisStatus.ANALYZED
                        if root_str in self.errors and rel_path in self.errors[root_str]:
                            del self.errors[root_str][rel_path]
                        
                        # Update job
                        if job_id and self.job_service:
                            await self.job_service.update_job_file_status(
                                job_id, rel_path, AnalysisStatus.ANALYZED
                            )
                    else:
                        # Failed
                        error_msg = "Processing returned None"
                        self.status[root_str][rel_path] = AnalysisStatus.ERROR
                        if root_str not in self.errors:
                            self.errors[root_str] = {}
                        self.errors[root_str][rel_path] = error_msg
                        
                        # Update job
                        if job_id and self.job_service:
                            await self.job_service.update_job_file_status(
                                job_id, rel_path, AnalysisStatus.ERROR, error_msg
                            )
            except Exception as e:
                # Error occurred
                error_msg = str(e)
                async with self.lock:
                    self.status[root_str][rel_path] = AnalysisStatus.ERROR
                    if root_str not in self.errors:
                        self.errors[root_str] = {}
                    self.errors[root_str][rel_path] = error_msg
                
                # Update job
                if job_id and self.job_service:
                    await self.job_service.update_job_file_status(
                        job_id, rel_path, AnalysisStatus.ERROR, error_msg
                    )
            finally:
                # Remove from processing set
                async with self.lock:
                    self.processing.discard(key)
    
    async def get_file_status(
        self, root_path: Path, file_path: Path
    ) -> tuple[AnalysisStatus, Optional[str]]:
        """
        Get the analysis status for a file.
        
        Args:
            root_path: Root directory path
            file_path: Full path to the file
            
        Returns:
            Tuple of (AnalysisStatus, error_message)
        """
        root_str = str(root_path.absolute())
        rel_path = str(file_path.relative_to(root_path))
        
        # Check if file has .ruga (already analyzed)
        if has_ruga_metadata(file_path):
            return AnalysisStatus.ANALYZED, None
        
        # Check tracked status
        async with self.lock:
            if root_str in self.status and rel_path in self.status[root_str]:
                status = self.status[root_str][rel_path]
                error_msg = None
                if status == AnalysisStatus.ERROR and root_str in self.errors:
                    error_msg = self.errors[root_str].get(rel_path)
                return status, error_msg
        
        # Not found in tracking
        return AnalysisStatus.NOT_FOUND, None
    
    async def cleanup(self):
        """Cleanup resources."""
        # Cancel processing task if running
        if self.processing_task and not self.processing_task.done():
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
