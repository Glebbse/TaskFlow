import pytest

from app.core.config import settings
from app.core.exceptions import OAuthProviderError
from app.schemas.oauth import ProviderIdentity
from app.services.oauth_google import (
    exchange_google_code_for_tokens,
    verify_google_id_token,
)


class FakeGoogleTokenHttpResponse:
    status_code = 200

    @staticmethod
    def json():
        return {
            "access_token": "google-access-token",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": "openid email profile",
            "id_token": "fake-google-id-token",
        }


class FakeBadGoogleHttpResponse:
    status_code = 400

    @staticmethod
    def json():
        return {
            "error": "invalid grant"
        }


class FakeBadGoogleAsyncClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def post(self, url: str, data: dict):
        return FakeBadGoogleHttpResponse()



class FakeGoogleAsyncClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def post(self, url: str, data: dict):
        assert url == "https://oauth2.googleapis.com/token"
        assert data == {
            "code": "fake-valid-code",
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }
        return FakeGoogleTokenHttpResponse()


async def fake_verified_google_identity(code: str) -> ProviderIdentity:
    return ProviderIdentity(
        provider_user_id="google_sub_123",
        email="gleb@test.com",
        email_verified=True,
    )
async def fake_unverified_google_identity(code: str) -> ProviderIdentity:
    return ProviderIdentity(
        provider_user_id="google_sub_unverified",
        email="gleb@test.com",
        email_verified=False,
    )

async def fake_invalid_google_code(code: str):
    raise OAuthProviderError("Invalid Google authorization code")


@pytest.mark.asyncio
async def test_exchange_google_code_for_tokens_sends_expected_request(monkeypatch):
    monkeypatch.setattr("app.services.oauth_google.httpx.AsyncClient",
                        lambda: FakeGoogleAsyncClient(),)

    token_response = await exchange_google_code_for_tokens("fake-valid-code")
    assert token_response.access_token == "google-access-token"
    assert token_response.id_token == "fake-google-id-token"

@pytest.mark.asyncio
async def test_exchange_google_code_for_tokens_rejects_bad_google_response(monkeypatch):
    monkeypatch.setattr("app.services.oauth_google.httpx.AsyncClient",
        lambda: FakeBadGoogleAsyncClient(),)

    with pytest.raises(OAuthProviderError) as exc_info:
        await exchange_google_code_for_tokens("bad-code")

    assert str(exc_info.value) == "Invalid Google authorization code"

@pytest.mark.asyncio
async def test_verify_google_id_token_returns_provider_identity(monkeypatch):
    def fake_verify_oauth2_token(token, request, audience):
        assert token == "fake-google-id-token"
        assert audience == settings.GOOGLE_CLIENT_ID

        return {
            "sub": "google_sub_123",
            "email": "gleb@test.com",
            "email_verified": True,
        }

    monkeypatch.setattr(
        "app.services.oauth_google.google_id_token.verify_oauth2_token",
        fake_verify_oauth2_token)
    identity = await verify_google_id_token("fake-google-id-token")

    assert identity.provider_user_id == "google_sub_123"
    assert identity.email == "gleb@test.com"
    assert identity.email_verified is True

@pytest.mark.asyncio
async def test_verify_google_id_token_rejects_invalid_token(monkeypatch):
    def fake_verify_oauth2_token(token, request, audience):
        raise ValueError("bad token")

    monkeypatch.setattr(
        "app.services.oauth_google.google_id_token.verify_oauth2_token",
        fake_verify_oauth2_token)


    with pytest.raises(OAuthProviderError) as exc:
        await verify_google_id_token("bad-token")

    assert str(exc.value) == "Invalid Google ID token"
