# entropy-based validation - THE SECRET SAUCE
# inspired by Anthropic's circuit tracing research
# measures if multiple query variants retrieve consistent results
# low entropy = confident answer, high entropy = uncertain/hallucinating

import numpy as np
from typing import List, Dict, Any
from collections import Counter
from scipy.stats import entropy as scipy_entropy
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.orm import Session

from app.core.config import settings


class EntropyValidator:
    """
    Validates retrieval results using entropy analysis

    Key Insight: Robust answers should converge when approached from
    multiple query reformulations. If different phrasings of the same
    question retrieve wildly different chunks, we probably don't have
    a good answer.
    """

    def validate(
        self,
        query_variants: List[str],
        retrieval_by_variant: Dict[str, List[int]],
        final_chunk_ids: List[int],
        chunk_data: Dict[int, Dict],
        db: Session
    ) -> Dict[str, Any]:
        """
        Perform entropy-based validation

        Args:
            query_variants: The 3 query reformulations
            retrieval_by_variant: Dict mapping each variant to its retrieved chunk IDs
            final_chunk_ids: The final selected chunks
            chunk_data: Dict with chunk metadata and embeddings
            db: Database session

        Returns:
            Validation results with entropy analysis and confidence scores
        """
        # Step 1: Calculate retrieval entropy
        # How consistent are the retrievals across query variants?

        all_retrieved_chunks = []
        for variant, chunk_ids in retrieval_by_variant.items():
            all_retrieved_chunks.extend(chunk_ids)

        # count frequency of each chunk across variants
        chunk_frequency = Counter(all_retrieved_chunks)

        # calculate entropy of this frequency distribution
        # low entropy = a few chunks appear very frequently (consistent)
        # high entropy = chunks are evenly distributed (inconsistent)

        if len(chunk_frequency) == 0:
            # no results at all
            return self._empty_validation()

        # get frequency values and normalize to probabilities
        frequencies = np.array(list(chunk_frequency.values()), dtype=float)
        probabilities = frequencies / frequencies.sum()

        # calculate Shannon entropy
        retrieval_entropy = scipy_entropy(probabilities)

        # normalize entropy to [0, 1] range
        # max entropy is log(n) where n is number of unique chunks
        max_entropy = np.log(len(chunk_frequency))
        normalized_entropy = retrieval_entropy / max_entropy if max_entropy > 0 else 0

        # Step 2: Check semantic consistency of consensus chunks
        # Get the chunks that appeared most frequently (consensus chunks)

        # chunks that appeared in at least 2 out of 3 variants
        consensus_chunks = [chunk_id for chunk_id, freq in chunk_frequency.items() if freq >= 2]

        if len(consensus_chunks) >= 2:
            # calculate pairwise cosine similarity of consensus chunks
            consensus_embeddings = []
            for chunk_id in consensus_chunks[:5]:  # limit to top 5 for efficiency
                if chunk_id in chunk_data:
                    consensus_embeddings.append(chunk_data[chunk_id]["embedding"])

            if len(consensus_embeddings) >= 2:
                # calculate average pairwise similarity
                embeddings_array = np.array(consensus_embeddings)
                similarity_matrix = cosine_similarity(embeddings_array)

                # get upper triangle (excluding diagonal)
                n = len(similarity_matrix)
                similarities = []
                for i in range(n):
                    for j in range(i+1, n):
                        similarities.append(similarity_matrix[i][j])

                semantic_consistency = np.mean(similarities) if similarities else 0.0
            else:
                semantic_consistency = 0.5  # neutral
        else:
            semantic_consistency = 0.3  # low consistency

        # Step 3: Determine confidence

        # confident if:
        # - low entropy (< threshold) = consistent retrieval
        # - high semantic consistency = consensus chunks are similar

        is_confident = (
            normalized_entropy < settings.ENTROPY_THRESHOLD and
            semantic_consistency > 0.6
        )

        # calculate overall confidence score (0-1)
        # weight: 60% from low entropy, 40% from semantic consistency
        entropy_score = 1.0 - normalized_entropy  # flip so higher = better
        confidence_score = 0.6 * entropy_score + 0.4 * semantic_consistency

        # Step 4: Generate interpretation

        if is_confident:
            if normalized_entropy < 0.2:
                interpretation = (
                    "HIGH CONFIDENCE: Query variants converge strongly. "
                    f"Top chunks appear in {np.max(list(chunk_frequency.values()))}/3 variants. "
                    "Answer is well-supported."
                )
            else:
                interpretation = (
                    "MODERATE CONFIDENCE: Query variants show reasonable agreement. "
                    "Answer is likely accurate but may benefit from more context."
                )
        else:
            if normalized_entropy > 0.7:
                interpretation = (
                    "LOW CONFIDENCE: Query variants retrieve different chunks. "
                    "Results are inconsistent - possible hallucination risk. "
                    "Consider rephrasing the question."
                )
            else:
                interpretation = (
                    "UNCERTAIN: Some consistency in retrieval but semantic similarity is low. "
                    "Answer may be partially grounded but lacks strong support."
                )

        return {
            "overall_confidence": confidence_score,
            "entropy_analysis": {
                "is_confident": is_confident,
                "confidence_score": confidence_score,
                "retrieval_entropy": normalized_entropy,
                "semantic_consistency": semantic_consistency,
                "interpretation": interpretation
            }
        }

    def _empty_validation(self) -> Dict[str, Any]:
        """Return default validation when no results found"""
        return {
            "overall_confidence": 0.0,
            "entropy_analysis": {
                "is_confident": False,
                "confidence_score": 0.0,
                "retrieval_entropy": 1.0,
                "semantic_consistency": 0.0,
                "interpretation": "NO RESULTS: No relevant chunks found for this query."
            }
        }


# global validator instance
entropy_validator = EntropyValidator()
