"""
Example script to embed documents analyzed using Docling in ChromaDB
and create a LangChain agent to interact with the vector store.

This script demonstrates:
1. Using Docling to analyze and extract content from documents
2. Embedding documents in ChromaDB with persistent local storage
3. Creating a LangChain RAG agent to query the vector store
"""

from pathlib import Path
from typing import List
import os

from docling.document_converter import DocumentConverter
from langchain.tools import tool
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# ============================================================
# Configuration
# ============================================================

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
CHROMA_DB_PATH = PROJECT_ROOT / "chroma_db"
EXAMPLES_DIR = Path(__file__).parent
UNSTRUCTURED_FOLDER = EXAMPLES_DIR / "unstructured_folder"

# Ensure ChromaDB directory exists
CHROMA_DB_PATH.mkdir(exist_ok=True)

# ============================================================
# 1. Document Processing with Docling
# ============================================================

def process_txt_file(file_path: Path) -> str:
    """Process a .txt file directly (since it's already text)."""
    return file_path.read_text(encoding="utf-8")


def process_with_docling(file_path: Path) -> str:
    """Process a file with Docling (PDF, DOCX, etc.) and return markdown."""
    converter = DocumentConverter()
    result = converter.convert(str(file_path))
    return result.document.export_to_markdown()


def get_file_content(file_path: Path) -> str:
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
        return process_txt_file(file_path)
    elif file_ext in ['.pdf', '.docx', '.doc']:
        # Use Docling for supported formats
        try:
            return process_with_docling(file_path)
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
            return process_with_docling(file_path)
        except Exception:
            # Fallback to reading as text
            try:
                return file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                return f"[Could not extract content from {file_path.name}]"


def load_documents_from_folder(folder_path: Path) -> List[Document]:
    """
    Load all documents from a folder and convert them to LangChain Documents.
    
    Args:
        folder_path: Path to the folder containing documents
        
    Returns:
        List of LangChain Document objects
    """
    documents = []
    
    if not folder_path.exists():
        print(f"⚠️  Folder {folder_path} does not exist")
        return documents
    
    # Supported file extensions
    supported_extensions = {'.txt', '.pdf', '.docx', '.doc', '.md'}
    
    # Find all supported files
    for file_path in folder_path.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
            try:
                print(f"📄 Processing: {file_path.relative_to(folder_path)}")
                content = get_file_content(file_path)
                
                # Create LangChain Document with metadata
                doc = Document(
                    page_content=content,
                    metadata={
                        "source": str(file_path.relative_to(folder_path)),
                        "file_path": str(file_path),
                        "file_name": file_path.name,
                        "file_type": file_path.suffix.lower(),
                    }
                )
                documents.append(doc)
                print(f"  ✓ Loaded {len(content)} characters")
            except Exception as e:
                print(f"  ❌ Error processing {file_path.name}: {e}")
    
    return documents


# ============================================================
# 2. Vector Store Setup
# ============================================================

def create_vector_store(embeddings, collection_name: str = "documents") -> Chroma:
    """
    Create or load a ChromaDB vector store with persistent storage.
    
    Args:
        embeddings: Embeddings model to use
        collection_name: Name of the collection
        
    Returns:
        Chroma vector store instance
    """
    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=str(CHROMA_DB_PATH),
    )
    return vector_store


# ============================================================
# 3. Indexing Pipeline
# ============================================================

def index_documents(
    documents: List[Document],
    vector_store: Chroma,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> List[str]:
    """
    Split documents into chunks and add them to the vector store.
    
    Args:
        documents: List of LangChain Document objects
        vector_store: Chroma vector store instance
        chunk_size: Size of each chunk in characters
        chunk_overlap: Overlap between chunks in characters
        
    Returns:
        List of document IDs added to the vector store
    """
    # Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
    )
    
    print(f"\n📝 Splitting {len(documents)} documents into chunks...")
    all_splits = text_splitter.split_documents(documents)
    print(f"  ✓ Created {len(all_splits)} chunks")
    
    # Add chunks to vector store
    print(f"\n💾 Adding chunks to vector store...")
    document_ids = vector_store.add_documents(documents=all_splits)
    print(f"  ✓ Added {len(document_ids)} chunks to vector store")
    print(f"  ✓ Vector store automatically persisted to {CHROMA_DB_PATH}")
    
    return document_ids


# ============================================================
# 4. RAG Agent Setup
# ============================================================

