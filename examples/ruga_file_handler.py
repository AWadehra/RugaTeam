"""
Handle .ruga metadata files.

A .ruga file contains JSON metadata about a file. It has the same name as the
original file but with a .ruga extension. If a .ruga file exists, it means
we already have metadata available for that file.

Example:
    original_file.txt -> original_file.txt.ruga
    document.pdf -> document.pdf.ruga
"""

from pathlib import Path
from typing import Optional
import json
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ValidationError

# Import the FinalFileRecord from test_llm.py
# We'll import it dynamically to avoid circular dependencies
import sys
from pathlib import Path

# Add examples directory to path for imports
examples_dir = Path(__file__).parent
if str(examples_dir) not in sys.path:
    sys.path.insert(0, str(examples_dir))

try:
    from test_llm import FinalFileRecord, Author, FinalGlossaryTerm
except ImportError:
    # Fallback definitions if test_llm is not available
    from pydantic import BaseModel, Field
    from typing import List, Optional
    from uuid import UUID
    from datetime import date, datetime
    
    class Author(BaseModel):
        name: str
        orcid: Optional[str] = None
    
    class FinalGlossaryTerm(BaseModel):
        term: str
        definition: Optional[str] = None
        source: str = "llm_extracted"
    
    class FinalFileRecord(BaseModel):
        file_id: UUID
        original_path: str
        file_type: str
        content_hash: str
        title: str
        suggested_filename: str
        categories: List[str]
        creation_date: Optional[date] = None
        last_modified_date: datetime
        analysis_date: datetime
        authors: List[Author]
        topics: List[str]
        tags: List[str]
        summary: str
        glossary_terms: List[FinalGlossaryTerm]
        possible_duplicate: bool
        reviewed_by_human: bool = False
        llm_model: str
        extracted_at: datetime


def get_ruga_path(file_path: Path) -> Path:
    """
    Get the .ruga file path for a given file.
    
    Args:
        file_path: Path to the original file
        
    Returns:
        Path to the corresponding .ruga file
    """
    return file_path.with_suffix(file_path.suffix + ".ruga")


def has_ruga_metadata(file_path: Path) -> bool:
    """
    Check if a .ruga metadata file exists for the given file.
    
    Args:
        file_path: Path to the original file
        
    Returns:
        True if .ruga file exists, False otherwise
    """
    ruga_path = get_ruga_path(file_path)
    return ruga_path.exists() and ruga_path.is_file()


def save_ruga_metadata(file_path: Path, metadata: FinalFileRecord) -> Path:
    """
    Save metadata to a .ruga file.
    
    Args:
        file_path: Path to the original file
        metadata: FinalFileRecord containing the metadata
        
    Returns:
        Path to the created .ruga file
        
    Raises:
        ValueError: If file_path is not a valid file path
    """
    if not file_path.exists():
        raise ValueError(f"File does not exist: {file_path}")
    
    ruga_path = get_ruga_path(file_path)
    
    # Convert to JSON-serializable dict
    metadata_dict = metadata.model_dump(mode='json')
    
    # Write to .ruga file with pretty formatting
    ruga_path.write_text(
        json.dumps(metadata_dict, indent=2, default=str, ensure_ascii=False),
        encoding="utf-8"
    )
    
    return ruga_path


def load_ruga_metadata(file_path: Path) -> Optional[FinalFileRecord]:
    """
    Load metadata from a .ruga file.
    
    Args:
        file_path: Path to the original file (or directly to .ruga file)
        
    Returns:
        FinalFileRecord if .ruga file exists and is valid, None otherwise
    """
    # If the path already ends with .ruga, use it directly
    if file_path.suffix == ".ruga":
        ruga_path = file_path
    else:
        ruga_path = get_ruga_path(file_path)
    
    if not ruga_path.exists():
        return None
    
    try:
        # Read and parse JSON
        content = ruga_path.read_text(encoding="utf-8")
        metadata_dict = json.loads(content)
        
        # Convert to FinalFileRecord
        return FinalFileRecord(**metadata_dict)
    except (json.JSONDecodeError, ValidationError, Exception) as e:
        print(f"⚠️  Error loading .ruga file {ruga_path}: {e}")
        return None


