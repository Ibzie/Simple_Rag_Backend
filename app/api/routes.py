from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
import traceback

from app.core.database import get_db
from app.models.schemas import (
    IngestResponse, QueryRequest, QueryResponse,
    DocumentListResponse, DocumentInfo,
    HealthResponse, MetricsResponse
)
from app.models.document import Document, Chunk
from app.services.ingest_service import ingest_service
from app.services.query_agent import query_agent
from app.services.embedder import embedder

router = APIRouter()


# ============================================================================
# INGEST ENDPOINT
# ============================================================================

@router.post("/ingest", response_model=IngestResponse, tags=["Ingest"])
async def ingest_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Ingest a document (text or markdown file)

    - Reads the file
    - Chunks it into 512-token pieces with overlap
    - Generates embeddings
    - Indexes in FAISS and BM25
    - Saves to database

    Returns metadata about the ingested document
    """
    try:
        # read file content
        file_content = await file.read()

        # determine doc type from filename
        filename = file.filename
        if filename.endswith('.md'):
            doc_type = "markdown"
        elif filename.endswith('.txt'):
            doc_type = "text"
        else:
            doc_type = "unknown"

        # ingest the document
        doc_id, num_chunks = ingest_service.ingest_document(
            file_content=file_content,
            filename=filename,
            doc_type=doc_type,
            db=db
        )

        # get total indexed chunks
        total_indexed = ingest_service.get_total_indexed()

        return IngestResponse(
            doc_id=doc_id,
            filename=filename,
            doc_type=doc_type,
            chunks_created=num_chunks,
            faiss_total=total_indexed
        )

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error ingesting document: {str(e)}")


# ============================================================================
# QUERY ENDPOINT
# ============================================================================

@router.post("/query", response_model=QueryResponse, tags=["Query"])
async def query_documents(
    request: QueryRequest,
    db: Session = Depends(get_db)
):
    """
    Query the RAG system

    Full pipeline:
    1. Query expansion (3 variants)
    2. Multi-query retrieval (BM25, FAISS, or hybrid)
    3. Deduplication
    4. Optional BM25 reranking
    5. MMR diversity filtering
    6. Entropy validation
    7. LLM answer generation
    8. Hallucination check

    Returns both synthesized answer and source chunks
    """
    try:
        # validate method
        if request.method not in ["sparse", "dense", "hybrid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid method '{request.method}'. Must be 'sparse', 'dense', or 'hybrid'"
            )

        # run the full query pipeline
        result = query_agent.query(
            query=request.query,
            method=request.method,
            use_rerank=request.use_rerank,
            top_k=request.top_k,
            db=db
        )

        return QueryResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


# ============================================================================
# DOCUMENTS ENDPOINT
# ============================================================================

@router.get("/documents", response_model=DocumentListResponse, tags=["Documents"])
async def list_documents(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    List all ingested documents with pagination

    Returns document metadata including:
    - Filename, type, size
    - Creation timestamp
    - Number of chunks created
    """
    try:
        # get total count
        total = db.query(Document).count()

        # calculate offset
        offset = (page - 1) * size

        # get paginated documents
        docs = db.query(Document).offset(offset).limit(size).all()

        # build response
        doc_infos = []
        for doc in docs:
            # count chunks for this document
            chunk_count = db.query(Chunk).filter(Chunk.document_id == doc.id).count()

            doc_infos.append(DocumentInfo(
                id=doc.id,
                filename=doc.filename,
                doc_type=doc.doc_type,
                file_size=doc.file_size,
                created_at=doc.created_at,
                chunk_count=chunk_count
            ))

        return DocumentListResponse(
            total=total,
            page=page,
            size=size,
            documents=doc_infos
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing documents: {str(e)}")


# ============================================================================
# HEALTH & METRICS ENDPOINTS
# ============================================================================

@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint

    Returns:
    - Service status
    - Index sizes
    - Document/chunk counts
    - Embedder status
    """
    try:
        # check if indices are loaded
        faiss_size = ingest_service.get_total_indexed()

        # check document and chunk counts
        doc_count = db.query(Document).count()
        chunk_count = db.query(Chunk).count()

        # check embedder health
        embedder_healthy = embedder.check_health()
        embedder_status = "healthy" if embedder_healthy else "unhealthy"

        return HealthResponse(
            status="healthy",
            faiss_index_size=faiss_size,
            document_count=doc_count,
            chunk_count=chunk_count,
            llm_status=embedder_status
        )

    except Exception as e:
        return HealthResponse(
            status="degraded",
            faiss_index_size=0,
            document_count=0,
            chunk_count=0,
            llm_status=f"error: {str(e)}"
        )


@router.get("/metrics", response_model=MetricsResponse, tags=["Metrics"])
async def get_metrics(db: Session = Depends(get_db)):
    """
    Get system metrics

    Note: In a production system, you'd track these with proper monitoring
    For now, we return basic stats
    """
    try:
        total_docs = db.query(Document).count()
        total_chunks = db.query(Chunk).count()

        # Placeholder metrics | would need middleware for tracking
        # in production, track these in Redis or similar
        return MetricsResponse(
            total_queries=0,  # would track this with middleware
            total_documents=total_docs,
            total_chunks=total_chunks,
            avg_query_latency_ms=0.0,  # would track this with middleware
            retrieval_method_distribution={}  # would track this with middleware
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting metrics: {str(e)}")
