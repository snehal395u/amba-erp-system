from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_orders_requires_auth():
    response = client.post("/api/v1/orders", json={"customer_id": 1, "product_id": 2, "quantity": 3})
    assert response.status_code == 401
