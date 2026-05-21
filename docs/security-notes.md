# Security Notes

These notes document the intended security model and the learning tradeoffs in this project.

## Refresh Tokens

Refresh tokens are generated as random opaque values.

The database stores:

- SHA-256 token hash
- user id
- expiration time
- revocation time
- creation time

The raw refresh token is only sent to the browser as an HttpOnly cookie.

## Rotation And Reuse Detection

Refresh rotates on every `/auth/refresh` call:

1. old refresh token is revoked
2. new refresh token is created
3. original refresh expiration is preserved

If a revoked refresh token is reused, active refresh tokens for that user are revoked.

## Cookies

Local development uses HTTP, so refresh cookies are not marked `Secure`.

Production HTTPS should use:

```text
Secure=True
HttpOnly=True
SameSite=Lax
Path=/auth
```

## OAuth State

OAuth state is short-lived and single-use.

It protects the Google redirect flow from CSRF and login confusion by proving that the callback belongs to a flow the backend started.

After successful callback, the state cookie is deleted.

## Access Token Storage

The static frontend stores TaskFlow access tokens in localStorage.

This is a conscious learning tradeoff. It keeps the browser/backend flow simple while studying access tokens, refresh cookies, and OAuth.

A more hardened production design could avoid exposing access tokens to JavaScript by using cookie-backed sessions or a backend-for-frontend pattern.

## Google Identity

TaskFlow links Google accounts by `(provider, provider_user_id)`.

For Google, `provider_user_id` is `sub`.

Verified email is used only for first-time linking to an existing local account.
