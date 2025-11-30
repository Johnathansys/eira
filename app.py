from flask import Flask, render_template, request, session, redirect, url_for
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime 

app = Flask(__name__)
app.secret_key = "a_strong_and_unique_key_for_eira_app"

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
    
    # 1. User Table (Existing)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS User
        (
            username VARCHAR(20) NOT NULL PRIMARY KEY,
            password VARCHAR(128) NOT NULL
        )
    """)
    
    # 2. Journal Table (NEW)
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
                return render_template("login.html") 
        else:
            return render_template("login.html")
        
    return render_template("login.html")

# --- Journal Entry Route ---
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

# --- Journal History Route ---
@app.route('/history', methods=["GET"])
def history():
    if not is_logged_in():
        return redirect(url_for("index"))

    username = session["Username"]
    conn = get_db_connection()
    # Fetch all entries for the logged-in user, ordered by timestamp descending
    entries = conn.execute("SELECT id, title, strftime('%Y-%m-%d %H:%M', timestamp) AS timestamp FROM Journal WHERE user_username = ? ORDER BY timestamp DESC", 
                            (username,)).fetchall()
    conn.close()

    return render_template("history.html", entries=entries)

# --- View Specific Entry Route ---
@app.route('/entry/<int:entry_id>', methods=["GET"])
def view_entry(entry_id):
    if not is_logged_in():
        return redirect(url_for("index"))

    username = session["Username"]
    conn = get_db_connection()
    # Fetch the specific entry, ensuring it belongs to the logged-in user
    entry = conn.execute("SELECT id, title, content, strftime('%Y-%m-%d %H:%M:%S', timestamp) AS timestamp FROM Journal WHERE id = ? AND user_username = ?", 
                          (entry_id, username)).fetchone()
    conn.close()

    if entry is None:
        return "Entry not found.", 404

    return render_template("view_entry.html", entry=entry)

# --- Delete Entry Route ---
@app.route('/delete/<int:entry_id>', methods=["POST"])
def delete_entry(entry_id):
    if not is_logged_in():
        return redirect(url_for("index"))

    username = session["Username"]
    conn = get_db_connection()
    
    # Check if the entry exists and belongs to the user, then delete it
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