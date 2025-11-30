from flask import Flask, render_template, request, session, redirect, url_for
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# IMPORTANT: This secret key is necessary for session security.
app.secret_key = "a_strong_and_unique_key_for_eira_app"

DATABASE = "userdata.db"

def get_db_connection():
    """Returns a new database connection."""
    # check_same_thread=False is used for development purposes
    conn = sqlite3.connect(DATABASE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database and creates the User table."""
    conn = get_db_connection()
    cur = conn.cursor()
    # Stores password hash (VARCHAR(128))
    cur.execute("""
            CREATE TABLE IF NOT EXISTS User
            (
            username VARCHAR(20) NOT NULL PRIMARY KEY,
            password VARCHAR(128) NOT NULL
            )
        """)
    conn.commit()
    conn.close()

# Initialize the database when the app starts
init_db()

# --- Routes ---

# Route for the Home/Index page
@app.route('/', methods=["GET"])
def index():
    # If logged in, redirect to the personalized welcome page
    if "Username" in session:
        return redirect(url_for("welcome"))
    # If not logged in, show the generic index page
    return render_template("index.html")

# Route for the Welcome page (Logged In Home)
@app.route("/welcome", methods=["GET"])
def welcome():
    # Check session to ensure the user is logged in
    if "Username" in session:
        # Pass the username. Note: The HTML template will use a placeholder
        # since it is pure static HTML without Jinja templating.
        return render_template("welcome.html", username=session["Username"])
    else:
        # Redirect if session is missing
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
            # Redirect to login page upon success
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            # Username already exists
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
                session["Username"] = user_data["username"] # Set session
                return redirect(url_for("welcome"))
            else:
                # Invalid password
                return render_template("login.html")
        else:
            # User not found
            return render_template("login.html")
    
    return render_template("login.html")

# Route for Logout
@app.route('/logout')
def logout():
    session.pop('Username', None)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)