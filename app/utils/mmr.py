# Maximal Marginal Relevance (MMR)
# picks diverse results instead of returning redundant chunks
# balances relevance to query vs diversity from already-selected results

import numpy as np
from typing import List, Tuple
from sklearn.metrics.pairwise import cosine_similarity
from app.core.config import settings


def maximal_marginal_relevance(
    query_embedding: np.ndarray,
    candidate_embeddings: List[np.ndarray],
    candidate_ids: List[int],
    lambda_param: float = None,
    top_k: int = 5
) -> List[int]:
    """
    Select diverse results using MMR

    Args:
        query_embedding: The query's embedding vector
        candidate_embeddings: List of embeddings for candidate chunks
        candidate_ids: Corresponding chunk IDs
        lambda_param: Balance between relevance (1.0) and diversity (0.0)
                      Default 0.7 = 70% relevance, 30% diversity
        top_k: Number of results to return

    Returns:
        List of selected chunk IDs (in order of selection)

    Algorithm:
    1. Start with the most relevant chunk
    2. For each remaining chunk, calculate MMR score:
       MMR = λ * relevance_to_query - (1-λ) * max_similarity_to_selected
    3. Pick chunk with highest MMR score
    4. Repeat until we have top_k chunks

    Why? If all top results say the same thing (just worded differently),
    that's not helpful. MMR ensures we get diverse information.
    """
    lambda_param = lambda_param or settings.MMR_LAMBDA

    if len(candidate_ids) <= top_k:
        # not enough candidates to diversify, return all
        return candidate_ids

    # convert to numpy arrays if needed
    query_emb = np.array(query_embedding).reshape(1, -1)
    candidate_embs = np.array(candidate_embeddings)

    # calculate relevance scores (similarity to query) for all candidates
    relevance_scores = cosine_similarity(query_emb, candidate_embs)[0]

    # start with the most relevant chunk
    selected_indices = [int(np.argmax(relevance_scores))]
    remaining_indices = [i for i in range(len(candidate_ids)) if i != selected_indices[0]]

    # iteratively select diverse chunks
    while len(selected_indices) < top_k and remaining_indices:
        mmr_scores = []

        for idx in remaining_indices:
            # relevance to query
            relevance = relevance_scores[idx]

            # max similarity to any already-selected chunk
            selected_embs = candidate_embs[selected_indices]
            current_emb = candidate_embs[idx].reshape(1, -1)
            similarities = cosine_similarity(current_emb, selected_embs)[0]
            max_sim_to_selected = np.max(similarities)

            # MMR formula
            mmr = lambda_param * relevance - (1 - lambda_param) * max_sim_to_selected
            mmr_scores.append((idx, mmr))

        # pick the chunk with highest MMR score
        best_idx, best_score = max(mmr_scores, key=lambda x: x[1])
        selected_indices.append(best_idx)
        remaining_indices.remove(best_idx)

    # convert indices back to chunk IDs
    selected_ids = [candidate_ids[idx] for idx in selected_indices]

    return selected_ids


def simple_mmr_rerank(
    chunks_with_scores: List[Tuple[int, str, float, np.ndarray]],
    lambda_param: float = None,
    top_k: int = 5
) -> List[Tuple[int, str, float]]:
    """
    Simplified MMR that works with (chunk_id, text, score, embedding) tuples

    Args:
        chunks_with_scores: List of (chunk_id, text, score, embedding)
        lambda_param: MMR balance parameter
        top_k: Number to return

    Returns:
        List of (chunk_id, text, score) tuples after MMR reranking
    """
    if len(chunks_with_scores) <= top_k:
        return [(cid, txt, score) for cid, txt, score, emb in chunks_with_scores]

    lambda_param = lambda_param or settings.MMR_LAMBDA

    # extract embeddings and compute pairwise similarities
    embeddings = np.array([emb for _, _, _, emb in chunks_with_scores])

    selected_indices = []
    remaining_indices = list(range(len(chunks_with_scores)))

    # start with highest scored chunk
    best_idx = max(remaining_indices, key=lambda i: chunks_with_scores[i][2])
    selected_indices.append(best_idx)
    remaining_indices.remove(best_idx)

    # iteratively select diverse chunks
    while len(selected_indices) < top_k and remaining_indices:
        mmr_scores = []

        for idx in remaining_indices:
            # original relevance score
            relevance = chunks_with_scores[idx][2]

            # similarity to selected chunks
            selected_embs = embeddings[selected_indices]
            current_emb = embeddings[idx].reshape(1, -1)
            sims = cosine_similarity(current_emb, selected_embs)[0]
            max_sim = np.max(sims)

            # MMR score
            mmr = lambda_param * relevance - (1 - lambda_param) * max_sim
            mmr_scores.append((idx, mmr))

        best_idx, _ = max(mmr_scores, key=lambda x: x[1])
        selected_indices.append(best_idx)
        remaining_indices.remove(best_idx)

    # return selected chunks (without embeddings)
    return [(chunks_with_scores[idx][0], chunks_with_scores[idx][1], chunks_with_scores[idx][2])
            for idx in selected_indices]
