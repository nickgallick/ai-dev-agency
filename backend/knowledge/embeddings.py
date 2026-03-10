"""Phase 11B: Embedding Generation

Generates embeddings for knowledge entries using OpenAI's API.
"""
import os
import httpx
import numpy as np
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

# OpenAI embedding model
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536


async def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Generate embedding vector for text using OpenAI API.
    
    Args:
        text: Text to embed
        
    Returns:
        List of floats representing the embedding vector, or None if failed
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Fall back to OpenRouter if available
        api_key = os.getenv("OPENROUTER_API_KEY")
        if api_key:
            return await _generate_embedding_openrouter(text, api_key)
        logger.warning("No embedding API key found, returning None")
        return None
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "input": text[:8000],  # Truncate to fit token limit
                    "model": EMBEDDING_MODEL,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
    except Exception as e:
        logger.error(f"Failed to generate embedding: {e}")
        return None


async def _generate_embedding_openrouter(text: str, api_key: str) -> Optional[List[float]]:
    """
    Generate embedding using OpenRouter API.
    Falls back to a hash-based embedding if no embedding model available.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "input": text[:8000],
                    "model": "openai/text-embedding-3-small",
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
    except Exception as e:
        logger.warning(f"OpenRouter embedding failed, using fallback: {e}")
        return _generate_fallback_embedding(text)


def _generate_fallback_embedding(text: str) -> List[float]:
    """
    Generate a simple hash-based embedding as fallback.
    This is not ideal but allows the system to function without embeddings.
    """
    import hashlib
    # Create a deterministic but simple embedding
    hash_bytes = hashlib.sha512(text.encode()).digest()
    # Extend to 1536 dimensions by repeating and normalizing
    values = []
    for i in range(EMBEDDING_DIMENSION):
        byte_idx = i % len(hash_bytes)
        values.append((hash_bytes[byte_idx] - 128) / 128.0)
    # Normalize the vector
    norm = np.linalg.norm(values)
    if norm > 0:
        values = [v / norm for v in values]
    return values


def compute_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """
    Compute cosine similarity between two embedding vectors.
    
    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector
        
    Returns:
        Similarity score between -1 and 1
    """
    if not embedding1 or not embedding2:
        return 0.0
    
    vec1 = np.array(embedding1)
    vec2 = np.array(embedding2)
    
    # Cosine similarity
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))


async def generate_embeddings_batch(texts: List[str]) -> List[Optional[List[float]]]:
    """
    Generate embeddings for multiple texts in batch.
    
    Args:
        texts: List of texts to embed
        
    Returns:
        List of embedding vectors
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Fall back to individual calls
        return [await generate_embedding(t) for t in texts]
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "input": [t[:8000] for t in texts],
                    "model": EMBEDDING_MODEL,
                },
            )
            response.raise_for_status()
            data = response.json()
            return [item["embedding"] for item in data["data"]]
    except Exception as e:
        logger.error(f"Batch embedding failed: {e}")
        return [None] * len(texts)
