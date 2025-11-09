# text chunking utility
# breaks documents into overlapping chunks using tiktoken for accurate token counting
# 512 tokens is the sweet spot - enough context, not too much

import tiktoken
from typing import List, Tuple
from app.core.config import settings


def chunk_text(
    text: str,
    chunk_size: int = None,
    overlap: int = None,
    encoding_name: str = "cl100k_base"
) -> List[Tuple[str, int]]:
    """
    Split text into overlapping chunks based on token count

    Args:
        text: The text to chunk
        chunk_size: Max tokens per chunk (defaults to settings.CHUNK_SIZE)
        overlap: Number of overlapping tokens (defaults to settings.CHUNK_OVERLAP)
        encoding_name: tiktoken encoding to use

    Returns:
        List of (chunk_text, token_count) tuples

    Why overlap? So we don't split sentences in the middle like idiots
    If a concept spans two chunks, the overlap ensures we capture it
    """
    chunk_size = chunk_size or settings.CHUNK_SIZE
    overlap = overlap or settings.CHUNK_OVERLAP

    # get the tiktoken encoder
    try:
        encoding = tiktoken.get_encoding(encoding_name)
    except Exception:
        # fallback if encoding not found
        encoding = tiktoken.get_encoding("cl100k_base")

    # encode the entire text to tokens
    tokens = encoding.encode(text)

    chunks = []
    start = 0

    while start < len(tokens):
        # get chunk_size tokens starting from start position
        end = start + chunk_size
        chunk_tokens = tokens[start:end]

        # decode back to text
        chunk_text = encoding.decode(chunk_tokens)
        token_count = len(chunk_tokens)

        chunks.append((chunk_text, token_count))

        # move forward by (chunk_size - overlap) to create overlap
        # this means each chunk shares 'overlap' tokens with the next one
        start += (chunk_size - overlap)

        # stop if we've processed everything
        if end >= len(tokens):
            break

    return chunks


def estimate_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """
    Quick token count estimate without chunking
    Useful for logging and debugging
    """
    try:
        encoding = tiktoken.get_encoding(encoding_name)
        return len(encoding.encode(text))
    except Exception:
        # rough fallback: ~4 characters per token
        return len(text) // 4
