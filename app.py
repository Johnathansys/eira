from flask import Flask, render_template, request, session, redirect, url_for
import sqlite3
import hashlib

app = Flask(__name__)
app.secret_key = "random"  # Secret key for sessions

@app.route("/home")
def home():
    return render_template('index.html')

@app.route("/welcome")
def welcome():
    if "Username" in session:
        return render_template("welcome.html")
    else:
        return redirect("/")  # Redirect to home if not logged in

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

@app.route('/', methods=["GET", "POST"])
def home():
    if "Username" in session:
        return render_template("welcome.html")  # If logged in, go to welcome page
    else:
        return render_template("index.html")  # Show login page if not logged in

# Route for the Sign Up page
@app.route('/signup', methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")  # Render the signup form
    else:
        con = sqlite3.connect("userdata.db")
        cur = con.cursor()
        hashed = hashlib.sha256(request.form["Password"].encode()).hexdigest()
        cur.execute("INSERT INTO User (username, password) VALUES (?, ?)",
                    (request.form["Username"], hashed))
        con.commit()
        con.close()
        return redirect("/")  # Redirect to the login page after successful signup

# Route for the Login page
@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")  # Render the login form
    else:
        con = sqlite3.connect("userdata.db")
        cur = con.cursor()
        hashed = hashlib.sha256(request.form["Password"].encode()).hexdigest()
        cur.execute("SELECT * FROM User WHERE username = ? AND password = ?",
                    (request.form["Username"], hashed))
        data = cur.fetchall()
        con.commit()
        con.close()
        if len(data) == 0:
            return "Login Unsuccessful. Try again."
        else:
            session["Username"] = request.form["Username"]
            return render_template("welcome.html")

@app.route("/password", methods=["GET", "POST"])
def password():
    if "Username" in session:
        if request.method == "POST":
            con = sqlite3.connect("userdata.db")
            cur = con.cursor()
            hashed = hashlib.sha256(request.form["Password"].encode()).hexdigest()
            cur.execute("UPDATE User SET password = ? WHERE username = ?",
                        (hashed, session["Username"]))
            con.commit()
            con.close()
            return "Password Updated"
        return render_template("change_password.html")
    return redirect("/")

@app.route("/logout")
def logout():
    session.pop("Username", None)
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)