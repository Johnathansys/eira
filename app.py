from flask import Flask, render_template, request, session, redirect, url_for, flash
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import calendar
import secrets
import random

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "a_strong_and_unique_key_for_eira_app")
DATABASE = "userdata.db"

def get_db_connection():
    """Returns a new database connection."""
    conn = sqlite3.connect(DATABASE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database and creates all necessary tables."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # User Table (updated with email)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS User
        (
            username VARCHAR(20) NOT NULL PRIMARY KEY,
            password VARCHAR(128) NOT NULL,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    
    # Journal Table with mood_rating
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS Journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_username VARCHAR(20) NOT NULL,
            title VARCHAR(100) NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            sleep_hours FLOAT,
            mood TEXT,
            mood_rating REAL,
            tags TEXT,
            FOREIGN KEY (user_username) REFERENCES User(username) ON DELETE CASCADE
        )
        """
    )
    
    # Resources Table (for recommendations)
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS Resources
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            description TEXT,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    
    # Password Reset Tokens Table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS PasswordResetTokens
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(20) NOT NULL,
            token TEXT NOT NULL UNIQUE,
            expiry TIMESTAMP NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES User(username) ON DELETE CASCADE
        )
        """
    )
    
    conn.commit()
    
    # Insert sample resources if table is empty
    count = conn.execute("SELECT COUNT(*) FROM Resources").fetchone()[0]
    if count == 0:
        sample_resources = [
            # Depression support resources
            ("depression_support", "National Suicide Prevention Lifeline", "https://988lifeline.org/", "24/7 crisis support", "crisis,depression"),
            ("depression_support", "SAMHSA National Helpline", "https://www.samhsa.gov/find-help/national-helpline", "Free, confidential, 24/7 treatment referral", "support,depression"),
            
            # Crisis helpline
            ("crisis_helpline", "Crisis Text Line", "https://www.crisistextline.org/", "Text HOME to 741741 for 24/7 crisis support", "crisis,text"),
            ("crisis_helpline", "988 Suicide & Crisis Lifeline", "https://988lifeline.org/", "Call or text 988 for immediate help", "crisis,suicide"),
            
            # Stress management
            ("stress_management", "Headspace: Stress Management", "https://www.headspace.com/stress", "Guided meditation for stress relief", "stress,meditation"),
            ("stress_management", "Mayo Clinic: Stress Relief", "https://www.mayoclinic.org/healthy-lifestyle/stress-management", "Science-based stress reduction techniques", "stress,health"),
            ("stress_management", "APA: Stress Management Tips", "https://www.apa.org/topics/stress/tips", "Psychological tips for managing stress", "stress,psychology"),
            
            # Motivation
            ("motivation", "TED: How to Stay Motivated", "https://www.ted.com/topics/motivation", "Inspiring talks on motivation", "motivation,inspiration"),
            ("motivation", "Tiny Habits by BJ Fogg", "https://tinyhabits.com/", "Build motivation through small wins", "motivation,habits"),
            
            # Sleep hygiene
            ("sleep_hygiene", "Sleep Foundation", "https://www.sleepfoundation.org/sleep-hygiene", "Evidence-based sleep improvement tips", "sleep,health"),
            ("sleep_hygiene", "CDC: Sleep Hygiene Tips", "https://www.cdc.gov/sleep/about_sleep/sleep_hygiene.html", "Healthy sleep habits", "sleep,hygiene"),
            ("sleep_hygiene", "Calm: Sleep Stories", "https://www.calm.com/sleep-stories", "Relaxing bedtime stories", "sleep,meditation"),
            
            # Relaxation techniques
            ("relaxation_techniques", "4-7-8 Breathing Exercise", "https://www.drweil.com/health-wellness/body-mind-spirit/stress-anxiety/breathing-three-exercises/", "Simple breathing for relaxation", "breathing,relaxation"),
            ("relaxation_techniques", "Progressive Muscle Relaxation", "https://www.anxietycanada.com/articles/progressive-muscle-relaxation/", "Physical relaxation technique", "relaxation,anxiety"),
            
            # General wellness
            ("general_wellness", "MindTools: Wellbeing Resources", "https://www.mindtools.com/pages/main/newMN_TCS.htm", "Mental wellness strategies", "wellness,mental-health"),
            ("general_wellness", "Mental Health America", "https://www.mhanational.org/", "Mental health information and support", "wellness,support"),
            
            # Gratitude exercises
            ("gratitude_exercises", "Greater Good Science Center: Gratitude", "https://greatergood.berkeley.edu/topic/gratitude", "Science of gratitude", "gratitude,positive"),
            ("gratitude_exercises", "5-Minute Gratitude Journal", "https://www.intelligentchange.com/blogs/read/gratitude-journal-prompts", "Daily gratitude prompts", "gratitude,journal"),
            
            # Positive psychology
            ("positive_psychology", "Positive Psychology Center", "https://ppc.sas.upenn.edu/", "Research-based positive psychology", "positive,psychology"),
            ("positive_psychology", "Action for Happiness", "https://actionforhappiness.org/", "Evidence-based actions for happiness", "positive,happiness"),
            
            # Energy boosting
            ("energy_boosting", "Natural Energy Boosters", "https://www.health.harvard.edu/staying-healthy/9-tips-to-boost-your-energy-naturally", "Science-backed energy tips", "energy,health"),
            ("energy_boosting", "Movement for Energy", "https://www.mayoclinic.org/healthy-lifestyle/fitness/in-depth/exercise/art-20048389", "Exercise for better energy", "energy,exercise"),
        ]
        
        for resource in sample_resources:
            conn.execute(
                "INSERT INTO Resources (category, title, url, description, tags) VALUES (?, ?, ?, ?, ?)",
                resource
            )
        conn.commit()
    
    conn.close()

