"""Knowledge base semantic search tool using pgvector + local embeddings."""
from pydantic import BaseModel, Field
from agents import function_tool
from production.agent.llm_client import generate_embedding_async
from production.database import repositories


@function_tool
async def search_knowledge_base(query: str, max_results: int = 5) -> str:
    """Search knowledge base using semantic similarity. Returns formatted results."""
    try:
        # Generate embedding locally (free, no API key needed)
        embedding = await generate_embedding_async(query)

        # Search pgvector
        results = await repositories.search_knowledge_base(embedding, max_results)

        if not results:
            return "No relevant knowledge base entries found."

        formatted = []
        for r in results:
            similarity = r.get("similarity", 0)
            formatted.append(f"[{similarity:.2f}] {r['title']}: {r['content']}")

        return "\n\n".join(formatted)
    except Exception as e:
        return f"Knowledge base search error: {e}"
