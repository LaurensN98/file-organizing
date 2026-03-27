import httpx


# Shared client for connection pooling locally
local_inference_client = httpx.AsyncClient(
    timeout=httpx.Timeout(120.0),
    limits=httpx.Limits(max_keepalive_connections=20, max_connections=50)
)