init_db()

# Helper function to check login status
def is_logged_in():
    return "Username" in session


def get_resource_recommendations(mood_rating, sleep_hours):
    """
    Rule-based recommendation system.
    Returns list of recommended resources based on mood and sleep.
    """
    conn = get_db_connection()
    recommended_categories = []
    
    # Analyze mood
    if mood_rating <= 3:
        recommended_categories.extend(["depression_support", "crisis_helpline"])
    elif mood_rating <= 5:
        recommended_categories.extend(["stress_management", "motivation"])
    elif mood_rating <= 7:
        recommended_categories.append("general_wellness")
    else:
        recommended_categories.extend(["gratitude_exercises", "positive_psychology"])
    
    # Analyze sleep
    if sleep_hours < 5:
        recommended_categories.extend(["sleep_hygiene", "relaxation_techniques"])
    elif sleep_hours > 10:
        recommended_categories.extend(["energy_boosting", "sleep_hygiene"])
    
    # Remove duplicates
    recommended_categories = list(set(recommended_categories))
    
    # Fetch resources
    resources = []
    for category in recommended_categories:
        category_resources = conn.execute(
            """
            SELECT title, url, description, category 
            FROM Resources 
            WHERE category = ? 
            ORDER BY RANDOM() 
            LIMIT 2
            """,
            (category,)
        ).fetchall()
        resources.extend(category_resources)
    
    conn.close()
    
    # Limit to 6 total recommendations
    if len(resources) > 6:
        resources = random.sample(resources, 6)
    
    return resources


# --- Routes ---

