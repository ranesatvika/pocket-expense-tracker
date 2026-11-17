import hmac
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for

BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USE_POSTGRES = bool(DATABASE_URL)
DATABASE = Path(os.environ.get("EXPENSES_DB_PATH", str(BASE_DIR / "expenses.db")))
if not USE_POSTGRES:
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
CATEGORIES = ["Food", "Transport", "Shopping", "Bills", "Health", "Entertainment", "Other"]
IS_PRODUCTION = os.environ.get("APP_ENV", "development").lower() == "production" or os.environ.get("RENDER", "").lower() == "true"
APP_PASSWORD = os.environ.get("APP_PASSWORD", "local-demo-password")
SECRET_KEY = os.environ.get("SECRET_KEY", "local-only-change-before-deploying")

if IS_PRODUCTION and (APP_PASSWORD == "local-demo-password" or SECRET_KEY == "local-only-change-before-deploying"):
    raise RuntimeError("Set unique APP_PASSWORD and SECRET_KEY environment variables before production deployment.")

app = Flask(__name__)
app.config.update(
    SECRET_KEY=SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=IS_PRODUCTION,
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
)


@contextmanager
def get_db():
    if USE_POSTGRES:
        import psycopg
        from psycopg.rows import dict_row
        connection = psycopg.connect(DATABASE_URL, row_factory=dict_row, sslmode="require")
    else:
        connection = sqlite3.connect(DATABASE)
        connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def execute(connection, query, params=()):
    if USE_POSTGRES:
        query = query.replace("?", "%s")
    return connection.execute(query, params)


def initialize_db():
    with get_db() as connection:
        if USE_POSTGRES:
            execute(connection, """CREATE TABLE IF NOT EXISTS expenses (
                id BIGSERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                amount_paise BIGINT NOT NULL,
                category TEXT NOT NULL,
                spent_on TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
        else:
            execute(connection, """CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                amount_paise INTEGER NOT NULL,
                category TEXT NOT NULL,
                spent_on TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")


def csrf_token():
    token = session.get("_csrf_token")
    if token is None:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


@app.context_processor
def inject_template_helpers():
    return {"csrf_token": csrf_token}


@app.before_request
def protect_requests():
    if request.method == "POST":
        supplied = request.form.get("_csrf_token", "")
        expected = session.get("_csrf_token", "")
        if not expected or not hmac.compare_digest(supplied, expected):
            abort(400, description="Your session expired. Refresh the page and try again.")

    if request.endpoint not in {"login", "static"} and not session.get("authenticated"):
        return redirect(url_for("login"))


@app.after_request
def prevent_private_page_caching(response):
    if request.endpoint != "static":
        response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        supplied = request.form.get("password", "")
        if hmac.compare_digest(supplied, APP_PASSWORD):
            session.clear()
            session.permanent = True
            session["authenticated"] = True
            session["_csrf_token"] = secrets.token_urlsafe(32)
            return redirect(url_for("index"))
        flash("That password didn’t match. Please try again.", "error")
    return render_template("login.html")


@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "")
        spent_on = request.form.get("spent_on", "")
        try:
            amount = Decimal(request.form.get("amount", "").strip()).quantize(Decimal("0.01"))
            if amount <= 0:
                raise InvalidOperation
            datetime.strptime(spent_on, "%Y-%m-%d")
            if not title or len(title) > 100 or category not in CATEGORIES:
                raise ValueError
        except (InvalidOperation, ValueError):
            flash("Enter a description, valid amount, category, and date.", "error")
            return redirect(url_for("index"))
        with get_db() as connection:
            execute(connection,
                "INSERT INTO expenses (title, amount_paise, category, spent_on) VALUES (?, ?, ?, ?)",
                (title, int(amount * 100), category, spent_on),
            )
        flash("Expense added.", "success")
        return redirect(url_for("index"))

    month = request.args.get("month", date.today().strftime("%Y-%m"))
    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError:
        month = date.today().strftime("%Y-%m")
    with get_db() as connection:
        expenses = execute(connection,
            "SELECT * FROM expenses WHERE substr(spent_on,1,7)=? ORDER BY spent_on DESC,id DESC", (month,)
        ).fetchall()
        total = execute(connection,
            "SELECT COALESCE(SUM(amount_paise),0) AS total FROM expenses WHERE substr(spent_on,1,7)=?", (month,)
        ).fetchone()["total"]
        category_totals = execute(connection,
            "SELECT category,SUM(amount_paise) AS total FROM expenses WHERE substr(spent_on,1,7)=? GROUP BY category ORDER BY total DESC",
            (month,),
        ).fetchall()
    return render_template(
        "index.html", expenses=expenses, total=total, category_totals=category_totals,
        categories=CATEGORIES, month=month, today=date.today().isoformat(),
    )


@app.post("/expenses/<int:expense_id>/delete")
def delete_expense(expense_id):
    with get_db() as connection:
        execute(connection, "DELETE FROM expenses WHERE id=?", (expense_id,))
    flash("Expense deleted.", "success")
    return redirect(url_for("index"))


initialize_db()

if __name__ == "__main__":
    app.run(debug=not IS_PRODUCTION)
