"""
Service for file operations.
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
import json

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

from ruga_file_handler import has_ruga_metadata, load_ruga_metadata
from models.schemas import FileInfo

# Skip these file types - no useful content for metadata extraction
SKIP_EXTENSIONS = {
    '.mp4', '.mp3', '.wav', '.avi', '.mov', '.mkv', '.webm', '.ogg', '.flac', '.m4a',
    '.csv', '.tsv', '.parquet', '.feather', '.pickle', '.pkl',
    '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2',
    '.exe', '.dll', '.so', '.dylib', '.bin',
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg', '.webp',
}


class FileService:
    """Service for file listing and operations."""
    
    async def list_files_recursive(self, root_path: Path) -> List[FileInfo]:
        """
        List all files and folders recursively from root_path.
        
        Returns FileInfo for each item, including whether it has a .ruga file
        and the content if it exists.
        """
        files = []
        
        # Walk through all items recursively
        for item in sorted(root_path.rglob('*')):
            # Skip .ruga files themselves
            if item.suffix == '.ruga':
                continue
            
            rel_path = item.relative_to(root_path)
            
            # Check if it has a .ruga file
            has_ruga = False
            ruga_content = None
            
            if item.is_file():
                has_ruga = has_ruga_metadata(item)
                if has_ruga:
                    metadata = load_ruga_metadata(item)
                    if metadata:
                        # Convert to dict for JSON serialization
                        ruga_content = metadata.model_dump(mode='json')
            
            file_info = FileInfo(
                path=str(rel_path),
                is_directory=item.is_dir(),
                has_ruga=has_ruga,
                ruga_content=ruga_content,
                size=item.stat().st_size if item.is_file() else None,
            )
            files.append(file_info)
        
        return files
    
    async def get_files_without_ruga(self, root_path: Path) -> List[Path]:
        """
        Get all processable files in root_path that don't have .ruga files.

        Returns list of Path objects (excludes unsupported file types).
        """
        files_without_ruga = []

        try:
            for item in root_path.rglob('*'):
                # Skip if not a file or is a .ruga file itself
                if not item.is_file() or item.suffix == '.ruga':
                    continue

                # Skip unsupported file types
                if item.suffix.lower() in SKIP_EXTENSIONS:
                    continue

                # Check if .ruga metadata exists
                if not has_ruga_metadata(item):
                    files_without_ruga.append(item)
        except Exception as e:
            # Log error but don't fail completely
            import logging
            logging.error(f"Error scanning files in {root_path}: {e}")

        return files_without_ruga
