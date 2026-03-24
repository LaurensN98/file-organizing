import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.ml_engine import (
    get_embeddings, 
    get_cluster_label, 
    generate_dataset_summary,
    clustering_pipeline
)

@pytest.mark.asyncio
async def test_get_embeddings(mocker):
    # Mock the AsyncOpenAI client in the ml_engine module
    mock_embeddings = MagicMock()
    mock_embeddings.data = [MagicMock(embedding=[0.1] * 1536) for _ in range(3)]
    
    # We patch the 'client' object that was imported/created in ml_engine.py
    with patch("app.services.ml_engine.client.embeddings.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_embeddings
        
        texts = ["text1", "text2", "text3"]
        embeddings = await get_embeddings(texts)
        
        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape == (3, 1536)
        assert mock_create.called

@pytest.mark.asyncio
async def test_get_cluster_label():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Financial Reports"
    
    with patch("app.services.ml_engine.client.chat.completions.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        
        label = await get_cluster_label([{"filename": "test.pdf", "text": "Some financial text content about invoices and money."}])
        
        assert label == "Financial Reports"
        assert mock_create.called

@pytest.mark.asyncio
async def test_generate_dataset_summary():
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "A collection of financial documents."
    
    with patch("app.services.ml_engine.client.chat.completions.create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        
        cluster_data = [{"category": "Finance", "text": "invoice text"}]
        summary = await generate_dataset_summary(cluster_data)
        
        assert summary == "A collection of financial documents."
        assert mock_create.called

@pytest.mark.asyncio
async def test_clustering_pipeline_tiny_dataset():
    # Mock both embedded types to avoid real network attempts
    with patch("app.services.ml_engine.get_embeddings", new_callable=AsyncMock) as mock_dense, \
         patch("app.services.ml_engine.generate_sparse_embeddings", new_callable=AsyncMock) as mock_sparse:
        
        mock_dense.return_value = np.array([[0.1] * 1536])
        mock_sparse.return_value = [{"1": 0.5}]
        
        # Test with very few samples (should return dummy folders)
        processed_data = [{"filename": "doc1.txt", "text": "single document", "metadata": {}}]
        
        organized_data, summary = await clustering_pipeline(processed_data)
        
        assert organized_data[0]["folder"] == "Miscellaneous"
        assert summary == "An organized collection of documents."


@pytest.mark.asyncio
async def test_clustering_pipeline_full_flow():
    # Mock all external calls to test the logic flow
    texts = ["apple " * 10, "banana " * 10, "cherry " * 10, "date " * 10, "elderberry " * 10]
    processed_data = [{"filename": f"doc_{i}.txt", "text": t, "metadata": {"file_size_kb": 1}} for i, t in enumerate(texts)]
    
    # 1. Mock dense embeddings
    with patch("app.services.ml_engine.get_embeddings", new_callable=AsyncMock) as mock_emb, \
         patch("app.services.ml_engine.generate_sparse_embeddings", new_callable=AsyncMock) as mock_sparse:
        
        mock_emb.return_value = np.random.rand(len(texts), 1536)
        mock_sparse.return_value = [{} for _ in texts]
        
        # 2. Mock labeler
        with patch("app.services.ml_engine.get_cluster_label", new_callable=AsyncMock) as mock_label:
            mock_label.return_value = "Mock Cluster"
            
            # 3. Mock summary
            with patch("app.services.ml_engine.generate_dataset_summary", new_callable=AsyncMock) as mock_sum:
                mock_sum.return_value = "Mock Summary"
                
                organized_data, summary = await clustering_pipeline(processed_data)

                
                assert len(organized_data) == len(texts)
                assert summary == "Mock Summary"
                # Check that folders were assigned
                for d in organized_data:
                    assert "folder" in d
                    assert "x" in d
                    assert "y" in d
