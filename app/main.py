# main FastAPI application
# wires everything together and sets up the API

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.database import init_db
from app.core.config import settings
from app.services.ingest_service import ingest_service
from app.api.routes import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown events
    Load indices on startup, clean up on shutdown
    """
    # Startup
    print("=" * 50)
    print("RAG Microservice Starting...")
    print("=" * 50)

    # initialize database
    print("Initializing database...")
    init_db()

    # initialize indices
    print("Loading FAISS and BM25 indices...")
    ingest_service.initialize_indices()

    print("=" * 50)
    print("RAG Microservice Ready!")
    print(f"FAISS index size: {ingest_service.get_total_indexed()} chunks")
    print(f"Embedding model: {settings.EMBEDDING_MODEL}")
    print(f"LLM model: {settings.LLM_MODEL}")
    print("=" * 50)

    yield

    # Shutdown
    print("Shutting down RAG Microservice...")
    # could save indices here if needed, but ingest_service already saves on each ingest


# create FastAPI app
app = FastAPI(
    title="RAG Microservice",
    description="Document Q&A with hybrid retrieval and entropy-based validation",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - allows requests from any origin
# in production, you'd restrict this to specific domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include all API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """
    Root endpoint - basic info about the service
    """
    return {
        "service": "RAG Microservice",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "ingest": "POST /api/v1/ingest",
            "query": "POST /api/v1/query",
            "documents": "GET /api/v1/documents",
            "health": "GET /api/v1/health",
            "metrics": "GET /api/v1/metrics"
        }
    }
