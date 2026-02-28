"""MCP tool: Search knowledge base using pgvector semantic similarity."""
import os
import asyncpg
from openai import AsyncOpenAI

_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://fte_user:fte_pass@localhost:5432/fte_crm")

async def search_knowledge_base(args: dict) -> str:
    query = args.get("query", "")
    max_results = args.get("max_results", 5)
    try:
        resp = await _client.embeddings.create(model="text-embedding-3-small", input=query)
        embedding = resp.data[0].embedding

        conn = await asyncpg.connect(DATABASE_URL)
        rows = await conn.fetch(
            """SELECT title, content, category,
                      1 - (embedding <=> $1::vector) AS similarity
               FROM knowledge_base
               ORDER BY embedding <=> $1::vector LIMIT $2""",
            str(embedding), max_results,
        )
        await conn.close()

        if not rows:
            return "No relevant knowledge base entries found."
        return "\n\n".join(f"[{r['similarity']:.2f}] {r['title']}: {r['content']}" for r in rows)
    except Exception as e:
        return f"KB search error: {e}"
