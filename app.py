import os
import sqlite3
from urllib.parse import urlparse, parse_qs
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "learning_hub.db")
app = Flask(__name__, template_folder=".")
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key-before-deploying")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT NOT NULL,
            level TEXT NOT NULL DEFAULT 'Beginner',
            price REAL NOT NULL DEFAULT 0,
            thumbnail TEXT NOT NULL DEFAULT 'code',
            published INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            video_url TEXT NOT NULL DEFAULT '',
            position INTEGER NOT NULL DEFAULT 1,
            is_preview INTEGER NOT NULL DEFAULT 0,
            notes_url TEXT NOT NULL DEFAULT '',
            FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            enrolled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, course_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            lesson_id INTEGER NOT NULL,
            completed INTEGER NOT NULL DEFAULT 1,
            UNIQUE(user_id, lesson_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS academy_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS payment_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_no TEXT NOT NULL UNIQUE,
            user_id INTEGER NOT NULL,
            lesson_id INTEGER NOT NULL,
            item_type TEXT NOT NULL CHECK(item_type IN ('video','notes')),
            amount REAL NOT NULL,
            transaction_ref TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            paid_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
        );
        """)
        db.execute("INSERT OR IGNORE INTO academy_settings(key,value) VALUES('upi_id','jip930031-1@oksbi')")
        db.execute("INSERT OR IGNORE INTO academy_settings(key,value) VALUES('upi_name','Himanshu NextGen Academy')")
        count = db.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
        if count == 0:
            seed_courses = [
                ("Python Programming: Zero to Hero", "Programming", "Python fundamentals, variables, conditions, loops, functions and practical exercises.", "Beginner", 0, "python"),
                ("HTML & CSS Web Design", "Web Development", "Build responsive web pages with semantic HTML, modern CSS, flexbox and grid.", "Beginner", 499, "web"),
                ("Computer Basics & Internet", "Computer Basics", "Learn computer fundamentals, files, internet safety, email and everyday digital skills.", "Beginner", 0, "computer"),
                ("English Grammar Essentials", "English", "Practice parts of speech, tenses, sentence structure and common grammar mistakes.", "Beginner", 299, "english"),
                ("JavaScript Interactive Websites", "Web Development", "Learn variables, functions, DOM events and browser-based interactive features.", "Intermediate", 699, "javascript"),
                ("MS Office Productivity", "Computer Basics", "Learn practical Word, Excel and PowerPoint workflows for study and office work.", "Beginner", 399, "office")
            ]
            db.executemany("INSERT INTO courses(title,category,description,level,price,thumbnail) VALUES(?,?,?,?,?,?)", seed_courses)
            course_ids = {r["title"]: r["id"] for r in db.execute("SELECT id,title FROM courses").fetchall()}
            lessons = [
                (course_ids["Python Programming: Zero to Hero"], "Welcome to Python", "Python is a beginner-friendly programming language. In this lesson, install Python or use an online editor, then run print('Hello, world!').", "", 1, 1),
                (course_ids["Python Programming: Zero to Hero"], "Variables and Data Types", "Variables store values. Try: name = 'Himanshu'; age = 18; print(name, age). Explore strings, integers, floats and booleans.", "", 2, 0),
                (course_ids["Python Programming: Zero to Hero"], "Conditions and Loops", "Use if/elif/else to make decisions. Use for and while loops to repeat work. Practice printing numbers from 1 to 10.", "", 3, 0),
                (course_ids["HTML & CSS Web Design"], "Your First HTML Page", "HTML gives a page its structure. Create index.html with a heading, paragraph and link. This is a sample preview lesson.", "", 1, 1),
                (course_ids["HTML & CSS Web Design"], "CSS Styling Basics", "CSS controls colors, spacing, typography and layout. Try a dark background, readable text and a purple accent.", "", 2, 0),
                (course_ids["Computer Basics & Internet"], "Computer Fundamentals", "A computer accepts input, processes data, stores information and produces output. Learn the roles of CPU, RAM, storage and operating system.", "", 1, 1),
                (course_ids["Computer Basics & Internet"], "Internet Safety", "Use unique passwords, enable two-factor authentication, verify links before opening them and never share OTPs.", "", 2, 0),
                (course_ids["English Grammar Essentials"], "Parts of Speech", "Nouns name people or things, verbs show actions or states, adjectives describe nouns and adverbs often describe verbs. Write five examples of each.", "", 1, 1),
                (course_ids["English Grammar Essentials"], "Present Simple Tense", "Use the present simple for habits and facts: 'I study every day.' With he/she/it, many verbs take -s or -es.", "", 2, 0),
                (course_ids["JavaScript Interactive Websites"], "JavaScript in the Browser", "JavaScript adds behavior to websites. Open the browser console and try console.log('Hello!').", "", 1, 1),
                (course_ids["MS Office Productivity"], "Excel Cells and Formulas", "A spreadsheet is made of rows, columns and cells. In Excel, enter =SUM(A1:A5) to add a range.", "", 1, 1),
            ]
            db.executemany("INSERT INTO lessons(course_id,title,content,video_url,position,is_preview) VALUES(?,?,?,?,?,?)", lessons)
        # Safe schema migration for older databases.
        lesson_columns = {row[1] for row in db.execute("PRAGMA table_info(lessons)").fetchall()}
        if "notes_url" not in lesson_columns:
            db.execute("ALTER TABLE lessons ADD COLUMN notes_url TEXT NOT NULL DEFAULT ''")
        if "video_price" not in lesson_columns:
            db.execute("ALTER TABLE lessons ADD COLUMN video_price REAL NOT NULL DEFAULT 0")
        if "notes_price" not in lesson_columns:
            db.execute("ALTER TABLE lessons ADD COLUMN notes_price REAL NOT NULL DEFAULT 0")
        user_columns = {row[1] for row in db.execute("PRAGMA table_info(users)").fetchall()}
        if "phone" not in user_columns:
            db.execute("ALTER TABLE users ADD COLUMN phone TEXT NOT NULL DEFAULT ''")

        # Add Himanshu's Basic Computer course and lessons without duplicating them.
        basic_title = "Basic Computer — WordPad Tutorials"
        existing_course = db.execute("SELECT id FROM courses WHERE title=?", (basic_title,)).fetchone()
        if existing_course:
            basic_course_id = existing_course["id"]
        else:
            cur = db.execute("INSERT INTO courses(title,category,description,level,price,thumbnail,published) VALUES(?,?,?,?,0,?,1)",
                (basic_title, "Computer Basics", "Free Hindi WordPad tutorials: font formatting, superscript, saving files, colors and page design.", "Beginner", "computer"))
            basic_course_id = cur.lastrowid
        starter_lessons = [
            ("Lesson 1: WordPad — Font Change, Superscript & Save File", "Learn how to change font settings, apply superscript formatting, and save your WordPad document. Watch the video and practise each step on your computer.", "https://www.youtube.com/embed/RT3EuIYAlo0", 1),
            ("Lesson 2: WordPad — Fonts, Colors & Page Design", "Learn to select fonts, change text colors, and improve the page design in WordPad. Follow along with the video and create a sample document.", "https://www.youtube.com/embed/FJm1M202Jv0", 2),
        ]
        for lesson_title, lesson_content, lesson_video, lesson_position in starter_lessons:
            if not db.execute("SELECT 1 FROM lessons WHERE course_id=? AND title=?", (basic_course_id, lesson_title)).fetchone():
                db.execute("INSERT INTO lessons(course_id,title,content,video_url,position,is_preview,notes_url) VALUES(?,?,?,?,?,1,'')",
                           (basic_course_id, lesson_title, lesson_content, lesson_video, lesson_position))

        # Keep only the Basic Computer course and set the single course price to ₹9.
        db.execute("DELETE FROM courses WHERE title != ?", (basic_title,))
        db.execute("UPDATE courses SET price=9, category='Computer Basics', published=1 WHERE id=?", (basic_course_id,))
        db.execute("UPDATE lessons SET is_preview=0, video_price=0, notes_price=0 WHERE course_id=?", (basic_course_id,))

        admin_email = os.environ.get("ADMIN_EMAIL", "admin@himanshulearning.local").strip().lower()
        admin_password = os.environ.get("ADMIN_PASSWORD", "Admin@12345")
        existing = db.execute("SELECT id FROM users WHERE email=?", (admin_email,)).fetchone()
        if not existing:
            db.execute("INSERT INTO users(name,email,password_hash,role) VALUES(?,?,?,?)",
                       ("Hub Admin", admin_email, generate_password_hash(admin_password), "admin"))

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "info")
            return redirect(url_for("login", next=request.path))
        return fn(*args, **kwargs)
    return wrapped

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            abort(403)
        return fn(*args, **kwargs)
    return wrapped

@app.context_processor
def inject_user():
    return {"current_user": session.get("user_name"), "current_role": session.get("role")}

@app.route("/")
def index():
    with get_db() as db:
        courses = db.execute("SELECT * FROM courses WHERE published=1 AND title='Basic Computer — WordPad Tutorials' ORDER BY id DESC LIMIT 1").fetchall()
        total_courses = db.execute("SELECT COUNT(*) FROM courses WHERE published=1 AND title='Basic Computer — WordPad Tutorials'").fetchone()[0]
        total_students = db.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0]
    return render_template("index.html", courses=courses, total_courses=total_courses, total_students=total_students)

@app.route("/courses")
def courses():
    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    sql = "SELECT * FROM courses WHERE published=1 AND title='Basic Computer — WordPad Tutorials'"
    params = []
    if search:
        sql += " AND (title LIKE ? OR description LIKE ? OR category LIKE ?)"
        params.extend([f"%{search}%"] * 3)
    if category:
        sql += " AND category=?"
        params.append(category)
    sql += " ORDER BY id DESC"
    with get_db() as db:
        rows = db.execute(sql, params).fetchall()
        categories = [r["category"] for r in db.execute("SELECT DISTINCT category FROM courses WHERE published=1 AND title='Basic Computer — WordPad Tutorials' ORDER BY category").fetchall()]
    return render_template("courses.html", courses=rows, categories=categories, q=search, selected_category=category)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        phone = request.form.get("phone", "").strip()
        if len(name) < 2 or "@" not in email or len(password) < 8:
            flash("Enter a valid name/email and a password of at least 8 characters.", "error")
            return render_template("signup.html")
        try:
            with get_db() as db:
                db.execute("INSERT INTO users(name,email,password_hash,role,phone) VALUES(?,?,?,'student',?)",
                           (name, email, generate_password_hash(password), phone))
            flash("Account created successfully. Your details are visible in the academy admin dashboard.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("An account with this email already exists.", "error")
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with get_db() as db:
            user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["role"] = user["role"]
            flash(f"Welcome back, {user['name']}!", "success")
            next_url = request.args.get("next", "")
            if next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect(url_for("admin_dashboard" if user["role"] == "admin" else "dashboard"))
        flash("Email or password is incorrect.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))

@app.route("/course/<int:course_id>")
def course_detail(course_id):
    with get_db() as db:
        course = db.execute("SELECT * FROM courses WHERE id=? AND published=1", (course_id,)).fetchone()
        if not course:
            abort(404)
        lessons = db.execute("SELECT * FROM lessons WHERE course_id=? ORDER BY position,id", (course_id,)).fetchall()
        enrolled = False
        if session.get("user_id"):
            enrolled = db.execute("SELECT 1 FROM enrollments WHERE user_id=? AND course_id=? AND status='active'",
                                  (session["user_id"], course_id)).fetchone() is not None
    return render_template("course_detail.html", course=course, lessons=lessons, enrolled=enrolled)

@app.route("/enroll/<int:course_id>", methods=["POST"])
@login_required
def enroll(course_id):
    with get_db() as db:
        course = db.execute("SELECT * FROM courses WHERE id=? AND published=1", (course_id,)).fetchone()
        if not course:
            abort(404)
        if course["price"] > 0:
            flash("This is a paid course. Payment is demo-only in this starter project; contact the admin to activate enrollment.", "info")
            return redirect(url_for("course_detail", course_id=course_id))
        db.execute("INSERT OR IGNORE INTO enrollments(user_id,course_id,status) VALUES(?,?,'active')",
                   (session["user_id"], course_id))
    flash("You are enrolled! Start learning below.", "success")
    return redirect(url_for("course_detail", course_id=course_id))

@app.route("/lesson/<int:lesson_id>")
@login_required
def lesson_detail(lesson_id):
    with get_db() as db:
        lesson = db.execute("""SELECT l.*, c.title AS course_title, c.id AS course_id, c.price
                               FROM lessons l JOIN courses c ON c.id=l.course_id
                               WHERE l.id=? AND c.published=1""", (lesson_id,)).fetchone()
        if not lesson:
            abort(404)
        enrolled = db.execute("SELECT 1 FROM enrollments WHERE user_id=? AND course_id=? AND status='active'",
                              (session["user_id"], lesson["course_id"])).fetchone() is not None
        if not lesson["is_preview"] and not enrolled and session.get("role") != "admin" and float(lesson["video_price"] or 0) <= 0 and float(lesson["notes_price"] or 0) <= 0:
            flash("Enroll in this course to unlock this lesson.", "info")
            return redirect(url_for("course_detail", course_id=lesson["course_id"]))
        video_paid = db.execute("SELECT 1 FROM payment_orders WHERE user_id=? AND lesson_id=? AND item_type='video' AND status='paid'", (session["user_id"], lesson_id)).fetchone() is not None
        notes_paid = db.execute("SELECT 1 FROM payment_orders WHERE user_id=? AND lesson_id=? AND item_type='notes' AND status='paid'", (session["user_id"], lesson_id)).fetchone() is not None
        done = db.execute("SELECT 1 FROM progress WHERE user_id=? AND lesson_id=? AND completed=1",
                          (session["user_id"], lesson_id)).fetchone() is not None
        lessons = db.execute("SELECT id,title,position FROM lessons WHERE course_id=? ORDER BY position,id",
                             (lesson["course_id"],)).fetchall()
    return render_template("lesson.html", lesson=lesson, done=done, lessons=lessons, video_paid=video_paid, notes_paid=notes_paid)

@app.route("/lesson/<int:lesson_id>/complete", methods=["POST"])
@login_required
def complete_lesson(lesson_id):
    with get_db() as db:
        lesson = db.execute("SELECT * FROM lessons WHERE id=?", (lesson_id,)).fetchone()
        if not lesson:
            abort(404)
        enrolled = db.execute("SELECT 1 FROM enrollments WHERE user_id=? AND course_id=? AND status='active'",
                              (session["user_id"], lesson["course_id"])).fetchone() is not None
        if not lesson["is_preview"] and not enrolled and session.get("role") != "admin":
            abort(403)
        db.execute("INSERT INTO progress(user_id,lesson_id,completed) VALUES(?,?,1) ON CONFLICT(user_id,lesson_id) DO UPDATE SET completed=1",
                   (session["user_id"], lesson_id))
    flash("Lesson marked complete.", "success")
    return redirect(url_for("lesson_detail", lesson_id=lesson_id))

@app.route("/dashboard")
@login_required
def dashboard():
    if session.get("role") == "admin":
        return redirect(url_for("admin_dashboard"))
    with get_db() as db:
        enrolled = db.execute("""SELECT c.*, e.enrolled_at,
                                 (SELECT COUNT(*) FROM lessons l WHERE l.course_id=c.id) AS lesson_count,
                                 (SELECT COUNT(*) FROM lessons l JOIN progress p ON p.lesson_id=l.id
                                  WHERE l.course_id=c.id AND p.user_id=? AND p.completed=1) AS completed_count
                                 FROM enrollments e JOIN courses c ON c.id=e.course_id
                                 WHERE e.user_id=? AND e.status='active' ORDER BY e.enrolled_at DESC""",
                              (session["user_id"], session["user_id"])).fetchall()
        preview_count = db.execute("SELECT COUNT(*) FROM progress WHERE user_id=? AND completed=1",
                                    (session["user_id"],)).fetchone()[0]
    return render_template("dashboard.html", enrolled=enrolled, preview_count=preview_count)

@app.route("/admin")
@admin_required
def admin_dashboard():
    with get_db() as db:
        stats = {
            "students": db.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0],
            "courses": db.execute("SELECT COUNT(*) FROM courses").fetchone()[0],
            "lessons": db.execute("SELECT COUNT(*) FROM lessons").fetchone()[0],
            "enrollments": db.execute("SELECT COUNT(*) FROM enrollments").fetchone()[0],
        }
        users = db.execute("SELECT id,name,email,phone,role,created_at FROM users WHERE role='student' ORDER BY id DESC").fetchall()
        orders = db.execute("SELECT p.*, u.name AS student_name, u.email, l.title AS lesson_title FROM payment_orders p JOIN users u ON u.id=p.user_id JOIN lessons l ON l.id=p.lesson_id ORDER BY p.id DESC LIMIT 100").fetchall()
        courses = db.execute("SELECT c.*, COUNT(l.id) lesson_count FROM courses c LEFT JOIN lessons l ON l.course_id=c.id GROUP BY c.id ORDER BY c.id DESC").fetchall()
    return render_template("admin.html", stats=stats, users=users, courses=courses, orders=orders)

@app.route("/admin/settings/payments", methods=["GET", "POST"])
@admin_required
def admin_payment_settings():
    with get_db() as db:
        if request.method == "POST":
            upi_id = request.form.get("upi_id", "").strip()
            upi_name = request.form.get("upi_name", "").strip()
            if "@" not in upi_id or len(upi_id) > 100:
                flash("Please enter a valid UPI ID, for example name@oksbi.", "error")
            else:
                db.execute("INSERT INTO academy_settings(key,value) VALUES('upi_id',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (upi_id,))
                db.execute("INSERT INTO academy_settings(key,value) VALUES('upi_name',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (upi_name[:100],))
                flash("Payment settings saved.", "success")
                return redirect(url_for("admin_payment_settings"))
        settings = {r["key"]: r["value"] for r in db.execute("SELECT key,value FROM academy_settings").fetchall()}
    return render_template("admin_payment_settings.html", settings=settings)

@app.route("/admin/course/new", methods=["GET", "POST"])
@admin_required
def admin_new_course():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        level = request.form.get("level", "Beginner")
        try:
            price = max(0, float(request.form.get("price", "0")))
        except ValueError:
            price = 0
        if not title or not category or not description:
            flash("Please complete all required fields.", "error")
        else:
            with get_db() as db:
                db.execute("INSERT INTO courses(title,category,description,level,price,thumbnail,published) VALUES(?,?,?,?,?,'code',1)",
                           (title, category, description, level, price))
            flash("Course created. Add lessons from the course page in the admin dashboard.", "success")
            return redirect(url_for("admin_dashboard"))
    return render_template("admin_course_form.html")

@app.route("/admin/course/<int:course_id>/lesson/new", methods=["GET", "POST"])
@admin_required
def admin_new_lesson(course_id):
    with get_db() as db:
        course = db.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
        if not course:
            abort(404)
        if request.method == "POST":
            title = request.form.get("title", "").strip()
            content = request.form.get("content", "").strip()
            video_url = request.form.get("video_url", "").strip()
            notes_url = request.form.get("notes_url", "").strip()
            is_preview = 1 if request.form.get("is_preview") == "on" else 0
            try:
                video_price = max(0, float(request.form.get("video_price", "0") or 0))
                notes_price = max(0, float(request.form.get("notes_price", "0") or 0))
            except ValueError:
                video_price, notes_price = 0, 0
            position = db.execute("SELECT COALESCE(MAX(position),0)+1 FROM lessons WHERE course_id=?", (course_id,)).fetchone()[0]
            if not title or not content:
                flash("Lesson title and content are required.", "error")
            else:
                db.execute("INSERT INTO lessons(course_id,title,content,video_url,position,is_preview,notes_url,video_price,notes_price) VALUES(?,?,?,?,?,?,?,?,?)",
                           (course_id, title, content, video_url, position, is_preview, notes_url, video_price, notes_price))
                flash("Lesson added.", "success")
                return redirect(url_for("admin_dashboard"))
    return render_template("admin_lesson_form.html", course=course)


@app.route("/purchase-course/<int:course_id>", methods=["GET", "POST"])
@login_required
def purchase_course(course_id):
    with get_db() as db:
        course = db.execute("SELECT * FROM courses WHERE id=? AND published=1 AND title='Basic Computer — WordPad Tutorials'", (course_id,)).fetchone()
        if not course:
            abort(404)
        enrolled = db.execute("SELECT 1 FROM enrollments WHERE user_id=? AND course_id=? AND status='active'", (session['user_id'], course_id)).fetchone()
        if enrolled:
            flash("You already have access to this course.", "success")
            return redirect(url_for("course_detail", course_id=course_id))
        lesson = db.execute("SELECT * FROM lessons WHERE course_id=? ORDER BY position,id LIMIT 1", (course_id,)).fetchone()
        if not lesson:
            flash("Course lessons are being prepared. Please try again later.", "error")
            return redirect(url_for("course_detail", course_id=course_id))
        pending = db.execute("SELECT id FROM payment_orders WHERE user_id=? AND lesson_id=? AND item_type='video' AND amount=? AND status='pending' ORDER BY id DESC LIMIT 1", (session['user_id'], lesson['id'], float(course['price']))).fetchone()
        if request.method == 'POST':
            txn = request.form.get('transaction_ref', '').strip()
            if len(txn) < 4:
                flash("Enter the transaction reference after paying.", "error")
            else:
                import uuid
                receipt = "HNA-" + uuid.uuid4().hex[:10].upper()
                cur = db.execute("INSERT INTO payment_orders(receipt_no,user_id,lesson_id,item_type,amount,transaction_ref,status) VALUES(?,?,?,?,?,?, 'pending')", (receipt, session['user_id'], lesson['id'], 'video', float(course['price']), txn))
                flash("Payment reference submitted. Access unlocks after admin verification.", "success")
                return redirect(url_for('payment_receipt', order_id=cur.lastrowid))
        settings = {r['key']: r['value'] for r in db.execute("SELECT key,value FROM academy_settings").fetchall()}
    return render_template('payment.html', lesson={**dict(lesson), 'title': course['title']}, item_type='course', amount=float(course['price']), upi_id=settings.get('upi_id','jip930031-1@oksbi'), upi_name=settings.get('upi_name','Himanshu NextGen Academy'))

@app.route("/purchase/<int:lesson_id>/<item_type>", methods=["GET", "POST"])
@login_required
def purchase_item(lesson_id, item_type):
    if item_type not in ("video", "notes"):
        abort(404)
    with get_db() as db:
        lesson = db.execute("SELECT l.*, c.title AS course_title FROM lessons l JOIN courses c ON c.id=l.course_id WHERE l.id=?", (lesson_id,)).fetchone()
        if not lesson:
            abort(404)
        amount = float(lesson["video_price"] if item_type == "video" else lesson["notes_price"])
        if amount <= 0:
            flash("This item is free. Open the lesson to access it.", "info")
            return redirect(url_for("lesson_detail", lesson_id=lesson_id))
        already = db.execute("SELECT id FROM payment_orders WHERE user_id=? AND lesson_id=? AND item_type=? AND status='paid'", (session["user_id"], lesson_id, item_type)).fetchone()
        if already:
            flash("You already have access to this item.", "success")
            return redirect(url_for("lesson_detail", lesson_id=lesson_id))
        if request.method == "POST":
            txn = request.form.get("transaction_ref", "").strip()
            if len(txn) < 4:
                flash("Enter your UPI/bank transaction reference after making the payment.", "error")
            else:
                import uuid
                receipt = "HNA-" + uuid.uuid4().hex[:10].upper()
                cur = db.execute("INSERT INTO payment_orders(receipt_no,user_id,lesson_id,item_type,amount,transaction_ref,status) VALUES(?,?,?,?,?,?, 'pending')",
                                 (receipt, session["user_id"], lesson_id, item_type, amount, txn))
                return redirect(url_for("payment_receipt", order_id=cur.lastrowid))
    with get_db() as db:
        settings = {r["key"]: r["value"] for r in db.execute("SELECT key,value FROM academy_settings").fetchall()}
    upi_id = settings.get("upi_id", "jip930031-1@oksbi")
    upi_name = settings.get("upi_name", "Himanshu NextGen Academy")
    return render_template("payment.html", lesson=lesson, item_type=item_type, amount=amount, upi_id=upi_id, upi_name=upi_name)

@app.route("/payments")
@login_required
def payments():
    with get_db() as db:
        orders = db.execute("""SELECT p.*, l.title AS lesson_title FROM payment_orders p
                              JOIN lessons l ON l.id=p.lesson_id
                              WHERE p.user_id=? ORDER BY p.created_at DESC""", (session["user_id"],)).fetchall()
    return render_template("payments.html", orders=orders)

@app.route("/receipt/<int:order_id>")
@login_required
def payment_receipt(order_id):
    with get_db() as db:
        order = db.execute("SELECT p.*, u.name AS student_name, u.email, u.phone, l.title AS lesson_title FROM payment_orders p JOIN users u ON u.id=p.user_id JOIN lessons l ON l.id=p.lesson_id WHERE p.id=?", (order_id,)).fetchone()
        if not order:
            abort(404)
        if order["user_id"] != session.get("user_id") and session.get("role") != "admin":
            abort(403)
    return render_template("receipt.html", order=order)

@app.route("/admin/payment/<int:order_id>/approve", methods=["POST"])
@admin_required
def approve_payment(order_id):
    with get_db() as db:
        order = db.execute("SELECT * FROM payment_orders WHERE id=?", (order_id,)).fetchone()
        if not order:
            abort(404)
        db.execute("UPDATE payment_orders SET status='paid', paid_at=CURRENT_TIMESTAMP WHERE id=?", (order_id,))
        course_row = db.execute("SELECT c.id,c.title,c.price FROM lessons l JOIN courses c ON c.id=l.course_id WHERE l.id=?", (order['lesson_id'],)).fetchone()
        if course_row and course_row['title'] == 'Basic Computer — WordPad Tutorials' and abs(float(order['amount']) - float(course_row['price'])) < 0.01:
            db.execute("INSERT OR IGNORE INTO enrollments(user_id,course_id,status) VALUES(?,?,'active')", (order['user_id'], course_row['id']))
    flash("Payment verified and approved. Course access is now enabled.", "success")
    return redirect(url_for("admin_dashboard") + "#payments")

@app.errorhandler(403)
def forbidden(_):
    return render_template("error.html", code=403, message="You don't have permission to view this page."), 403

@app.errorhandler(404)
def not_found(_):
    return render_template("error.html", code=404, message="The page or course you requested could not be found."), 404

init_db()

if __name__ == "__main__":
    app.run(debug=True)
