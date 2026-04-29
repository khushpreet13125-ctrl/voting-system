import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# ---------------- VOTERS TABLE ----------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS voters(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    father_name TEXT,
    mother_name TEXT,
    dob TEXT,
    email TEXT UNIQUE,
    phone INTEGER,
    aadhaar INTEGER,
    occupation TEXT,
    password TEXT,
    photo TEXT,
    has_voted INTEGER DEFAULT 0,
    vote_candidate_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    voter_id INTEGER,
    candidate_id INTEGER,
    voted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY(voter_id) REFERENCES voters(id),
    FOREIGN KEY(candidate_id) REFERENCES candidates(id)
)
               """)

# ---------------- CANDIDATES TABLE ----------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    party TEXT,
    symbol TEXT,
    votes INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
           """)

# ---------------- ADMIN TABLE ----------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS admin (
    username TEXT,
    password TEXT
)
""")

# Insert default admin (only once)
cursor.execute("DELETE FROM admin")
cursor.execute("INSERT INTO admin VALUES ('admin','1234')")

conn.commit()
conn.close()

print("Database created successfully!")