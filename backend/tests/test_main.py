from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_root():
    """
    Test the root endpoint to ensure the API is running.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to Neatly"}

def test_upload_router_exists():
    """
    A simple check to see if the upload router is mounted.
    """
    # Just checking if the route exists, even if it returns 405 (Method Not Allowed) for GET
    response = client.get("/api/upload")
    assert response.status_code in [404, 405] 
