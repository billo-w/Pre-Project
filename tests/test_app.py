from app import app  # Import directly from app.py

def test_index():
    client = app.test_client()
    response = client.get('/')
    assert response.status_code == 200
