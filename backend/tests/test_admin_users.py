import uuid

from .helpers import client, login_as_admin


def test_admin_user_crud():
    headers = login_as_admin()
    username = f"test-admin-{uuid.uuid4().hex[:6]}"
    user_id = None
    try:
        payload = {'username': username, 'password': 'Pass1234!', 'role': 'user'}
        create_resp = client.post('/api/admin/users', json=payload, headers=headers)
        create_resp.raise_for_status()
        user_id = create_resp.json()['id']

        list_resp = client.get('/api/admin/users', headers=headers)
        list_resp.raise_for_status()
        users = list_resp.json()
        assert any(u['username'] == username for u in users)

        update_resp = client.put(
            f'/api/admin/users/{user_id}',
            json={'password': 'NewPass123!', 'role': 'admin'},
            headers=headers,
        )
        update_resp.raise_for_status()
        assert update_resp.json()['role'] == 'admin'
    finally:
        if user_id:
            client.delete(f'/api/admin/users/{user_id}', headers=headers)
