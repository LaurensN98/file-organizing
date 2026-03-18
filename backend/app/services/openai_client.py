from openai import AsyncOpenAI
from app.core.config import settings

# Initialize client for OpenRouter 
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY,
    timeout=60.0,
    max_retries=3,
    default_headers={
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "Neatly AI Organizer",
    }
)
