from datetime import date, timedelta
from functools import wraps
import os
import sqlite3
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "local-development-key-change-before-deployment")
DB_PATH = Path(os.environ.get("DATABASE_PATH", str(Path(__file__).with_name("library.db"))))
LOAN_DAYS = 14
FINE_PER_DAY = 5  # Demo fine amount in your chosen currency units.


def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'student' CHECK(role IN ('admin','student')),
                interests TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                total_copies INTEGER NOT NULL DEFAULT 1 CHECK(total_copies >= 0),
                available_copies INTEGER NOT NULL DEFAULT 1 CHECK(available_copies >= 0),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS loans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                book_id INTEGER NOT NULL,
                borrowed_on TEXT NOT NULL,
                due_date TEXT NOT NULL,
                returned_on TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(book_id) REFERENCES books(id)
            );
        """)

        admin_email = os.environ.get("ADMIN_EMAIL", "admin@library.local")
        admin_password = os.environ.get("ADMIN_PASSWORD", "Admin123!")
        admin = db.execute("SELECT id FROM users WHERE email = ?", (admin_email,)).fetchone()
        if not admin:
            db.execute(
                "INSERT INTO users (name,email,password_hash,role,interests) VALUES (?,?,?,?,?)",
                ("Library Admin", admin_email,
                 generate_password_hash(admin_password), "admin", "management")
            )

        if db.execute("SELECT COUNT(*) FROM books").fetchone()[0] == 0:
            seed_books = [
                ("Python for Beginners", "John Smith", "Programming", "A gentle introduction to Python and problem solving.", 5, 5),
                ("Learning SQL", "Alan Beaulieu", "Programming", "Learn how to query and organise relational databases.", 4, 4),
                ("Artificial Intelligence Basics", "M. Rao", "Artificial Intelligence", "An introduction to AI concepts and intelligent systems.", 3, 3),
                ("Data Science Handbook", "Jake VanderPlas", "Data Science", "Explore practical data analysis and visualisation.", 3, 3),
                ("Web Development Essentials", "A. Kumar", "Web Development", "Learn the foundations of websites and web applications.", 4, 4),
                ("The Hidden Library", "Helen Harper", "Fiction", "A fictional adventure for readers who love mysteries.", 2, 2),
                ("The Universe Explained", "Nina Patel", "Science", "A beginner-friendly guide to the universe.", 2, 2),
                ("Mindful Living", "Sarah Green", "Self-Help", "Ideas for building positive everyday habits.", 2, 2),
            ]
            db.executemany("""
                INSERT INTO books (title,author,category,description,total_copies,available_copies)
                VALUES (?,?,?,?,?,?)
            """, seed_books)


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    with get_db() as db:
        user = db.execute(
            "SELECT id,name,email,role,interests FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    return user


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def role_required(role):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = current_user()
            if not user:
                flash("Please log in to continue.", "error")
                return redirect(url_for("login"))
            if user["role"] != role:
                flash("You do not have permission to access that page.", "error")
                return redirect(url_for("dashboard"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


def recommendation_score(book, interests):
    """Simple explainable keyword/category matching; not a trained AI model."""
    interests = (interests or "").lower()
    if not interests.strip():
        return 0
    tokens = [token for token in interests.replace(",", " ").split() if len(token) > 1]
    title = book["title"].lower()
    author = book["author"].lower()
    category = book["category"].lower()
    description = book["description"].lower()
    score = 0

    for token in tokens:
        if token in category:
            score += 5
        if token in title:
            score += 4
        if token in description:
            score += 2
        if token in author:
            score += 1

    groups = [
        ({"ai", "artificial", "intelligence", "robot", "machine", "learning"}, {"artificial intelligence"}),
        ({"python", "coding", "code", "programming", "software", "sql"}, {"programming"}),
        ({"story", "stories", "novel", "mystery", "fiction", "adventure"}, {"fiction"}),
        ({"data", "analytics", "statistics", "visualisation", "visualization"}, {"data science"}),
        ({"website", "web", "html", "css", "javascript", "design"}, {"web development"}),
        ({"space", "universe", "physics", "science", "planet"}, {"science"}),
        ({"mind", "habits", "motivation", "calm", "wellbeing"}, {"self-help"}),
    ]
    for words, categories in groups:
        if set(tokens) & words and category in categories:
            score += 3
    return score


@app.route("/")
def home():
    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    with get_db() as db:
        sql = "SELECT * FROM books WHERE 1=1"
        params = []
        if search:
            sql += " AND (title LIKE ? OR author LIKE ? OR category LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        if category:
            sql += " AND category = ?"
            params.append(category)
        sql += " ORDER BY title"
        books = db.execute(sql, params).fetchall()
        categories = db.execute("SELECT DISTINCT category FROM books ORDER BY category").fetchall()
        stats = {
            "titles": db.execute("SELECT COUNT(*) FROM books").fetchone()[0],
            "copies": db.execute("SELECT COALESCE(SUM(total_copies),0) FROM books").fetchone()[0],
            "available": db.execute("SELECT COALESCE(SUM(available_copies),0) FROM books").fetchone()[0],
            "students": db.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0],
        }
    return render_template("home.html", books=books, categories=categories, search=search,
                           category=category, stats=stats, user=current_user())


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        interests = request.form.get("interests", "").strip()
        if not name or not email or len(password) < 8:
            flash("Enter your name and email. Password must be at least 8 characters.", "error")
            return render_template("register.html")
        try:
            with get_db() as db:
                db.execute(
                    "INSERT INTO users (name,email,password_hash,role,interests) VALUES (?,?,?,?,?)",
                    (name, email, generate_password_hash(password), "student", interests)
                )
            flash("Account created. You can now log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("An account with that email already exists.", "error")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with get_db() as db:
            user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("dashboard"))
        flash("Email or password is incorrect.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have logged out.", "success")
    return redirect(url_for("home"))


@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    with get_db() as db:
        if user["role"] == "admin":
            stats = {
                "titles": db.execute("SELECT COUNT(*) FROM books").fetchone()[0],
                "copies": db.execute("SELECT COALESCE(SUM(total_copies),0) FROM books").fetchone()[0],
                "available": db.execute("SELECT COALESCE(SUM(available_copies),0) FROM books").fetchone()[0],
                "students": db.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0],
                "active": db.execute("SELECT COUNT(*) FROM loans WHERE returned_on IS NULL").fetchone()[0],
            }
            loans = db.execute("""
                SELECT loans.*, users.name AS student_name, books.title AS book_title
                FROM loans JOIN users ON users.id=loans.user_id
                JOIN books ON books.id=loans.book_id
                ORDER BY loans.id DESC LIMIT 30
            """).fetchall()
            books = db.execute("SELECT * FROM books ORDER BY title").fetchall()
            return render_template("admin_dashboard.html", user=user, stats=stats, loans=loans, books=books)
        loans = db.execute("""
            SELECT loans.*, books.title AS book_title, books.author, books.category
            FROM loans JOIN books ON books.id=loans.book_id
            WHERE loans.user_id=? ORDER BY loans.id DESC
        """, (user["id"],)).fetchall()
        all_books = db.execute("SELECT * FROM books ORDER BY title").fetchall()
    recommendations = sorted(all_books, key=lambda b: recommendation_score(b, user["interests"]), reverse=True)
    recommendations = [b for b in recommendations if recommendation_score(b, user["interests"]) > 0][:4]
    return render_template("student_dashboard.html", user=user, loans=loans, recommendations=recommendations,
                           fine_per_day=FINE_PER_DAY)


@app.route("/borrow/<int:book_id>", methods=["POST"])
@login_required
@role_required("student")
def borrow(book_id):
    user = current_user()
    with get_db() as db:
        book = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        active = db.execute(
            "SELECT id FROM loans WHERE user_id=? AND book_id=? AND returned_on IS NULL",
            (user["id"], book_id)
        ).fetchone()
        if not book:
            flash("Book not found.", "error")
        elif active:
            flash("You already have this book checked out.", "error")
        elif book["available_copies"] < 1:
            flash("This book is currently unavailable.", "error")
        else:
            borrowed = date.today()
            due = borrowed + timedelta(days=LOAN_DAYS)
            db.execute("UPDATE books SET available_copies=available_copies-1 WHERE id=?", (book_id,))
            db.execute(
                "INSERT INTO loans (user_id,book_id,borrowed_on,due_date) VALUES (?,?,?,?)",
                (user["id"], book_id, borrowed.isoformat(), due.isoformat())
            )
            flash(f"Book issued. Please return it by {due.isoformat()}.", "success")
    return redirect(request.referrer or url_for("home"))


@app.route("/return/<int:loan_id>", methods=["POST"])
@login_required
def return_loan(loan_id):
    user = current_user()
    with get_db() as db:
        if user["role"] == "admin":
            loan = db.execute("SELECT * FROM loans WHERE id=? AND returned_on IS NULL", (loan_id,)).fetchone()
        else:
            loan = db.execute(
                "SELECT * FROM loans WHERE id=? AND user_id=? AND returned_on IS NULL",
                (loan_id, user["id"])
            ).fetchone()
        if not loan:
            flash("Active loan not found or you do not have permission to return it.", "error")
        else:
            today = date.today()
            due = date.fromisoformat(loan["due_date"])
            late_days = max(0, (today - due).days)
            fine = late_days * FINE_PER_DAY
            db.execute("UPDATE loans SET returned_on=? WHERE id=?", (today.isoformat(), loan_id))
            db.execute("UPDATE books SET available_copies=available_copies+1 WHERE id=?", (loan["book_id"],))
            if fine:
                flash(f"Book returned. It was {late_days} day(s) late; demo fine: {fine}.", "success")
            else:
                flash("Book returned successfully. No overdue fine.", "success")
    return redirect(url_for("dashboard"))


@app.route("/admin/books/add", methods=["POST"])
@login_required
@role_required("admin")
def add_book():
    title = request.form.get("title", "").strip()
    author = request.form.get("author", "").strip()
    category = request.form.get("category", "").strip()
    description = request.form.get("description", "").strip()
    try:
        copies = int(request.form.get("copies", "1"))
    except ValueError:
        copies = 0
    if not title or not author or not category or copies < 1 or copies > 500:
        flash("Enter valid book details and a copy count between 1 and 500.", "error")
    else:
        with get_db() as db:
            db.execute("""
                INSERT INTO books (title,author,category,description,total_copies,available_copies)
                VALUES (?,?,?,?,?,?)
            """, (title, author, category, description, copies, copies))
        flash("Book added successfully.", "success")
    return redirect(url_for("dashboard"))


@app.route("/admin/books/<int:book_id>/update", methods=["POST"])
@login_required
@role_required("admin")
def update_book(book_id):
    title = request.form.get("title", "").strip()
    author = request.form.get("author", "").strip()
    category = request.form.get("category", "").strip()
    description = request.form.get("description", "").strip()
    try:
        total = int(request.form.get("total_copies", "0"))
    except ValueError:
        total = 0
    with get_db() as db:
        book = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        if not book:
            flash("Book not found.", "error")
        elif not title or not author or not category or total < 1 or total < (book["total_copies"] - book["available_copies"]):
            flash("Invalid details. Total copies cannot be less than copies currently borrowed.", "error")
        else:
            borrowed = book["total_copies"] - book["available_copies"]
            db.execute("""
                UPDATE books SET title=?,author=?,category=?,description=?,total_copies=?,available_copies=?
                WHERE id=?
            """, (title, author, category, description, total, total-borrowed, book_id))
            flash("Book updated.", "success")
    return redirect(url_for("dashboard"))


@app.route("/admin/books/<int:book_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_book(book_id):
    with get_db() as db:
        book = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        if not book:
            flash("Book not found.", "error")
        elif db.execute("SELECT COUNT(*) FROM loans WHERE book_id=? AND returned_on IS NULL", (book_id,)).fetchone()[0]:
            flash("Return all borrowed copies before deleting this book.", "error")
        else:
            # Keep old loan history by preventing deletion if the book has ever been borrowed.
            history = db.execute("SELECT COUNT(*) FROM loans WHERE book_id=?", (book_id,)).fetchone()[0]
            if history:
                flash("This book has borrowing history and cannot be deleted. You can edit its details instead.", "error")
            else:
                db.execute("DELETE FROM books WHERE id=?", (book_id,))
                flash("Book deleted.", "success")
    return redirect(url_for("dashboard"))


@app.route("/recommend", methods=["POST"])
@login_required
@role_required("student")
def recommend():
    user = current_user()
    interests = request.form.get("interests", "").strip()
    with get_db() as db:
        db.execute("UPDATE users SET interests=? WHERE id=?", (interests, user["id"]))
        all_books = db.execute("SELECT * FROM books").fetchall()
    scored = sorted(
        [(recommendation_score(book, interests), book) for book in all_books],
        key=lambda pair: (pair[0], pair[1]["available_copies"]), reverse=True
    )
    results = [book for score, book in scored if score > 0][:6]
    if results:
        flash("Recommendations updated for your interests.", "success")
    else:
        flash("No close matches. Try Python, programming, AI, fiction, data, web, science, or self-help.", "error")
    return render_template("recommendations.html", user=current_user(), interests=interests, results=results)


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
