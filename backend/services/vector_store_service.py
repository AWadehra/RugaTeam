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

from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from docling.document_converter import DocumentConverter

# Add backend to path for imports
BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from utils.llm_config import get_embeddings


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
        
        # Initialize embeddings (uses GreenPT if enabled, otherwise OpenAI)
        self.embeddings = get_embeddings()
        
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
    
    def filter_by_category(self, category: str, query: Optional[str] = None, k: int = 5) -> List[Document]:
        """
        Filter documents by category and optionally search within them.
        
        Args:
            category: Category to filter by
            query: Optional search query to filter results
            k: Number of results to return
            
        Returns:
            List of filtered documents
        """
        try:
            collection = self.vector_store._collection
            
            # Get all documents - we'll filter in Python since categories are stored as string representations
            # First, get all documents with embeddings
            # IDs are returned by default, so we don't need to include them
            all_results = collection.get(
                include=["documents", "metadatas", "embeddings"],
            )
            
            if not all_results or not all_results.get("ids"):
                return []
            
            # Filter by category in Python
            # Categories are stored as string representations like "['Education/Capita Selecta', 'Research Meeting']"
            filtered_ids = []
            filtered_documents = []
            filtered_metadatas = []
            filtered_embeddings = []
            
            for i, metadata in enumerate(all_results.get("metadatas", [])):
                categories_str = metadata.get("categories", "")
                if categories_str:
                    # Parse the string representation or check if category is in the string
                    # Handle both list string format and simple string format
                    import ast
                    try:
                        # Try to parse as Python literal (list string)
                        categories_list = ast.literal_eval(categories_str)
                        if isinstance(categories_list, list):
                            if any(category.lower() in cat.lower() or cat.lower() in category.lower() 
                                   for cat in categories_list):
                                filtered_ids.append(all_results["ids"][i])
                                filtered_documents.append(all_results["documents"][i])
                                filtered_metadatas.append(metadata)
                                embeddings_list = all_results.get("embeddings")
                                if embeddings_list is not None and i < len(embeddings_list):
                                    filtered_embeddings.append(embeddings_list[i])
                        elif isinstance(categories_list, str):
                            if category.lower() in categories_list.lower():
                                filtered_ids.append(all_results["ids"][i])
                                filtered_documents.append(all_results["documents"][i])
                                filtered_metadatas.append(metadata)
                                embeddings_list = all_results.get("embeddings")
                                if embeddings_list is not None and i < len(embeddings_list):
                                    filtered_embeddings.append(embeddings_list[i])
                    except (ValueError, SyntaxError):
                        # If parsing fails, do simple string contains check
                        if category.lower() in categories_str.lower():
                            filtered_ids.append(all_results["ids"][i])
                            filtered_documents.append(all_results["documents"][i])
                            filtered_metadatas.append(metadata)
                            embeddings_list = all_results.get("embeddings")
                            if embeddings_list is not None and i < len(embeddings_list):
                                filtered_embeddings.append(embeddings_list[i])
            
            if not filtered_ids:
                return []
            
            results = {
                "ids": filtered_ids,
                "documents": filtered_documents,
                "metadatas": filtered_metadatas,
                "embeddings": filtered_embeddings,
            }
            
            # If query is provided, use similarity search on filtered results
            if query:
                # Get embeddings for the query
                query_embedding = self.embeddings.embed_query(query)
                
                # Get embeddings for filtered documents
                filtered_embeddings = results.get("embeddings", [])
                filtered_ids = results["ids"]
                filtered_metadatas = results.get("metadatas", [])
                filtered_documents = results.get("documents", [])
                
                # Check if we have embeddings (check length, not truthiness to avoid numpy array issues)
                if not filtered_embeddings or len(filtered_embeddings) == 0:
                    # If no embeddings, just return filtered documents without similarity ranking
                    docs = []
                    for i, doc_text in enumerate(filtered_documents):
                        doc = Document(
                            page_content=doc_text,
                            metadata=filtered_metadatas[i] if filtered_metadatas and i < len(filtered_metadatas) else {},
                        )
                        docs.append(doc)
                    return docs[:k]
                
                # Compute similarities
                import numpy as np
                query_vec = np.array(query_embedding, dtype=np.float32)
                doc_embeddings = np.array(filtered_embeddings, dtype=np.float32)
                
                # Ensure doc_embeddings is 2D
                if doc_embeddings.ndim == 1:
                    doc_embeddings = doc_embeddings.reshape(1, -1)
                
                # Compute cosine similarities
                # Normalize vectors
                query_norm = np.linalg.norm(query_vec)
                doc_norms = np.linalg.norm(doc_embeddings, axis=1)
                
                # Avoid division by zero
                doc_norms = np.where(doc_norms == 0, 1, doc_norms)
                query_norm = query_norm if query_norm != 0 else 1
                
                # Compute dot products and normalize
                similarities = np.dot(doc_embeddings, query_vec) / (doc_norms * query_norm)
                
                # Get top k
                top_indices = np.argsort(similarities)[::-1][:k]
                
                # Build documents
                docs = []
                for idx in top_indices:
                    doc = Document(
                        page_content=filtered_documents[idx],
                        metadata=filtered_metadatas[idx] if filtered_metadatas and idx < len(filtered_metadatas) else {},
                    )
                    docs.append(doc)
                
                return docs
            else:
                # Return filtered documents without search
                docs = []
                for i, doc_text in enumerate(results.get("documents", [])):
                    doc = Document(
                        page_content=doc_text,
                        metadata=results.get("metadatas", [{}])[i] if results.get("metadatas") else {},
                    )
                    docs.append(doc)
                
                return docs[:k]
                
        except Exception as e:
            print(f"  ❌ Error filtering by category: {e}")
            return []
    
    def filter_by_topic(self, topic: str, query: Optional[str] = None, k: int = 5) -> List[Document]:
        """
        Filter documents by topic and optionally search within them.
        
        Args:
            topic: Topic to filter by
            query: Optional search query to filter results
            k: Number of results to return
            
        Returns:
            List of filtered documents
        """
        try:
            collection = self.vector_store._collection
            
            # Get all documents - we'll filter in Python since topics are stored as string representations
            # IDs are returned by default, so we don't need to include them
            all_results = collection.get(
                include=["documents", "metadatas", "embeddings"],
            )
            
            if not all_results or not all_results.get("ids"):
                return []
            
            # Filter by topic in Python
            filtered_ids = []
            filtered_documents = []
            filtered_metadatas = []
            filtered_embeddings = []
            
            for i, metadata in enumerate(all_results.get("metadatas", [])):
                topics_str = metadata.get("topics", "")
                if topics_str:
                    import ast
                    try:
                        topics_list = ast.literal_eval(topics_str)
                        if isinstance(topics_list, list):
                            if any(topic.lower() in t.lower() or t.lower() in topic.lower() 
                                   for t in topics_list):
                                filtered_ids.append(all_results["ids"][i])
                                filtered_documents.append(all_results["documents"][i])
                                filtered_metadatas.append(metadata)
                                embeddings_list = all_results.get("embeddings")
                                if embeddings_list is not None and i < len(embeddings_list):
                                    filtered_embeddings.append(embeddings_list[i])
                        elif isinstance(topics_list, str):
                            if topic.lower() in topics_list.lower():
                                filtered_ids.append(all_results["ids"][i])
                                filtered_documents.append(all_results["documents"][i])
                                filtered_metadatas.append(metadata)
                                embeddings_list = all_results.get("embeddings")
                                if embeddings_list is not None and i < len(embeddings_list):
                                    filtered_embeddings.append(embeddings_list[i])
                    except (ValueError, SyntaxError):
                        if topic.lower() in topics_str.lower():
                            filtered_ids.append(all_results["ids"][i])
                            filtered_documents.append(all_results["documents"][i])
                            filtered_metadatas.append(metadata)
                            embeddings_list = all_results.get("embeddings")
                            if embeddings_list is not None and i < len(embeddings_list):
                                filtered_embeddings.append(embeddings_list[i])
            
            if not filtered_ids:
                return []
            
            results = {
                "ids": filtered_ids,
                "documents": filtered_documents,
                "metadatas": filtered_metadatas,
                "embeddings": filtered_embeddings,
            }
            
            # If query is provided, use similarity search on filtered results
            if query:
                query_embedding = self.embeddings.embed_query(query)
                filtered_embeddings = results.get("embeddings", [])
                filtered_documents = results.get("documents", [])
                filtered_metadatas = results.get("metadatas", [])
                
                # Check if we have embeddings (check length, not truthiness to avoid numpy array issues)
                if not filtered_embeddings or len(filtered_embeddings) == 0:
                    # If no embeddings, just return filtered documents without similarity ranking
                    docs = []
                    for i, doc_text in enumerate(filtered_documents):
                        doc = Document(
                            page_content=doc_text,
                            metadata=filtered_metadatas[i] if filtered_metadatas and i < len(filtered_metadatas) else {},
                        )
                        docs.append(doc)
                    return docs[:k]
                
                import numpy as np
                query_vec = np.array(query_embedding, dtype=np.float32)
                doc_embeddings = np.array(filtered_embeddings, dtype=np.float32)
                
                # Ensure doc_embeddings is 2D
                if doc_embeddings.ndim == 1:
                    doc_embeddings = doc_embeddings.reshape(1, -1)
                
                # Compute cosine similarities with proper normalization
                query_norm = np.linalg.norm(query_vec)
                doc_norms = np.linalg.norm(doc_embeddings, axis=1)
                
                # Avoid division by zero
                doc_norms = np.where(doc_norms == 0, 1, doc_norms)
                query_norm = query_norm if query_norm != 0 else 1
                
                similarities = np.dot(doc_embeddings, query_vec) / (doc_norms * query_norm)
                top_indices = np.argsort(similarities)[::-1][:k]
                
                docs = []
                for idx in top_indices:
                    doc = Document(
                        page_content=filtered_documents[idx],
                        metadata=filtered_metadatas[idx] if filtered_metadatas and idx < len(filtered_metadatas) else {},
                    )
                    docs.append(doc)
                
                return docs
            else:
                docs = []
                for i, doc_text in enumerate(results.get("documents", [])):
                    doc = Document(
                        page_content=doc_text,
                        metadata=results.get("metadatas", [{}])[i] if results.get("metadatas") else {},
                    )
                    docs.append(doc)
                
                return docs[:k]
                
        except Exception as e:
            print(f"  ❌ Error filtering by topic: {e}")
            return []
    
    def filter_by_tag(self, tag: str, query: Optional[str] = None, k: int = 5) -> List[Document]:
        """
        Filter documents by tag and optionally search within them.
        
        Args:
            tag: Tag to filter by
            query: Optional search query to filter results
            k: Number of results to return
            
        Returns:
            List of filtered documents
        """
        try:
            collection = self.vector_store._collection
            
            # Get all documents - we'll filter in Python since tags are stored as string representations
            # IDs are returned by default, so we don't need to include them
            all_results = collection.get(
                include=["documents", "metadatas", "embeddings"],
            )
            
            if not all_results or not all_results.get("ids"):
                return []
            
            # Filter by tag in Python
            filtered_ids = []
            filtered_documents = []
            filtered_metadatas = []
            filtered_embeddings = []
            
            for i, metadata in enumerate(all_results.get("metadatas", [])):
                tags_str = metadata.get("tags", "")
                if tags_str:
                    import ast
                    try:
                        tags_list = ast.literal_eval(tags_str)
                        if isinstance(tags_list, list):
                            if any(tag.lower() in t.lower() or t.lower() in tag.lower() 
                                   for t in tags_list):
                                filtered_ids.append(all_results["ids"][i])
                                filtered_documents.append(all_results["documents"][i])
                                filtered_metadatas.append(metadata)
                                embeddings_list = all_results.get("embeddings")
                                if embeddings_list is not None and i < len(embeddings_list):
                                    filtered_embeddings.append(embeddings_list[i])
                        elif isinstance(tags_list, str):
                            if tag.lower() in tags_list.lower():
                                filtered_ids.append(all_results["ids"][i])
                                filtered_documents.append(all_results["documents"][i])
                                filtered_metadatas.append(metadata)
                                embeddings_list = all_results.get("embeddings")
                                if embeddings_list is not None and i < len(embeddings_list):
                                    filtered_embeddings.append(embeddings_list[i])
                    except (ValueError, SyntaxError):
                        if tag.lower() in tags_str.lower():
                            filtered_ids.append(all_results["ids"][i])
                            filtered_documents.append(all_results["documents"][i])
                            filtered_metadatas.append(metadata)
                            embeddings_list = all_results.get("embeddings")
                            if embeddings_list is not None and i < len(embeddings_list):
                                filtered_embeddings.append(embeddings_list[i])
            
            if not filtered_ids:
                return []
            
            results = {
                "ids": filtered_ids,
                "documents": filtered_documents,
                "metadatas": filtered_metadatas,
                "embeddings": filtered_embeddings,
            }
            
            # If query is provided, use similarity search on filtered results
            if query:
                query_embedding = self.embeddings.embed_query(query)
                filtered_embeddings = results.get("embeddings", [])
                filtered_documents = results.get("documents", [])
                filtered_metadatas = results.get("metadatas", [])
                
                # Check if we have embeddings (check length, not truthiness to avoid numpy array issues)
                if not filtered_embeddings or len(filtered_embeddings) == 0:
                    # If no embeddings, just return filtered documents without similarity ranking
                    docs = []
                    for i, doc_text in enumerate(filtered_documents):
                        doc = Document(
                            page_content=doc_text,
                            metadata=filtered_metadatas[i] if filtered_metadatas and i < len(filtered_metadatas) else {},
                        )
                        docs.append(doc)
                    return docs[:k]
                
                import numpy as np
                query_vec = np.array(query_embedding, dtype=np.float32)
                doc_embeddings = np.array(filtered_embeddings, dtype=np.float32)
                
                # Ensure doc_embeddings is 2D
                if doc_embeddings.ndim == 1:
                    doc_embeddings = doc_embeddings.reshape(1, -1)
                
                # Compute cosine similarities with proper normalization
                query_norm = np.linalg.norm(query_vec)
                doc_norms = np.linalg.norm(doc_embeddings, axis=1)
                
                # Avoid division by zero
                doc_norms = np.where(doc_norms == 0, 1, doc_norms)
                query_norm = query_norm if query_norm != 0 else 1
                
                similarities = np.dot(doc_embeddings, query_vec) / (doc_norms * query_norm)
                top_indices = np.argsort(similarities)[::-1][:k]
                
                docs = []
                for idx in top_indices:
                    doc = Document(
                        page_content=filtered_documents[idx],
                        metadata=filtered_metadatas[idx] if filtered_metadatas and idx < len(filtered_metadatas) else {},
                    )
                    docs.append(doc)
                
                return docs
            else:
                docs = []
                for i, doc_text in enumerate(results.get("documents", [])):
                    doc = Document(
                        page_content=doc_text,
                        metadata=results.get("metadatas", [{}])[i] if results.get("metadatas") else {},
                    )
                    docs.append(doc)
                
                return docs[:k]
                
        except Exception as e:
            print(f"  ❌ Error filtering by tag: {e}")
            return []
