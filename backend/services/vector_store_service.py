"""
Service for managing ChromaDB vector store for document embeddings.
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from docling.document_converter import DocumentConverter


class VectorStoreService:
    """Service for managing document embeddings in ChromaDB."""
    
    def __init__(self, persist_directory: Optional[Path] = None, collection_name: str = "documents"):
        """
        Initialize the vector store service.
        
        Args:
            persist_directory: Directory to persist ChromaDB data. Defaults to PROJECT_ROOT / "chroma_db"
            collection_name: Name of the ChromaDB collection
        """
        if persist_directory is None:
            persist_directory = PROJECT_ROOT / "chroma_db"
        
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(exist_ok=True)
        self.collection_name = collection_name
        
        # Initialize embeddings
        self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        
        # Initialize vector store
        self.vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=str(self.persist_directory),
        )
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            add_start_index=True,
        )
        
        # Initialize Docling converter (lazy)
        self._converter: Optional[DocumentConverter] = None
    
    @property
    def converter(self) -> DocumentConverter:
        """Lazy initialization of Docling converter."""
        if self._converter is None:
            self._converter = DocumentConverter()
        return self._converter
    
    def get_file_content(self, file_path: Path) -> str:
        """
        Extract content from a file using Docling if supported, otherwise read directly.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Extracted text content
        """
        file_ext = file_path.suffix.lower()
        
        if file_ext == '.txt':
            # Read .txt files directly
            return file_path.read_text(encoding="utf-8")
        elif file_ext in ['.pdf', '.docx', '.doc']:
            # Use Docling for supported formats
            try:
                result = self.converter.convert(str(file_path))
                return result.document.export_to_markdown()
            except Exception as e:
                print(f"⚠️  Error processing {file_path.name} with Docling: {e}")
                # Fallback: try to read as text
                try:
                    return file_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    return f"[Could not extract content from {file_path.name}]"
        else:
            # For other formats, try Docling first, then fallback to text reading
            try:
                result = self.converter.convert(str(file_path))
                return result.document.export_to_markdown()
            except Exception:
                # Fallback to reading as text
                try:
                    return file_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    return f"[Could not extract content from {file_path.name}]"
    
    def add_document(
        self,
        file_path: Path,
        root_path: Path,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        Add a document to the vector store.
        
        Args:
            file_path: Full path to the file
            root_path: Root directory path (for relative paths)
            metadata: Additional metadata to include (e.g., from .ruga file)
            
        Returns:
            List of document IDs added to the vector store
        """
        try:
            # Extract content
            content = self.get_file_content(file_path)
            
            if not content or len(content.strip()) < 10:
                print(f"⚠️  File {file_path.name} appears empty, skipping vector store")
                return []
            
            # Create base metadata
            rel_path = str(file_path.relative_to(root_path))
            doc_metadata = {
                "source": rel_path,
                "file_path": str(file_path.absolute()),
                "file_name": file_path.name,
                "file_type": file_path.suffix.lower(),
            }
            
            # Add additional metadata if provided
            if metadata:
                # Add relevant fields from metadata
                if "title" in metadata:
                    doc_metadata["title"] = metadata["title"]
                if "categories" in metadata:
                    doc_metadata["categories"] = str(metadata["categories"])
                if "topics" in metadata:
                    doc_metadata["topics"] = str(metadata["topics"])
                if "tags" in metadata:
                    doc_metadata["tags"] = str(metadata["tags"])
                if "summary" in metadata:
                    doc_metadata["summary"] = metadata["summary"]
                if "file_id" in metadata:
                    doc_metadata["file_id"] = str(metadata["file_id"])
            
            # Create document
            doc = Document(
                page_content=content,
                metadata=doc_metadata,
            )
            
            # Split into chunks
            chunks = self.text_splitter.split_documents([doc])
            
            # Add to vector store
            document_ids = self.vector_store.add_documents(documents=chunks)
            
            print(f"  ✓ Added {len(document_ids)} chunks to vector store for {file_path.name}")
            return document_ids
            
        except Exception as e:
            print(f"  ❌ Error adding {file_path.name} to vector store: {e}")
            return []
    
    def update_document_path(
        self,
        old_path: Path,
        new_path: Path,
        old_root_path: Path,
        new_root_path: Optional[Path] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Update the file path metadata for a document in the vector store.
        
        This is used when files are moved during organization.
        Since ChromaDB doesn't support direct updates, we delete the old document
        and re-add it with the new path.
        
        Args:
            old_path: Original file path (absolute)
            new_path: New file path (absolute)
            old_root_path: Original root directory path (for relative paths)
            new_root_path: New root directory path (for relative paths). If None, uses old_root_path
            metadata: Optional metadata to include (e.g., from .ruga file)
            
        Returns:
            True if update was successful, False otherwise
        """
        try:
            if new_root_path is None:
                new_root_path = old_root_path
            
            old_rel_path = str(old_path.relative_to(old_root_path))
            
            # Delete old document
            deleted = self.delete_document(old_path, old_root_path)
            
            if not deleted:
                print(f"  ⚠️  No documents found to update for: {old_rel_path}")
                return False
            
            # Re-add document with new path
            # Load .ruga metadata if available
            if metadata is None:
                ruga_path = new_path.with_suffix(new_path.suffix + ".ruga")
                if ruga_path.exists():
                    try:
                        from ruga_file_handler import load_ruga_metadata
                        ruga_metadata = load_ruga_metadata(new_path)
                        if ruga_metadata:
                            metadata = ruga_metadata.model_dump(mode='json')
                    except Exception:
                        pass
            
            # Add document with new path
            self.add_document(
                file_path=new_path,
                root_path=new_root_path,
                metadata=metadata,
            )
            
            new_rel_path = str(new_path.relative_to(new_root_path))
            print(f"  ✓ Updated document from {old_rel_path} to {new_rel_path}")
            return True
            
        except Exception as e:
            print(f"  ❌ Error updating document path in vector store: {e}")
            return False
    
    def delete_document(self, file_path: Path, root_path: Path) -> bool:
        """
        Delete a document from the vector store.
        
        Args:
            file_path: Path to the file to delete
            root_path: Root directory path (for relative paths)
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            rel_path = str(file_path.relative_to(root_path))
            file_path_str = str(file_path.absolute())
            
            # Use the collection directly to query by metadata
            # ChromaDB where clause: {"metadata_field": {"$eq": "value"}}
            collection = self.vector_store._collection
            
            # Try to find documents by source (relative path)
            try:
                results = collection.get(
                    where={"source": {"$eq": rel_path}},
                )
            except Exception:
                # If that fails, try by file_path (absolute path)
                try:
                    results = collection.get(
                        where={"file_path": {"$eq": file_path_str}},
                    )
                except Exception:
                    # Last resort: try simple equality
                    try:
                        results = collection.get(
                            where={"source": rel_path},
                        )
                    except Exception:
                        results = None
            
            if not results or not results.get("ids") or len(results["ids"]) == 0:
                return False
            
            # Delete documents
            collection.delete(ids=results["ids"])
            
            print(f"  ✓ Deleted {len(results['ids'])} document chunks for {file_path.name}")
            return True
            
        except Exception as e:
            print(f"  ❌ Error deleting document from vector store: {e}")
            return False
    
    def get_document_count(self) -> int:
        """Get the total number of documents in the vector store."""
        try:
            return self.vector_store._collection.count()
        except Exception:
            return 0
