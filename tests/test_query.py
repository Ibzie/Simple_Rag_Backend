# basic tests for full query pipeline
# verifies that query expansion, validation, and answer generation work

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module")
def ingest_ml_doc():
    """Ingest a machine learning document for query tests"""
    test_content = b"""# Neural Networks

Neural networks are computing systems inspired by biological neural networks. They consist of interconnected nodes organized in layers.

## Backpropagation

Backpropagation is the fundamental algorithm used to train neural networks. It calculates gradients using the chain rule and updates weights to minimize loss.

## Activation Functions

Common activation functions include ReLU, sigmoid, and tanh. ReLU is most popular for hidden layers because it's computationally efficient.
"""

    files = {"file": ("ml_test.md", test_content, "text/markdown")}
    response = client.post("/api/v1/ingest", files=files)
    assert response.status_code == 200
    return response.json()


def test_full_query_pipeline(ingest_ml_doc):
    """Test the complete query pipeline"""
    query_data = {
        "query": "What is backpropagation?",
        "method": "hybrid",
        "use_rerank": True,
        "top_k": 3
    }

    response = client.post("/api/v1/query", json=query_data)
    assert response.status_code == 200
    data = response.json()

    # verify all components are present
    assert "synthesized_answer" in data
    assert "source_chunks" in data
    assert "query_variants" in data
    assert "validation" in data
    assert "retrieval_stats" in data

    # verify query expansion
    assert len(data["query_variants"]) == 3
    assert data["query_variants"][0] == "What is backpropagation?"

    # verify validation results
    validation = data["validation"]
    assert "entropy_analysis" in validation
    assert "grounding_check" in validation
    assert "overall_confidence" in validation

    # verify entropy analysis
    entropy = validation["entropy_analysis"]
    assert "is_confident" in entropy
    assert "confidence_score" in entropy
    assert "retrieval_entropy" in entropy
    assert "semantic_consistency" in entropy

    # verify grounding check
    grounding = validation["grounding_check"]
    assert "is_grounded" in grounding
    assert "overlap_ratio" in grounding
    assert "confidence" in grounding


def test_query_returns_relevant_chunks(ingest_ml_doc):
    """Test that query returns relevant chunks"""
    query_data = {
        "query": "What is ReLU?",
        "method": "hybrid",
        "use_rerank": True,
        "top_k": 2
    }

    response = client.post("/api/v1/query", json=query_data)
    assert response.status_code == 200
    data = response.json()

    # verify chunks are returned
    assert len(data["source_chunks"]) > 0

    # verify chunk structure
    chunk = data["source_chunks"][0]
    assert "chunk_id" in chunk
    assert "text" in chunk
    assert "score" in chunk
    assert "doc_name" in chunk


def test_empty_query():
    """Test that empty query returns error"""
    query_data = {
        "query": "",
        "method": "hybrid",
        "use_rerank": False,
        "top_k": 3
    }

    response = client.post("/api/v1/query", json=query_data)
    # should fail validation due to min_length=1
    assert response.status_code == 422


def test_query_pagination():
    """Test that top_k parameter limits results"""
    query_data = {
        "query": "neural networks",
        "method": "hybrid",
        "use_rerank": False,
        "top_k": 2
    }

    response = client.post("/api/v1/query", json=query_data)
    assert response.status_code == 200
    data = response.json()

    # should return at most top_k chunks
    assert len(data["source_chunks"]) <= 2
