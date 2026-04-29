from flask import Flask, render_template, request, redirect, session, flash, url_for
import sqlite3
import os
from werkzeug.utils import secure_filename
from flask import send_file
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
import datetime
import uuid
app = Flask(__name__)
app.secret_key = "secret123"
candidate_list=[]

# ---------------- DATABASE ----------------
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# ---------------- HOME ----------------
@app.route('/')
def home():

    conn = get_db()

    # total voters
    total_voters = conn.execute("SELECT COUNT(*) FROM voters").fetchone()[0]

    # total votes cast
    total_votes = conn.execute("SELECT COUNT(*) FROM voters WHERE has_voted=1").fetchone()[0]

    # list of voters who voted
    voted_users = conn.execute("""
        SELECT name, id FROM voters WHERE has_voted=1
    """).fetchall()

    return render_template(
        "index.html",
        total_voters=total_voters,
        total_votes=total_votes,
        voted_users=voted_users
    )

def generate_pdf_receipt(user_id):

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM voters WHERE id=?", (user_id,))
    user = cur.fetchone()

    conn.close()

    file_name = f"vote_receipt_{user_id}.pdf"
    doc = SimpleDocTemplate(file_name, pagesize=A4)

    styles = getSampleStyleSheet()
    content = []

    receipt_id = str(uuid.uuid4())[:8].upper()
    time_now = datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    content.append(Paragraph("🗳 Election Commission of India", styles['Title']))
    content.append(Spacer(1, 12))

    content.append(Paragraph("OFFICIAL VOTE RECEIPT", styles['Heading2']))
    content.append(Spacer(1, 20))

    content.append(Paragraph(f"<b>Name:</b> {user[1]}", styles['Normal']))
    content.append(Paragraph(f"<b>Email:</b> {user[5]}", styles['Normal']))
    content.append(Paragraph(f"<b>Voter ID:</b> {user[7]}", styles['Normal']))
    content.append(Spacer(1, 12))

    content.append(Paragraph("<b>Status:</b> VOTED SUCCESSFULLY", styles['Normal']))
    content.append(Paragraph(f"<b>Receipt ID:</b> {receipt_id}", styles['Normal']))
    content.append(Paragraph(f"<b>Date & Time:</b> {time_now}", styles['Normal']))

    content.append(Spacer(1, 30))
    content.append(Paragraph("This is a system generated receipt and does not require signature.", styles['Italic']))

    doc.build(content)

    return send_file(file_name, as_attachment=True)

# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':

        name = request.form['name']
        father_name = request.form['father_name']
        mother_name = request.form['mother_name']
        dob = request.form['dob']
        email = request.form['email']
        phone = request.form['phone']
        aadhaar = request.form['aadhaar']
        occupation = request.form['occupation']
        password = request.form['password']

        photo = request.files['photo']
        photo_filename = None

        if photo and photo.filename != "":
            os.makedirs("static/uploads", exist_ok=True)
            photo_filename = photo.filename
            photo.save("static/uploads/" + photo_filename)

        conn = get_db()

        try:
            conn.execute("""
                INSERT INTO voters 
                (name, father_name, mother_name, dob, email, phone, aadhaar, occupation, password, photo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                name, father_name, mother_name, dob,
                email, phone, aadhaar, occupation,
                password, photo_filename
            ))
            conn.commit()

        except Exception as e:
            return f"Error: {str(e)}"

        return redirect('/login')

    return render_template("register.html")


# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        email = request.form['email']
        password = request.form['password']

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM voters WHERE email=? AND password=?",
            (email, password)
        ).fetchone()

        if user:
            session['user'] = user['id']
            return redirect('/dashboard')

        flash("Invalid email or password ❌")
        return redirect('/login')

    return render_template("login.html")


# ---------------- USER DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM voters WHERE id=?",
        (session['user'],)
    ).fetchone()

    vote_status = conn.execute(
        "SELECT has_voted FROM voters WHERE id=?",
        (session['user'],)
    ).fetchone()[0]

    conn.close()

    return render_template(
        "dashboard.html",
        user=user,
        vote=vote_status
    )
@app.route('/download_receipt')
def download_receipt():
    if 'user' not in session:
        return redirect('/login')

    user_id = session['user']

    conn = get_db()
    user = conn.execute(
        "SELECT * FROM voters WHERE id=?",
        (user_id,)
    ).fetchone()
    conn.close()

    # optional safety check: allow only voted users
    if user[11] != 1:
        return "❌ You have not voted yet!", 403

    return generate_pdf_receipt(user_id)
# ---------------- VOTE PAGE ----------------
@app.route('/vote')
def vote():
    if 'user' not in session:
        return redirect('/login')

    conn = get_db()

    # user info (to check voted)
    user = conn.execute(
        "SELECT * FROM voters WHERE id=?",
        (session['user'],)
    ).fetchone()

    # candidates
    candidates = conn.execute(
        "SELECT * FROM candidates"
    ).fetchall()

    conn.close()

    return render_template(
        "vote.html",
        user=user,
        candidates=candidates
    )

# ---------------- SUBMIT VOTE ----------------
@app.route('/submit/<int:id>')
def submit(id):
    if 'user' not in session:
        return redirect('/login')

    user_id = session['user']
    conn = get_db()

    user = conn.execute(
        "SELECT has_voted FROM voters WHERE id=?",
        (user_id,)
    ).fetchone()

    if user['has_voted'] == 1:
        return redirect('/dashboard')

    conn.execute(
        "UPDATE candidates SET votes = votes + 1 WHERE id=?",
        (id,)
    )

    conn.execute(
        "UPDATE voters SET has_voted = 1 WHERE id=?",
        (user_id,)
    )

    conn.commit()

    # 🔥 redirect with success flag
    return redirect('/dashboard?has_voted=success')
# ---------------- RESULT ----------------

@app.route('/result')
def result():
    conn = get_db()

    data = conn.execute(
        "SELECT * FROM candidates ORDER BY votes DESC"
    ).fetchall()

    # Prepare chart data
    names = [row['name'] for row in data]
    votes = [row['votes'] for row in data]

    winner = data[0]['name'] if data else "No votes yet"

    return render_template(
        "result.html",
        data=data,
        winner=winner,
        names=names,
        votes=votes
    )

from flask import jsonify

@app.route('/get_votes')
def get_votes():
    conn = get_db()
    data = conn.execute(
        "SELECT name, votes FROM candidates ORDER BY votes DESC"
    ).fetchall()

    result = []
    for row in data:
        result.append({
            "name": row["name"],
            "votes": row["votes"]
        })

    return jsonify(result)
   
# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# ---------------- ADMIN LOGIN ----------------
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':

        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        admin = conn.execute(
            "SELECT * FROM admin WHERE username=? AND password=?",
            (username, password)
        ).fetchone()

        if admin:
            session['admin'] = username
            return redirect('/admin_dashboard')

        return "Invalid admin credentials"

    return render_template("admin_login.html")


# ---------------- ADMIN DASHBOARD ----------------
@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'admin' not in session:
        return redirect('/admin')

    conn = get_db()

    # 🔥 ADD CANDIDATE (UPDATED)
    if request.method == 'POST':
        name = request.form.get('name')
        party = request.form.get('party')

        symbol = request.files.get('symbol')
        filename = None

        if symbol and symbol.filename != "":
            import os
            os.makedirs("static/symbols", exist_ok=True)
            filename = symbol.filename
            symbol.save("static/symbols/" + filename)

        conn.execute(
            "INSERT INTO candidates (name, party, symbol, votes) VALUES (?, ?, ?, 0)",
            (name, party, filename)
        )
        conn.commit()

    # 📊 COUNTS
    voters = conn.execute("SELECT COUNT(*) FROM voters").fetchone()[0]
    candidates = conn.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
    votes = conn.execute("SELECT SUM(votes) FROM candidates").fetchone()[0] or 0

    # 🗳 CANDIDATES
    candidate_list = conn.execute(
        "SELECT * FROM candidates ORDER BY votes DESC"
    ).fetchall()

    # 🔍 SEARCH
    search = request.args.get('search', '')

    if search:
        all_voters = conn.execute(
            "SELECT * FROM voters WHERE name LIKE ? OR email LIKE ?",
            (f'%{search}%', f'%{search}%')
        ).fetchall()
    else:
        all_voters = conn.execute("SELECT * FROM voters").fetchall()

    # 👥 FILTERED DATA
    voted_users = [v for v in all_voters if v['has_voted'] == 1]
    not_voted_users = [v for v in all_voters if v['has_voted'] == 0]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        voters=voters,
        candidates=candidates,
        votes=votes,
        candidate_list=candidate_list,
        all_voters=all_voters,
        voted_users=voted_users,
        not_voted_users=not_voted_users,
        search=search
    )
# ---------------- ADD CANDIDATE ----------------
@app.route('/add_candidate', methods=['POST'])
def add_candidate():
    if 'admin' not in session:
        return redirect('/admin')

    name = request.form['name']
    party = request.form['party']

    symbol = request.files.get('symbol')
    symbol_filename = None

    if symbol and symbol.filename != "":
        os.makedirs("static/symbols", exist_ok=True)
        symbol_filename = symbol.filename
        symbol.save("static/symbols/" + symbol_filename)

    conn = get_db()

    conn.execute("""
        INSERT INTO candidates (name, party, symbol, votes)
        VALUES (?, ?, ?, 0)
    """, (name, party, symbol_filename))

    conn.commit()
    conn.close()

    return redirect('/admin_dashboard')
# ---------------- DELETE CANDIDATE ----------------
@app.route('/delete_candidate/<int:id>')
def delete_candidate(id):
    if 'admin' not in session:
        return redirect('/admin')

    conn = get_db()
    conn.execute("DELETE FROM candidates WHERE id=?", (id,))
    conn.commit()

    return redirect('/admin_dashboard')

@app.route('/admin_users')
def admin_users():
    if 'admin' not in session:
        return redirect('/admin')

    search = request.args.get('search')
    filter_type = request.args.get('filter')

    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM voters WHERE 1=1"
    params = []

    # 🔍 SEARCH
    if search:
        query += " AND (name LIKE ? OR email LIKE ?)"
        params.append(f"%{search}%")
        params.append(f"%{search}%")

    # 🔽 FILTER
    if filter_type == 'voted':
        query += " AND has_voted = 1"
    elif filter_type == 'not_voted':
        query += " AND has_voted = 0"

    voters = cursor.execute(query, params).fetchall()
    conn.close()

    return render_template("admin_users.html", voters=voters)

@app.route('/admin/delete_user/<int:id>')
def delete_user(id):
    if 'admin' not in session:
        return redirect('/admin')

    conn = get_db()
    conn.execute("DELETE FROM voters WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect('/admin_users')


@app.route("/admin_candidates", methods=["GET", "POST"])
def admin_candidates():

    if request.method == "POST":
        name = request.form.get("name")
        party = request.form.get("party")
        file = request.files.get("symbol")

        filename = None

        if file and file.filename != "":
            filename = secure_filename(file.filename)
            file.save(os.path.join("static/symbols", filename))

        conn = sqlite3.connect("database.db")
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO candidates (name, party, votes, symbol)
            VALUES (?, ?, ?, ?)
        """, (name, party, 0, filename))   # votes = 0 by default

        conn.commit()
        conn.close()

        return redirect("/admin_candidates")

    # GET request → show candidates
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT * FROM candidates")
    candidates = cur.fetchall()

    conn.close()

    return render_template("admin_candidates.html", candidates=candidates) 


@app.route("/edit_candidate/<int:id>", methods=["GET", "POST"])
def edit_candidate(id):

    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # ---------------- GET (show form) ----------------
    if request.method == "GET":
        cur.execute("SELECT * FROM candidates WHERE id=?", (id,))
        candidate = cur.fetchone()
        conn.close()

        return render_template(
            "edit_candidate.html",
            c=candidate,
            active="candidates"
        )

    # ---------------- POST (update data) ----------------
    name = request.form.get("name")
    party = request.form.get("party")
    file = request.files.get("symbol")

    # if new image uploaded
    if file and file.filename != "":
        filename = secure_filename(file.filename)
        file.save(os.path.join("static/symbols", filename))

        cur.execute("""
            UPDATE candidates
            SET name=?, party=?, symbol=?
            WHERE id=?
        """, (name, party, filename, id))

    else:
        cur.execute("""
            UPDATE candidates
            SET name=?, party=?
            WHERE id=?
        """, (name, party, id))

    conn.commit()
    conn.close()

    return redirect("/admin_candidates")

@app.route('/admin_logout')
def admin_logout():
    if 'admin' in session:
        session.pop('admin')   # remove only admin session
    return redirect("/index")

# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(debug=True)