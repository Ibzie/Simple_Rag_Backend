# Pydantic schemas for API request/response validation
# keeps our API clean and predictable
# automatically generates API docs with these schemas

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict, Any


# --- Request Schemas ---

class IngestRequest(BaseModel):
    """File upload is handled via multipart/form-data, so no schema needed here"""
    pass


class QueryRequest(BaseModel):
    """Request for querying the RAG system"""
    query: str = Field(..., description="The question to ask", min_length=1)
    method: str = Field(
        default="hybrid",
        description="Retrieval method: 'sparse' (BM25), 'dense' (FAISS), or 'hybrid'"
    )
    use_rerank: bool = Field(
        default=True,
        description="Whether to use BM25 reranking on FAISS results"
    )
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return")


# --- Response Schemas ---

class ChunkResponse(BaseModel):
    """Represents a single retrieved chunk"""
    chunk_id: int
    text: str
    score: float
    doc_name: str
    doc_type: str
    chunk_idx: int


class EntropyAnalysis(BaseModel):
    """Results from entropy-based validation"""
    is_confident: bool
    confidence_score: float
    retrieval_entropy: float
    semantic_consistency: float
    interpretation: str


class GroundingCheck(BaseModel):
    """Results from hallucination detection"""
    is_grounded: bool
    overlap_ratio: float
    confidence: str  # "high", "medium", "low"


class ValidationResult(BaseModel):
    """Combined validation results"""
    entropy_analysis: EntropyAnalysis
    grounding_check: GroundingCheck
    overall_confidence: float


class RetrievalStats(BaseModel):
    """Statistics about the retrieval process"""
    method: str
    total_retrieved: int
    after_dedup: int
    after_rerank: int
    after_mmr: int


class QueryResponse(BaseModel):
    """Complete response for a query"""
    synthesized_answer: str = Field(description="LLM-generated answer from the chunks")
    source_chunks: List[ChunkResponse] = Field(description="Raw retrieved chunks with scores")
    query_variants: List[str] = Field(description="The expanded query variants used")
    validation: ValidationResult = Field(description="Confidence and grounding analysis")
    retrieval_stats: RetrievalStats = Field(description="Statistics about retrieval")


class IngestResponse(BaseModel):
    """Response after ingesting a document"""
    doc_id: int
    filename: str
    doc_type: str
    chunks_created: int
    faiss_total: int  # total chunks in FAISS index after this ingest


class DocumentInfo(BaseModel):
    """Information about a single document"""
    id: int
    filename: str
    doc_type: str
    file_size: int
    created_at: datetime
    chunk_count: int


class DocumentListResponse(BaseModel):
    """Paginated list of documents"""
    total: int
    page: int
    size: int
    documents: List[DocumentInfo]


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    faiss_index_size: int
    document_count: int
    chunk_count: int
    llm_status: str


class MetricsResponse(BaseModel):
    """System metrics"""
    total_queries: int
    total_documents: int
    total_chunks: int
    avg_query_latency_ms: float
    retrieval_method_distribution: Dict[str, int]
