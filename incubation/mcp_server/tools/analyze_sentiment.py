"""MCP tool: Analyze sentiment using OpenAI gpt-4o-mini."""
import os
from openai import AsyncOpenAI

_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

async def analyze_sentiment(args: dict) -> str:
    message = args.get("message", "")
    try:
        response = await _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Respond with ONLY a number between 0.0 and 1.0. 0.0=extremely negative, 0.5=neutral, 1.0=extremely positive."},
                {"role": "user", "content": message},
            ],
            temperature=0,
            max_tokens=10,
        )
        score = float(response.choices[0].message.content.strip())
        return str(max(0.0, min(1.0, score)))
    except Exception as e:
        return f"0.5"
