"""Sentiment analysis tool — calls Groq (free, OpenAI-compatible)."""
from pydantic import BaseModel, Field
from agents import function_tool
from production.agent.llm_client import get_chat_client, LLM_MODEL

class SentimentInput(BaseModel):
    message: str = Field(..., description="Message text to analyze")

class SentimentOutput(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0, description="Sentiment 0.0-1.0")
    label: str = Field(..., description="positive/neutral/negative")


@function_tool
async def analyze_sentiment(message: str) -> float:
    """Analyze sentiment of a message. Returns float 0.0-1.0."""
    try:
        client = get_chat_client()
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "You are a sentiment analyzer. Respond with ONLY a number between 0.0 and 1.0. 0.0 = extremely negative, 0.5 = neutral, 1.0 = extremely positive."},
                {"role": "user", "content": message},
            ],
            temperature=0,
            max_tokens=10,
        )
        score = float(response.choices[0].message.content.strip())
        return max(0.0, min(1.0, score))
    except Exception:
        return 0.5  # Default neutral on error
