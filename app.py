from flask import Flask, render_template, request, session, redirect, url_for
import sqlite3

app = Flask(__name__)
app.secret_key = "random"  # Secret key for sessions

# Initialize database and table if not exists
con = sqlite3.connect("userdata.db", check_same_thread=False)
cur = con.cursor()
cur.execute("""
            CREATE TABLE IF NOT EXISTS User
            (
            username VARCHAR(20) NOT NULL PRIMARY KEY,
            password VARCHAR(64) NOT NULL
            )
        """)
con.commit()
con.close()

# Route for the Home (Login) page
@app.route('/', methods=["GET", "POST"])
def home():
    if "Username" in session:
        return render_template("/welcome.html")  # If logged in, go to welcome page
    else:
        return render_template("/index.html")  # Show login page if not logged in

# Route for the Welcome page (if logged in)
@app.route("/welcome", methods=["GET"])
def welcome():
    if "Username" in session:
        return render_template("/welcome.html")  # Show the welcome page if logged in
    else:
        return redirect("/login.html")  # Redirect to home (login page) if not logged in

# Route for the Sign Up page
@app.route('/signup', methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("/signup.html")  # Render the signup form
    else:
        con = sqlite3.connect("userdata.db")
        cur = con.cursor()
        cur.execute("INSERT INTO User (username, password) VALUES (?, ?)",
                    (request.form["username"], request.form["password"]))  # No hashing for now
        con.commit()
        con.close()
        return redirect("/login.html")  # Redirect to the login page after successful signup

# Route for the Login page
@app.route('/login', methods=["GET","POST"])
def login():
    if request.method == "GET":
        return render_template("/login.html")  # Render the login form
    else:
        con = sqlite3.connect("userdata.db")
        cur = con.cursor()
        cur.execute("SELECT * FROM User WHERE username = ? AND password = ?",
                    (request.form["username"], request.form["password"]))  # No hashing for now
        data = cur.fetchall()
        con.commit()
        con.close()


if __name__ == "__main__":
    app.run(debug=True)
