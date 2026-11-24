# Pocket Expense Tracker

Pocket is a personal expense tracker built with Flask, SQLite for local use, and PostgreSQL for hosted use. It supports individual email/password accounts, budgeting, expense management, and data isolation between accounts.

## Run it locally

1. Install Python 3.10 or newer.
2. In this folder, run `python -m pip install -r requirements.txt`.
3. Start the site with `python app.py`.
4. Open `http://127.0.0.1:5000`, choose **Create an account**, and register with your email and a password of at least 12 characters.

With no `DATABASE_URL` set, entries are stored in `expenses.db` beside `app.py`.

## Deploy on Render with Supabase

The hosted version uses Supabase PostgreSQL.

1. Back up your Supabase database before deploying updates that modify the database schema.
2. In Render, open your Pocket web service and its Environment settings.
3. Ensure `DATABASE_URL` and `SECRET_KEY` are configured.
4. `SECRET_KEY` should be a unique, long random secret. Keep it private.
5. Ensure `DATABASE_URL` uses the appropriate Supabase PostgreSQL connection string for your deployment.
6. Save your environment settings and deploy the repository.

During database initialization, existing expenses without an assigned user are assigned to the oldest registered account if one exists. Review and back up existing data before deploying database changes.

New accounts start with their own expense records. Personal expense access is restricted by account.

**Important:** Never commit `SECRET_KEY`, database connection credentials, passwords, or personal database files to GitHub.

## Install Pocket on a phone or computer

After deployment over HTTPS, open the service URL in a supported browser and choose **Install app** or **Add to Home Screen** from the browser menu.

## Data locations

- Local entries are stored in `expenses.db`.
- Hosted entries are stored in Supabase PostgreSQL.
- Local and hosted data are separate unless deliberately migrated.

## Project files

- `app.py` - Flask routes, account authentication, data isolation, and SQLite/PostgreSQL storage.
- `templates/` — Tracker, sign-in, and registration pages.
- `static/style.css` — Page styling.
- `static/manifest.webmanifest` and icons — Installable app settings and icons.
- `requirements.txt` — Dependencies.
- `Procfile` — Production web start command.
