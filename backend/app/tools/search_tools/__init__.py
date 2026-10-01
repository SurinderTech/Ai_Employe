"""
Search Tools — RAG-powered knowledge base search for the agent.
"""
from __future__ import annotations
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import logger
from app.rag.pipeline import rag_pipeline


async def search_knowledge(
    query: str,
    business_id: str,
    db: AsyncSession,
    top_k: int = 5,
) -> dict[str, Any]:
    """
    Semantic search over the business's knowledge base (properties, FAQs, pricing, policies).

    Returns: {results: [{content, similarity, metadata}, ...], context: str}
    """
    try:
        results = await rag_pipeline.search(
            query=query,
            business_id=business_id,
            db=db,
            top_k=top_k,
        )
        # Concatenate top results into a single context string for the LLM
        context = "\n\n---\n\n".join(r["content"] for r in results)
        logger.info(f"🔍 RAG search '{query[:50]}' → {len(results)} chunks")
        return {
            "results": results,
            "context": context,
            "found": len(results) > 0,
        }
    except Exception as e:
        logger.error(f"Knowledge search failed: {e}")
        return {"results": [], "context": "", "found": False, "error": str(e)}


async def search_properties(
    query: str,
    business_id: str,
    db: AsyncSession,
    filters: dict | None = None,
) -> dict[str, Any]:
    """
    Search for properties in the knowledge base matching customer requirements.
    Builds a targeted query from filters (location, bedrooms, budget).

    Returns: {properties: [...], context: str}
    """
    # Enrich query with filters
    filter_text = ""
    if filters:
        parts = []
        if filters.get("location"):
            parts.append(f"in {filters['location']}")
        if filters.get("bedrooms"):
            parts.append(f"{filters['bedrooms']} BHK")
        if filters.get("budget"):
            parts.append(f"under ₹{filters['budget']} budget")
        if filters.get("property_type"):
            parts.append(filters["property_type"])
        filter_text = " ".join(parts)

    full_query = f"{query} {filter_text}".strip()
    result = await search_knowledge(full_query, business_id, db, top_k=5)

    # Try to parse structured property listings from the context
    # (The actual properties come from whatever the business uploaded)
    return {
        "properties": _extract_properties_from_context(result["results"]),
        "context": result["context"],
        "found": result["found"],
    }


def _extract_properties_from_context(results: list[dict]) -> list[dict]:
    """
    Best-effort extraction of property records from RAG chunks.
    If the business uploaded a structured CSV, chunks may have metadata.
    Otherwise returns raw text chunks formatted as pseudo-cards.
    """
    properties = []
    for r in results[:3]:
        meta = r.get("metadata", {})
        # If metadata has structured fields (from CSV ingestion)
        if meta.get("name") or meta.get("price"):
            properties.append({
                "name": meta.get("name", "Property"),
                "location": meta.get("location", ""),
                "price_lakhs": meta.get("price_lakhs", meta.get("price", "?")),
                "bedrooms": meta.get("bedrooms", "?"),
                "area_sqft": meta.get("area_sqft", "?"),
                "description": r["content"][:200],
            })
        else:
            # Unstructured — return snippet as a card
            properties.append({
                "name": "Property Option",
                "location": "",
                "price_lakhs": "?",
                "bedrooms": "?",
                "area_sqft": "?",
                "description": r["content"][:200],
            })
    return properties
