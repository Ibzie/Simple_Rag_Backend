# basic tests for retrieval functionality
# verifies that different retrieval methods work

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# setup: ingest a test document
@pytest.fixture(scope="module")
def ingest_test_doc():
    """Ingest a test document for retrieval tests"""
    test_content = b"""# Python Programming

Python is a high-level programming language. It is known for its simplicity and readability.

## Functions

Functions in Python are defined using the def keyword. They can accept parameters and return values.

## Lists

Lists are ordered collections in Python. They can contain items of different types.
"""

    files = {"file": ("python_test.md", test_content, "text/markdown")}
    response = client.post("/api/v1/ingest", files=files)
    assert response.status_code == 200
    return response.json()


def test_sparse_retrieval(ingest_test_doc):
    """Test BM25 (sparse) retrieval"""
    query_data = {
        "query": "What is Python?",
        "method": "sparse",
        "use_rerank": False,
        "top_k": 3
    }

    response = client.post("/api/v1/query", json=query_data)
    assert response.status_code == 200
    data = response.json()

    # verify response structure
    assert "source_chunks" in data
    assert "retrieval_stats" in data
    assert data["retrieval_stats"]["method"] == "sparse"


def test_dense_retrieval(ingest_test_doc):
    """Test FAISS (dense) retrieval"""
    query_data = {
        "query": "What is Python?",
        "method": "dense",
        "use_rerank": False,
        "top_k": 3
    }

    response = client.post("/api/v1/query", json=query_data)
    assert response.status_code == 200
    data = response.json()

    assert "source_chunks" in data
    assert data["retrieval_stats"]["method"] == "dense"


def test_hybrid_retrieval(ingest_test_doc):
    """Test hybrid retrieval (BM25 + FAISS)"""
    query_data = {
        "query": "What is Python?",
        "method": "hybrid",
        "use_rerank": True,
        "top_k": 3
    }

    response = client.post("/api/v1/query", json=query_data)
    assert response.status_code == 200
    data = response.json()

    assert "source_chunks" in data
    assert "hybrid" in data["retrieval_stats"]["method"]


def test_invalid_method():
    """Test that invalid retrieval method returns error"""
    query_data = {
        "query": "test",
        "method": "invalid_method",
        "use_rerank": False,
        "top_k": 3
    }

    response = client.post("/api/v1/query", json=query_data)
    assert response.status_code == 400
