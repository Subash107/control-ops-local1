import uuid

from .helpers import client, login_as_admin


def _create_tool(headers, name, category, tag):
    payload = {
        'name': name,
        'description': 'filter test tool',
        'url': 'https://example.org',
        'category': category,
        'tags': [tag],
    }
    response = client.post('/api/tools', json=payload, headers=headers)
    response.raise_for_status()
    return response.json()


def _delete_tool(tool_id, headers):
    client.delete(f'/api/tools/{tool_id}', headers=headers)


def test_tools_filtered_by_category_tag_and_sort():
    headers = login_as_admin()
    prefix = f"filter-tool-{uuid.uuid4().hex[:6]}"
    category = f"filter-category-{uuid.uuid4().hex[:4]}"
    tag = f"tag-{uuid.uuid4().hex[:4]}"
    created = []

    try:
        for idx in range(2):
            name = f"{prefix}-{idx}"
            created.append(_create_tool(headers, name, category, tag))

        params = {
            'category': category,
            'tag': tag,
            'q': prefix,
            'limit': 2,
            'sort': 'name:asc',
        }
        resp = client.get('/api/tools', params=params, headers=headers)
        resp.raise_for_status()
        items = [item for item in resp.json().get('items', []) if item['name'].startswith(prefix)]
        assert len(items) >= 2
        assert {item['name'] for item in items} >= {tool['name'] for tool in created}

        offset_resp = client.get('/api/tools', params={**params, 'offset': 1}, headers=headers)
        offset_resp.raise_for_status()
        assert len(offset_resp.json().get('items', [])) >= 1
    finally:
        for tool in created:
            _delete_tool(tool['id'], headers)
