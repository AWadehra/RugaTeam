"""
Utility for configuring LLM clients and embeddings.
Supports: Gemini (default), OpenAI, GreenPT
"""

import os
from typing import Optional

# Provider selection - defaults to gemini (free tier available)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()


def get_embeddings():
    """
    Get embeddings instance based on provider.

    Returns:
        Configured embeddings instance
    """
    if LLM_PROVIDER == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        return GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")

    elif LLM_PROVIDER == "greenpt":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            model="green-embedding",
            openai_api_base="https://api.greenpt.ai/v1",
            openai_api_key=os.getenv("GREENPT_API_KEY"),
        )

    else:  # openai
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(model="text-embedding-3-small")


def get_chat_llm(model: Optional[str] = None, temperature: float = 0):
    """
    Get chat LLM instance based on provider.

    Args:
        model: Model name (optional, will use default based on provider)
        temperature: Temperature for the model

    Returns:
        Configured chat LLM instance
    """
    if LLM_PROVIDER == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        gemini_model = model or "gemini-2.5-flash"
        return ChatGoogleGenerativeAI(
            model=gemini_model,
            temperature=temperature,
            max_retries=2,  # Limit retries to avoid burning quota on rate limit errors
        )

    elif LLM_PROVIDER == "greenpt":
        from langchain_openai import ChatOpenAI
        greenpt_model = model or "mistral-small-3.2-24b-instruct-2506"
        return ChatOpenAI(
            model=greenpt_model,
            temperature=temperature,
            base_url="https://api.greenpt.ai/v1",
            api_key=os.getenv("GREENPT_API_KEY"),
        )

    else:  # openai
        from langchain_openai import ChatOpenAI
        openai_model = model or "gpt-4o-mini"
        return ChatOpenAI(
            model=openai_model,
            temperature=temperature,
        )
