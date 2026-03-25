import httpx
from app.core.config import settings

class DeepInfraClient:
    """Wrapper for DeepInfra API that handles specialized inference."""
    def __init__(self, api_key: str):
        self.api_key = api_key
        # Shared client for connection pooling and faster TLS handshakes
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),
            headers={
                "Authorization": f"bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )

    async def rerank(self, model: str, queries: list[str], documents: list[str]) -> dict:
        """Call DeepInfra's direct inference endpoint for reranking models."""
        url = f"https://api.deepinfra.com/v1/inference/{model}"
        payload = {
            "queries": queries,
            "documents": documents
        }
        
        # Reusing the shared client
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    async def aclose(self):
        """Close the internal httpx client properly."""
        await self.client.aclose()

# Export an instance
deepinfra_client = DeepInfraClient(settings.DEEPINFRA_API_KEY)
