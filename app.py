from flask import Flask, render_template, request, session, redirect, url_for
import sqlite3
import hashlib

#initialising a database
def init_db():
    conn = sqlite3.connect('database.db')
    cursor=conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS journal(
                   id INTEGER PRIMARY KEY AUTOINCREMENT
                   entry TEXT NOT NULL
                   date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)'''
    )
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/resources')
def resources():
    return render_template('resources.html')

@app.route('/journal', methods=['GET','POST'])
def journal():
    if request.method == 'POST':
        entry = request.form['entry']
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO journal (entry) VALUES (?)", (entry,))
        conn.commit()
        conn.close()
        return redirect(url_for('journal'))
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM journal ORDER BY date DESC")
    entries = cursor.fetchall()
    conn.close()
    return render_template('journal.html', entries=entries)

