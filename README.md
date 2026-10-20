# Plant Rental and Sales Management System

## Public landing page

The application root (`/`) serves `frontend/landing_index.html`; other frontend
pages and assets are served from the same directory. The landing page reads
available listings from the public `GET /api/v1/plants/public` endpoint.
Existing dashboard pages, including `buy.html` and `rent.html`, remain separate.

## Frontend API URL

Dashboard pages default to the current host on port `8000` and use `/api/v1`.
The landing page configures the API base to its current origin. To point a page
at another backend, set `window.GRENNEST_API_URL` to the API base URL (including
`/api/v1`) before loading `js/app.js`, for example:

```html
<script>window.GRENNEST_API_URL = "https://api.example.com/api/v1";</script>
<script src="js/app.js"></script>
```

## Admin access

Administrators sign in at `/admin-login.html`. The page authenticates against
`POST /api/v1/admin/login`; the account must be active and its existing `role_id`
must reference the active `Admin` role. Admin API endpoints require a valid
Bearer token and re-check the user's current database role on each request.
The admin UI keeps its token in tab-scoped `sessionStorage` and signs out through
`POST /api/v1/auth/logout`, which revokes the token.
