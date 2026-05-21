from pydantic import BaseModel


class ProviderIdentity(BaseModel):
    provider_user_id: str
    email: str | None
    email_verified: bool


class GoogleTokenResponse(BaseModel):
    access_token: str
    expires_in: int
    token_type: str
    scope: str
    id_token: str
    refresh_token: str | None = None