@app.route("/", methods=["GET"])
def index():
    if is_logged_in():
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/dashboard", methods=["GET"])
def dashboard():
    if is_logged_in():
        username = session["Username"]
        conn = get_db_connection()
        
        # Get last 10 mood ratings for chart
        recent_entries = conn.execute(
            """
            SELECT strftime('%Y-%m-%d', timestamp) as timestamp, mood_rating
            FROM Journal 
            WHERE user_username = ? 
            ORDER BY timestamp DESC 
            LIMIT 10
            """,
            (username,),
        ).fetchall()
        
        recent_dates = [entry["timestamp"] for entry in recent_entries]
        recent_moods = [
            float(entry["mood_rating"]) if entry["mood_rating"] else 5.0
            for entry in recent_entries
        ]

        # NEW: get the most recent mood rating for "current mood"
        latest_entry = conn.execute(
            """
            SELECT mood_rating
            FROM Journal
            WHERE user_username = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (username,)
        ).fetchone()

        if latest_entry and latest_entry["mood_rating"] is not None:
            current_mood = float(latest_entry["mood_rating"])
        else:
            # Fallback if no entries exist yet
            current_mood = None  # or 5.0 as a neutral default

        # Check if user has completed today's check-in
        today = datetime.now().strftime('%Y-%m-%d')
        todays_checkin = conn.execute(
            "SELECT id FROM Journal WHERE user_username = ? AND timestamp = ?",
            (username, today)
        ).fetchone()
        
        conn.close()
        
        return render_template(
            "dashboard.html",
            username=username,
            recent_dates=recent_dates,
            recent_moods=recent_moods,
            checkin_complete=todays_checkin is not None,
            current_mood=current_mood,      # ⬅ pass to template
        )
    else:
        return redirect(url_for("index"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        email = request.form.get("email", "")
        
        if not username or not password:
            flash("Username and password are required", "error")
            return render_template("signup.html")
        
        if len(password) < 4:
            flash("Password must be at least 4 characters", "error")
            return render_template("signup.html")
        
        password_hash = generate_password_hash(password)
        
        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO User (username, password, email) VALUES (?, ?, ?)",
                (username, password_hash, email),
            )
            conn.commit()
            flash("Account created successfully! Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already exists", "error")
            return render_template("signup.html")
        finally:
            conn.close()
    
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        conn = get_db_connection()
        user_data = conn.execute(
            "SELECT username, password FROM User WHERE username = ?", (username,)
        ).fetchone()
        conn.close()
        
        if user_data:
            stored_hash = user_data["password"]
            if check_password_hash(stored_hash, password):
                session["Username"] = user_data["username"]
                flash(f"Welcome back, {username}!", "success")
                return redirect(url_for("dashboard"))
            else:
                flash("Invalid username or password", "error")
                return render_template("login.html")
        else:
            flash("Invalid username or password", "error")
            return render_template("login.html")
    
    return render_template("login.html")


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Initiate password reset process"""
    if request.method == "POST":
        username = request.form.get("username")
        
        conn = get_db_connection()
        user = conn.execute("SELECT username, email FROM User WHERE username = ?", (username,)).fetchone()
        
        if user:
            # Generate secure token
            token = secrets.token_urlsafe(32)
            expiry = datetime.now() + timedelta(hours=1)
            
            # Store token in database
            conn.execute(
                "INSERT INTO PasswordResetTokens (username, token, expiry) VALUES (?, ?, ?)",
                (username, token, expiry)
            )
            conn.commit()
            
            # In a real app, you would send an email here
            # For NEA purposes, we'll display the reset link
            reset_url = url_for('reset_password', token=token, _external=True)
            flash(f"Password reset link generated: {reset_url}", "info")
            flash("(In production, this would be emailed to you)", "info")
        else:
            # Don't reveal whether username exists (security)
            flash("If that username exists, a reset link has been sent", "info")
        
        conn.close()
        return redirect(url_for("login"))
    
    return render_template("forgot_password.html")


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Complete password reset with token"""
    if request.method == "POST":
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")
        
        if new_password != confirm_password:
            flash("Passwords do not match", "error")
            return render_template("reset_password.html", token=token)
        
        if len(new_password) < 8:
            flash("Password must be at least 8 characters", "error")
            return render_template("reset_password.html", token=token)
        
        conn = get_db_connection()
        
        # Validate token
        reset_request = conn.execute(
            "SELECT username, expiry FROM PasswordResetTokens WHERE token = ? AND used = 0",
            (token,)
        ).fetchone()
        
        if not reset_request:
            flash("Invalid or expired reset link", "error")
            conn.close()
            return redirect(url_for("login"))
        
        # Check expiry
        expiry_time = datetime.strptime(reset_request["expiry"], '%Y-%m-%d %H:%M:%S.%f')
        if expiry_time < datetime.now():
            flash("Reset link has expired", "error")
            conn.close()
            return redirect(url_for("forgot_password"))
        
        # Update password
        password_hash = generate_password_hash(new_password)
        conn.execute(
            "UPDATE User SET password = ? WHERE username = ?",
            (password_hash, reset_request["username"])
        )
        
        # Mark token as used
        conn.execute(
            "UPDATE PasswordResetTokens SET used = 1 WHERE token = ?",
            (token,)
        )
        
        conn.commit()
        conn.close()
        
        flash("Password reset successfully! Please log in.", "success")
        return redirect(url_for("login"))
    
    # GET request - show reset form
    return render_template("reset_password.html", token=token)


@app.route("/daily-checkin", methods=["GET", "POST"])
def daily_checkin():
    """Daily mood check-in with recommendations"""
    if not is_logged_in():
        return redirect(url_for("index"))
    
    username = session["Username"]
    today = datetime.now().strftime('%Y-%m-%d')
    
    if request.method == "POST":
        mood_rating = float(request.form.get("mood_rating", 5.0))
        sleep_hours = int(request.form.get("sleep_hours", 7))
        notes = request.form.get("content", "")
        
        # Validate inputs
        if not (1 <= mood_rating <= 10):
            flash("Mood rating must be between 1 and 10", "error")
            return render_template("daily_checkin.html")
        
        if not (0 <= sleep_hours <= 24):
            flash("Sleep hours must be between 0 and 24", "error")
            return render_template("daily_checkin.html")
        
        conn = get_db_connection()
        
        # Check if entry already exists for today
        existing = conn.execute(
            "SELECT id FROM Journal WHERE user_username = ? AND timestamp = ?",
            (username, today)
        ).fetchone()
        
        if existing:
            # Update existing entry
            conn.execute(
                """
                UPDATE Journal 
                SET mood_rating = ?, sleep_hours = ?, content = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_username = ? AND timestamp = ?
                """,
                (mood_rating, sleep_hours, notes, username, today)
            )
            flash("Check-in updated successfully!", "success")
        else:
            # Insert new entry; decide on a title
            title = "Daily check-in"
            conn.execute(
                """
                INSERT INTO Journal (user_username, timestamp, mood_rating, sleep_hours, content, title)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (username, today, mood_rating, sleep_hours, notes, title)
            )
            flash("Check-in saved successfully!", "success")
            
        conn.commit()
        conn.close()
        
        # Get recommendations
        recommendations = get_resource_recommendations(mood_rating, sleep_hours)
        
        return render_template(
            "checkin_complete.html",
            mood_rating=mood_rating,
            sleep_hours=sleep_hours,
            recommendations=recommendations
        )
    
    # GET request - check if already completed today
    conn = get_db_connection()
    todays_entry = conn.execute(
        "SELECT mood_rating, sleep_hours, title FROM Journal WHERE user_username = ? AND timestamp = ?",
        (username, today)
    ).fetchone()
    conn.close()
    
    return render_template("daily_checkin.html", existing_entry=todays_entry)


