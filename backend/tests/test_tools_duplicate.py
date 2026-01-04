from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def login_as_admin():
    res = client.post('/api/auth/login', json={'username': 'admin', 'password': 'admin123'})
    assert res.status_code == 200
    tok = res.json()['access_token']
    return {'Authorization': f'Bearer {tok}'}


def test_create_tool_and_duplicate():
    headers = login_as_admin()
    payload = {'name': 'dup-tool', 'description': 'x', 'url': 'https://example.local', 'category': 'general', 'tags': ['x']}

    # First create should succeed
    res = client.post('/api/tools', json=payload, headers=headers)
    assert res.status_code == 200
    created = res.json()
    assert created['name'] == payload['name']

    # Second create with same name should return 409
    res2 = client.post('/api/tools', json=payload, headers=headers)
    assert res2.status_code == 409
    data = res2.json()
    assert data.get('field') == 'name' or isinstance(data.get('detail'), dict)
