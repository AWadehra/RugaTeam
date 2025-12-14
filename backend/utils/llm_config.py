"""
Utility for configuring LLM clients and embeddings with support for OpenAI and GreenPT.
"""

import os
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from typing import Optional


def get_embeddings() -> OpenAIEmbeddings:
    """
    Get an OpenAIEmbeddings instance configured for either OpenAI or GreenPT.
    
    Returns:
        Configured OpenAIEmbeddings instance
    """
    # Check if GreenPT is enabled
    use_greenpt = os.getenv("GREENPT_ENABLED", "false").lower() == "true"
    greenpt_api_key = os.getenv("GREENPT_API_KEY")
    
    if use_greenpt and greenpt_api_key:
        # Use GreenPT embeddings
        return OpenAIEmbeddings(
            model="green-embedding",
            openai_api_base="https://api.greenpt.ai/v1",
            openai_api_key=greenpt_api_key,
        )
    else:
        # Use OpenAI embeddings (default)
        return OpenAIEmbeddings(model="text-embedding-3-small")


def get_chat_llm(model: Optional[str] = None, temperature: float = 0) -> ChatOpenAI:
    """
    Get a ChatOpenAI instance configured for either OpenAI or GreenPT.
    
    Args:
        model: Model name (optional, will use default based on provider)
        temperature: Temperature for the model
        
    Returns:
        Configured ChatOpenAI instance
    """
    # Check if GreenPT is enabled
    use_greenpt = os.getenv("GREENPT_ENABLED", "false").lower() == "true"
    greenpt_api_key = os.getenv("GREENPT_API_KEY")
    
    if use_greenpt and greenpt_api_key:
        # Use GreenPT
        greenpt_model = model or "mistral-small-3.2-24b-instruct-2506"
        return ChatOpenAI(
            model=greenpt_model,
            temperature=temperature,
            base_url="https://api.greenpt.ai/v1",
            api_key=greenpt_api_key,
        )
    else:
        # Use OpenAI (default)
        openai_model = model or "gpt-4o-mini"
        return ChatOpenAI(
            model=openai_model,
            temperature=temperature,
        )
