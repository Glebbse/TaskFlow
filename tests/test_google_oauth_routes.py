from urllib.parse import parse_qs, urlparse

import pytest

from app.core.config import settings
from tests.test_google_oauth_service import fake_invalid_google_code, fake_unverified_google_identity, \
    fake_verified_google_identity


@pytest.mark.asyncio
async def test_google_callback_sets_cookie_and_returns_access_token(client, monkeypatch):
    login_response = await client.get("/auth/google/login")
    assert login_response.status_code == 307

    location = login_response.headers["location"]
    state = parse_qs(urlparse(location).query)["state"][0]

    monkeypatch.setattr("app.api.routes.auth.get_google_identity_from_code",
                        fake_verified_google_identity)
    response = await client.get(
        f"/auth/google/callback?code=fake-valid-code&state={state}",
        follow_redirects=False,
    )

    assert response.status_code == 307
    redirect_location = response.headers["location"]
    parsed = urlparse(redirect_location)
    fragment = parse_qs(parsed.fragment)
    assert fragment["access_token"][0]
    assert fragment["token_type"][0] == "bearer"
    assert response.cookies.get("taskflow_refresh_token") is not None

    set_cookie_headers = response.headers.get_list("set-cookie")
    assert any("taskflow_google_oauth_state=" in h and "Max-Age=0" in h for h in set_cookie_headers)

@pytest.mark.asyncio
async def test_google_callback_rejects_unverified_email(client, monkeypatch):
    login_response = await client.get("/auth/google/login")

    assert login_response.status_code == 307

    location = login_response.headers["location"]
    state = parse_qs(urlparse(location).query)["state"][0]
    monkeypatch.setattr("app.api.routes.auth.get_google_identity_from_code",
                        fake_unverified_google_identity)
    response = await client.get(f"/auth/google/callback?code=fake-unverified-email-code&state={state}")

    assert response.status_code == 401
    assert response.json()["detail"] == "Verified email required"
    assert response.cookies.get("taskflow_refresh_token") is None

@pytest.mark.asyncio
async def test_google_login_returns_redirect_status_and_sets_state_cookie(client):
    response = await client.get("/auth/google/login")
    assert response.status_code == 307
    assert response.cookies.get("taskflow_google_oauth_state") is not None
    location = response.headers["location"]
    assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth")
    assert f"client_id={settings.GOOGLE_CLIENT_ID}" in location
    assert "response_type=code" in location
    assert "state=" in location
    assert "scope=openid+email+profile" in location

@pytest.mark.asyncio
async def test_google_callback_rejects_wrong_state(client):
    login_response = await client.get("/auth/google/login")
    assert login_response.status_code == 307

    response = await client.get(
        "/auth/google/callback?code=fake-valid-code&state=wrong-state"
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid OAuth state"

@pytest.mark.asyncio
async def test_google_callback_rejects_missing_state_cookie(client):
    response = await client.get(
        "/auth/google/callback?code=fake-valid-code&state=test-state")

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid OAuth state"

@pytest.mark.asyncio
async def test_google_callback_rejects_invalid_code(client, monkeypatch):
    login_response = await client.get("/auth/google/login")
    location = login_response.headers["location"]
    state = parse_qs(urlparse(location).query)["state"][0]
    monkeypatch.setattr("app.api.routes.auth.get_google_identity_from_code",
                        fake_invalid_google_code)
    response = await client.get(f"/auth/google/callback?code=fake-code&state={state}")
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid Google authorization code"
