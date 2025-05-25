import os
import sys

# Add parent directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app

def test_home_route():
    app = create_app({'TESTING': True})
    client = app.test_client()
    response = client.get('/')
    assert response.status_code == 200
