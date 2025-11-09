from flask import Flask, render_template, request, session, redirect, url_for
import sqlite3
import hashlib


app = Flask(__name__)
app.secret_key = "random"
con = sqlite3.connect("userdata.db")
cur = con.cursor()
cur.execute("""
            CREATE TABLE IF NOT EXISTS User
            (
            username VARCHAR(20) NOT NULL PRIMARY KEY,
            password VARCHAR(64) NOT NULL
            )
        """)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("signup.html")
    else:
        con = sqlite3.connect("userdata.db")
        cur = con.cursor()
        encoded= request.form["Password"].encode()
        hash=hashlib.sha256(encoded).hexdigest()
        print(hash)
        cur.execute("INSERT INTO User (username, password) VALUES (?, ?)",
                        (request.form["Username"], hash))
        con.commit()
        con.close()
    return "Signup Sucessful"
    
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("index.html")
    else:
        con = sqlite3.connect("userdata.db")
        cur = con.cursor()
        hash= hashlib.sha256(request.form["Password"].encode()).hexdigest()
        cur.execute("SELECT * FROM User WHERE username = ? and password = ?",
                        (request.form["Username"], hash))
        data = cur.fetchall()
        con.commit()
        con.close()
        if len(data) == 0:
            return "Login Unsucessful"
        else:
            session["Username"] = request.form["Username"]
            return render_template("welcome.html")

@app.route("/w")
def welcome():
    return render_template("welcome.html")

@app.route("/password")
def password():
    if request.method == "GET":    
        if "Username" in session:
            return render_template("change_password.html")
        else:
            return render_template("index.html")
    else:
        if "Username" in session:
            con = sqlite3.connect("userdata.db")
            cur = con.cursor()
            hash= hashlib.sha256(request.form["Password"].encode()).hexdigest()
            cur.execute("UPDATE User SET Password = ? WHERE Username = ?",
                            (hash, session["Username"]))
            con.commit()
            con.close()
            return "Password Updated"
        else:
            return render_template("index.html")

@app.route("/logout")
def logout():
    session.pop("Username", None)
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)