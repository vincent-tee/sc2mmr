"""
Tests for the group-password access layer (app/auth.py).

Auth is disabled by default; these tests flip settings attributes on the
module-level singleton and restore them afterwards, so the rest of the suite
keeps seeing the defaults.
"""
import pytest
from fastapi.testclient import TestClient

from app.auth import require_admin
from app.config import settings
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_on():
    """Enable auth with a known password/secret; restore defaults after."""
    saved = (
        settings.auth_enabled,
        settings.group_password,
        settings.auth_secret,
        settings.auth_cookie_secure,
        settings.auth_cookie_samesite,
    )
    settings.auth_enabled = True
    settings.group_password = "squad-pw"
    settings.auth_secret = "test-secret"
    # TestClient talks plain http; Secure cookies would be dropped.
    settings.auth_cookie_secure = False
    settings.auth_cookie_samesite = "lax"
    yield
    (
        settings.auth_enabled,
        settings.group_password,
        settings.auth_secret,
        settings.auth_cookie_secure,
        settings.auth_cookie_samesite,
    ) = saved


@pytest.fixture
def public_read_on():
    """auth_on plus auth_public_read=True; restores all of it afterwards."""
    saved = (
        settings.auth_enabled,
        settings.group_password,
        settings.auth_secret,
        settings.auth_cookie_secure,
        settings.auth_cookie_samesite,
        settings.auth_public_read,
    )
    settings.auth_enabled = True
    settings.group_password = "squad-pw"
    settings.auth_secret = "test-secret"
    settings.auth_cookie_secure = False
    settings.auth_cookie_samesite = "lax"
    settings.auth_public_read = True
    yield
    (
        settings.auth_enabled,
        settings.group_password,
        settings.auth_secret,
        settings.auth_cookie_secure,
        settings.auth_cookie_samesite,
        settings.auth_public_read,
    ) = saved


@pytest.fixture
def admin_token_on():
    saved = settings.admin_token
    settings.admin_token = "admin-secret"
    yield
    settings.admin_token = saved


class TestAuthDisabled:
    def test_everything_open_by_default(self, client):
        assert settings.auth_enabled is False
        assert client.get("/health").status_code == 200
        status = client.get("/auth/status").json()
        assert status == {"auth_enabled": False, "public_read": True, "authenticated": True}

    def test_login_is_a_noop(self, client):
        resp = client.post("/auth/login", json={"password": "anything"})
        assert resp.status_code == 200
        assert resp.json()["auth_enabled"] is False


class TestAuthEnabled:
    def test_unauthenticated_requests_rejected(self, client, auth_on):
        assert client.get("/leaderboard/mmr").status_code == 401
        assert client.get("/docs").status_code == 401

    def test_public_paths_stay_open(self, client, auth_on):
        assert client.get("/health").status_code == 200
        status = client.get("/auth/status").json()
        assert status == {"auth_enabled": True, "public_read": False, "authenticated": False}

    def test_wrong_password_rejected_no_cookie(self, client, auth_on):
        resp = client.post("/auth/login", json={"password": "nope"})
        assert resp.status_code == 401
        assert "sc2mmr_session" not in resp.cookies

    def test_login_sets_working_session(self, client, auth_on):
        resp = client.post("/auth/login", json={"password": "squad-pw"})
        assert resp.status_code == 200
        assert "sc2mmr_session" in resp.cookies
        # TestClient persists cookies; subsequent requests are authenticated
        assert client.get("/auth/status").json()["authenticated"] is True
        assert client.get("/leaderboard/mmr").status_code == 200

    def test_logout_clears_session(self, client, auth_on):
        client.post("/auth/login", json={"password": "squad-pw"})
        client.post("/auth/logout")
        assert client.get("/auth/status").json()["authenticated"] is False
        assert client.get("/leaderboard/mmr").status_code == 401

    def test_forged_cookie_rejected(self, client, auth_on):
        client.cookies.set("sc2mmr_session", "9999999999.deadbeef")
        assert client.get("/leaderboard/mmr").status_code == 401

    def test_missing_group_password_config(self, client, auth_on):
        settings.group_password = ""
        resp = client.post("/auth/login", json={"password": "whatever"})
        assert resp.status_code == 503


class TestAdminToken:
    def test_not_enforced_when_unset(self):
        assert settings.admin_token == ""
        # Dependency passes without a header when no token is configured
        require_admin(x_admin_token=None)

    def test_enforced_when_set(self, admin_token_on):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            require_admin(x_admin_token=None)
        assert exc.value.status_code == 403
        with pytest.raises(HTTPException):
            require_admin(x_admin_token="wrong")
        require_admin(x_admin_token="admin-secret")  # no raise

    def test_admin_endpoint_rejects_without_header(self, client, admin_token_on):
        resp = client.post("/h2h/calculate-all")
        assert resp.status_code == 403


class TestUploadSizeLimit:
    def test_oversized_upload_rejected(self, client):
        oversized = b"x" * (settings.max_replay_size_mb * 1024 * 1024 + 1)
        resp = client.post(
            "/replays/upload",
            files={"file": ("big.SC2Replay", oversized, "application/octet-stream")},
        )
        assert resp.status_code == 413


class TestPublicReadMode:
    def test_anonymous_get_data_endpoint_allowed(self, client, public_read_on):
        assert client.get("/leaderboard/mmr").status_code == 200

    def test_anonymous_write_still_rejected(self, client, public_read_on):
        # 401 must come from the middleware before any file parsing happens.
        resp = client.post(
            "/replays/upload",
            files={"file": ("dummy.SC2Replay", b"not a real replay", "application/octet-stream")},
        )
        assert resp.status_code == 401

    def test_anonymous_docs_and_openapi_still_protected(self, client, public_read_on):
        assert client.get("/docs").status_code == 401
        assert client.get("/openapi.json").status_code == 401

    def test_anonymous_replay_download_still_protected(self, client, public_read_on):
        assert client.get("/replays/matches/1/download").status_code == 401
        # Trailing slash must not slip past the endswith("/download") check.
        assert client.get("/replays/matches/1/download/").status_code == 401

    def test_auth_status_reports_public_read(self, client, public_read_on):
        status = client.get("/auth/status").json()
        assert status == {
            "auth_enabled": True,
            "public_read": True,
            "authenticated": False,
        }

    def test_login_unlocks_write_paths(self, client, public_read_on):
        resp = client.post("/auth/login", json={"password": "squad-pw"})
        assert resp.status_code == 200
        # Past the middleware now; a dummy file 400s on invalid content,
        # which is fine - the point is it's not a 401 from the auth gate.
        resp = client.post(
            "/replays/upload",
            files={"file": ("dummy.SC2Replay", b"not a real replay", "application/octet-stream")},
        )
        assert resp.status_code != 401

    def test_anonymous_head_data_endpoint_allowed(self, client, public_read_on):
        resp = client.head("/leaderboard/mmr")
        assert resp.status_code != 401

    def test_public_read_without_auth_enabled_is_fully_open(self, client):
        # Regression guard: auth_public_read=True but auth_enabled=False must
        # behave exactly like today's fully-open default (the middleware's
        # very first check is `if not settings.auth_enabled: return`).
        assert settings.auth_enabled is False
        settings.auth_public_read = True
        try:
            assert client.get("/leaderboard/mmr").status_code == 200
            assert client.get("/docs").status_code == 200
            assert client.get("/replays/matches/1/download").status_code != 401
            resp = client.post(
                "/replays/upload",
                files={"file": ("dummy.SC2Replay", b"not a real replay", "application/octet-stream")},
            )
            assert resp.status_code != 401
        finally:
            settings.auth_public_read = False
