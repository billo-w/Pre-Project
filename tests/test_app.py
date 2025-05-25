import os
import pytest
from app import create_app

def test_home_route():
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///:memory:'),
        'SQLALCHEMY_TRACK_MODIFICATIONS': False
    })
    client = app.test_client()
    response = client.get('/')
    assert response.status_code == 200
