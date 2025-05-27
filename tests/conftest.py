import pytest
from app import create_app, db

@pytest.fixture(scope='module')
def test_app():
    """Create and configure a new app instance for each test module."""
    app = create_app('testing')
    return app

@pytest.fixture(scope='function')
def test_client(test_app):
    """Create a test client for the app."""
    with test_app.test_client() as testing_client:
        with test_app.app_context():
            db.create_all() # Create all tables
            yield testing_client # this is where the testing happens
            db.session.remove()
            db.drop_all() # Drop all tables after test