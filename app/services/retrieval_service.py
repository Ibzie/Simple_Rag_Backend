# retrieval service
# implements sparse (BM25), dense (FAISS), and hybrid search
# includes the smart BM25 reranking on FAISS results

import numpy as np
from typing import List, Tuple, Dict
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.embedder import embedder
from app.services.ingest_service import ingest_service
from app.models.document import Chunk
from app.utils.rrf import reciprocal_rank_fusion


class RetrievalService:
    """
    Handles all retrieval methods
    """

    def sparse_retrieval(self, query: str, top_k: int, db: Session) -> List[Tuple[int, float]]:
        """
        BM25 keyword search

        Args:
            query: Search query
            top_k: Number of results to return
            db: Database session

        Returns:
            List of (chunk_id, score) tuples
        """
        if not ingest_service.bm25_index or not ingest_service.bm25_corpus:
            return []

        # tokenize query (same as we did for corpus)
        query_tokens = query.lower().split()

        # get BM25 scores for all documents
        scores = ingest_service.bm25_index.get_scores(query_tokens)

        # get top-k indices
        top_indices = np.argsort(scores)[::-1][:top_k]

        # convert to (chunk_id, score) tuples
        results = []
        for idx in top_indices:
            chunk_id = ingest_service.index_to_chunk_id[idx]
            score = float(scores[idx])
            results.append((chunk_id, score))

        return results

    def dense_retrieval(self, query: str, top_k: int, db: Session) -> List[Tuple[int, float]]:
        """
        FAISS semantic search using Ollama embeddings

        Args:
            query: Search query
            top_k: Number of results to return
            db: Database session

        Returns:
            List of (chunk_id, score) tuples
        """
        if not ingest_service.faiss_index or ingest_service.faiss_index.ntotal == 0:
            return []

        # embed the query
        query_embedding = embedder.embed_text(query)
        query_vector = np.array([query_embedding], dtype=np.float32)

        # search FAISS index
        # returns distances and indices
        # FAISS uses L2 distance, so lower = more similar
        distances, indices = ingest_service.faiss_index.search(query_vector, top_k)

        # convert L2 distance to similarity score
        # similarity = 1 / (1 + distance)
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            chunk_id = ingest_service.index_to_chunk_id[idx]
            similarity = 1.0 / (1.0 + float(distance))
            results.append((chunk_id, similarity))

        return results

    def hybrid_retrieval(
        self,
        query: str,
        top_k: int,
        db: Session,
        use_rerank: bool = True
    ) -> List[Tuple[int, float]]:
        """
        Hybrid search combining BM25 and FAISS using RRF

        Args:
            query: Search query
            top_k: Number of results to return
            db: Database session
            use_rerank: Whether to apply BM25 reranking on FAISS results

        Returns:
            List of (chunk_id, score) tuples

        The magic happens here:
        1. Get top-20 from FAISS (semantic)
        2. Get top-20 from BM25 (keyword)
        3. If use_rerank: re-score FAISS results with BM25
        4. Merge with RRF
        """
        retrieve_k = min(top_k * 4, 20)  # retrieve more candidates for fusion

        # get results from both methods
        sparse_results = self.sparse_retrieval(query, retrieve_k, db)
        dense_results = self.dense_retrieval(query, retrieve_k, db)

        if use_rerank and dense_results:
            # this is the cool part - BM25 reranking on FAISS candidates
            # get the chunk IDs from FAISS results
            faiss_chunk_ids = [cid for cid, score in dense_results]

            # get the actual chunk texts
            chunks = db.query(Chunk).filter(Chunk.id.in_(faiss_chunk_ids)).all()
            chunk_texts = {c.id: c.text for c in chunks}

            # tokenize query for BM25
            query_tokens = query.lower().split()

            # build a mini BM25 index just for these candidates
            mini_corpus = []
            mini_chunk_ids = []
            for chunk_id in faiss_chunk_ids:
                if chunk_id in chunk_texts:
                    text = chunk_texts[chunk_id]
                    tokens = text.lower().split()
                    mini_corpus.append(tokens)
                    mini_chunk_ids.append(chunk_id)

            if mini_corpus:
                from rank_bm25 import BM25Okapi
                mini_bm25 = BM25Okapi(mini_corpus)
                bm25_scores = mini_bm25.get_scores(query_tokens)

                # replace FAISS scores with BM25 scores
                reranked_results = [(chunk_id, float(score))
                                   for chunk_id, score in zip(mini_chunk_ids, bm25_scores)]

                # use reranked results instead of original FAISS results
                dense_results = reranked_results

        # merge using RRF
        # convert to rankings (just the chunk IDs in order)
        sparse_ranking = [cid for cid, score in sparse_results]
        dense_ranking = [cid for cid, score in dense_results]

        # apply RRF
        rrf_results = reciprocal_rank_fusion([sparse_ranking, dense_ranking])

        # return top-k
        return rrf_results[:top_k]

    def retrieve(
        self,
        query: str,
        method: str,
        top_k: int,
        db: Session,
        use_rerank: bool = True
    ) -> List[Tuple[int, float]]:
        """
        Main retrieval method

        Args:
            query: Search query
            method: 'sparse', 'dense', or 'hybrid'
            top_k: Number of results
            db: Database session
            use_rerank: Whether to use BM25 reranking (only for hybrid)

        Returns:
            List of (chunk_id, score) tuples
        """
        if method == "sparse":
            return self.sparse_retrieval(query, top_k, db)
        elif method == "dense":
            return self.dense_retrieval(query, top_k, db)
        elif method == "hybrid":
            return self.hybrid_retrieval(query, top_k, db, use_rerank)
        else:
            raise ValueError(f"Unknown retrieval method: {method}")


# global retrieval service instance
retrieval_service = RetrievalService()
