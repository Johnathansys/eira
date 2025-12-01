from flask import Flask, render_template, request, session, redirect, url_for
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import calendar 
import os # Ensure os is imported

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "a_strong_and_unique_key_for_eira_app")

DATABASE = "userdata.db"

def get_db_connection():
    """Returns a new database connection."""
    conn = sqlite3.connect(DATABASE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database and creates the User and Journal tables."""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # User Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS User
        (
            username VARCHAR(20) NOT NULL PRIMARY KEY,
            password VARCHAR(128) NOT NULL
        )
    """)
    
    # Journal Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Journal
        (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_username VARCHAR(20) NOT NULL,
            title VARCHAR(100) NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_username) REFERENCES User(username)
        )
    """)
    
    conn.commit()
    conn.close()

init_db()

# Helper function to check login status
def is_logged_in():
    return "Username" in session

# --- Routes ---

# Route for the Home/Index page
@app.route('/', methods=["GET"])
def index():
    if is_logged_in():
        return redirect(url_for("dashboard"))
    return render_template("index.html")

# --- Dashboard Route ---
@app.route("/dashboard", methods=["GET"])
def dashboard():
    if is_logged_in():
        return render_template("dashboard.html", username=session["Username"])
    else:
        return redirect(url_for("index"))

# Route for the Sign Up page
@app.route('/signup', methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if not username or not password:
            return render_template("signup.html")

        password_hash = generate_password_hash(password)

        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO User (username, password) VALUES (?, ?)",
                        (username, password_hash))
            conn.commit()
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            # Add error handling or flash message here if username exists
            return render_template("signup.html")
        finally:
            conn.close()

    return render_template("signup.html")

# Route for the Login page
@app.route('/login', methods=["GET","POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_db_connection()
        user_data = conn.execute("SELECT username, password FROM User WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user_data:
            stored_hash = user_data["password"]
            if check_password_hash(stored_hash, password):
                session["Username"] = user_data["username"] 
                return redirect(url_for("dashboard")) 
            else:
                # Add error handling or flash message for wrong password
                return render_template("login.html") 
        else:
            # Add error handling or flash message for user not found
            return render_template("login.html")
        
    return render_template("login.html")

# --- Calendar Route (IMPROVED) ---
@app.route("/calendar", methods=["GET"])
def calendar_view():
    if not is_logged_in():
        return redirect(url_for("index"))

    username = session["Username"]
    
    # Determine the current month/year to display
    try:
        current_year = int(request.args.get('year', datetime.now().year))
        current_month = int(request.args.get('month', datetime.now().month))
        # Basic validation to ensure month is 1-12
        if not 1 <= current_month <= 12:
            raise ValueError
    except ValueError:
        current_year = datetime.now().year
        current_month = datetime.now().month

    # Calculate previous and next months using datetime for simplicity
    first_day_of_month = datetime(current_year, current_month, 1)
    
    # Calculate prev month: go back one day from the 1st of the current month
    prev_dt = first_day_of_month - timedelta(days=1)
    # Calculate next month: go forward roughly 32 days from the 1st of the current month
    next_dt = first_day_of_month + timedelta(days=32)
    next_dt = datetime(next_dt.year, next_dt.month, 1)


    # 2. Get entries for the current month
    conn = get_db_connection()
    # SQL query to fetch distinct dates that have entries in the current month
    sql = """
    SELECT DISTINCT strftime('%Y-%m-%d', timestamp) AS entry_date 
    FROM Journal 
    WHERE user_username = ? 
    AND strftime('%Y-%m', timestamp) = ?
    """
    
    month_filter = f"{current_year}-{current_month:02d}"
    entries = conn.execute(sql, (username, month_filter)).fetchall()
    conn.close()
    
    # Convert list of rows into a dictionary for fast lookup in the template
    entries_by_date = {row['entry_date']: True for row in entries}

    # 3. Generate calendar data
    cal = calendar.Calendar(firstweekday=calendar.SUNDAY) # Set calendar to start on Sunday
    
    # monthdayscalendar returns a list of lists (weeks), where days are integers (1-31) or 0
    month_days = cal.monthdayscalendar(current_year, current_month)
    
    # Flatten the list and replace 0s with None for template processing
    calendar_days = [day if day != 0 else None for week in month_days for day in week]

    return render_template("calendar.html", 
                           calendar_days=calendar_days,
                           entries_by_date=entries_by_date,
                           current_month=current_month,
                           current_year=current_year,
                           month_name=calendar.month_name[current_month],
                           prev_month={'year': prev_dt.year, 'month': prev_dt.month},
                           next_month={'year': next_dt.year, 'month': next_dt.month})

# --- Journal Entry Route (remains unchanged) ---
@app.route('/journal_entry', methods=["GET", "POST"])
def journal_entry():
    if not is_logged_in():
        return redirect(url_for("index"))

    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        username = session["Username"]
        
        if not title or not content:
            return render_template("journal_entry.html")
        
        conn = get_db_connection()
        try:
            conn.execute("INSERT INTO Journal (user_username, title, content) VALUES (?, ?, ?)",
                         (username, title, content))
            conn.commit()
            return redirect(url_for("history")) 
        except Exception as e:
            print(f"Database error on journal entry: {e}")
            return "An error occurred while saving the entry.", 500
        finally:
            conn.close()

    return render_template("journal_entry.html")

# --- Journal History Route (MODIFIED to accept date filter) ---
@app.route('/history', methods=["GET"])
def history():
    if not is_logged_in():
        return redirect(url_for("index"))

    username = session["Username"]
    date_filter = request.args.get('date') # Get optional date filter from URL (?date=YYYY-MM-DD)
    
    conn = get_db_connection()
    
    if date_filter:
        # Filter by a specific date (e.g., from the calendar click)
        sql = """
        SELECT id, title, strftime('%Y-%m-%d %H:%M', timestamp) AS timestamp 
        FROM Journal 
        WHERE user_username = ? AND strftime('%Y-%m-%d', timestamp) = ?
        ORDER BY timestamp DESC
        """
        entries = conn.execute(sql, (username, date_filter)).fetchall()
        page_title = f"Entries for {date_filter}"
    else:
        # Default: Fetch all entries
        sql = """
        SELECT id, title, strftime('%Y-%m-%d %H:%M', timestamp) AS timestamp 
        FROM Journal 
        WHERE user_username = ? 
        ORDER BY timestamp DESC
        """
        entries = conn.execute(sql, (username,)).fetchall()
        page_title = "Your Journal History"

    conn.close()

    return render_template("history.html", entries=entries, page_title=page_title)

# --- View Specific Entry Route (remains unchanged) ---
@app.route('/entry/<int:entry_id>', methods=["GET"])
def view_entry(entry_id):
    if not is_logged_in():
        return redirect(url_for("index"))

    username = session["Username"]
    conn = get_db_connection()
    entry = conn.execute("SELECT id, title, content, strftime('%Y-%m-%d %H:%M:%S', timestamp) AS timestamp FROM Journal WHERE id = ? AND user_username = ?", 
                          (entry_id, username)).fetchone()
    conn.close()

    if entry is None:
        return "Entry not found.", 404

    return render_template("view_entry.html", entry=entry)

# --- Delete Entry Route (remains unchanged) ---
@app.route('/delete/<int:entry_id>', methods=["POST"])
def delete_entry(entry_id):
    if not is_logged_in():
        return redirect(url_for("index"))

    username = session["Username"]
    conn = get_db_connection()
    
    cursor = conn.execute("DELETE FROM Journal WHERE id = ? AND user_username = ?", (entry_id, username))
    conn.commit()
    conn.close()

    if cursor.rowcount > 0:
        return redirect(url_for("history")) 
    else:
        return "Error deleting entry or entry not found.", 404

# Route for Logout
@app.route('/logout')
def logout():
    session.pop('Username', None)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)