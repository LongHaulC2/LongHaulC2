import pytest
import requests
import os
import time
from typing import Optional, Dict, Any, Union


class C2APIClient:
    """A dedicated client for interacting with the server API."""
    
    def __init__(self, base_url):
        self.base_url = base_url
        # Use a session to persist headers and keep connections alive
        self.session = requests.Session()
        self.session.headers.update({
            #"Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })

    def wait_for_ready(self, timeout=30):
        """Polls the server's health check endpoint until it's online."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.session.get(f"{self.base_url}/api/health", timeout=2)
                if response.status_code == 200:
                    return True
            except requests.ConnectionError:
                pass
            time.sleep(2)
        raise TimeoutError(f"API at {self.base_url} did not come online in time.")

    # api funcs
    def post_build(self, uuid: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a build task to build a payload"""
        response = self.session.post(f"{self.base_url}/build/{uuid}", json=payload)
        response.raise_for_status()
        return response.json()

    def get_build(self) -> Dict[str, Any]:
        """Get a list of all payloads in the Database"""
        response = self.session.get(f"{self.base_url}/build/")
        response.raise_for_status()
        return response.json()

    def get_build_jobs(self, build_uuid: str) -> Dict[str, Any]:
        """Get the status of a build job"""
        response = self.session.get(f"{self.base_url}/build/jobs/{build_uuid}")
        response.raise_for_status()
        return response.json()

    def get_binary_actions(self, hash: str) -> bytes:
        """Download a specific payload artifact, based on the provided hash"""
        response = self.session.get(f"{self.base_url}/build/{hash}")
        response.raise_for_status()
        return response.content

    def delete_binary_actions(self, hash: str) -> Dict[str, Any]:
        """Delete a specific payload artifact, based on the provided hash"""
        response = self.session.delete(f"{self.base_url}/build/{hash}")
        response.raise_for_status()
        return response.json()

    def get_source_actions(self, hash: str) -> bytes:
        """Download the source of an implant"""
        response = self.session.get(f"{self.base_url}/build/{hash}/source")
        response.raise_for_status()
        return response.content

    def post_implants(self) -> Dict[str, Any]:
        """Create a new implant entry"""
        response = self.session.post(f"{self.base_url}/implants/")
        response.raise_for_status()
        return response.json()

    def get_implants(self) -> Dict[str, Any]:
        """Gets all implants"""
        response = self.session.get(f"{self.base_url}/implants/")
        response.raise_for_status()
        return response.json()

    def post_task_search(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Search for an task with fields that match the supplied term"""
        response = self.session.post(f"{self.base_url}/implants/history/search", json=payload)
        response.raise_for_status()
        return response.json()

    def post_implant_search(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Search for an implant with fields that match the supplied term"""
        response = self.session.post(f"{self.base_url}/implants/search", json=payload)
        response.raise_for_status()
        return response.json()

    def put_implant(self, uuid: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Update a single implant by its unique ID"""
        response = self.session.put(f"{self.base_url}/implants/{uuid}", json=payload)
        response.raise_for_status()
        return response.json()

    def get_implant(self, uuid: str) -> Dict[str, Any]:
        """Gets one implant based on user supplied ID"""
        response = self.session.get(f"{self.base_url}/implants/{uuid}")
        response.raise_for_status()
        return response.json()

    def delete_implant(self, uuid: str) -> Dict[str, Any]:
        """Deletes one implant based on user supplied ID"""
        response = self.session.delete(f"{self.base_url}/implants/{uuid}")
        response.raise_for_status()
        return response.json()

    def post_implant_task(self, uuid: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Add a task to a single implant by its unique ID"""
        response = self.session.post(f"{self.base_url}/implants/{uuid}/task", json=payload)
        response.raise_for_status()
        return response.json()

    def get_implant_task(self, uuid: str) -> Dict[str, Any]:
        """Gets next task of implant"""
        response = self.session.get(f"{self.base_url}/implants/{uuid}/task")
        response.raise_for_status()
        return response.json()

    def get_implant_tasks(self, uuid: str) -> Dict[str, Any]:
        """Peek all currently queued tasks of implant"""
        response = self.session.get(f"{self.base_url}/implants/{uuid}/tasks")
        response.raise_for_status()
        return response.json()

    def delete_implant_tasks(self, uuid: str) -> Dict[str, Any]:
        """Delete all the currently queued tasks of an agent"""
        response = self.session.delete(f"{self.base_url}/implants/{uuid}/tasks")
        response.raise_for_status()
        return response.json()

    def get_implant_history(self, uuid: str, since: Optional[str] = None) -> Dict[str, Any]:
        """Gets ALL history of an implant from the DB"""
        params = {"since": since} if since else None
        response = self.session.get(f"{self.base_url}/implants/{uuid}/tasks/history", params=params)
        response.raise_for_status()
        return response.json()

    def post_listeners(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Spawn a new listener"""
        response = self.session.post(f"{self.base_url}/listeners/", json=payload)
        response.raise_for_status()
        return response.json()

    def get_listeners(self) -> Dict[str, Any]:
        """Gets all listeners"""
        response = self.session.get(f"{self.base_url}/listeners/")
        response.raise_for_status()
        return response.json()

    def get_listener(self, uuid: str) -> Dict[str, Any]:
        """Gets one listener based on user supplied ID"""
        response = self.session.get(f"{self.base_url}/listeners/{uuid}")
        response.raise_for_status()
        return response.json()

    def delete_listener(self, uuid: str) -> Dict[str, Any]:
        """Deletes/Stops one listener based on user supplied ID"""
        response = self.session.delete(f"{self.base_url}/listeners/{uuid}")
        response.raise_for_status()
        return response.json()


@pytest.fixture(scope="session")
def api_client():
    """
    This fixture spins up the API client once for the whole test session.
    It pulls the URL and Auth from environment variables (great for GitHub Actions).
    """
    # Fallback to localhost for local testing if env vars aren't set
    base_url = os.getenv("SERVER_URL", "http://localhost:8080")
    #api_key = os.getenv("SERVER_API_KEY", "dev_secret_key")
    
    client = C2APIClient(base_url)
    
    # Block tests from starting until the API is actually accepting connections
    print(f"\n[SETUP] Waiting for API at {base_url} to come online...")
    client.wait_for_ready()
    print("[SETUP] API is online. Starting tests.")
    
    yield client
    
    # Teardown phase
    print("\n[TEARDOWN] Closing API session.")
    client.session.close()

# ex use in other files
'''
import time

def test_agent_registration(api_client):
    # The api_client fixture is ready to go
    response = api_client.register_agent("test-win-01", "Windows 11")
    
    assert "agent_id" in response
    assert response["status"] == "registered"
'''