@app.route("/delete-account", methods=["GET", "POST"])
def delete_account():
    """Allow users to delete their account (GDPR compliance)"""
    if not is_logged_in():
        return redirect(url_for("index"))
    
    username = session["Username"]
    
    if request.method == "POST":
        password_confirmation = request.form.get("password")
        
        # Verify password
        conn = get_db_connection()
        user = conn.execute(
            "SELECT password FROM User WHERE username = ?",
            (username,)
        ).fetchone()
        
        if not user or not check_password_hash(user["password"], password_confirmation):
            flash("Incorrect password", "error")
            conn.close()
            return render_template("delete_account.html")
        
        # Delete all user data (CASCADE should handle foreign keys)
        try:
            conn.execute("DELETE FROM User WHERE username = ?", (username,))
            conn.commit()
            
            # Clear session
            session.clear()
            
            flash("Account deleted successfully", "success")
            return redirect(url_for("index"))
        
        except Exception as e:
            conn.rollback()
            flash(f"Error deleting account: {str(e)}", "error")
            return render_template("delete_account.html")
        finally:
            conn.close()
    
    return render_template("delete_account.html")


@app.route("/calendar", methods=["GET"])
def calendar_view():
    if not is_logged_in():
        return redirect(url_for("index"))
    
    username = session["Username"]
    
    try:
        current_year = int(request.args.get("year", datetime.now().year))
        current_month = int(request.args.get("month", datetime.now().month))
        if not 1 <= current_month <= 12:
            raise ValueError
    except ValueError:
        current_year = datetime.now().year
        current_month = datetime.now().month
    
    first_day_of_month = datetime(current_year, current_month, 1)
    prev_dt = first_day_of_month - timedelta(days=1)
    next_dt = first_day_of_month + timedelta(days=32)
    next_dt = datetime(next_dt.year, next_dt.month, 1)
    
    conn = get_db_connection()
    sql = """
        SELECT DISTINCT strftime('%Y-%m-%d', timestamp) AS entry_date 
        FROM Journal 
        WHERE user_username = ? 
        AND strftime('%Y-%m', timestamp) = ?
    """
    month_filter = f"{current_year}-{current_month:02d}"
    entries = conn.execute(sql, (username, month_filter)).fetchall()
    conn.close()
    
    entries_by_date = {row["entry_date"]: True for row in entries}
    
    cal = calendar.Calendar(firstweekday=calendar.SUNDAY)
    month_days = cal.monthdayscalendar(current_year, current_month)
    calendar_days = [day if day != 0 else None for week in month_days for day in week]
    
    return render_template(
        "calendar.html",
        calendar_days=calendar_days,
        entries_by_date=entries_by_date,
        current_month=current_month,
        current_year=current_year,
        month_name=calendar.month_name[current_month],
        prev_month={"year": prev_dt.year, "month": prev_dt.month},
        next_month={"year": next_dt.year, "month": next_dt.month},
    )


