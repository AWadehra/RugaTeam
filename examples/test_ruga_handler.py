"""
Test script to demonstrate .ruga file creation and reading.

This script:
1. Takes a file from unstructured_folder
2. Uses test_llm.py to extract metadata
3. Saves metadata to a .ruga file
4. Reads it back and displays it
"""

from pathlib import Path
from ruga_file_handler import (
    save_ruga_metadata,
    load_ruga_metadata,
    has_ruga_metadata,
    get_metadata_summary,
    get_ruga_path
)

# Import from test_llm
from test_llm import (
    chain,
    build_final_record,
    UNSTRUCTURED_FOLDER
)

if __name__ == "__main__":
    print("=" * 80)
    print("Testing .ruga File Handler")
    print("=" * 80)
    
    # Find a test file
    test_file = UNSTRUCTURED_FOLDER / "Research" / "systematic_review_methods.txt"
    
    if not test_file.exists():
        print(f"\n⚠️  Test file not found: {test_file}")
        print("Looking for any .txt file...")
        txt_files = list(UNSTRUCTURED_FOLDER.rglob("*.txt"))
        if txt_files:
            test_file = txt_files[0]
            print(f"Using: {test_file}")
        else:
            print("No .txt files found!")
            exit(1)
    
    print(f"\n📄 Processing file: {test_file}")
    
    # Check if .ruga already exists
    if has_ruga_metadata(test_file):
        print(f"\n✅ .ruga file already exists: {get_ruga_path(test_file)}")
        print("Loading existing metadata...")
        existing_metadata = load_ruga_metadata(test_file)
        if existing_metadata:
            print("\n📋 Existing Metadata Summary:")
            summary = get_metadata_summary(existing_metadata)
            for key, value in summary.items():
                print(f"  {key}: {value}")
    else:
        print("\n📝 No .ruga file found. Generating metadata...")
        
        # Read file content
        file_content = test_file.read_text(encoding="utf-8")
        
        # Extract metadata using LLM
        print("🤖 Running LLM extraction...")
        llm_result = chain.invoke({"text": file_content})
        
        # Build final record
        print("📊 Building final record...")
        final_record = build_final_record(
            llm_result=llm_result,
            file_path=test_file,
            llm_model_name="gpt-4o-mini",
        )
        
        # Save to .ruga file
        print(f"💾 Saving metadata to .ruga file...")
        ruga_path = save_ruga_metadata(test_file, final_record)
        print(f"✅ Saved to: {ruga_path}")
        
        # Load it back to verify
        print("\n📖 Loading .ruga file back...")
        loaded_metadata = load_ruga_metadata(test_file)
        
        if loaded_metadata:
            print("✅ Successfully loaded metadata!")
            print("\n📋 Metadata Summary:")
            summary = get_metadata_summary(loaded_metadata)
            for key, value in summary.items():
                print(f"  {key}: {value}")
            
            print(f"\n📄 Full JSON saved to: {ruga_path}")
            print(f"   File size: {ruga_path.stat().st_size} bytes")
        else:
            print("❌ Failed to load metadata")
    
    print("\n" + "=" * 80)
    print("Test complete!")
    print("=" * 80)

