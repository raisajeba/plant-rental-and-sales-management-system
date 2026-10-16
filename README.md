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

Admins can review nursery accounts at `/api/v1/admin/nurseries`, retrieve an
account at `/api/v1/admin/nurseries/{id}`, and change its status to `active` or
`inactive` with `PATCH`. Nursery status changes are also available from the
Admin panel; inactive nurseries are hidden from customer listings and cannot
serve their plants.

Admins can review all plant listings at `/api/v1/admin/plants` and pending
submissions at `/api/v1/admin/plants/pending`. Approve or reject pending
listings with the corresponding `POST /api/v1/admin/plants/{id}/approve` or
`POST /api/v1/admin/plants/{id}/reject` endpoint. Approved listing availability
and quantity can be managed with `PATCH /api/v1/admin/plants/{id}`. Pending and
rejected listings are not visible to customers.

New public registrations and nursery plant listings require Admin approval.
Before deploying these changes to an existing database, apply
`app/migrations/001_add_user_approval_status.sql` and
`app/migrations/003_add_plant_listing_approval_status.sql`. Existing accounts
and listings default to approved; new registrations remain pending and
inactive until an Admin approves them. Rejected accounts remain inactive and
cannot sign in or access protected API routes.
