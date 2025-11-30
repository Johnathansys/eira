from flask import Flask, render_template, request, session, redirect, url_for
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "random"  # Secret key for sessions

DATABASE = "userdata.db"



def get_db_connection():
    """Returns a new database connection."""
    # check_same_thread=False is needed for SQLite to work correctly with Flask's
    # multi-threaded development server. For production, consider using a connection pool
    # and a more robust database like PostgreSQL or MySQL.
    conn = sqlite3.connect(DATABASE, check_same_thread=False)
    conn.row_factory = sqlite3.Row # Allows accessing columns by name
    return conn

def init_db():
    """Initializes the database and creates the User table."""
    conn = get_db_connection()
    cur = conn.cursor()
    # Updated table schema: password stores a hash, requiring more space (VARCHAR(128))
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



# --- Routing ---

# Route for the Home/Index page (The main landing page)
@app.route('/', methods=["GET"])
def index():
    # Corrected template path to just the filename
    if "Username" in session:
        return redirect(url_for("welcome"))
    return render_template("index.html")

# Route for the Welcome page (if logged in)
@app.route("/welcome", methods=["GET"])
def welcome():
    if "Username" in session:
        return render_template("welcome.html", username=session["Username"])
    else:
        # Use url_for for better path handling
        return redirect(url_for("login"))

# Route for the Sign Up page
@app.route('/signup', methods=["GET", "POST"])
def signup():
    message = None
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if not username or not password:
            message = "Both username and password are required."
        else:
            # 1. Hash the password before storage for security
            password_hash = generate_password_hash(password)

            conn = get_db_connection()
            cur = conn.cursor()
            try:
                # 2. Store the hashed password
                cur.execute("INSERT INTO User (username, password) VALUES (?, ?)",
                            (username, password_hash))
                conn.commit()
                # Redirect to the login page after successful signup
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                message = "Username already exists. Please choose a different one."
            except Exception as e:
                message = f"An unexpected error occurred during signup: {e}"
            finally:
                conn.close()

    return render_template("signup.html", message=message)

# Route for the Login page (COMPLETED and SECURED)
@app.route('/login', methods=["GET","POST"])
def login():
    message = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_db_connection()
        cur = conn.cursor()
        
        # Retrieve the user record, including the stored password hash
        user_data = cur.execute("SELECT username, password FROM User WHERE username = ?", (username,)).fetchone()
        conn.close()

        if user_data:
            stored_hash = user_data["password"]
            # 3. Use check_password_hash to verify the password securely
            if check_password_hash(stored_hash, password):
                session["Username"] = user_data["username"] # Set session for successful login
                return redirect(url_for("welcome"))
            else:
                message = "Invalid username or password."
        else:
            message = "Invalid username or password."
    
    # Corrected template path to just the filename
    return render_template("login.html", message=message)

# New Route for Logout
@app.route('/logout')
def logout():
    session.pop('Username', None) # Remove the username from the session
    return redirect(url_for("index")) # Redirect to the index page

if __name__ == "__main__":
    # Remove debug=True for production
    app.run(debug=True)