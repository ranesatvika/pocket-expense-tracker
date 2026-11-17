# Pocket expense tracker

Pocket is a personal expense tracker built with Flask, SQLite for local use, and PostgreSQL for hosted use. It includes a sign-in screen and can be installed from its HTTPS address as a progressive web app (PWA).

## Run it locally

1. Install Python 3.10 or newer.
2. In this folder, run `python -m pip install -r requirements.txt`.
3. Start the site with `python app.py`.
4. Open `http://127.0.0.1:5000` and sign in with the local demo password: `local-demo-password`.

With no `DATABASE_URL` set, local entries are stored in `expenses.db` beside `app.py`.

## Free hosting with Render and Supabase

The hosted copy uses Supabase PostgreSQL, so it does not depend on Render's temporary filesystem. Supabase's free plan includes a 500 MB database. Free Supabase projects can pause after a week of low activity, and Render's free web service sleeps after 15 minutes without traffic; the first visit after sleeping may take a little longer.

1. **Create the Supabase database.** Sign in or create an account at Supabase, create a project, and set a database password. Save it somewhere private.
2. In Supabase, choose **Connect**, then choose the **Session pooler** connection method. Copy its connection string and replace the password placeholder. Use the exact pooler host and username Supabase provides. The session pooler works for apps that need an IPv4 connection.
3. **Create the Render web service.** Sign in or create an account at Render using GitHub, choose **New > Web Service**, and connect this repository.
4. Set the build command to `pip install -r requirements.txt` and the start command to `gunicorn app:app`.
5. In Render's **Environment** settings, add:
   - `APP_ENV` = `production`
   - `APP_PASSWORD` = a unique, strong password for signing in to Pocket
   - `SECRET_KEY` = a long random secret. Generate one locally with `python -c "import secrets; print(secrets.token_hex(32))"`.
   - `DATABASE_URL` = the Supabase Session pooler connection string
6. Save the settings and deploy. Open the HTTPS address Render provides and sign in with the `APP_PASSWORD` you chose.

Keep `APP_PASSWORD`, `SECRET_KEY`, and `DATABASE_URL` private. Do not put them in source files or commit them to GitHub. The `.gitignore` file keeps your local database and `.env` file out of Git by default.

This free setup can go idle: Render's service may need time to wake, and Supabase may require you to resume a database project after a week of low activity. Supabase says paused projects retain their data. If you use the hosted app and can't connect after inactivity, check the project status in Supabase and resume it if needed.

## Install Pocket on a phone or computer

After deployment over HTTPS, open the service URL in a supported browser and choose **Install app** or **Add to Home Screen** from the browser menu. Pocket opens in its own app-style window but still needs an internet connection.

## Data locations

Your existing local entries remain in `expenses.db` and are not copied to Supabase automatically. Local mode uses SQLite; when `DATABASE_URL` is set, the hosted app uses PostgreSQL. New local and hosted entries are stored separately.

## Project files

- `app.py` — Flask routes, sign-in, validation, and SQLite/PostgreSQL storage.
- `templates/` — tracker and sign-in pages.
- `static/style.css` — page styling.
- `static/manifest.webmanifest` and `static/icons/` — installable app settings and icons.
- `requirements.txt` — Flask, Gunicorn, and PostgreSQL driver dependencies.
- `Procfile` — production web start command.
