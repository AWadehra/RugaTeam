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
