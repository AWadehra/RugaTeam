"""
Service for managing RAG chat interactions with the vector store.
"""

from typing import Optional
from langchain.tools import tool
from langchain.agents import create_agent
from langchain_chroma import Chroma
from services.vector_store_service import VectorStoreService
from utils.llm_config import get_chat_llm


class ChatService:
    """Service for managing chat interactions with RAG agent."""
    
    def __init__(self, vector_store_service: VectorStoreService):
        """
        Initialize the chat service.
        
        Args:
            vector_store_service: Vector store service instance
        """
        self.vector_store_service = vector_store_service
        self.model = get_chat_llm(temperature=0)
        self._agent = None
    
    def _create_retrieve_tool(self, vector_store_instance: Chroma):
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
    
    def _create_filter_by_category_tool(self):
        """
        Create a tool to filter documents by category.
        
        Returns:
            Tool function for category filtering
        """
        @tool(response_format="content_and_artifact")
        def filter_by_category(category: str, query: str = ""):
            """
            Filter documents by category and optionally search within them.
            
            Use this tool when the user wants to find documents in a specific category
            like "Education", "Capita Selecta", "Research Meeting", "World Headlines", etc.
            
            Args:
                category: The category to filter by (e.g., "Education", Capita Selecta", "Research Meeting")
                query: Optional search query to further filter results within the category
                
            Returns:
                Serialized context string and filtered documents
            """
            retrieved_docs = self.vector_store_service.filter_by_category(
                category=category,
                query=query if query else None,
                k=5
            )
            
            if not retrieved_docs:
                return f"No documents found in category: {category}", []
            
            serialized = f"Found {len(retrieved_docs)} document(s) in category '{category}':\n\n"
            serialized += "\n\n".join(
                (f"Source: {doc.metadata.get('source', 'Unknown')}\n"
                 f"File: {doc.metadata.get('file_name', 'Unknown')}\n"
                 f"Content: {doc.page_content}")
                for doc in retrieved_docs
            )
            return serialized, retrieved_docs
        
        return filter_by_category
    
    def _create_filter_by_topic_tool(self):
        """
        Create a tool to filter documents by topic.
        
        Returns:
            Tool function for topic filtering
        """
        @tool(response_format="content_and_artifact")
        def filter_by_topic(topic: str, query: str = ""):
            """
            Filter documents by topic and optionally search within them.
            
            Use this tool when the user wants to find documents about a specific topic
            like "survival analysis", "causal inference", "machine learning", etc.
            
            Args:
                topic: The topic to filter by (e.g., "survival analysis", "causal inference")
                query: Optional search query to further filter results within the topic
                
            Returns:
                Serialized context string and filtered documents
            """
            retrieved_docs = self.vector_store_service.filter_by_topic(
                topic=topic,
                query=query if query else None,
                k=5
            )
            
            if not retrieved_docs:
                return f"No documents found with topic: {topic}", []
            
            serialized = f"Found {len(retrieved_docs)} document(s) with topic '{topic}':\n\n"
            serialized += "\n\n".join(
                (f"Source: {doc.metadata.get('source', 'Unknown')}\n"
                 f"File: {doc.metadata.get('file_name', 'Unknown')}\n"
                 f"Content: {doc.page_content}")
                for doc in retrieved_docs
            )
            return serialized, retrieved_docs
        
        return filter_by_topic
    
    def _create_filter_by_tag_tool(self):
        """
        Create a tool to filter documents by tag.
        
        Returns:
            Tool function for tag filtering
        """
        @tool(response_format="content_and_artifact")
        def filter_by_tag(tag: str, query: str = ""):
            """
            Filter documents by tag and optionally search within them.
            
            Use this tool when the user wants to find documents with a specific tag.
            
            Args:
                tag: The tag to filter by
                query: Optional search query to further filter results within the tag
                
            Returns:
                Serialized context string and filtered documents
            """
            retrieved_docs = self.vector_store_service.filter_by_tag(
                tag=tag,
                query=query if query else None,
                k=5
            )
            
            if not retrieved_docs:
                return f"No documents found with tag: {tag}", []
            
            serialized = f"Found {len(retrieved_docs)} document(s) with tag '{tag}':\n\n"
            serialized += "\n\n".join(
                (f"Source: {doc.metadata.get('source', 'Unknown')}\n"
                 f"File: {doc.metadata.get('file_name', 'Unknown')}\n"
                 f"Content: {doc.page_content}")
                for doc in retrieved_docs
            )
            return serialized, retrieved_docs
        
        return filter_by_tag
    
    def get_agent(self):
        """
        Get or create the RAG agent.
        
        Returns:
            LangChain agent
        """
        if self._agent is None:
            # Create all tools
            retrieve_tool = self._create_retrieve_tool(self.vector_store_service.vector_store)
            filter_by_category_tool = self._create_filter_by_category_tool()
            filter_by_topic_tool = self._create_filter_by_topic_tool()
            filter_by_tag_tool = self._create_filter_by_tag_tool()
            
            tools = [
                retrieve_tool,
                filter_by_category_tool,
                filter_by_topic_tool,
                filter_by_tag_tool,
            ]
            
            # Custom system prompt for the agent
            prompt = (
                "You are a helpful assistant that answers questions based on documents "
                "that have been analyzed and indexed. You have access to several tools:\n"
                "- retrieve_context: General semantic search across all documents\n"
                "- filter_by_category: Filter documents by category (e.g., 'Education', Capita Selecta', 'Research Meeting')\n"
                "- filter_by_topic: Filter documents by topic (e.g., 'survival analysis', 'causal inference')\n"
                "- filter_by_tag: Filter documents by tag\n\n"
                "Use the appropriate tool based on the user's query. If they mention a specific category, "
                "topic, or tag, use the corresponding filter tool. Otherwise, use retrieve_context for general searches. "
                "You can also combine tools - for example, filter by category first, then search within those results. "
                "Always cite the source documents when providing answers."
            )
            
            self._agent = create_agent(self.model, tools, system_prompt=prompt)
        
        return self._agent
