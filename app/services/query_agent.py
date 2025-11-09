# query agent - orchestrates the full RAG pipeline
# handles query expansion, retrieval, MMR, validation, and answer generation using Groq LLM

import httpx
from typing import List, Tuple, Dict, Any
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.retrieval_service import retrieval_service
from app.services.embedder import embedder
from app.services.validator import entropy_validator
from app.models.document import Chunk, Document
from app.utils.hallucination import check_grounding


class QueryAgent:
    """
    Orchestrates the full RAG query pipeline
    """

    def __init__(self):
        self.groq_api_key = settings.GROQ_API_KEY
        self.llm_model = settings.LLM_MODEL
        self.groq_api_url = "https://api.groq.com/openai/v1/chat/completions"

    def expand_query(self, original_query: str) -> List[str]:
        """
        Generate 3 query variants using Groq LLM

        Args:
            original_query: The user's original question

        Returns:
            List of 3 query strings (including the original)

        Why? Different phrasings might retrieve different relevant chunks
        Inspired by multi-query retrieval strategies
        """
        # prompt for query expansion
        system_prompt = "You are a helpful assistant that generates alternative phrasings of questions. Generate exactly 2 alternative ways to ask the given question. Keep them concise and focused. Output only the alternatives, one per line, without numbering or labels."

        try:
            response = httpx.post(
                self.groq_api_url,
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.llm_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Generate 2 alternative phrasings for: {original_query}"}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 100
                },
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            generated_text = result["choices"][0]["message"]["content"].strip()

            # parse out the alternatives
            lines = [l.strip() for l in generated_text.split('\n') if l.strip()]
            variants = [original_query]  # always include original

            # extract up to 2 alternatives
            for line in lines[:2]:
                # remove any numbering or labels if present
                clean_line = line.replace("Alternative 1:", "").replace("Alternative 2:", "").strip()
                clean_line = clean_line.lstrip("12.-) ")
                if clean_line and len(clean_line) > 10:
                    variants.append(clean_line)

            # fallback if parsing failed
            if len(variants) < 3:
                # just make simple variations
                variants.append(f"Explain {original_query.lower()}")
                if len(variants) < 3:
                    variants.append(f"What is {original_query.lower()}?")

            return variants[:3]

        except Exception as e:
            print(f"Error expanding query: {e}")
            # fallback to just the original query repeated
            return [original_query, original_query, original_query]

    def generate_answer(self, query: str, chunks: List[str]) -> str:
        """
        Generate answer from retrieved chunks using Groq LLM

        Args:
            query: The user's question
            chunks: List of relevant text chunks

        Returns:
            Generated answer string
        """
        # build context from chunks
        context = "\n\n".join([f"[{i+1}] {chunk}" for i, chunk in enumerate(chunks)])

        # system prompt for answer generation
        system_prompt = "You are a helpful assistant that answers questions based on provided context. Be concise and factual. Only use information from the provided context. If the context doesn't contain enough information to answer the question, say so."

        user_prompt = f"""Context:
{context}

Question: {query}"""

        try:
            response = httpx.post(
                self.groq_api_url,
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.llm_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": settings.LLM_TEMPERATURE,
                    "max_tokens": settings.LLM_MAX_TOKENS
                },
                timeout=60.0
            )
            response.raise_for_status()
            result = response.json()
            answer = result["choices"][0]["message"]["content"].strip()

            if not answer:
                return "I couldn't generate an answer from the provided context."

            return answer

        except Exception as e:
            print(f"Error generating answer: {e}")
            return f"Error generating answer: {str(e)}"

    def query(
        self,
        query: str,
        method: str,
        use_rerank: bool,
        top_k: int,
        db: Session
    ) -> Dict[str, Any]:
        """
        Full RAG query pipeline

        Pipeline:
        1. Query expansion (3 variants)
        2. Multi-query retrieval
        3. Deduplication
        4. BM25 reranking (if enabled)
        5. MMR diversity
        6. Entropy validation
        7. Answer generation
        8. Hallucination check

        Returns:
            Complete query response with answer, chunks, validation, etc.
        """
        # Step 1: Query expansion
        query_variants = self.expand_query(query)

        # Step 2: Multi-query retrieval
        all_results = {}  # chunk_id -> best_score
        retrieval_by_variant = {}  # track which chunks each variant retrieved

        for variant in query_variants:
            results = retrieval_service.retrieve(variant, method, top_k * 2, db, use_rerank)
            retrieval_by_variant[variant] = [cid for cid, score in results]

            for chunk_id, score in results:
                if chunk_id not in all_results or score > all_results[chunk_id]:
                    all_results[chunk_id] = score

        # Step 3: Deduplicate and sort
        deduped_results = sorted(all_results.items(), key=lambda x: x[1], reverse=True)
        after_dedup_count = len(deduped_results)

        # Step 4: Get top candidates for MMR
        candidate_count = min(top_k * 2, len(deduped_results))
        candidates = deduped_results[:candidate_count]

        # Step 5: Apply MMR diversity
        # get chunk data with embeddings
        candidate_ids = [cid for cid, score in candidates]
        chunks = db.query(Chunk).filter(Chunk.id.in_(candidate_ids)).all()

        chunk_data = {}
        for chunk in chunks:
            # get embedding for this chunk
            embedding = embedder.embed_text(chunk.text)
            chunk_data[chunk.id] = {
                "text": chunk.text,
                "embedding": embedding,
                "score": all_results[chunk.id],
                "doc_id": chunk.document_id,
                "chunk_idx": chunk.chunk_idx
            }

        # apply MMR if we have enough candidates
        if len(candidates) > top_k:
            from app.utils.mmr import maximal_marginal_relevance
            query_embedding = embedder.embed_text(query)
            candidate_embeddings = [chunk_data[cid]["embedding"] for cid in candidate_ids]

            selected_ids = maximal_marginal_relevance(
                query_embedding,
                candidate_embeddings,
                candidate_ids,
                top_k=top_k
            )
        else:
            selected_ids = candidate_ids[:top_k]

        # Step 6: Entropy validation
        validation_result = entropy_validator.validate(
            query_variants,
            retrieval_by_variant,
            selected_ids,
            chunk_data,
            db
        )

        # Step 7: Prepare chunks for answer generation
        source_chunks = []
        chunk_texts = []

        for chunk_id in selected_ids:
            if chunk_id in chunk_data:
                data = chunk_data[chunk_id]
                chunk_texts.append(data["text"])

                # get document info
                doc = db.query(Document).filter(Document.id == data["doc_id"]).first()

                source_chunks.append({
                    "chunk_id": chunk_id,
                    "text": data["text"],
                    "score": data["score"],
                    "doc_name": doc.filename if doc else "unknown",
                    "doc_type": doc.doc_type if doc else "unknown",
                    "chunk_idx": data["chunk_idx"]
                })

        # Step 8: Generate answer
        synthesized_answer = self.generate_answer(query, chunk_texts)

        # Step 9: Hallucination check
        is_grounded, overlap_ratio, confidence = check_grounding(
            synthesized_answer,
            chunk_texts
        )

        # Build response
        return {
            "synthesized_answer": synthesized_answer,
            "source_chunks": source_chunks,
            "query_variants": query_variants,
            "validation": {
                "entropy_analysis": validation_result["entropy_analysis"],
                "grounding_check": {
                    "is_grounded": is_grounded,
                    "overlap_ratio": overlap_ratio,
                    "confidence": confidence
                },
                "overall_confidence": validation_result["overall_confidence"]
            },
            "retrieval_stats": {
                "method": method + ("_rerank" if use_rerank else ""),
                "total_retrieved": len(all_results),
                "after_dedup": after_dedup_count,
                "after_rerank": after_dedup_count,  # reranking happens during retrieval
                "after_mmr": len(selected_ids)
            }
        }


# global query agent instance
query_agent = QueryAgent()
