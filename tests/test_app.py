import json
from unittest.mock import patch, MagicMock

from app import User

def test_home_page(test_client):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/' page is requested (GET)
    THEN check that the response is valid
    """
    response = test_client.get('/')
    assert response.status_code == 200
    assert b"Job Market Insights" in response.data

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
    user = User.query.filter_by(email='test@example.com').first()
    assert user is not None

# KSBs: K14 (Mocking Strategies)
@patch('app.requests.get')
def test_fetch_market_insights_mocked(mock_get, test_client):
    """
    GIVEN a mocked Adzuna API
    WHEN fetch_market_insights is called
    THEN check that the mock API was called correctly and data is processed
    """
    # Setup mock response for Adzuna search
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "count": 1,
        "results": [
            {
                "title": "Software Engineer",
                "company": {"display_name": "Test Inc"},
                "location": {"display_name": "Test City"},
                "description": "A test job.",
                "redirect_url": "https://www.adzuna.com/details/12345",
                "created": "2023-10-27T10:00:00Z"
            }
        ]
    }
    # The first call is to Adzuna search, the second is to the histogram
    mock_get.side_effect = [mock_response, MagicMock(status_code=404)]

    # We need to be in an app context to use the functions
    with test_client.application.app_context():
        from app import fetch_market_insights
        insights = fetch_market_insights(
            what="devops", where="london", country="gb", generate_summary=False
        )

    assert insights is not None
    assert insights['total_matching_jobs'] == 1
    assert insights['job_listings'][0]['title'] == 'Software Engineer'
    # Check that our mock was called with the correct parameters
    mock_get.assert_any_call(
        'https://api.adzuna.com/v1/api/jobs/gb/search/1',
        params={
            'app_id': None, 'app_key': None, 'what': 'devops', 'where': 'london',
            'results_per_page': 20, 'content-type': 'application/json'
        },
        timeout=20
    )