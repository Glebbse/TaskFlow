# Auth And OAuth Notes

## Internal User Model

TaskFlow has one internal `users` table. Local login and Google login both lead to the same internal user identity.

External provider identities are stored in `auth_accounts`:

- `provider`
- `provider_user_id`
- `email`
- `user_id`

For Google, `provider_user_id` is Google `sub`.

Email is not the permanent provider identity. It can change, and it is used only as a verified linking hint when a provider account is seen for the first time.

## Local Auth

Local login verifies a username/password pair.

On success, TaskFlow issues:

- a JWT access token in the response body
- an opaque refresh token in an HttpOnly cookie

Only the hash of the refresh token is stored in the database.

## Google OAuth

Google login starts at:

```text
GET /auth/google/login
```

The backend creates a random OAuth `state`, stores it in a short-lived HttpOnly cookie, and redirects the browser to Google's authorization endpoint.

Google redirects back to:

```text
GET /auth/google/callback?code=...&state=...
```

The callback:

1. compares query `state` with the state cookie
2. exchanges the authorization code with Google
3. receives Google tokens
4. verifies the Google ID token
5. extracts `sub`, `email`, and `email_verified`
6. links or creates an internal TaskFlow user
7. creates TaskFlow tokens
8. redirects back to `/ui/#access_token=...`

## Token Roles

- OAuth `state`: binds callback to the login flow that TaskFlow started
- Google authorization `code`: one-time ticket exchanged server-side for Google tokens
- Google ID token: signed identity statement about the Google user
- Google access token: permission token for Google APIs
- TaskFlow access token: permission token for TaskFlow API
- TaskFlow refresh token: long-lived session token used to rotate access tokens

## Decode vs Verify

Decoding a JWT only reads its payload.

Verifying a JWT checks that the token is trustworthy:

- valid signature
- expected issuer
- expected audience
- not expired

TaskFlow verifies Google ID tokens before trusting `sub`, `email`, or `email_verified`.
