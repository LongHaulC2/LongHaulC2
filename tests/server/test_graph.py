import os

import requests as raw_requests


def test_get_graph(api_client):
    """GET /graph/ returns 200 with graph data structure."""
    resp = api_client.get_graph()
    assert resp["status"] == "200"
    assert "categories" in resp["data"]
    assert "nodes" in resp["data"]
    assert "links" in resp["data"]


def test_graph_search(api_client):
    """POST /graph/search with a wildcard returns 200."""
    resp = api_client.post_graph_search({"search_term": "*"})
    assert resp["status"] == "200"
    assert "data" in resp


def test_list_implant_nodes(api_client):
    """GET /graph/node/Implant/ returns 200 with a list."""
    base_url = os.getenv("SERVER_URL", "http://localhost:45045")
    resp = api_client.session.get(f"{base_url}/api/v1/graph/node/Implant/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "200"
    assert isinstance(data["data"], list)


def test_invalid_node_type(api_client):
    """GET /graph/node/FakeNode/ returns 400 for invalid node type."""
    base_url = os.getenv("SERVER_URL", "http://localhost:45045")
    resp = api_client.session.get(f"{base_url}/api/v1/graph/node/FakeNode/")
    assert resp.status_code == 400


def test_graph_unauthed():
    """GET /graph/ without a token returns 401."""
    base_url = os.getenv("SERVER_URL", "http://localhost:45045")
    resp = raw_requests.get(f"{base_url}/api/v1/graph/")
    assert resp.status_code == 401
