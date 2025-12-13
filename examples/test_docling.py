"""
Test Docling document converter with local files from unstructured_folder.

Note: Docling doesn't support .txt files directly (they're already text).
- .txt files are read directly as text
- PDF files (converted from .txt) are processed with Docling to demonstrate conversion
"""

from pathlib import Path
from collections import defaultdict
from docling.document_converter import DocumentConverter

# Get the unstructured_folder path
UNSTRUCTURED_FOLDER = Path(__file__).parent / "unstructured_folder"

# Initialize converter
converter = DocumentConverter()


def analyze_folder_structure(folder_path: Path) -> dict:
    """
    Analyze the folder structure and return a dictionary with:
    - 'folders': list of all subdirectories
    - 'txt_files': list of all .txt files
    - 'pdf_files': list of all .pdf files
    - 'other_files': list of other file types
    - 'file_tree': nested structure representation
    """
    result = {
        'folders': [],
        'txt_files': [],
        'pdf_files': [],
        'other_files': [],
        'file_tree': defaultdict(list)
    }
    
    if not folder_path.exists():
        return result
    
    # Recursively scan all files and folders
    for item in folder_path.rglob('*'):
        if item.is_dir():
            result['folders'].append(item.relative_to(folder_path))
        elif item.is_file():
            rel_path = item.relative_to(folder_path)
            parent_dir = rel_path.parent
            
            if item.suffix.lower() == '.txt':
                result['txt_files'].append(rel_path)
                result['file_tree'][str(parent_dir)].append(('txt', rel_path))
            elif item.suffix.lower() == '.pdf':
                result['pdf_files'].append(rel_path)
                result['file_tree'][str(parent_dir)].append(('pdf', rel_path))
            else:
                result['other_files'].append(rel_path)
                result['file_tree'][str(parent_dir)].append(('other', rel_path))
    
    return result


def find_matching_pdf(txt_path: Path, pdf_files: list[Path]) -> Path | None:
    """Find a PDF file that matches a TXT file (same stem name)."""
    txt_stem = txt_path.stem
    for pdf_path in pdf_files:
        if pdf_path.stem == txt_stem:
            return pdf_path
    return None


def process_txt_file(txt_path: Path) -> str:
    """Process a .txt file directly (since it's already text)."""
    return txt_path.read_text(encoding="utf-8")


def process_with_docling(file_path: Path) -> str:
    """Process a file with Docling (PDF, DOCX, etc.)."""
    result = converter.convert(str(file_path))
    return result.document.export_to_markdown()


# Analyze folder structure
print("=" * 80)
print("Analyzing folder structure...")
print("=" * 80)

folder_analysis = analyze_folder_structure(UNSTRUCTURED_FOLDER)

print(f"\n📁 Found {len(folder_analysis['folders'])} folders")
print(f"📝 Found {len(folder_analysis['txt_files'])} .txt files")
print(f"📄 Found {len(folder_analysis['pdf_files'])} .pdf files")
if folder_analysis['other_files']:
    print(f"📎 Found {len(folder_analysis['other_files'])} other files")

print("\n" + "=" * 80)
print("Folder Structure:")
print("=" * 80)
for folder, files in sorted(folder_analysis['file_tree'].items()):
    folder_name = folder if folder != '.' else 'root'
    print(f"\n📂 {folder_name}/")
    for file_type, file_path in sorted(files):
        icon = "📝" if file_type == "txt" else "📄" if file_type == "pdf" else "📎"
        print(f"  {icon} {file_path.name}")

print("\n" + "=" * 80)
print("Testing Docling with files from unstructured_folder")
print("=" * 80)

# Process a sample of files (first few txt files and their matching PDFs)
sample_txt_files = folder_analysis['txt_files'][:4]  # Take first 4 txt files

for txt_rel_path in sample_txt_files:
    txt_path = UNSTRUCTURED_FOLDER / txt_rel_path
    
    print(f"\n{'='*80}")
    print(f"Processing: {txt_rel_path}")
    print(f"Path: {txt_path}")
    print(f"{'='*80}\n")
    
    try:
        # Handle .txt files directly (they're already text)
        print("📝 Processing as text file (Docling doesn't support .txt directly)...")
        content = process_txt_file(txt_path)
        print("Text Content (first 500 chars):")
        print("-" * 80)
        print(content[:500])
        if len(content) > 500:
            print(f"\n... (truncated, total length: {len(content)} characters)")
        print("-" * 80)
        
        # Try to find matching PDF file
        matching_pdf = find_matching_pdf(txt_rel_path, folder_analysis['pdf_files'])
        if matching_pdf:
            pdf_path = UNSTRUCTURED_FOLDER / matching_pdf
            print(f"\n📄 Found matching PDF: {matching_pdf}")
            print("Processing PDF version with Docling...")
            markdown_output = process_with_docling(pdf_path)
            print("Docling Markdown Output (first 500 chars):")
            print("-" * 80)
            print(markdown_output[:500])
            if len(markdown_output) > 500:
                print(f"\n... (truncated, total length: {len(markdown_output)} characters)")
            print("-" * 80)
        else:
            print(f"\n⚠️  No matching PDF found for {txt_rel_path.stem}")
        
    except Exception as e:
        print(f"❌ Error processing {txt_rel_path}: {e}")

# Also process standalone PDF files if any
standalone_pdfs = [pdf for pdf in folder_analysis['pdf_files'] 
                   if not find_matching_pdf(pdf, folder_analysis['txt_files'])]

if standalone_pdfs:
    print(f"\n{'='*80}")
    print(f"Processing {len(standalone_pdfs)} standalone PDF file(s)...")
    print("=" * 80)
    
    for pdf_rel_path in standalone_pdfs[:2]:  # Process first 2 standalone PDFs
        pdf_path = UNSTRUCTURED_FOLDER / pdf_rel_path
        print(f"\n{'='*80}")
        print(f"Processing standalone PDF: {pdf_rel_path}")
        print(f"{'='*80}\n")
        
        try:
            markdown_output = process_with_docling(pdf_path)
            print("Docling Markdown Output (first 500 chars):")
            print("-" * 80)
            print(markdown_output[:500])
            if len(markdown_output) > 500:
                print(f"\n... (truncated, total length: {len(markdown_output)} characters)")
            print("-" * 80)
        except Exception as e:
            print(f"❌ Error processing {pdf_rel_path}: {e}")

print(f"\n{'='*80}")
print("Test complete!")
print(f"Total .txt files: {len(folder_analysis['txt_files'])}")
print(f"Total .pdf files: {len(folder_analysis['pdf_files'])}")
print("=" * 80)