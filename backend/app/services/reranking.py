from app.services.deepinfra_client import deepinfra_client

# This correctly calls the DeepInfra inference endpoint for reranking
# Example based on DeepInfra documentation
async def get_reranked_scores(queries: list[str], documents: list[str]):
    """
    Reranks a list of documents against a set of queries.
    Returns: list[float] (scores for each doc input pair)
    """
    response = await deepinfra_client.rerank(
        model="nvidia/llama-nemotron-rerank-vl-1b-v2",
        queries=queries,
        documents=documents
    )
    return response.get("scores")