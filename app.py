import hmac
import csv
import os
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from io import StringIO, BytesIO
from decimal import Decimal, InvalidOperation
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for, send_file
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USE_POSTGRES = bool(DATABASE_URL)
DATABASE = Path(os.environ.get("EXPENSES_DB_PATH", str(BASE_DIR / "expenses.db")))
if not USE_POSTGRES:
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
CATEGORIES = ["Food", "Transport", "Shopping", "Bills", "Health", "Entertainment", "Other"]
IS_PRODUCTION = os.environ.get("APP_ENV", "development").lower() == "production" or os.environ.get("RENDER", "").lower() == "true"
SECRET_KEY = os.environ.get("SECRET_KEY", "local-only-change-before-deploying")

if IS_PRODUCTION and SECRET_KEY == "local-only-change-before-deploying":
    raise RuntimeError("Set a unique SECRET_KEY environment variable before production deployment.")

app = Flask(__name__)
app.config.update(
    SECRET_KEY=SECRET_KEY,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=IS_PRODUCTION,
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
)
@app.route("/service-worker.js")
def service_worker():
    return send_file(
        os.path.join(app.root_path, "static", "service-worker.js"),
        mimetype="application/javascript"
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
            execute(connection, """CREATE TABLE IF NOT EXISTS users (
                id BIGSERIAL PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")

            execute(
    connection,
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS name TEXT"
)

            execute(connection, """CREATE TABLE IF NOT EXISTS expenses (
                id BIGSERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                amount_paise BIGINT NOT NULL,
                category TEXT NOT NULL,
                spent_on TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")

            execute(
                connection,
                "ALTER TABLE expenses ADD COLUMN IF NOT EXISTS user_id BIGINT REFERENCES users(id)"
            )

            execute(connection, """CREATE TABLE IF NOT EXISTS family_groups (
                id BIGSERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                join_code TEXT UNIQUE,
                created_by BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")

            execute(
                connection,
                "ALTER TABLE family_groups ADD COLUMN IF NOT EXISTS join_code TEXT"
            )

            execute(
                connection,
                """CREATE UNIQUE INDEX IF NOT EXISTS idx_family_groups_join_code
                   ON family_groups(join_code)"""
            )

            execute(connection, """CREATE TABLE IF NOT EXISTS family_members (
                group_id BIGINT NOT NULL REFERENCES family_groups(id) ON DELETE CASCADE,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                role TEXT NOT NULL DEFAULT 'member',
                joined_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (group_id, user_id)
            )""")

            execute(connection, """CREATE TABLE IF NOT EXISTS family_expenses (
                id BIGSERIAL PRIMARY KEY,
                group_id BIGINT NOT NULL REFERENCES family_groups(id) ON DELETE CASCADE,
                paid_by BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                amount_paise BIGINT NOT NULL CHECK (amount_paise > 0),
                category TEXT NOT NULL,
                spent_on TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")

            execute(
                connection,
                """CREATE INDEX IF NOT EXISTS idx_family_expenses_group
                   ON family_expenses(group_id, spent_on)"""
            )

            execute(
                connection,
                """CREATE INDEX IF NOT EXISTS idx_family_expenses_paid_by
                   ON family_expenses(group_id, paid_by)"""
            )
            execute(connection, """CREATE TABLE IF NOT EXISTS budgets (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    month TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'Overall',
    amount_paise BIGINT NOT NULL CHECK (amount_paise > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, month, category)
)""")
            unassigned = execute(
                connection,
                "SELECT COUNT(*) AS count FROM expenses WHERE user_id IS NULL"
            ).fetchone()["count"]

            if unassigned > 0:
                first_user = execute(
                    connection,
                    "SELECT id FROM users ORDER BY id ASC LIMIT 1"
                ).fetchone()

                if first_user:
                    execute(
                        connection,
                        "UPDATE expenses SET user_id=? WHERE user_id IS NULL",
                        (first_user["id"],)
                    )

        else:
            execute(connection, """CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")

            user_columns = {
    row["name"]
    for row in execute(
        connection, "PRAGMA table_info(users)"
    ).fetchall()
}

            if "name" not in user_columns:
             execute(connection, "ALTER TABLE users ADD COLUMN name TEXT")

            execute(connection, """CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                amount_paise INTEGER NOT NULL,
                category TEXT NOT NULL,
                spent_on TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")

            columns = {
                row["name"]
                for row in execute(
                    connection, "PRAGMA table_info(expenses)"
                ).fetchall()
            }

            if "user_id" not in columns:
                execute(
                    connection,
                    "ALTER TABLE expenses ADD COLUMN user_id INTEGER REFERENCES users(id)"
                )

            execute(connection, """CREATE TABLE IF NOT EXISTS family_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                join_code TEXT UNIQUE,
                created_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")

            family_columns = {
                row["name"]
                for row in execute(
                    connection, "PRAGMA table_info(family_groups)"
                ).fetchall()
            }

            if "join_code" not in family_columns:
                execute(
                    connection,
                    "ALTER TABLE family_groups ADD COLUMN join_code TEXT"
                )

            execute(
                connection,
                """CREATE UNIQUE INDEX IF NOT EXISTS idx_family_groups_join_code
                   ON family_groups(join_code)"""
            )

            execute(connection, """CREATE TABLE IF NOT EXISTS family_members (
                group_id INTEGER NOT NULL REFERENCES family_groups(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                role TEXT NOT NULL DEFAULT 'member',
                joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (group_id, user_id)
            )""")

            execute(connection, """CREATE TABLE IF NOT EXISTS family_expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL REFERENCES family_groups(id) ON DELETE CASCADE,
                paid_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                amount_paise INTEGER NOT NULL CHECK (amount_paise > 0),
                category TEXT NOT NULL,
                spent_on TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")

            execute(
                connection,
                """CREATE INDEX IF NOT EXISTS idx_family_expenses_group
                   ON family_expenses(group_id, spent_on)"""
            )

            execute(
                connection,
                """CREATE INDEX IF NOT EXISTS idx_family_expenses_paid_by
                   ON family_expenses(group_id, paid_by)"""
            )
            execute(connection, """CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    month TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'Overall',
    amount_paise INTEGER NOT NULL CHECK (amount_paise > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (user_id, month, category)
)""")
            unassigned = execute(
                connection,
                "SELECT COUNT(*) AS count FROM expenses WHERE user_id IS NULL"
            ).fetchone()["count"]

            if unassigned > 0:
                first_user = execute(
                    connection,
                    "SELECT id FROM users ORDER BY id ASC LIMIT 1"
                ).fetchone()

                if first_user:
                    execute(
                        connection,
                        "UPDATE expenses SET user_id=? WHERE user_id IS NULL",
                        (first_user["id"],)
                    )
# Email validation function
def valid_email(email):
    return bool(
        re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email)
    ) and len(email) <= 254


# CSRF token function
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

    if request.endpoint not in {"login", "register", "static"} and not session.get("user_id"):
        return redirect(url_for("login"))


@app.after_request
def prevent_private_page_caching(response):
    if request.endpoint != "static":
        response.headers["Cache-Control"] = "no-store"
    return response

@app.route("/offline")
def offline():
    return render_template("offline.html")
@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with get_db() as connection:
            user = execute(connection, "SELECT id, password_hash FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session.permanent = True
            session["user_id"] = user["id"]
            session["user_email"] = email
            session["_csrf_token"] = secrets.token_urlsafe(32)
            return redirect(url_for("index"))
        flash("Email or password didn’t match. Please try again.", "error")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or len(name) > 100:
            flash("Please enter a valid full name.", "error")

        elif not valid_email(email):
            flash("Enter a valid email address.", "error")

        elif len(password) < 12:
            flash("Choose a password with at least 12 characters.", "error")

        elif password != confirm_password:
            flash("The passwords do not match.", "error")

        else:
            try:
                with get_db() as connection:
                    cursor = execute(
                        connection,
                        """INSERT INTO users
                           (name, email, password_hash)
                           VALUES (?, ?, ?)
                           RETURNING id""",
                        (name, email, generate_password_hash(password)),
                    )

                    user_id = cursor.fetchone()["id"]

            except Exception as error:
                if "unique" in str(error).lower() or "duplicate" in str(error).lower():
                    flash(
                        "An account with that email already exists. Please sign in.",
                        "error"
                    )
                else:
                    raise

            else:
                session.clear()
                session.permanent = True
                session["user_id"] = user_id
                session["user_email"] = email
                session["user_name"] = name
                session["_csrf_token"] = secrets.token_urlsafe(32)

                flash("Your account is ready. Welcome to Pocket!", "success")
                return redirect(url_for("index"))

    return render_template("register.html")


@app.route("/expenses/export")
def export_expenses():
    user_id = session["user_id"]

    month = request.args.get(
        "month", date.today().strftime("%Y-%m")
    )

    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError:
        month = date.today().strftime("%Y-%m")

    with get_db() as connection:
        expenses = execute(
            connection,
            """SELECT title, amount_paise, category, spent_on
               FROM expenses
               WHERE user_id=? AND substr(spent_on,1,7)=?
               ORDER BY spent_on DESC, id DESC""",
            (user_id, month),
        ).fetchall()

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Description",
        "Amount (INR)",
        "Category",
        "Date"
    ])

    for expense in expenses:
        writer.writerow([
            expense["title"],
            f'{expense["amount_paise"] / 100:.2f}',
            expense["category"],
            expense["spent_on"]
        ])

    file_data = BytesIO(output.getvalue().encode("utf-8-sig"))
    file_data.seek(0)

    return send_file(
        file_data,
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"pocket_expenses_{month}.csv"
    )

@app.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))



@app.route("/", methods=["GET", "POST"])

def index():
    user_id = session["user_id"]

    if request.method == "POST":
                # Save a monthly budget
        if request.form.get("form_action") == "save_budget":
            budget_category = request.form.get(
                "budget_category", ""
            )
            budget_month = request.form.get(
                "budget_month", ""
            )
            budget_amount_text = request.form.get(
                "budget_amount", ""
            ).strip()

            try:
                datetime.strptime(budget_month, "%Y-%m")

                if budget_category != "Overall" and budget_category not in CATEGORIES:
                    raise ValueError

                budget_amount = Decimal(
                    budget_amount_text
                ).quantize(Decimal("0.01"))

                if budget_amount <= 0:
                    raise InvalidOperation

            except (InvalidOperation, ValueError):
                flash("Please enter a valid budget.", "error")
                return redirect(url_for("index"))

            with get_db() as connection:
                execute(
                    connection,
                    """INSERT INTO budgets
                       (user_id, month, category, amount_paise)
                       VALUES (?, ?, ?, ?)
                       ON CONFLICT (user_id, month, category)
                       DO UPDATE SET amount_paise=excluded.amount_paise""",
                    (
                        user_id,
                        budget_month,
                        budget_category,
                        int(budget_amount * 100),
                    ),
                )

            flash("Budget saved successfully.", "success")
            return redirect(url_for("index", month=budget_month))
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "")
        spent_on = request.form.get("spent_on", "")

        try:
            amount = Decimal(
                request.form.get("amount", "").strip()
            ).quantize(Decimal("0.01"))

            if amount <= 0:
                raise InvalidOperation

            datetime.strptime(spent_on, "%Y-%m-%d")

            if not title or len(title) > 100 or category not in CATEGORIES:
                raise ValueError

        except (InvalidOperation, ValueError):
            flash(
                "Enter a description, valid amount, category, and date.",
                "error"
            )
            return redirect(url_for("index"))

        with get_db() as connection:
            execute(
                connection,
                """INSERT INTO expenses
                   (user_id, title, amount_paise, category, spent_on)
                   VALUES (?, ?, ?, ?, ?)""",
                (user_id, title, int(amount * 100), category, spent_on),
            )

        flash("Expense added.", "success")
        return redirect(url_for("index"))

    month = request.args.get(
        "month", date.today().strftime("%Y-%m")
    )

    try:
        datetime.strptime(month, "%Y-%m")
    except ValueError:
        month = date.today().strftime("%Y-%m")
    # Calculate the previous month
    selected_month_date = datetime.strptime(month, "%Y-%m")

    if selected_month_date.month == 1:
        previous_month = f"{selected_month_date.year - 1}-12"
    else:
        previous_month = (
            f"{selected_month_date.year}-"
            f"{selected_month_date.month - 1:02d}"
        )
    with get_db() as connection:

        # Personal expenses
        expenses = execute(
            connection,
            """SELECT * FROM expenses
               WHERE user_id=? AND substr(spent_on,1,7)=?
               ORDER BY spent_on DESC,id DESC""",
            (user_id, month),
        ).fetchall()

        # Monthly total
        total = execute(
            connection,
            """SELECT COALESCE(SUM(amount_paise),0) AS total
               FROM expenses
               WHERE user_id=? AND substr(spent_on,1,7)=?""",
            (user_id, month),
        ).fetchone()["total"]
        # Previous month's personal spending
        previous_total = execute(
            connection,
            """SELECT COALESCE(SUM(amount_paise),0) AS total
               FROM expenses
               WHERE user_id=? AND substr(spent_on,1,7)=?""",
            (user_id, previous_month),
        ).fetchone()["total"]
        # Category totals
        category_totals = execute(
            connection,
            """SELECT category,SUM(amount_paise) AS total
               FROM expenses
               WHERE user_id=? AND substr(spent_on,1,7)=?
               GROUP BY category ORDER BY total DESC""",
            (user_id, month),
        ).fetchall()
                # Monthly budgets
        budgets = execute(
            connection,
            """SELECT category, amount_paise
               FROM budgets
               WHERE user_id=? AND month=?
               ORDER BY category ASC""",
            (user_id, month),
        ).fetchall()
        # Daily spending totals for analytics
        daily_totals = execute(
            connection,
            """SELECT spent_on, SUM(amount_paise) AS total
               FROM expenses
               WHERE user_id=? AND substr(spent_on,1,7)=?
               GROUP BY spent_on
               ORDER BY spent_on ASC""",
            (user_id, month),
        ).fetchall()

        # Family groups
        family_groups = execute(
            connection,
            """SELECT fg.id, fg.name, fg.join_code, fm.role
               FROM family_groups fg
               JOIN family_members fm ON fg.id = fm.group_id
               WHERE fm.user_id=?
               ORDER BY fg.id DESC""",
            (user_id,),
        ).fetchall()

        # Shared family expenses
        family_expenses = execute(
            connection,
            """SELECT fe.*, u.email AS payer_email, fg.name AS group_name
               FROM family_expenses fe
               JOIN family_members fm ON fm.group_id = fe.group_id
               JOIN users u ON u.id = fe.paid_by
               JOIN family_groups fg ON fg.id = fe.group_id
               WHERE fm.user_id = ?
               AND substr(fe.spent_on, 1, 7) = ?
               ORDER BY fe.spent_on DESC, fe.id DESC""",
            (user_id, month),
        ).fetchall()

        # Family total
        family_total = execute(
            connection,
            """SELECT COALESCE(SUM(fe.amount_paise), 0) AS total
               FROM family_expenses fe
               JOIN family_members fm ON fm.group_id = fe.group_id
               WHERE fm.user_id = ?
               AND substr(fe.spent_on, 1, 7) = ?""",
            (user_id, month),
        ).fetchone()["total"]

        # Family member totals
        family_member_totals = execute(
            connection,
            """SELECT
                   COALESCE(NULLIF(TRIM(u.name), ''), u.email)
                       AS display_name,
                   SUM(fe.amount_paise) AS total
               FROM family_expenses fe
               JOIN family_members fm ON fm.group_id = fe.group_id
               JOIN users u ON u.id = fe.paid_by
               WHERE fm.user_id = ?
               AND substr(fe.spent_on, 1, 7) = ?
               GROUP BY u.id, u.name, u.email
               ORDER BY total DESC""",
            (user_id, month),
        ).fetchall()
        daily_totals = [
        {
            "spent_on": row["spent_on"],
            "total": row["total"]
        }
        for row in daily_totals
    ]
            # Monthly spending comparison
    monthly_difference = total - previous_total

    if previous_total > 0:
        monthly_percentage = (
            monthly_difference / previous_total
        ) * 100
    else:
        monthly_percentage = None
            # Budget calculations
    budget_data = []
    overall_budget = 0
    category_spending = {
        row["category"]: row["total"]
        for row in category_totals
    }

    for budget in budgets:
        budget_amount = budget["amount_paise"]
        budget_category = budget["category"]

        if budget_category == "Overall":
            spent_amount = total
            overall_budget = budget_amount
        else:
            spent_amount = category_spending.get(
                budget_category, 0
            )

        remaining = budget_amount - spent_amount

        budget_data.append({
            "category": budget_category,
            "budget": budget_amount,
            "spent": spent_amount,
            "remaining": remaining,
            "percentage": min(
                (spent_amount / budget_amount) * 100,
                100
            ),
            "overspent": spent_amount > budget_amount,
        })
            # Smart spending insights
    spending_insights = []

    if total > 0 and category_totals:
        top_category = category_totals[0]
        top_category_name = top_category["category"]
        top_category_total = top_category["total"]

        top_category_percentage = (
            top_category_total / total
        ) * 100

        spending_insights.append(
            f"{top_category_name} is your highest spending "
            f"category this month, accounting for "
            f"{top_category_percentage:.1f}% of your expenses."
        )

    if monthly_difference > 0:
        spending_insights.append(
            "Your spending is higher than last month."
        )
    elif monthly_difference < 0:
        spending_insights.append(
            "Your spending is lower than last month."
        )
    elif total > 0:
        spending_insights.append(
            "Your spending matches last month's total."
        )

    for item in budget_data:
        if item["overspent"]:
            spending_insights.append(
                f"You exceeded your {item['category']} budget."
            )
        elif item["budget"] > 0 and item["percentage"] >= 80:
            spending_insights.append(
                f"You have used at least 80% of your "
                f"{item['category']} budget."
            )

    if not spending_insights:
        spending_insights.append(
            "Add expenses and budgets to unlock your spending insights."
        )
    return render_template(
        "index.html",
        expenses=expenses,
        total=total,
        category_totals=category_totals,
        daily_totals=daily_totals,
        categories=CATEGORIES,
        month=month,
        previous_month=previous_month,
        previous_total=previous_total,
        monthly_difference=monthly_difference,
        monthly_percentage=monthly_percentage,
                budgets=budgets,
        budget_data=budget_data,
                spending_insights=spending_insights,
        overall_budget=overall_budget,
        today=date.today().isoformat(),
        family_groups=family_groups,
        family_expenses=family_expenses,
        family_total=family_total,
        family_member_totals=family_member_totals,
    )

@app.post("/family/create")
def create_family():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    family_name = request.form.get("family_name", "").strip()

    if len(family_name) < 2 or len(family_name) > 50:
        flash("Family group name must be between 2 and 50 characters.", "error")
        return redirect(url_for("index") + "#family-expenses")

    join_code = secrets.token_hex(4).upper()

    with get_db() as connection:
        cursor = execute(
            connection,
            """INSERT INTO family_groups (name, created_by, join_code)
               VALUES (?, ?, ?) RETURNING id""",
            (family_name, user_id, join_code),
        )

        group_id = cursor.fetchone()["id"]

        execute(
            connection,
            """INSERT INTO family_members (group_id, user_id, role)
               VALUES (?, ?, ?)""",
            (group_id, user_id, "admin"),
        )

    flash(f"Family group created successfully! Join code: {join_code}", "success")
    return redirect(url_for("index") + "#family-expenses")

@app.post("/family/join")
def join_family():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    join_code = request.form.get("join_code", "").strip().upper()

    if not join_code:
        flash("Please enter a family join code.", "error")
        return redirect(url_for("index") + "#family-expenses")

    with get_db() as connection:
        family = execute(
            connection,
            "SELECT id, name FROM family_groups WHERE join_code=?",
            (join_code,),
        ).fetchone()

        if not family:
            flash("Invalid family join code.", "error")
            return redirect(url_for("index") + "#family-expenses")

        existing_member = execute(
            connection,
            """SELECT user_id FROM family_members
               WHERE group_id=? AND user_id=?""",
            (family["id"], user_id),
        ).fetchone()

        if existing_member:
            flash("You are already a member of this family group.", "error")
            return redirect(url_for("index") + "#family-expenses")

        execute(
            connection,
            """INSERT INTO family_members (group_id, user_id, role)
               VALUES (?, ?, ?)""",
            (family["id"], user_id, "member"),
        )

    flash(f"You joined {family['name']} successfully!", "success")
    return redirect(url_for("index") + "#family-expenses")

@app.route("/expenses/<int:expense_id>/edit", methods=["GET", "POST"])
def edit_expense(expense_id):
    user_id = session["user_id"]

    with get_db() as connection:
        expense = execute(
            connection,
            "SELECT * FROM expenses WHERE id=? AND user_id=?",
            (expense_id, user_id)
        ).fetchone()

    if not expense:
        abort(404)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "")
        spent_on = request.form.get("spent_on", "")

        try:
            amount = Decimal(
                request.form.get("amount", "").strip()
            ).quantize(Decimal("0.01"))

            if amount <= 0:
                raise InvalidOperation

            datetime.strptime(spent_on, "%Y-%m-%d")

            if not title or len(title) > 100 or category not in CATEGORIES:
                raise ValueError

        except (InvalidOperation, ValueError):
            flash("Enter a valid description, amount, category, and date.", "error")
            return redirect(url_for("edit_expense", expense_id=expense_id))

        with get_db() as connection:
            result = execute(
                connection,
                """UPDATE expenses
                   SET title=?, amount_paise=?, category=?, spent_on=?
                   WHERE id=? AND user_id=?""",
                (
                    title,
                    int(amount * 100),
                    category,
                    spent_on,
                    expense_id,
                    user_id
                )
            )

            if result.rowcount == 0:
                abort(404)

        flash("Expense updated successfully!", "success")
        return redirect(url_for("index", month=spent_on[:7]))

    return render_template(
        "edit_expense.html",
        expense=expense,
        categories=CATEGORIES
    )


@app.post("/expenses/<int:expense_id>/delete")
def delete_expense(expense_id):
    with get_db() as connection:
        result = execute(connection, "DELETE FROM expenses WHERE id=? AND user_id=?", (expense_id, session["user_id"]))
        if result.rowcount == 0:
            abort(404)
    flash("Expense deleted.", "success")
    return redirect(url_for("index"))


initialize_db()

@app.post("/family/expense/add")
def add_family_expense():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]

    group_id = request.form.get("group_id", "").strip()
    title = request.form.get("title", "").strip()
    amount = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()
    spent_on = request.form.get("spent_on", "").strip()

    # Validate title
    if not title or len(title) > 100:
        flash("Expense title must be between 1 and 100 characters.", "error")
        return redirect(url_for("index") + "#family-expenses")

    # Validate amount
    try:
        amount_paise = round(float(amount) * 100)

        if amount_paise <= 0 or amount_paise > 100000000000:
            raise ValueError

    except (ValueError, TypeError):
        flash("Please enter a valid expense amount.", "error")
        return redirect(url_for("index") + "#family-expenses")

    # Validate category
    if category not in CATEGORIES:
        flash("Please select a valid expense category.", "error")
        return redirect(url_for("index") + "#family-expenses")

    # Validate date
    try:
        date.fromisoformat(spent_on)
    except (ValueError, TypeError):
        flash("Please select a valid expense date.", "error")
        return redirect(url_for("index") + "#family-expenses")

    # Validate group ID
    try:
        group_id = int(group_id)
        if group_id <= 0:
            raise ValueError
    except (ValueError, TypeError):
        flash("Invalid family group.", "error")
        return redirect(url_for("index") + "#family-expenses")

    with get_db() as connection:
        # Verify membership
        membership = execute(
            connection,
            """SELECT group_id FROM family_members
               WHERE group_id=? AND user_id=?""",
            (group_id, user_id),
        ).fetchone()

        if not membership:
            flash("You are not a member of this family group.", "error")
            return redirect(url_for("index") + "#family-expenses")

        # Insert shared expense
        execute(
            connection,
            """INSERT INTO family_expenses
               (group_id, paid_by, title, amount_paise, category, spent_on)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (group_id, user_id, title, amount_paise, category, spent_on),
        )

    flash("Shared expense added successfully!", "success")
    return redirect(url_for("index") + "#family-expenses")
if __name__ == "__main__":
    app.run(debug=not IS_PRODUCTION)
