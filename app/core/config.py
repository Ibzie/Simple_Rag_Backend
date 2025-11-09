# configuration management using Pydantic

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:////app/data/persistent/rag.db"

    # Groq configuration (for LLM only)
    # IMPORTANT: Replace with your actual Groq API key from https://console.groq.com
    # Or set via environment variable: export GROQ_API_KEY=your_key_here
    GROQ_API_KEY: str = "your_groq_api_key_here"
    LLM_MODEL: str = "llama-3.3-70b-versatile"

    # Embedding model (sentence-transformers)
    # using all-MiniLM-L6-v2 (384 dimensions)
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Indices paths
    FAISS_INDEX_PATH: str = "/app/data/persistent/faiss.index"
    BM25_INDEX_PATH: str = "/app/data/persistent/bm25.pkl"

    # Chunking parameters
    # 512 tokens
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50

    # Retrieval parameters
    TOP_K_DEFAULT: int = 5  # how many results to return by default
    RRF_K: int = 60  # reciprocal rank fusion constant
    MMR_LAMBDA: float = 0.7  # 70% relevance, 30% diversity

    # Validation thresholds
    ENTROPY_THRESHOLD: float = 0.3  # below this = confident answer
    GROUNDING_THRESHOLD: float = 0.7  # above this = answer is grounded in sources

    # LLM generation settings
    LLM_TEMPERATURE: float = 0.1  # low temp for factual answers
    LLM_MAX_TOKENS: int = 500  # max length for generated answers

    class Config:
        env_file = ".env"
        case_sensitive = False


# single global settings instance
settings = Settings()