def delete_ruga_metadata(file_path: Path) -> bool:
    """
    Delete the .ruga metadata file for a given file.
    
    Args:
        file_path: Path to the original file
        
    Returns:
        True if file was deleted, False if it didn't exist
    """
    ruga_path = get_ruga_path(file_path)
    
    if ruga_path.exists():
        ruga_path.unlink()
        return True
    return False


def find_all_ruga_files(folder_path: Path) -> list[tuple[Optional[Path], Path]]:
    """
    Find all .ruga files in a folder and return tuples of (original_file, ruga_file).
    
    Args:
        folder_path: Path to folder to search
        
    Returns:
        List of tuples: (original_file_path, ruga_file_path)
    """
    ruga_files = []
    
    if not folder_path.exists() or not folder_path.is_dir():
        return ruga_files
    
    # Find all .ruga files
    for ruga_path in folder_path.rglob("*.ruga"):
        # Try to determine the original file path
        # .ruga files have format: original_file.ext.ruga
        # So we need to remove just the .ruga suffix
        if len(ruga_path.suffixes) >= 2:
            # Has multiple suffixes, e.g., .txt.ruga
            # Remove the last suffix (.ruga) to get original
            original_path = ruga_path.with_suffix('').with_suffix(ruga_path.suffixes[-2])
        else:
            # Only .ruga suffix, original had no extension
            original_path = ruga_path.with_suffix('')
        
        # If the original file exists, add it to the list
        if original_path.exists():
            ruga_files.append((original_path, ruga_path))
        else:
            # Original file doesn't exist, but we still have the .ruga file
            ruga_files.append((None, ruga_path))
    
    return ruga_files


def get_metadata_summary(metadata: FinalFileRecord) -> dict:
    """
    Get a summary of the metadata (useful for quick inspection).
    
    Args:
        metadata: FinalFileRecord
        
    Returns:
        Dictionary with key metadata fields
    """
    return {
        "file_id": str(metadata.file_id),
        "title": metadata.title,
        "categories": metadata.categories,
        "topics": metadata.topics[:5] if len(metadata.topics) > 5 else metadata.topics,  # First 5 topics
        "tags": metadata.tags,
        "authors": [a.name for a in metadata.authors],
        "creation_date": str(metadata.creation_date) if metadata.creation_date else None,
        "reviewed_by_human": metadata.reviewed_by_human,
        "possible_duplicate": metadata.possible_duplicate,
    }


if __name__ == "__main__":
    """Example usage and testing."""
    from pathlib import Path
    
    # Get the examples directory
    examples_dir = Path(__file__).parent
    unstructured_folder = examples_dir / "unstructured_folder"
    
    print("=" * 80)
    print("Ruga File Handler - Example Usage")
    print("=" * 80)
    
    # Find any .txt file to use as example
    example_file = None
    txt_files = list(unstructured_folder.rglob("*.txt")) if unstructured_folder.exists() else []
    
    if txt_files:
        example_file = txt_files[0]
        print(f"\n📄 Example file: {example_file.relative_to(examples_dir)}")
        
        has_metadata = has_ruga_metadata(example_file)
        print(f"Has .ruga metadata: {has_metadata}")
        
        if has_metadata:
            metadata = load_ruga_metadata(example_file)
            if metadata:
                print("\n📋 Metadata Summary:")
                summary = get_metadata_summary(metadata)
                for key, value in summary.items():
                    print(f"  {key}: {value}")
        else:
            print("\n⚠️  No .ruga file found. Metadata would need to be generated first.")
            print(f"   (Use test_ruga_handler.py to generate metadata)")
    else:
        print(f"\n⚠️  No .txt files found in {unstructured_folder}")
    
    # Find all .ruga files in unstructured_folder
    print("\n" + "=" * 80)
    print("Scanning for .ruga files...")
    print("=" * 80)
    
    if unstructured_folder.exists():
        ruga_files = find_all_ruga_files(unstructured_folder)
        
        if ruga_files:
            print(f"\nFound {len(ruga_files)} .ruga file(s):")
            for original, ruga in ruga_files:
                if original:
                    rel_path = original.relative_to(examples_dir)
                    print(f"  📄 {rel_path} -> {ruga.name}")
                else:
                    print(f"  ⚠️  {ruga.name} (original file not found)")
        else:
            print("\nNo .ruga files found in unstructured_folder")
    else:
        print(f"\n⚠️  Folder not found: {unstructured_folder}")

