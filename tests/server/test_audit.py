import csv
import io
import os

import requests as raw_requests


class TestAuditPagination:
    """Tests for the paginated GET /api/v1/audit/ endpoint."""

    def test_default_pagination(self, api_client):
        """Default call returns paginated structure with total_count."""
        resp = api_client.get_audit()
        assert resp["status"] == "200"
        data = resp["data"]
        assert "entries" in data
        assert "total_count" in data
        assert "limit" in data
        assert "offset" in data
        assert isinstance(data["entries"], list)
        assert isinstance(data["total_count"], int)
        assert data["limit"] == 50
        assert data["offset"] == 0

    def test_custom_limit(self, api_client):
        """Limit parameter controls page size."""
        resp = api_client.get_audit(limit=5)
        data = resp["data"]
        assert data["limit"] == 5
        assert len(data["entries"]) <= 5

    def test_offset(self, api_client):
        """Offset skips entries — page 2 returns different entries than page 1."""
        resp_page1 = api_client.get_audit(limit=5, offset=0)
        resp_page2 = api_client.get_audit(limit=5, offset=5)

        entries1 = resp_page1["data"]["entries"]
        entries2 = resp_page2["data"]["entries"]

        if resp_page1["data"]["total_count"] > 5:
            ids1 = {e["id"] for e in entries1}
            ids2 = {e["id"] for e in entries2}
            assert ids1.isdisjoint(ids2), "Page 1 and page 2 should have no overlapping entries"

    def test_total_count_consistent_across_pages(self, api_client):
        """total_count stays the same regardless of offset."""
        resp1 = api_client.get_audit(limit=5, offset=0)
        resp2 = api_client.get_audit(limit=5, offset=5)
        assert resp1["data"]["total_count"] == resp2["data"]["total_count"]

    def test_limit_capped_at_1000(self, api_client):
        """Requesting limit > 1000 gets clamped to 1000."""
        resp = api_client.get_audit(limit=5000)
        assert resp["data"]["limit"] == 1000

    def test_limit_minimum_is_1(self, api_client):
        """Requesting limit=0 gets clamped to 1."""
        resp = api_client.get_audit(limit=0)
        assert resp["data"]["limit"] == 1

    def test_negative_offset_clamped(self, api_client):
        """Negative offset gets clamped to 0."""
        resp = api_client.get_audit(offset=-10)
        assert resp["data"]["offset"] == 0

    def test_filter_by_action(self, api_client):
        """Filtering by action only returns matching entries."""
        resp = api_client.get_audit(action="login_success")
        for entry in resp["data"]["entries"]:
            assert entry["action"] == "login_success"

    def test_filter_by_actor(self, api_client):
        """Filtering by actor only returns matching entries."""
        resp = api_client.get_audit(actor="longhaul")
        for entry in resp["data"]["entries"]:
            assert entry["actor"] == "longhaul"

    def test_entries_ordered_newest_first(self, api_client):
        """Entries come back in descending timestamp order."""
        resp = api_client.get_audit(limit=50)
        entries = resp["data"]["entries"]
        if len(entries) > 1:
            timestamps = [e["timestamp"] for e in entries]
            assert timestamps == sorted(timestamps, reverse=True)


class TestAuditExport:
    """Tests for the GET /api/v1/audit/export CSV endpoint."""

    def test_export_returns_csv(self, api_client):
        """Export endpoint returns valid CSV with a header row."""
        resp = api_client.get_audit_export()
        assert resp.headers["Content-Type"].startswith("text/csv")
        assert "attachment" in resp.headers.get("Content-Disposition", "")

        reader = csv.reader(io.StringIO(resp.text))
        header = next(reader)
        assert header == ["timestamp", "actor", "action", "target_type", "target_uuid", "detail"]

    def test_export_with_filter(self, api_client):
        """Export with action filter only includes matching rows."""
        resp = api_client.get_audit_export(action="login_success")
        reader = csv.reader(io.StringIO(resp.text))
        next(reader)  # skip header
        for row in reader:
            assert row[2] == "login_success"

    def test_export_unauthed(self):
        """Export without auth token returns 401."""
        base_url = os.getenv("SERVER_URL", "http://localhost:45045")
        resp = raw_requests.get(f"{base_url}/api/v1/audit/export")
        assert resp.status_code == 401


class TestAuditUnauthed:
    """Auth enforcement on audit endpoints."""

    def test_list_unauthed(self):
        """GET /audit/ without auth returns 401."""
        base_url = os.getenv("SERVER_URL", "http://localhost:45045")
        resp = raw_requests.get(f"{base_url}/api/v1/audit/")
        assert resp.status_code == 401
