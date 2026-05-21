# Manual Smoke Test

Use this checklist before considering TaskFlow complete.

## Local Auth

- Register a new user with username/password.
- Register a new user with email.
- Duplicate username returns 409.
- Duplicate email returns 409.
- Login returns an access token.
- Refresh token is present as an HttpOnly cookie.
- `/users/me` works with the access token.

## Refresh And Logout

- Wait for or force access-token expiration.
- `/auth/refresh` returns a new access token.
- Refresh token rotates.
- `/auth/logout` clears the current refresh cookie.
- `/auth/logout-all` revokes active refresh tokens.

## Google Auth

- Open `/ui`.
- Click `Continue with Google`.
- Complete Google login.
- Browser returns to `/ui`.
- URL hash is cleared after frontend stores the access token.
- Profile shows the Google-linked user's email.
- Refresh cookie is present.
- Tasks load normally.

## Tasks

- Create a task.
- Toggle task completion.
- Delete a task.
- Search/filter/sort/paginate tasks.
- Confirm another user cannot access the task.

## Cascades

- Delete a user.
- Confirm related tasks, refresh tokens, and auth accounts are removed.
