"""
Process a folder structure:
1. Detect .ruga files (existing metadata)
2. For files without .ruga, extract content using Docling and generate metadata
3. After processing all files, suggest a new folder structure using LLM

Usage:
    python process_folder.py <folder_path>
"""

from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import defaultdict
import sys

# Import dependencies
from test_llm import (
    chain,
    build_final_record,
    FinalFileRecord,
    LLMExtractionSchema,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, AcceleratorOptions, AcceleratorDevice

# Configure accelerator to auto-detect GPU (CUDA/MPS) or fallback to CPU
_accelerator_options = AcceleratorOptions(device=AcceleratorDevice.AUTO)
_pdf_pipeline_options = PdfPipelineOptions(accelerator_options=_accelerator_options)
_pdf_format_option = PdfFormatOption(pipeline_options=_pdf_pipeline_options)

# Create a single reusable converter with GPU auto-detection
_docling_converter = DocumentConverter(
    format_options={
        InputFormat.PDF: _pdf_format_option,
    }
)


# Define helper functions for file processing
def process_txt_file(txt_path: Path) -> str:
    """Process a .txt file directly (since it's already text)."""
    return txt_path.read_text(encoding="utf-8")


def process_with_docling(file_path: Path) -> str:
    """Process a file with Docling (PDF, DOCX, etc.). Auto-detects GPU."""
    result = _docling_converter.convert(str(file_path))
    return result.document.export_to_markdown()
from ruga_file_handler import (
    has_ruga_metadata,
    save_ruga_metadata,
    load_ruga_metadata,
    get_ruga_path,
)
from langchain_core.prompts import ChatPromptTemplate

# Add backend to path for imports
import sys
BACKEND_DIR = Path(__file__).parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from utils.llm_config import get_chat_llm

# Docling converter will be initialized when needed

# Initialize LLM for folder structure suggestion (non-structured)
llm = get_chat_llm(temperature=0)


# Supported file extensions
DOCLING_SUPPORTED = {'.pdf', '.docx', '.pptx', '.xlsx'}
TEXT_EXTENSIONS = {'.txt', '.md', '.html', '.xml', '.json', '.yaml', '.yml'}

# Skip these - no useful content for metadata extraction
SKIP_EXTENSIONS = {
    # Media
    '.mp4', '.mp3', '.wav', '.avi', '.mov', '.mkv', '.webm', '.ogg', '.flac', '.m4a',
    # Data files
    '.csv', '.tsv', '.parquet', '.feather', '.pickle', '.pkl',
    # Archives
    '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2',
    # Executables/binaries
    '.exe', '.dll', '.so', '.dylib', '.bin',
    # Images (no text content)
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg', '.webp',
}


def get_file_content(file_path: Path) -> str:
    """
    Extract content from a file using Docling if supported, otherwise read directly.

    Args:
        file_path: Path to the file

    Returns:
        Extracted text content
    """
    file_ext = file_path.suffix.lower()

    # Skip files with no useful text content
    if file_ext in SKIP_EXTENSIONS:
        return None  # Signal to skip this file entirely

    if file_ext in TEXT_EXTENSIONS or file_ext == '.txt':
        # Read text files directly
        return process_txt_file(file_path)
    elif file_ext in DOCLING_SUPPORTED:
        # Use Docling for supported formats
        try:
            return process_with_docling(file_path)
        except Exception as e:
            print(f"⚠️  Error processing {file_ext} with Docling: {e}")
            # Fallback: try to read as text
            try:
                return file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                return f"[Could not extract content from {file_path.name}]"
    else:
        # Unknown format - try Docling first, then fallback to text reading
        print(f"  ⚠️  Unknown format {file_ext}, attempting to process...")
        try:
            return process_with_docling(file_path)
        except Exception:
            # Fallback to reading as text
            try:
                return file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                return f"[Could not extract content from {file_path.name}]"


def process_file_for_metadata(file_path: Path, folder_root: Path) -> Optional[FinalFileRecord]:
    """
    Process a single file to generate .ruga metadata.

    Args:
        file_path: Path to the file to process
        folder_root: Root folder path (for relative paths)

    Returns:
        FinalFileRecord if successful, None otherwise
    """
    # Skip unsupported file types early
    if file_path.suffix.lower() in SKIP_EXTENSIONS:
        print(f"  ⏭️  Skipping: {file_path.relative_to(folder_root)}")
        return None

    print(f"\n📄 Processing: {file_path.relative_to(folder_root)}")

    try:
        # Extract content
        print("  📖 Extracting content...")
        content = get_file_content(file_path)

        if not content or len(content.strip()) < 10:
            print(f"  ⚠️  File appears empty or content extraction failed")
            return None

        # Run LLM extraction
        print("  🤖 Running LLM extraction...")
        llm_result = chain.invoke({"text": content})

        # Build final record
        print("  📊 Building final record...")
        final_record = build_final_record(
            llm_result=llm_result,
            file_path=file_path,
            llm_model_name="gpt-4o-mini",
        )

        # Save to .ruga file
        print("  💾 Saving .ruga metadata...")
        ruga_path = save_ruga_metadata(file_path, final_record)
        print(f"  ✅ Saved: {ruga_path.name}")

        return final_record

    except Exception as e:
        print(f"  ❌ Error processing file: {e}")
        return None


def collect_file_summaries(folder_path: Path) -> List[Dict[str, Any]]:
    """
    Collect summaries of all files with their metadata.
    
    Args:
        folder_path: Root folder path
        
    Returns:
        List of dictionaries with file info and metadata
    """
    file_summaries = []
    
    # Find all files (excluding .ruga files)
    for file_path in folder_path.rglob('*'):
        if file_path.is_file() and file_path.suffix != '.ruga':
            rel_path = file_path.relative_to(folder_path)
            
            # Try to load existing metadata
            metadata = load_ruga_metadata(file_path)
            
            if metadata:
                file_summaries.append({
                    'path': str(rel_path),
                    'title': metadata.title,
                    'category': metadata.category,
                    'topics': metadata.topics,
                    'tags': metadata.tags,
                    'summary': metadata.summary,
                    'authors': [a.name for a in metadata.authors],
                    'creation_date': str(metadata.creation_date) if metadata.creation_date else None,
                })
            else:
                # File without metadata - use basic info
                file_summaries.append({
                    'path': str(rel_path),
                    'title': file_path.stem,
                    'category': 'Miscellaneous',
                    'topics': [],
                    'tags': [],
                    'summary': f"File: {file_path.name}",
                    'authors': [],
                    'creation_date': None,
                })
    
    return file_summaries


def get_current_folder_structure(folder_path: Path) -> str:
    """
    Get a text representation of the current folder structure.
    
    Args:
        folder_path: Root folder path
        
    Returns:
        String representation of folder structure
    """
    structure_lines = []
    
    def build_tree(node: Path, prefix: str = "", is_last: bool = True, depth: int = 0, max_depth: int = 5):
        """Recursively build tree structure."""
        if depth > max_depth:
            return
        
        # Get items in this directory
        try:
            items = sorted(node.iterdir(), key=lambda x: (x.is_file(), x.name))
        except PermissionError:
            return
        
        for i, item in enumerate(items):
            # Skip .ruga files in display
            if item.suffix == '.ruga':
                continue
                
            is_last_item = (i == len(items) - 1)
            current_prefix = "└── " if is_last_item else "├── "
            next_prefix = prefix + ("    " if is_last_item else "│   ")
            
            if item.is_dir():
                structure_lines.append(f"{prefix}{current_prefix}📁 {item.name}/")
                build_tree(item, next_prefix, is_last_item, depth + 1, max_depth)
            else:
                structure_lines.append(f"{prefix}{current_prefix}📄 {item.name}")
    
    structure_lines.append(f"📂 {folder_path.name}/")
    build_tree(folder_path, "", True, 0)
    
    return "\n".join(structure_lines)


def suggest_folder_structure(folder_path: Path, file_summaries: List[Dict[str, Any]]) -> str:
    """
    Use LLM to suggest a new folder structure based on file metadata.
    
    Args:
        folder_path: Root folder path
        file_summaries: List of file summaries with metadata
        
    Returns:
        LLM-suggested folder structure as text
    """
    current_structure = get_current_folder_structure(folder_path)
    
    # Build file summary text
    file_info_text = "\n\nFiles and their metadata:\n"
    file_info_text += "=" * 80 + "\n"
    
    for i, file_info in enumerate(file_summaries, 1):
        file_info_text += f"\n{i}. {file_info['path']}\n"
        file_info_text += f"   Title: {file_info['title']}\n"
        file_info_text += f"   Category: {file_info['category']}\n"
        if file_info['topics']:
            file_info_text += f"   Topics: {', '.join(file_info['topics'][:5])}\n"  # First 5 topics
        if file_info['tags']:
            file_info_text += f"   Tags: {', '.join(file_info['tags'][:5])}\n"  # First 5 tags
        if file_info['summary']:
            file_info_text += f"   Summary: {file_info['summary'][:200]}...\n"  # First 200 chars
        if file_info['authors']:
            file_info_text += f"   Authors: {', '.join(file_info['authors'])}\n"
        if file_info['creation_date']:
            file_info_text += f"   Date: {file_info['creation_date']}\n"
    
    prompt_text = f"""You are helping organize a folder structure for an academic medical department.

Current folder structure:
{current_structure}

{file_info_text}

Based on the file metadata (category, topics, tags, dates, authors), suggest a new, improved folder structure.

The desired organization should:
- Group files by category (Education, Capita Selecta, Research Meeting, World Headlines, Miscellaneous)
- Organize by year when relevant
- Use clear, descriptive folder names
- Avoid deep nesting (max 3-4 levels)
- Keep related files together

Provide your suggestion as a text tree structure using the same format as shown above (with 📁 and 📄 emojis and tree characters).

Suggested new folder structure:
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert at organizing academic documents and presentations. Provide clear, logical folder structures."),
        ("human", prompt_text),
    ])
    
    chain_prompt = prompt | llm
    
    print("\n🤖 Asking LLM to suggest new folder structure...")
    response = chain_prompt.invoke({})
    
    return response.content


def process_folder(folder_path: Path, skip_existing: bool = True) -> Dict[str, Any]:
    """
    Main function to process a folder structure.
    
    Args:
        folder_path: Path to the folder to process
        skip_existing: If True, skip files that already have .ruga metadata
        
    Returns:
        Dictionary with processing results
    """
    if not folder_path.exists():
        raise ValueError(f"Folder does not exist: {folder_path}")
    
    if not folder_path.is_dir():
        raise ValueError(f"Path is not a directory: {folder_path}")
    
    print("=" * 80)
    print(f"Processing folder: {folder_path}")
    print("=" * 80)
    
    # Step 1: Find all files and check for .ruga metadata
    print("\n📋 Step 1: Scanning folder for files...")
    
    files_to_process = []
    files_with_metadata = []
    
    for file_path in folder_path.rglob('*'):
        if file_path.is_file() and file_path.suffix != '.ruga':
            if has_ruga_metadata(file_path):
                files_with_metadata.append(file_path)
            else:
                files_to_process.append(file_path)
    
    print(f"  ✅ Found {len(files_to_process)} files without metadata")
    print(f"  ✅ Found {len(files_with_metadata)} files with existing metadata")
    
    # Step 2: Process files without metadata
    if files_to_process:
        print(f"\n📝 Step 2: Processing {len(files_to_process)} files...")
        processed_count = 0
        failed_count = 0
        
        for file_path in files_to_process:
            result = process_file_for_metadata(file_path, folder_path)
            if result:
                processed_count += 1
            else:
                failed_count += 1
        
        print(f"\n  ✅ Successfully processed: {processed_count}")
        if failed_count > 0:
            print(f"  ❌ Failed: {failed_count}")
    else:
        print("\n📝 Step 2: All files already have metadata. Skipping processing.")
    
    # Step 3: Collect all file summaries
    print("\n📊 Step 3: Collecting file summaries...")
    file_summaries = collect_file_summaries(folder_path)
    print(f"  ✅ Collected {len(file_summaries)} file summaries")
    
    # Step 4: Suggest new folder structure
    print("\n🗂️  Step 4: Generating folder structure suggestion...")
    suggested_structure = suggest_folder_structure(folder_path, file_summaries)
    
    print("\n" + "=" * 80)
    print("SUGGESTED NEW FOLDER STRUCTURE")
    print("=" * 80)
    print(suggested_structure)
    print("=" * 80)
    
    return {
        'files_processed': len(files_to_process),
        'files_with_metadata': len(files_with_metadata),
        'total_files': len(file_summaries),
        'suggested_structure': suggested_structure,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python process_folder.py <folder_path>")
        print("\nExample:")
        print("  python process_folder.py examples/unstructured_folder")
        sys.exit(1)
    
    folder_path = Path(sys.argv[1])
    
    try:
        results = process_folder(folder_path)
        
        print("\n" + "=" * 80)
        print("Processing Complete!")
        print("=" * 80)
        print(f"Files processed: {results['files_processed']}")
        print(f"Files with existing metadata: {results['files_with_metadata']}")
        print(f"Total files: {results['total_files']}")
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

