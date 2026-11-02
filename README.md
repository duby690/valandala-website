# Valandala launch website

A Romanian launch presentation using existing Valandala app artwork, the Elite palette, responsive layouts and light/dark themes. The signup form saves consented subscriptions to MongoDB; it does not create app accounts. Resend sends signup confirmations and daily private reports.

## Run the complete site

Install `backend/requirements.txt` in your Python environment, copy `backend/.env.example` to `backend/.env` and configure MongoDB. From `backend`, run:

```sh
uvicorn server:app --host 0.0.0.0 --port 8001
```

Open `http://localhost:8001/`. FastAPI serves the presentation, artwork and `/api/waitlist` together, so a frontend build is not required for this static launch page. Existing `/api/status` routes remain available.

## Existing React frontend

The React entry still redirects to `/valandala-landing.html`. `frontend/package.json` proxies development `/api` requests to `http://127.0.0.1:8001`. In production, route `/api` to the website backend through your reverse proxy. If frontend and API use different hosts, set the `api-base-url` meta tag in the landing HTML to the backend origin (without `/api`) and include the frontend origin in backend `CORS_ORIGINS`.

`frontend/public/valandala-landing.html` is the served frontend copy; `valandala-landing.html` is the identical standalone copy. Their `assets/` directories contain the same four source assets copied from the Valandala app. Keep both copies synchronized when editing. `vindetz-landing.html` remains untouched as a legacy file.

## Waitlist

`POST /api/waitlist` accepts JSON with `email`, optional `name`, `consent: true`, and an empty honeypot `website` field. Invalid inputs receive 422; storage failures receive 503. Success is shown only after the database acknowledges the operation. Emails are trimmed/lowercased, have a unique index, and use an atomic upsert so duplicate or retried submissions do not create duplicate rows. Duplicate signups receive the same confirmation without revealing subscription status. The form has loading/error/success states and a request timeout.

Subscriptions live in the configured database's `launch_waitlist` collection, with a timestamp, source and consent text/version. No public endpoint exposes the list. Back up MongoDB. Use `info@valandala.ro` for contact and manual consent-withdrawal/deletion requests. See the Resend configuration below. Sending the actual launch announcement remains a separate campaign action.

The complete page requires the backend and MongoDB to be running. Uploading only the HTML to a static host does not provide signup storage. No application credentials or production data are copied from the Valandala app.

## Resend confirmations and daily list

Configure `RESEND_API_KEY`, `EMAIL_FROM_NAME`, `EMAIL_FROM_ADDRESS` (a sender on your verified Resend domain), and `WAITLIST_REPORT_EMAIL=info@valandala.ro` in `backend/.env` or deployment secrets. These match the app's Resend variable names; no Resend SDK/dependency is added. Do not put the API key in the frontend or tracked files.

Each subscription queues one Romanian confirmation email, including repeat form submissions without sending a second receipt. Signup and the delivery queue are persisted before success. The queue worker runs inside the backend, checks for work every 30 seconds, and uses Resend idempotency keys. Failed deliveries retry up to five times with backoff; permanent failures remain visible in `waitlist_email_outbox`. Requeue failed jobs manually only after investigating the error and Resend delivery status (provider idempotency lasts 24 hours). Resend acceptance is recorded as `sent`; inbox delivery is not guaranteed or tracked by webhooks.

The first daily report is scheduled for the next 09:00 in `Europe/Bucharest`. Its schedule is persisted in `website_settings`, so downtime catches up after restart. It sends the full currently subscribed list (CSV attachment) and counts to the configured report inbox, not one notification per signup. CSV columns are name, email and Romanian local signup time, with spreadsheet formula protection. To stay within MongoDB's document limit, CSV exports over 8 MiB require a separate export workflow and log an explicit error. The worker retains the same payload during retries. The backend must stay running for scheduled emails; multiple workers share atomic queue claims.

If the Resend key is absent, signup still works and receipts remain queued; configure the key and restart. Existing subscriptions are not mass-emailed automatically; submitting again queues their missing receipt. When honoring a deletion/withdrawal request, remove the subscriber and their pending outbox receipts; already sent daily attachments in your private inbox must also be handled appropriately. No live email tests or announcement broadcasts are sent as part of setup.
