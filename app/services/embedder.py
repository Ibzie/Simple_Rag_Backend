# sentence-transformers embeddings wrapper
# uses sentence-transformers library directly for embeddings
# way faster than calling an API, and runs locally

import numpy as np
from typing import List, Union
from sentence_transformers import SentenceTransformer
from app.core.config import settings


class Embedder:
    """
    Wrapper for sentence-transformers
    Handles batching and provides a clean interface
    """

    def __init__(self):
        self.model_name = settings.EMBEDDING_MODEL
        print(f"Loading embedding model: {self.model_name}")
        # load the model - this downloads it on first run
        # subsequent runs load from cache (~/.cache/torch/sentence_transformers/)
        self.model = SentenceTransformer(self.model_name)
        print(f"Model loaded. Embedding dimension: {self.model.get_sentence_embedding_dimension()}")

    def embed_text(self, text: str) -> np.ndarray:
        """
        Get embedding for a single text

        Args:
            text: Text to embed

        Returns:
            Numpy array of embedding vector
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.astype(np.float32)

    def embed_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Get embeddings for multiple texts
        This is way more efficient than calling embed_text multiple times
        sentence-transformers handles batching internally

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        # convert to list of arrays
        return [emb.astype(np.float32) for emb in embeddings]

    def encode(self, texts: Union[str, List[str]]) -> Union[np.ndarray, List[np.ndarray]]:
        """
        Flexible encode method that handles both single text and batches

        Args:
            texts: Single text string or list of texts

        Returns:
            Single embedding array or list of arrays
        """
        if isinstance(texts, str):
            return self.embed_text(texts)
        else:
            return self.embed_batch(texts)

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings from this model
        Useful for initializing FAISS index
        """
        return self.model.get_sentence_embedding_dimension()

    def check_health(self) -> bool:
        """
        Check if the model is loaded and working

        Returns:
            True if healthy, False otherwise
        """
        try:
            # try to get a simple embedding
            self.embed_text("health check")
            return True
        except Exception:
            return False


# global embedder instance
# import this wherever you need embeddings
embedder = Embedder()
