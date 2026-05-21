from app.core.exceptions import OAuthProviderError
from app.schemas.oauth import ProviderIdentity


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
