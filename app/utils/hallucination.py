# hallucination detection
# checks if the LLM's answer actually comes from the source chunks
# or if it's making stuff up

from typing import List, Tuple
from app.core.config import settings


def check_grounding(answer: str, source_chunks: List[str]) -> Tuple[bool, float, str]:
    """
    Verify that the generated answer is grounded in the source chunks

    Args:
        answer: The LLM-generated answer
        source_chunks: List of source chunk texts

    Returns:
        (is_grounded, overlap_ratio, confidence_level)

    Method: Simple word overlap check
    - Extract words from answer and sources
    - Count how many answer words appear in sources
    - If >70% overlap -> grounded
    - If <70% overlap -> might be hallucinating

    Yeah this is basic, but it works surprisingly well
    Fancier methods exist (BERTScore, etc.) but add complexity
    """
    threshold = settings.GROUNDING_THRESHOLD

    # normalize and tokenize (simple word splitting)
    def normalize(text: str) -> set:
        # lowercase, split on whitespace, remove short words and punctuation
        words = text.lower().split()
        # keep words that are at least 3 chars and alphanumeric
        return set(w.strip('.,!?;:()[]{}"\'-') for w in words if len(w) >= 3 and w.isalnum())

    answer_words = normalize(answer)
    if not answer_words:
        return False, 0.0, "low"

    # combine all source chunks
    all_source_text = " ".join(source_chunks)
    source_words = normalize(all_source_text)

    # count overlap
    overlapping_words = answer_words.intersection(source_words)
    overlap_ratio = len(overlapping_words) / len(answer_words)

    # determine grounding
    is_grounded = overlap_ratio >= threshold

    # confidence level
    if overlap_ratio >= 0.8:
        confidence = "high"
    elif overlap_ratio >= 0.6:
        confidence = "medium"
    else:
        confidence = "low"

    return is_grounded, overlap_ratio, confidence


def calculate_word_overlap(text1: str, text2: str) -> float:
    """
    Calculate simple word overlap between two texts
    Returns ratio of overlapping words (0.0 to 1.0)
    """
    def get_words(text: str) -> set:
        words = text.lower().split()
        return set(w.strip('.,!?;:()[]{}"\'-') for w in words if len(w) >= 3)

    words1 = get_words(text1)
    words2 = get_words(text2)

    if not words1:
        return 0.0

    overlap = words1.intersection(words2)
    return len(overlap) / len(words1)
