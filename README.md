<<<<<<< HEAD
# Pocket Expense Tracker

Pocket is a personal expense tracker built with Flask, SQLite for local use, and PostgreSQL for hosted use. It supports individual email/password accounts, budgeting, expense management, and data isolation between accounts.
=======
# Pocket Expense Tracker

Pocket is a personal expense tracker built with Flask, SQLite for local use, and PostgreSQL for hosted use. It supports individual email/password accounts, budgeting, expense management, and data isolation between accounts.

## Run it locally

1. Install Python 3.10 or newer.
2. In this folder, run `python -m pip install -r requirements.txt`.
3. Start the site with `python app.py`.
4. Open `http://127.0.0.1:5000`, choose **Create an account**, and register with your email and a password of at least 12 characters.

With no `DATABASE_URL` set, entries are stored in `expenses.db` beside `app.py`.

## Deploy on Render with Supabase

<<<<<<< HEAD
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
=======
The hosted copy uses Supabase PostgreSQL, so it does not depend on Render's temporary filesystem.

1. **Back up your Supabase database before deploying this update.** In Supabase, use the project's database backup/export options and keep the backup private.
2. In Render, open your existing Pocket web service and its **Environment** settings.
3. Keep your existing `DATABASE_URL` and `SECRET_KEY` values unchanged.
4. Add these two environment variables before deploying:
   - `OWNER_EMAIL` = the email address you want to use for your existing Pocket account.
   - `OWNER_PASSWORD` = a new, unique password of at least 12 characters for that account. Store it in a password manager; do not put it in GitHub or send it in chat.
5. You can remove the old `APP_PASSWORD` variable; this version no longer uses one shared password.
6. Save the environment changes and deploy the updated repository.
7. After deployment, open the site and sign in using `OWNER_EMAIL` and `OWNER_PASSWORD`. All expenses already in the shared table will be assigned to this account during the first successful database initialization. New signups will start with an empty tracker.

**Important:** Do not deploy this update until `OWNER_EMAIL` and `OWNER_PASSWORD` are saved in Render. If old expenses exist and those settings are missing, the app intentionally stops rather than leaving old expenses unassigned or exposing them.

Keep `OWNER_PASSWORD`, `SECRET_KEY`, and `DATABASE_URL` private. Do not commit secrets to GitHub. `SECRET_KEY` should remain a long random secret. `DATABASE_URL` should be the Supabase Session pooler connection string recommended for your Render setup.

## Install Pocket on a phone or computer

After deployment over HTTPS, open the service URL in a supported browser and choose **Install app** or **Add to Home Screen** from the browser menu. Pocket still needs an internet connection.

## Data locations

Local entries are stored in `expenses.db`. Hosted entries are stored in Supabase PostgreSQL. Local and hosted data are separate unless you deliberately migrate them.

## Project files

- `app.py` — Flask routes, account authentication, data isolation, and SQLite/PostgreSQL storage.
- `templates/` — tracker, sign-in, and registration pages.
- `static/style.css` — page styling.
- `static/manifest.webmanifest` and icons — installable app settings and icons.
- `requirements.txt` — Flask, Gunicorn, and PostgreSQL driver dependencies.
- `Procfile` — production web start command.
>>>>>>> origin/main