@app.route("/journal_entry", methods=["GET", "POST"])
def journal_entry():
    """Create new journal entry with mood and tags."""
    if not is_logged_in():
        return redirect(url_for("index"))

    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        mood = request.form.get("mood") or None
        tags = request.form.get("tags") or None  # "school,friends" or empty
        username = session["Username"]

        if not title or not content:
            flash("Title and content are required", "error")
            return render_template("journal_entry.html")

        conn = get_db_connection()
        try:
            conn.execute(
                "INSERT INTO Journal (user_username, title, content, mood, tags) "
                "VALUES (?, ?, ?, ?, ?)",
                (username, title, content, mood, tags),
            )
            conn.commit()
            flash("Journal entry saved successfully!", "success")
            return redirect(url_for("history"))
        except Exception as e:
            print(f"Database error on journal entry: {e}")
            flash("An error occurred while saving the entry", "error")
            return render_template("journal_entry.html")
        finally:
            conn.close()

    return render_template("journal_entry.html")


@app.route("/history", methods=["GET"])
def history():
    if not is_logged_in():
        return redirect(url_for("index"))
    
    username = session["Username"]
    date_filter = request.args.get("timestamp")
    
    conn = get_db_connection()
    if date_filter:
        sql = """
            SELECT id, title, strftime('%Y-%m-%d %H:%M', timestamp) AS timestamp, mood, mood_rating
            FROM Journal 
            WHERE user_username = ? AND strftime('%Y-%m-%d', timestamp) = ?
            ORDER BY timestamp DESC
        """
        entries = conn.execute(sql, (username, date_filter)).fetchall()
        page_title = f"Entries for {date_filter}"
    else:
        sql = """
            SELECT id, title, strftime('%Y-%m-%d %H:%M', timestamp) AS timestamp, mood, mood_rating
            FROM Journal 
            WHERE user_username = ?
            ORDER BY timestamp DESC
        """
        entries = conn.execute(sql, (username,)).fetchall()
        page_title = "Your Journal History"
    
    conn.close()
    return render_template("history.html", entries=entries, page_title=page_title)


@app.route("/entry/<int:entry_id>", methods=["GET"])
def view_entry(entry_id):
    if not is_logged_in():
        return redirect(url_for("index"))
    
    username = session["Username"]
    conn = get_db_connection()
    entry = conn.execute(
        """
        SELECT id, title, content, strftime('%Y-%m-%d %H:%M:%S', timestamp) AS timestamp, 
               mood, mood_rating 
        FROM Journal WHERE id = ? AND user_username = ?
        """,
        (entry_id, username),
    ).fetchone()
    conn.close()
    
    if entry is None:
        flash("Entry not found", "error")
        return redirect(url_for("history"))
    
    return render_template("view_entry.html", entry=entry)


@app.route("/delete/<int:entry_id>", methods=["POST"])
def delete_entry(entry_id):
    if not is_logged_in():
        return redirect(url_for("index"))
    
    username = session["Username"]
    conn = get_db_connection()
    cursor = conn.execute(
        "DELETE FROM Journal WHERE id = ? AND user_username = ?", (entry_id, username)
    )
    conn.commit()
    conn.close()
    
    if cursor.rowcount > 0:
        flash("Entry deleted successfully", "success")
        return redirect(url_for("history"))
    else:
        flash("Error deleting entry or entry not found", "error")
        return redirect(url_for("history"))


@app.route('/ai_assistant')
def ai_assistant():
    if not is_logged_in():
        return redirect(url_for('login'))
    username = session["Username"]
    return render_template('ai_assistant.html', username=username)


@app.route("/logout")
def logout():
    session.pop("Username", None)
    flash("Logged out successfully", "success")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)
