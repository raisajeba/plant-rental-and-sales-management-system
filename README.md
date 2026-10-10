# Plant Rental and Sales Management System

## Frontend API URL

The frontend defaults to the current host on port `8000` and uses `/api/v1`.
To point it at another backend, set `window.GRENNEST_API_URL` to the API base
URL (including `/api/v1`) before loading `js/app.js`, for example:

```html
<script>window.GRENNEST_API_URL = "https://api.example.com/api/v1";</script>
<script src="js/app.js"></script>
```
