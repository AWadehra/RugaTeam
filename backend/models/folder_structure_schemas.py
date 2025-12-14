"""
Schemas for folder structure organization.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum


class FileMove(BaseModel):
    """Represents moving a file to a new location."""
    source_path: str = Field(description="Original relative path of the file from root")
    destination_path: str = Field(description="New relative path where file should be moved")
    reason: Optional[str] = Field(None, description="Reason for this move based on metadata")


class FolderStructure(BaseModel):
    """Structured folder organization suggestion."""
    root_folder_name: str = Field(description="Name for the root folder (will be prefixed with UUID)")
    folders: List[str] = Field(description="List of folder paths to create (relative to root), e.g., ['Education/2023', 'Research/2024']")
    file_moves: List[FileMove] = Field(description="List of files to move to new locations")
    organization_rationale: str = Field(description="Brief explanation of the organization strategy")


class GenerateStructureRequest(BaseModel):
    """Request to generate folder structure."""
    root_path: str = Field(description="Path to the root directory containing .ruga files")


class FolderStructureResponse(BaseModel):
    """Response for folder structure generation."""
    structure_id: str = Field(description="UUID for this structure suggestion")
    root_path: str = Field(description="Original root path that was analyzed")
    structure: FolderStructure = Field(description="Suggested folder structure")
    total_files: int = Field(description="Total number of files to be organized")


class ApplyStructureRequest(BaseModel):
    """Request to apply a folder structure."""
    structure_id: str = Field(description="UUID of the structure to apply")
    dry_run: bool = Field(False, description="If true, only show what would be done without actually copying files")


class ApplyStructureResponse(BaseModel):
    """Response from applying folder structure."""
    structure_id: str
    new_root_path: str = Field(description="Path to the new organized folder structure")
    files_copied: int = Field(description="Number of files successfully copied")
    folders_created: int = Field(description="Number of folders created")
    errors: List[str] = Field(default_factory=list, description="List of any errors encountered")


class OrganizeAllRequest(BaseModel):
    """Request to analyze, generate structure, and apply in one call."""
    root_path: str = Field(description="Path to the root directory to organize")
    wait_for_analysis: bool = Field(True, description="Wait for analysis to complete before generating structure")
    max_wait_seconds: int = Field(300, description="Maximum seconds to wait for analysis (default: 5 minutes)")


class OrganizeAllResponse(BaseModel):
    """Response from the organize all endpoint."""
    analysis_job_id: str = Field(description="Job ID from the analysis step")
    structure_id: str = Field(description="Structure ID from the generation step")
    new_root_path: str = Field(description="Path to the new organized folder structure")
    files_analyzed: int = Field(description="Number of files analyzed")
    files_organized: int = Field(description="Number of files organized/copied")
    folders_created: int = Field(description="Number of folders created in the new structure")
    analysis_status: str = Field(description="Final status of analysis job")
    errors: List[str] = Field(default_factory=list, description="List of any errors encountered")
