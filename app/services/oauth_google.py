from urllib.parse import urlencode

from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

import httpx

from app.core.exceptions import OAuthProviderError
from app.schemas.oauth import ProviderIdentity, GoogleTokenResponse
from app.core.config import settings


GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

def build_google_authorization_url(state: str) -> str:
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
    }

    return f"{GOOGLE_AUTHORIZATION_ENDPOINT}?{urlencode(params)}"

async def exchange_google_code_for_tokens(code: str) -> GoogleTokenResponse:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_ENDPOINT,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            }
        )

    if response.status_code != 200:
        raise OAuthProviderError("Invalid Google authorization code")

    return GoogleTokenResponse.model_validate(response.json())

async def verify_google_id_token(id_token: str) -> ProviderIdentity:
    try:
        id_info = google_id_token.verify_oauth2_token(
            id_token, google_requests.Request(), settings.GOOGLE_CLIENT_ID,
        )
    except ValueError:
        raise OAuthProviderError("Invalid Google ID token")

    return ProviderIdentity(
        provider_user_id=id_info["sub"],
        email=id_info.get("email"),
        email_verified=id_info.get("email_verified", False),
    )

async def get_google_identity_from_code(code: str) -> ProviderIdentity:
    token_response = await exchange_google_code_for_tokens(code)
    return await verify_google_id_token(token_response.id_token)
