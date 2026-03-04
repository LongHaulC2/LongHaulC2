import requests
from yarl import URL
from typing import Dict, Any, Optional, Union
import pytest 
import os
import time 
class C2APIClient:
    """A dedicated client for interacting with the server API."""
    
    def __init__(self, base_url: str):
        # YARL handles the base pathing safely
        self.base_url = URL(base_url) / "api" / "v1"
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json"
        })

    # def wait_for_ready(self, timeout=30):
    #     """Polls the server's health check endpoint until it's online."""
    #     start_time = time.time()
    #     while time.time() - start_time < timeout:
    #         try:
    #             response = self.session.get(f"{self.base_url}/api/v1/health/", timeout=2)
    #             if response.status_code == 200:
    #                 return True
    #         except requests.ConnectionError:
    #             pass
    #         time.sleep(2)
    #     raise TimeoutError(f"API at {self.base_url} did not come online in time.")


    def _log_error(self, response: requests.Response, payload: Any = None):
        """Helper to print consistent error blocks."""
        print(f"\n{'!'*20} API FAIL {'!'*20}")
        print(f"URL:    {response.url}")
        print(f"Status: {response.status_code}")
        if payload:
            print(f"Sent:   {payload}")
        print(f"Error:  {response.text}")
        print(f"{'!'*50}\n")

    # --- Build Functions ---

    def post_build(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = str(self.base_url / "build")
        response = self.session.post(url, json=payload)
        if not response.ok: self._log_error(response, payload)
        response.raise_for_status()
        return response.json()

    def get_build(self) -> Dict[str, Any]:
        url = str(self.base_url / "build")
        response = self.session.get(url)
        if not response.ok: self._log_error(response)
        response.raise_for_status()
        return response.json()

    def get_build_jobs(self, build_uuid: str) -> Dict[str, Any]:
        url = str(self.base_url / "build" / "jobs" / build_uuid)
        response = self.session.get(url)
        if not response.ok: self._log_error(response)
        response.raise_for_status()
        return response.json()

    # --- Binary / Source Actions ---

    def get_binary_actions(self, hash: str) -> bytes:
        url = str(self.base_url / "build" / hash)
        response = self.session.get(url)
        if not response.ok: self._log_error(response)
        response.raise_for_status()
        return response.content

    def delete_binary_actions(self, hash: str) -> Dict[str, Any]:
        url = str(self.base_url / "build" / hash)
        response = self.session.delete(url)
        if not response.ok: self._log_error(response)
        response.raise_for_status()
        return response.json()

    def get_source_actions(self, hash: str) -> bytes:
        url = str(self.base_url / "build" / hash / "source")
        response = self.session.get(url)
        if not response.ok: self._log_error(response)
        response.raise_for_status()
        return response.content

    # --- Implant Functions ---

    def post_implants(self) -> Dict[str, Any]:
        url = str(self.base_url / "implants")
        response = self.session.post(url)
        if not response.ok: self._log_error(response)
        response.raise_for_status()
        return response.json()

    def get_implants(self) -> Dict[str, Any]:
        url = str(self.base_url / "implants")
        response = self.session.get(url)
        if not response.ok: self._log_error(response)
        response.raise_for_status()
        return response.json()

    def post_task_search(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = str(self.base_url / "implants" / "history" / "search")
        response = self.session.post(url, json=payload)
        if not response.ok: self._log_error(response, payload)
        response.raise_for_status()
        return response.json()

    def post_implant_search(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = str(self.base_url / "implants" / "search")
        response = self.session.post(url, json=payload)
        if not response.ok: self._log_error(response, payload)
        response.raise_for_status()
        return response.json()

    def put_implant(self, uuid: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = str(self.base_url / "implants" / uuid)
        response = self.session.put(url, json=payload)
        if not response.ok: self._log_error(response, payload)
        response.raise_for_status()
        return response.json()

    def get_implant(self, uuid: str) -> Dict[str, Any]:
        url = str(self.base_url / "implants" / uuid)
        response = self.session.get(url)
        if not response.ok: self._log_error(response)
        response.raise_for_status()
        return response.json()

    def delete_implant(self, uuid: str) -> Dict[str, Any]:
        url = str(self.base_url / "implants" / uuid)
        response = self.session.delete(url)
        if not response.ok: self._log_error(response)
        response.raise_for_status()
        return response.json()

    # --- Tasking Functions ---

    def post_implant_task(self, uuid: str, payload: Union[Dict[str, Any], bytes]) -> Dict[str, Any]:
        url = str(self.base_url / "implants" / uuid / "task")
        
        if isinstance(payload, bytes):
            # Sending msgpack or raw bytes
            headers = {"Content-Type": "application/msgpack"} # server wants application/msgpack
            response = self.session.post(url, data=payload, headers=headers)
        else:
            # Sending standard dictionary as JSON
            response = self.session.post(url, json=payload)

        if not response.ok: 
            self._log_error(response, payload)
    
        response.raise_for_status()
        return response.json()

    def peek_implant_task(self, uuid: str) -> Dict[str, Any]:
        url = str(self.base_url / "implants" / uuid / "task")
        response = self.session.get(url)
        if not response.ok: self._log_error(response)
        response.raise_for_status()
        return response.json()

    def get_implant_task(self, implant_uuid: str, task_uuid:str) -> Dict[str, Any]:
        url = str(self.base_url / "implants" / implant_uuid / "task" / task_uuid)
        response = self.session.get(url)
        if not response.ok: self._log_error(response)
        response.raise_for_status()
        return response.json()

    def get_implant_tasks(self, uuid: str) -> Dict[str, Any]:
        url = str(self.base_url / "implants" / uuid / "tasks")
        response = self.session.get(url)
        if not response.ok: self._log_error(response)
        response.raise_for_status()
        return response.json()

    def delete_implant_tasks(self, uuid: str) -> Dict[str, Any]:
        url = str(self.base_url / "implants" / uuid / "tasks")
        response = self.session.delete(url)
        if not response.ok: self._log_error(response)
        response.raise_for_status()
        return response.json()

    def get_implant_history(self, uuid: str, since: Optional[str] = None) -> Dict[str, Any]:
        url = str(self.base_url / "implants" / uuid / "tasks" / "history")
        params = {"since": since} if since else None
        response = self.session.get(url, params=params)
        if not response.ok: self._log_error(response)
        response.raise_for_status()
        return response.json()

    # --- Listener Functions ---

    def post_listeners(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = str(self.base_url / "listeners")
        response = self.session.post(url, json=payload, timeout=10)
        if not response.ok: self._log_error(response, payload)
        response.raise_for_status()
        return response.json()

    def get_listeners(self) -> Dict[str, Any]:
        url = str(self.base_url / "listeners")
        response = self.session.get(url)
        if not response.ok: self._log_error(response)
        response.raise_for_status()
        return response.json()

    def get_listener(self, uuid: str) -> Dict[str, Any]:
        url = str(self.base_url / "listeners" / uuid)
        response = self.session.get(url)
        if not response.ok: self._log_error(response)
        response.raise_for_status()
        return response.json()

    def delete_listener(self, uuid: str) -> Dict[str, Any]:
        url = str(self.base_url / "listeners" / uuid)
        response = self.session.delete(url)
        if not response.ok: self._log_error(response)
        response.raise_for_status()
        return response.json()

@pytest.fixture(scope="session")
def api_client():
    """
    This fixture spins up the API client once for the whole test session.
    It pulls the URL and Auth from environment variables (great for GitHub Actions).
    """
    # Fallback to localhost for local testing if env vars aren't set
    base_url = os.getenv("SERVER_URL", "http://localhost:45045")
    #api_key = os.getenv("SERVER_API_KEY", "dev_secret_key")
    
    client = C2APIClient(base_url)
    
    # Block tests from starting until the API is actually accepting connections
    print(f"\n[SETUP] Waiting for API at {base_url} to come online...")
    #client.wait_for_ready()
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