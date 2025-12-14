"""
API client for RUGA server.
"""

import httpx
from typing import Optional, List, Dict, Any, Iterator
from pathlib import Path
import json


class RugaAPIClient:
    """Client for interacting with RUGA server API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize the API client.
        
        Args:
            base_url: Base URL of the RUGA server (default: http://localhost:8000)
        """
        self.base_url = base_url.rstrip('/')
        self.client = httpx.Client(timeout=300.0)  # 5 minute timeout for long operations
    
    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a GET request."""
        url = f"{self.base_url}{endpoint}"
        response = self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def _post(self, endpoint: str, json_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a POST request."""
        url = f"{self.base_url}{endpoint}"
        response = self.client.post(url, json=json_data)
        response.raise_for_status()
        return response.json()
    
    def _post_stream(self, endpoint: str, json_data: Optional[Dict] = None) -> Iterator[str]:
        """Make a streaming POST request (for chat)."""
        url = f"{self.base_url}{endpoint}"
        with self.client.stream("POST", url, json=json_data) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]  # Remove "data: " prefix
                    try:
                        data = json.loads(data_str)
                        yield data
                    except json.JSONDecodeError:
                        continue
    
    def get_info(self) -> Dict[str, Any]:
        """Get API information."""
        return self._get("/")
    
    def list_files(self, root_path: str) -> Dict[str, Any]:
        """
        List all files and folders recursively.
        
        Args:
            root_path: Root directory path
            
        Returns:
            File list response
        """
        return self._get("/files", params={"root_path": root_path})
    
    def analyze_folder(self, root_path: str) -> Dict[str, Any]:
        """
        Start analyzing a folder.
        
        Args:
            root_path: Root directory path
            
        Returns:
            Analysis response with job_id
        """
        return self._post("/analyze/folder", json_data={"root_path": root_path})
    
    def analyze_file(self, absolute_path: str, root_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Start analyzing a single file.
        
        Args:
            absolute_path: Absolute path to the file
            root_path: Optional root directory (if not provided, uses parent of file)
            
        Returns:
            Analysis response with job_id
        """
        data = {"absolute_path": absolute_path}
        if root_path:
            data["root_path"] = root_path
        return self._post("/analyze/file", json_data=data)
    
    def list_jobs(self, include_file_statuses: bool = False) -> Dict[str, Any]:
        """
        List all analysis jobs.
        
        Args:
            include_file_statuses: If True, includes individual file statuses
            
        Returns:
            Job list response
        """
        return self._get("/jobs", params={"include_file_statuses": include_file_statuses})
    
    def get_job(self, job_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific job.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job information
        """
        return self._get(f"/jobs/{job_id}")
    
    def generate_structure(self, root_path: str) -> Dict[str, Any]:
        """
        Generate an organized folder structure suggestion.
        
        Args:
            root_path: Root directory path containing .ruga files
            
        Returns:
            Folder structure response
        """
        return self._post("/organize/generate", json_data={"root_path": root_path})
    
    def apply_structure(self, structure_id: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Apply a folder structure.
        
        Args:
            structure_id: UUID of the structure to apply
            dry_run: If True, only show what would be done without copying
            
        Returns:
            Apply structure response
        """
        return self._post("/organize/apply", json_data={"structure_id": structure_id, "dry_run": dry_run})
    
    def organize_all(
        self,
        root_path: str,
        wait_for_analysis: bool = True,
        max_wait_seconds: int = 300
    ) -> Dict[str, Any]:
        """
        Analyze, generate structure, and apply in one call.
        
        Args:
            root_path: Root directory path
            wait_for_analysis: Wait for analysis to complete before generating structure
            max_wait_seconds: Maximum seconds to wait for analysis
            
        Returns:
            Organize all response
        """
        return self._post(
            "/organize/all",
            json_data={
                "root_path": root_path,
                "wait_for_analysis": wait_for_analysis,
                "max_wait_seconds": max_wait_seconds,
            }
        )
    
    def chat(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Iterator[Dict[str, Any]]:
        """
        Chat with documents using RAG (streaming).
        
        Args:
            message: User's message/query
            conversation_history: Optional list of previous messages
            
        Yields:
            Streaming response chunks
        """
        data = {"message": message}
        if conversation_history:
            data["conversation_history"] = conversation_history
        return self._post_stream("/chat", json_data=data)
    
    def close(self):
        """Close the HTTP client."""
        self.client.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
