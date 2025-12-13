"""
Test Docling document converter with local files from unstructured_folder.
Docling can convert various document formats (PDF, DOCX, TXT, etc.) to structured formats.
"""

from pathlib import Path
from docling.document_converter import DocumentConverter

# Get the unstructured_folder path
UNSTRUCTURED_FOLDER = Path(__file__).parent / "unstructured_folder"

# Initialize converter
converter = DocumentConverter()

# Test with a few example files
test_files = [
    "presentation_final_v2_FINAL.txt",
    "survival_analysis_talk.txt",
    "causal_inference_lecture.txt",
    "Research/systematic_review_methods.txt",
]

print("=" * 80)
print("Testing Docling with files from unstructured_folder")
print("=" * 80)

for filename in test_files:
    file_path = UNSTRUCTURED_FOLDER / filename
    
    if not file_path.exists():
        print(f"\n⚠️  File not found: {file_path}")
        continue
    
    print(f"\n{'='*80}")
    print(f"Processing: {filename}")
    print(f"Path: {file_path}")
    print(f"{'='*80}\n")
    
    try:
        result = converter.convert(str(file_path))
        markdown_output = result.document.export_to_markdown()
        
        print("Markdown Output:")
        print("-" * 80)
        print(markdown_output[:500])  # Print first 500 chars
        if len(markdown_output) > 500:
            print(f"\n... (truncated, total length: {len(markdown_output)} characters)")
        print("-" * 80)
        
    except Exception as e:
        print(f"❌ Error processing {filename}: {e}")

print(f"\n{'='*80}")
print("Test complete!")
print(f"Total files in unstructured_folder: {len(list(UNSTRUCTURED_FOLDER.rglob('*.txt')))}")
print("=" * 80)