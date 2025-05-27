import json
from unittest.mock import patch, MagicMock
import pytest # Import pytest for monkeypatch

from app import User # Assuming User is defined in app.py or accessible

def test_home_page(test_client):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/' page is requested (GET)
    THEN check that the response is valid
    """
    response = test_client.get('/')
    assert response.status_code == 200
    assert b"Job Market Insights" in response.data # Or whatever your home page title is

def test_successful_registration(test_client):
    """
    GIVEN a Flask application
    WHEN the '/register' page is posted to with valid data
    THEN check that the user is created and redirected
    """
    response = test_client.post('/register', data={
        'email': 'test@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Congratulations, you are now a registered user!" in response.data
    # Ensure user is actually in the database
    with test_client.application.app_context(): # Need app context for DB query
        user = User.query.filter_by(email='test@example.com').first()
        assert user is not None
        assert user.email == 'test@example.com'

# KSBs: K14 (Mocking Strategies)
@patch('app.requests.get') # Patch requests.get in the 'app' module where it's used
def test_fetch_market_insights_mocked(mock_get, test_client, monkeypatch): # Added monkeypatch
    """
    GIVEN a mocked Adzuna API and necessary credentials
    WHEN fetch_market_insights is called
    THEN check that the mock API was called correctly and data is processed
    """
    # Setup mock response for Adzuna search
    mock_adzuna_search_response = MagicMock()
    mock_adzuna_search_response.status_code = 200
    mock_adzuna_search_response.json.return_value = {
        "count": 1,
        "results": [
            {
                "title": "Software Engineer",
                "company": {"display_name": "Test Inc"},
                "location": {"display_name": "Test City"},
                "description": "A test job.",
                "redirect_url": "https://www.adzuna.com/details/12345", # Example Adzuna ID
                "created": "2023-10-27T10:00:00Z"
            }
        ]
    }

    # Setup mock response for Adzuna histogram (simulating it's not found or fails)
    mock_adzuna_histogram_response = MagicMock()
    mock_adzuna_histogram_response.status_code = 404 # Or 200 with empty data
    mock_adzuna_histogram_response.json.return_value = {"histogram": {}}


    # The first call to requests.get will be for Adzuna search,
    # The second will be for the salary histogram.
    mock_get.side_effect = [mock_adzuna_search_response, mock_adzuna_histogram_response]

    # Set necessary environment variables to prevent flash() due to missing creds
    monkeypatch.setenv('ADZUNA_APP_ID', 'test_app_id')
    monkeypatch.setenv('ADZUNA_APP_KEY', 'test_app_key')
    # No need to set AZURE_AI_ENDPOINT/KEY as generate_summary=False

    # We need to be in an app context to use the functions
    # and for db operations if any were directly in fetch_market_insights
    with test_client.application.app_context():
        from app import fetch_market_insights # Import locally to use patched version
        insights = fetch_market_insights(
            what="devops", where="london", country="gb", generate_summary=False
        )

    assert insights is not None
    assert insights['total_matching_jobs'] == 1
    assert len(insights['job_listings']) == 1
    assert insights['job_listings'][0]['title'] == 'Software Engineer'
    assert insights['job_listings'][0]['adzuna_job_id'] == '12345' # Check extracted ID

    # Check that our mock was called
    # First call (Adzuna search)
    mock_get.assert_any_call(
        'https://api.adzuna.com/v1/api/jobs/gb/search/1', # Make sure this matches your app.py
        params={
            'app_id': 'test_app_id', # Should match monkeypatched value
            'app_key': 'test_app_key', # Should match monkeypatched value
            'what': 'devops',
            'where': 'london',
            'results_per_page': 20, # As defined in app.py
            'content-type': 'application/json'
        },
        timeout=20 # As defined in app.py
    )
    # Second call (Adzuna histogram)
    mock_get.assert_any_call(
        'https://api.adzuna.com/v1/api/jobs/gb/histogram', # Make sure this matches your app.py
        params={
            'app_id': 'test_app_id',
            'app_key': 'test_app_key',
            'location0': 'london', # Check param name in get_salary_histogram
            'what': 'devops',
            'content-type': 'application/json'
        },
        timeout=15 # As defined in get_salary_histogram
    )
