# services module - this is where the magic happens
# embedder talks to Ollama for vectors
# ingest service processes documents
# retrieval does the hybrid BM25+FAISS search
# query agent orchestrates the whole RAG pipeline
# validator does the entropy-based confidence scoring (the secret sauce)
