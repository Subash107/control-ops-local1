from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def login_as_admin():
    response = client.post('/api/auth/login', json={'username': 'admin', 'password': 'admin123'})
    response.raise_for_status()
    token = response.json()['access_token']
    return {'Authorization': f'Bearer {token}'}
