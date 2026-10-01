"""
RAG Pipeline — ingest documents → chunk → embed → store in pgvector.
Then retrieve relevant chunks for customer queries.
"""
import asyncio
from pathlib import Path
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.core.logging import logger
from app.core.config import settings
import google.generativeai as genai


class RAGPipeline:
    CHUNK_SIZE = 800
    CHUNK_OVERLAP = 100
    TOP_K = 5

    def __init__(self):
        genai.configure(api_key=settings.GOOGLE_API_KEY)

    async def ingest_document(
        self,
        business_id: str,
        document_id: str,
        content: str,
        db: AsyncSession,
        metadata: dict | None = None,
    ) -> int:
        """Chunk a document, embed each chunk, and store in pgvector."""
        from app.models.knowledge import KnowledgeChunk, KnowledgeDocument
        from app.models.knowledge import DocumentStatus

        # Mark as processing
        result = await db.execute(
            select(KnowledgeDocument).where(KnowledgeDocument.id == document_id)
        )
        doc = result.scalar_one_or_none()
        if doc:
            doc.status = DocumentStatus.PROCESSING
            await db.flush()

        chunks = self._chunk_text(content)
        logger.info(f"📄 Chunking document {document_id} → {len(chunks)} chunks")

        stored = 0
        for i, chunk_text in enumerate(chunks):
            try:
                embedding = await self._embed(chunk_text)
                chunk = KnowledgeChunk(
                    document_id=document_id,
                    business_id=business_id,
                    content=chunk_text,
                    chunk_index=i,
                    embedding=embedding,
                    metadata=metadata or {},
                )
                db.add(chunk)
                stored += 1
            except Exception as e:
                logger.error(f"Failed to embed chunk {i}: {e}")

        await db.flush()

        if doc:
            doc.status = DocumentStatus.COMPLETED
            doc.chunk_count = stored

        logger.info(f"✅ Ingested {stored}/{len(chunks)} chunks for document {document_id}")
        return stored

    def _chunk_text(self, text: str) -> list[str]:
        """Simple sliding window chunker."""
        if len(text) <= self.CHUNK_SIZE:
            return [text]
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.CHUNK_SIZE
            chunk = text[start:end]
            # Try to break on sentence boundary
            if end < len(text):
                last_period = chunk.rfind(". ")
                if last_period > self.CHUNK_SIZE // 2:
                    end = start + last_period + 2
                    chunk = text[start:end]
            chunks.append(chunk.strip())
            start = end - self.CHUNK_OVERLAP
        return [c for c in chunks if c]

    async def _embed(self, text: str) -> list[float]:
        """Embed text using Google text-embedding-004."""
        loop = asyncio.get_event_loop()
        def _call():
            result = genai.embed_content(
                model=settings.EMBEDDING_MODEL,
                content=text,
                task_type="retrieval_document",
            )
            return result["embedding"]
        return await loop.run_in_executor(None, _call)

    async def _embed_query(self, query: str) -> list[float]:
        loop = asyncio.get_event_loop()
        def _call():
            result = genai.embed_content(
                model=settings.EMBEDDING_MODEL,
                content=query,
                task_type="retrieval_query",
            )
            return result["embedding"]
        return await loop.run_in_executor(None, _call)

    async def search(
        self,
        query: str,
        business_id: str,
        db: AsyncSession,
        top_k: int | None = None,
    ) -> list[dict]:
        """Semantic search — returns top-k relevant chunks."""
        top_k = top_k or self.TOP_K
        query_embedding = await self._embed_query(query)

        # pgvector cosine similarity search
        embedding_str = f"[{','.join(str(x) for x in query_embedding)}]"
        sql = text("""
            SELECT id, content, metadata,
                   1 - (embedding <=> :embedding::vector) AS similarity
            FROM knowledge_chunks
            WHERE business_id = :business_id
              AND embedding IS NOT NULL
            ORDER BY embedding <=> :embedding::vector
            LIMIT :top_k
        """)
        result = await db.execute(
            sql,
            {"embedding": embedding_str, "business_id": str(business_id), "top_k": top_k},
        )
        rows = result.fetchall()
        return [
            {"id": str(r.id), "content": r.content, "similarity": float(r.similarity), "metadata": r.metadata}
            for r in rows
        ]

    async def ingest_pdf(self, path: str, business_id: str, document_id: str, db: AsyncSession) -> int:
        """Extract text from PDF and ingest."""
        from pypdf import PdfReader
        reader = PdfReader(path)
        full_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return await self.ingest_document(business_id, document_id, full_text, db)


# Singleton
rag_pipeline = RAGPipeline()
