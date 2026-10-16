# Plant Rental and Sales Management System

## Frontend API URL

The frontend defaults to the current host on port `8000` and uses `/api/v1`.
To point it at another backend, set `window.GRENNEST_API_URL` to the API base
URL (including `/api/v1`) before loading `js/app.js`, for example:

```html
<script>window.GRENNEST_API_URL = "https://api.example.com/api/v1";</script>
<script src="js/app.js"></script>
```

## Admin access

Admin accounts cannot be created through public registration. To bootstrap the
first admin, configure `ADMIN_NAME`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD` in the
backend environment before starting the API. The password must be at least
12 bytes; it is stored as a bcrypt hash. Keep these values in a secret manager
or an untracked `.env` file, never in source control. The configured account is
created only if that email does not already exist; startup will fail rather
than promote an existing non-admin account or replace an existing password.

Admin users sign in through the regular login page and are directed to
`admin.html`. Admin API routes require a valid bearer token and the active
Admin role; logging out revokes the current token.
