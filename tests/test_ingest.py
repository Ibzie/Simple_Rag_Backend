# basic tests for document ingestion
# verifies that the ingestion pipeline works

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Test that the service is running"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_ingest_text_file():
    """Test ingesting a simple text file"""
    # create a simple test file
    test_content = b"This is a test document. It has multiple sentences. We want to test if chunking works properly."

    files = {"file": ("test.txt", test_content, "text/plain")}
    response = client.post("/api/v1/ingest", files=files)

    assert response.status_code == 200
    data = response.json()

    # verify response structure
    assert "doc_id" in data
    assert "filename" in data
    assert "chunks_created" in data
    assert data["filename"] == "test.txt"
    assert data["chunks_created"] > 0


def test_ingest_markdown_file():
    """Test ingesting a markdown file"""
    test_content = b"""# Test Document

This is a test markdown document.

## Section 1

Some content here.

## Section 2

More content here.
"""

    files = {"file": ("test.md", test_content, "text/markdown")}
    response = client.post("/api/v1/ingest", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["doc_type"] == "markdown"


def test_list_documents():
    """Test listing documents"""
    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    data = response.json()

    # verify response structure
    assert "total" in data
    assert "page" in data
    assert "documents" in data
    assert isinstance(data["documents"], list)
