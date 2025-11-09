# document ingestion service
# reads files, chunks them, generates embeddings, indexes in FAISS and BM25
# basically turns raw documents into searchable knowledge

import os
import pickle
import numpy as np
import faiss
from rank_bm25 import BM25Okapi
from typing import List, Tuple
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document, Chunk
from app.utils.chunking import chunk_text
from app.services.embedder import embedder


class IngestService:
    """
    Handles document ingestion pipeline
    """

    def __init__(self):
        self.faiss_index_path = settings.FAISS_INDEX_PATH
        self.bm25_index_path = settings.BM25_INDEX_PATH

        # FAISS index (will be loaded/created)
        self.faiss_index = None
        self.embedding_dim = None

        # BM25 index (will be loaded/created)
        self.bm25_index = None
        self.bm25_corpus = []  # list of tokenized documents for BM25

        # mapping from FAISS/BM25 index position to chunk ID
        self.index_to_chunk_id = []

    def initialize_indices(self):
        """
        Load existing indices from disk or create new ones
        Call this on startup
        """
        # try to load FAISS index
        if os.path.exists(self.faiss_index_path):
            print(f"Loading FAISS index from {self.faiss_index_path}")
            self.faiss_index = faiss.read_index(self.faiss_index_path)
            self.embedding_dim = self.faiss_index.d
        else:
            print("No existing FAISS index found, will create on first ingest")
            # get embedding dimension from embedder
            self.embedding_dim = embedder.get_embedding_dimension()
            # create new FAISS index (L2 distance)
            self.faiss_index = faiss.IndexFlatL2(self.embedding_dim)

        # try to load BM25 index
        if os.path.exists(self.bm25_index_path):
            print(f"Loading BM25 index from {self.bm25_index_path}")
            with open(self.bm25_index_path, "rb") as f:
                data = pickle.load(f)
                self.bm25_corpus = data["corpus"]
                self.index_to_chunk_id = data["chunk_ids"]
                if self.bm25_corpus:
                    self.bm25_index = BM25Okapi(self.bm25_corpus)
        else:
            print("No existing BM25 index found, will create on first ingest")

    def save_indices(self):
        """
        Save indices to disk
        """
        # ensure directory exists
        os.makedirs(os.path.dirname(self.faiss_index_path), exist_ok=True)

        # save FAISS
        faiss.write_index(self.faiss_index, self.faiss_index_path)

        # save BM25 (pickle the corpus and chunk mapping)
        with open(self.bm25_index_path, "wb") as f:
            pickle.dump({
                "corpus": self.bm25_corpus,
                "chunk_ids": self.index_to_chunk_id
            }, f)

        print(f"Indices saved. Total chunks indexed: {len(self.index_to_chunk_id)}")

    def ingest_document(
        self,
        file_content: bytes,
        filename: str,
        doc_type: str,
        db: Session
    ) -> Tuple[int, int]:
        """
        Ingest a single document

        Args:
            file_content: Raw file bytes
            filename: Original filename
            doc_type: File type (markdown, text, etc.)
            db: Database session

        Returns:
            (doc_id, num_chunks_created)
        """
        # decode file content
        try:
            text_content = file_content.decode('utf-8')
        except UnicodeDecodeError:
            # try latin-1 as fallback
            text_content = file_content.decode('latin-1')

        # create document record
        doc = Document(
            filename=filename,
            doc_type=doc_type,
            file_size=len(file_content)
        )
        db.add(doc)
        db.flush()  # get the doc.id

        # chunk the text
        chunks = chunk_text(text_content)

        # process each chunk
        chunk_texts = []
        chunk_records = []

        for idx, (chunk_txt, token_count) in enumerate(chunks):
            # create chunk record
            chunk_record = Chunk(
                document_id=doc.id,
                chunk_idx=idx,
                text=chunk_txt,
                token_count=token_count
            )
            db.add(chunk_record)
            chunk_records.append(chunk_record)
            chunk_texts.append(chunk_txt)

        # commit to get chunk IDs
        db.commit()

        # generate embeddings for all chunks
        print(f"Generating embeddings for {len(chunk_texts)} chunks...")
        embeddings = embedder.embed_batch(chunk_texts)

        # add to FAISS index
        embeddings_array = np.array(embeddings, dtype=np.float32)
        self.faiss_index.add(embeddings_array)

        # add to BM25 corpus (tokenized text)
        for chunk_record, chunk_txt_str in zip(chunk_records, chunk_texts):
            # simple tokenization: lowercase + split
            tokens = chunk_txt_str.lower().split()
            self.bm25_corpus.append(tokens)
            self.index_to_chunk_id.append(chunk_record.id)

        # rebuild BM25 index with updated corpus
        if self.bm25_corpus:
            self.bm25_index = BM25Okapi(self.bm25_corpus)

        # save indices
        self.save_indices()

        return doc.id, len(chunks)

    def get_total_indexed(self) -> int:
        """
        Get total number of chunks indexed
        """
        return len(self.index_to_chunk_id)


# global ingest service instance
ingest_service = IngestService()
