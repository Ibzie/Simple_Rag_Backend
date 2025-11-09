# Reciprocal Rank Fusion (RRF)
# combines results from multiple ranking methods (BM25 + FAISS)
# works by using ranks instead of scores, which is smart because
# different methods have wildly different score scales

from typing import List, Dict, Tuple
from app.core.config import settings


def reciprocal_rank_fusion(
    rankings: List[List[int]],
    k: int = None
) -> List[Tuple[int, float]]:
    """
    Combine multiple rankings using Reciprocal Rank Fusion

    Args:
        rankings: List of ranked item IDs from different methods
                  Example: [[chunk_5, chunk_1, chunk_3], [chunk_1, chunk_5, chunk_8]]
        k: Constant for RRF formula (default from settings)

    Returns:
        List of (item_id, rrf_score) tuples, sorted by score descending

    Formula: RRF_score(item) = sum(1 / (k + rank_in_method_i))
    where rank starts at 1 (not 0)

    Why RRF? Different retrieval methods return scores on different scales:
    - BM25 scores can be anywhere from 0 to infinity
    - Cosine similarity is 0 to 1
    - Can't just average those scores, it'd be meaningless
    - RRF only cares about rank position, not the actual score value
    """
    k = k or settings.RRF_K

    # collect scores for each item
    item_scores: Dict[int, float] = {}

    for ranking in rankings:
        for rank, item_id in enumerate(ranking, start=1):
            # RRF formula: 1 / (k + rank)
            score = 1.0 / (k + rank)

            if item_id in item_scores:
                item_scores[item_id] += score
            else:
                item_scores[item_id] = score

    # convert to list and sort by score descending
    results = sorted(item_scores.items(), key=lambda x: x[1], reverse=True)

    return results


def combine_scored_results(
    results_lists: List[List[Tuple[int, float]]],
    k: int = None
) -> List[Tuple[int, float]]:
    """
    Helper function when you already have (item_id, score) tuples
    Converts to rankings (discarding original scores) then applies RRF

    Args:
        results_lists: List of [(item_id, score)] lists from different methods
        k: RRF constant

    Returns:
        Combined results using RRF
    """
    # extract just the item IDs (rankings)
    rankings = []
    for results in results_lists:
        # sort by score descending to get ranking
        sorted_results = sorted(results, key=lambda x: x[1], reverse=True)
        ranking = [item_id for item_id, score in sorted_results]
        rankings.append(ranking)

    return reciprocal_rank_fusion(rankings, k)
