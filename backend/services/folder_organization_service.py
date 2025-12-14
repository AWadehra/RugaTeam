"""
Service for organizing folders using LLM-structured output.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
import json
import sys

# Import from examples
PROJECT_ROOT = Path(__file__).parent.parent.parent
EXAMPLES_DIR = PROJECT_ROOT / "examples"
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

# Add backend to path for imports
BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ruga_file_handler import load_ruga_metadata, find_all_ruga_files
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from models.folder_structure_schemas import FolderStructure, FileMove


class FolderOrganizationService:
    """Service for generating and applying folder structures."""
    
    def __init__(self):
        """Initialize the folder organization service."""
        # Store generated structures: structure_id -> FolderStructure
        self.structures: Dict[str, FolderStructure] = {}
        # Store root paths: structure_id -> original_root_path
        self.structure_roots: Dict[str, str] = {}
        
        # Initialize LLM with structured output
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
        )
        self.structured_llm = self.llm.with_structured_output(FolderStructure)
    
    async def collect_ruga_metadata(self, root_path: Path) -> List[Dict[str, Any]]:
        """
        Collect all .ruga file metadata from a root path.
        
        Returns list of dictionaries with file metadata.
        """
        metadata_list = []
        
        # Find all .ruga files
        ruga_files = find_all_ruga_files(root_path)
        
        for original_path, ruga_path in ruga_files:
            if original_path is None:
                continue
            
            # Load metadata
            metadata = load_ruga_metadata(original_path)
            if metadata:
                rel_path = str(original_path.relative_to(root_path))
                metadata_dict = metadata.model_dump(mode='json')
                metadata_list.append({
                    'relative_path': rel_path,
                    'metadata': metadata_dict,
                })
        
        return metadata_list
    
    async def generate_folder_structure(
        self, root_path: Path
    ) -> tuple[str, FolderStructure]:
        """
        Generate a folder structure suggestion using LLM with structured output.
        
        Returns:
            Tuple of (structure_id, FolderStructure)
        """
        # Collect all .ruga metadata
        metadata_list = await self.collect_ruga_metadata(root_path)
        
        if not metadata_list:
            raise ValueError("No .ruga files found in the specified path. Files must be analyzed first.")
        
        # Build prompt with all metadata
        file_summaries = []
        for item in metadata_list:
            meta = item['metadata']
            file_summaries.append({
                'path': item['relative_path'],
                'title': meta.get('title', ''),
                'categories': meta.get('categories', []),
                'topics': meta.get('topics', []),
                'tags': meta.get('tags', []),
                'summary': meta.get('summary', ''),
                'authors': [a.get('name', '') for a in meta.get('authors', [])],
                'creation_date': meta.get('creation_date'),
                'last_modified_date': meta.get('last_modified_date'),
            })
        
        # Build file information text
        file_info_text = "Files and their metadata:\n"
        file_info_text += "=" * 80 + "\n\n"
        
        for i, file_info in enumerate(file_summaries, 1):
            file_info_text += f"{i}. {file_info['path']}\n"
            file_info_text += f"   Title: {file_info['title']}\n"
            if file_info['categories']:
                file_info_text += f"   Categories: {', '.join(file_info['categories'])}\n"
            if file_info['topics']:
                file_info_text += f"   Topics: {', '.join(file_info['topics'][:5])}\n"
            if file_info['tags']:
                file_info_text += f"   Tags: {', '.join(file_info['tags'][:5])}\n"
            if file_info['summary']:
                file_info_text += f"   Summary: {file_info['summary'][:200]}...\n"
            if file_info['authors']:
                file_info_text += f"   Authors: {', '.join(file_info['authors'])}\n"
            if file_info['creation_date']:
                file_info_text += f"   Creation Date: {file_info['creation_date']}\n"
            if file_info['last_modified_date']:
                file_info_text += f"   Last Modified: {file_info['last_modified_date']}\n"
            file_info_text += "\n"
        
        # Create prompt
        system_prompt = """You are an expert at organizing academic documents and presentations for a medical department.

Your task is to analyze file metadata and suggest an organized folder structure that:
- Groups files by category (Education/Capita Selecta, Education/Course, Research Meeting, Seminar, Workshop, Miscellaneous)
- Organizes by academic year when dates are available
- Uses clear, descriptive folder names
- You can decide to give a different name to the file based on the summary, suggested_filename, title, topics, tags, etc.
- Avoids deep nesting (max 3-4 levels)
- Keeps related files together
- If duplicates are found, move the duplicate to the original file's folder with a suffix indicating the duplicate number.

For each file, suggest where it should be moved based on:
- Its categories (primary organization)
- Creation or modification dates (for year-based organization)
- Topics and tags (for subcategorization)

Return a structured folder organization with:
1. A root folder name (descriptive, e.g., "Organized_Documents")
2. List of all folders to create
3. List of file moves (source -> destination)
4. Brief rationale for the organization"""

        human_prompt = f"""Analyze the following files and their metadata, then suggest an organized folder structure.

{file_info_text}

Generate a folder structure that organizes these {len(file_summaries)} files logically by category and year."""

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", human_prompt),
        ])
        
        chain = prompt | self.structured_llm
        
        # Generate structure
        structure = chain.invoke({})
        
        # Generate structure ID
        structure_id = str(uuid4())
        
        # Store structure
        self.structures[structure_id] = structure
        self.structure_roots[structure_id] = str(root_path.absolute())
        
        return structure_id, structure
    
    async def apply_folder_structure(
        self, structure_id: str, original_root: Path, dry_run: bool = False
    ) -> tuple[str, int, int, List[str]]:
        """
        Apply a folder structure by creating folders and copying files.
        
        Returns:
            Tuple of (new_root_path, files_copied, folders_created, errors)
        """
        if structure_id not in self.structures:
            raise ValueError(f"Structure not found: {structure_id}")
        
        structure = self.structures[structure_id]
        
        # Create new root folder with UUID prefix
        new_root_name = f"{structure_id[:8]}_{structure.root_folder_name}"
        new_root = original_root.parent / new_root_name
        
        errors = []
        files_copied = 0
        folders_created = 0
        
        if not dry_run:
            # Create all folders first
            for folder_path in structure.folders:
                folder_full_path = new_root / folder_path
                try:
                    folder_full_path.mkdir(parents=True, exist_ok=True)
                    folders_created += 1
                except Exception as e:
                    errors.append(f"Error creating folder {folder_path}: {str(e)}")
        
        # Copy files
        for file_move in structure.file_moves:
            source_path = original_root / file_move.source_path
            dest_path = new_root / file_move.destination_path
            
            if not source_path.exists():
                errors.append(f"Source file not found: {file_move.source_path}")
                continue
            
            if not dry_run:
                try:
                    # Create destination directory if needed
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file
                    import shutil
                    shutil.copy2(source_path, dest_path)
                    
                    # Also copy .ruga file if it exists
                    ruga_source = source_path.with_suffix(source_path.suffix + ".ruga")
                    if ruga_source.exists():
                        ruga_dest = dest_path.with_suffix(dest_path.suffix + ".ruga")
                        shutil.copy2(ruga_source, ruga_dest)
                    
                    files_copied += 1
                except Exception as e:
                    errors.append(f"Error copying {file_move.source_path}: {str(e)}")
            else:
                # Dry run - just count
                files_copied += 1
        
        return str(new_root.absolute()), files_copied, folders_created, errors