def create_retrieve_tool(vector_store_instance: Chroma):
    """
    Create a retrieval tool that has access to the vector store.
    
    Args:
        vector_store_instance: Chroma vector store instance
        
    Returns:
        Tool function for retrieval
    """
    @tool(response_format="content_and_artifact")
    def retrieve_context(query: str):
        """
        Retrieve information from the document vector store to help answer a query.
        
        Args:
            query: The search query
            
        Returns:
            Serialized context string and retrieved documents
        """
        retrieved_docs = vector_store_instance.similarity_search(query, k=3)
        serialized = "\n\n".join(
            (f"Source: {doc.metadata.get('source', 'Unknown')}\n"
             f"File: {doc.metadata.get('file_name', 'Unknown')}\n"
             f"Content: {doc.page_content}")
            for doc in retrieved_docs
        )
        return serialized, retrieved_docs
    
    return retrieve_context


def create_rag_agent(model, vector_store_instance: Chroma):
    """
    Create a RAG agent with a retrieval tool.
    
    Args:
        model: LangChain chat model
        vector_store_instance: Chroma vector store instance
        
    Returns:
        LangChain agent
    """
    # Create the retrieval tool with access to the vector store
    retrieve_tool = create_retrieve_tool(vector_store_instance)
    tools = [retrieve_tool]
    
    # Custom system prompt for the agent
    prompt = (
        "You are a helpful assistant that answers questions based on documents "
        "that have been analyzed and indexed. Use the retrieve_context tool to "
        "search for relevant information when answering user queries. "
        "Always cite the source documents when providing answers."
    )
    
    agent = create_agent(model, tools, system_prompt=prompt)
    return agent


# ============================================================
# 5. Main Execution
# ============================================================

def main():
    """Main function to run the RAG pipeline."""
    
    print("=" * 80)
    print("RAG with Docling and ChromaDB")
    print("=" * 80)
    
    # Check for API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found in environment variables")
        print("   Please set it in your .env file or environment")
        return
    
    # ============================================================
    # Step 1: Initialize components
    # ============================================================
    print("\n🔧 Initializing components...")
    
    # Initialize embeddings
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    print("  ✓ Embeddings model initialized")
    
    # Initialize chat model
    model = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
    )
    print("  ✓ Chat model initialized")
    
    # Create or load vector store
    vector_store = create_vector_store(embeddings)
    print("  ✓ Vector store initialized")
    
    # ============================================================
    # Step 2: Load and process documents
    # ============================================================
    print("\n📚 Loading documents...")
    
    # Check if we should load documents or use existing vector store
    existing_count = vector_store._collection.count()
    
    if existing_count == 0:
        print("  ℹ️  Vector store is empty, loading documents...")
        
        # Load documents from unstructured folder
        documents = load_documents_from_folder(UNSTRUCTURED_FOLDER)
        
        if not documents:
            print("  ⚠️  No documents found. Please add documents to the unstructured_folder")
            print(f"     Expected location: {UNSTRUCTURED_FOLDER}")
            return
        
        print(f"\n  ✓ Loaded {len(documents)} documents")
        
        # ============================================================
        # Step 3: Index documents
        # ============================================================
        print("\n📇 Indexing documents...")
        document_ids = index_documents(
            documents=documents,
            vector_store=vector_store,
            chunk_size=1000,
            chunk_overlap=200,
        )
        print(f"  ✓ Indexing complete. {len(document_ids)} chunks indexed")
    else:
        print(f"  ℹ️  Vector store already contains {existing_count} documents")
        print("  ✓ Using existing vector store")
    
    # ============================================================
    # Step 4: Create RAG agent
    # ============================================================
    print("\n🤖 Creating RAG agent...")
    agent = create_rag_agent(model, vector_store)
    print("  ✓ Agent created")
    
    # ============================================================
    # Step 5: Example queries
    # ============================================================
    print("\n" + "=" * 80)
    print("Example Queries")
    print("=" * 80)
    
    example_queries = [
        "What topics are covered in the documents?",
        "Summarize the main content of the documents",
        "What are the key concepts discussed?",
    ]
    
    for i, query in enumerate(example_queries, 1):
        print(f"\n{'─' * 80}")
        print(f"Query {i}: {query}")
        print(f"{'─' * 80}\n")
        
        try:
            # Stream the agent response
            for step in agent.stream(
                {"messages": [{"role": "user", "content": query}]},
                stream_mode="values",
            ):
                step["messages"][-1].pretty_print()
        except Exception as e:
            print(f"❌ Error processing query: {e}")
    
    print("\n" + "=" * 80)
    print("Interactive Mode")
    print("=" * 80)
    print("\nYou can now interact with the agent programmatically.")
    print("Example usage:")
    print("""
    query = "Your question here"
    for step in agent.stream(
        {"messages": [{"role": "user", "content": query}]},
        stream_mode="values",
    ):
        step["messages"][-1].pretty_print()
    """)
    
    print("\n" + "=" * 80)
    print("✓ Complete!")
    print("=" * 80)
    print(f"\nVector store persisted at: {CHROMA_DB_PATH.absolute()}")
    print(f"Collection name: documents")
    print(f"Total documents in store: {vector_store._collection.count()}")


if __name__ == "__main__":
    main()
