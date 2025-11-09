# SQLAlchemy database models
# Document table stores metadata about uploaded files
# Chunk table stores the actual text chunks with their positions
# one document has many chunks - classic one-to-many relationship

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Document(Base):
    """
    Stores document metadata
    Each uploaded file becomes one Document record
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False, index=True)
    doc_type = Column(String, nullable=False)  # markdown, text, etc.
    file_size = Column(Integer)  # in bytes
    created_at = Column(DateTime, default=datetime.utcnow)

    # relationship to chunks - one doc has many chunks
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")


class Chunk(Base):
    """
    Stores individual text chunks from documents
    Each chunk is ~512 tokens with 50-token overlap
    chunk_idx tracks the order within the document
    """
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    chunk_idx = Column(Integer, nullable=False)  # position in the document (0, 1, 2, ...)
    text = Column(Text, nullable=False)  # the actual chunk content
    token_count = Column(Integer)  # how many tokens in this chunk

    # relationship back to document
    document = relationship("Document", back_populates="chunks")

    class Config:
        orm_mode = True
