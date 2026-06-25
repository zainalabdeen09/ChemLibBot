import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "chemlib.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_ar TEXT NOT NULL,
            name_en TEXT NOT NULL,
            parent_id INTEGER REFERENCES sections(id),
            sort_order INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_id INTEGER REFERENCES sections(id),
            title TEXT NOT NULL,
            authors TEXT,
            year INTEGER,
            doi TEXT,
            url TEXT,
            abstract TEXT,
            source TEXT,
            pdf_url TEXT,
            is_open_access INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            lang TEXT DEFAULT 'ar',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_papers_section ON papers(section_id);
        CREATE INDEX IF NOT EXISTS idx_papers_title ON papers(title);
    """)

    conn.commit()
    conn.close()


def get_user_lang(user_id: int) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row["lang"] if row else "ar"


def set_user_lang(user_id: int, lang: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO users (user_id, lang) VALUES (?, ?)",
        (user_id, lang),
    )
    conn.commit()
    conn.close()


def get_sections(parent_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    if parent_id is None:
        cursor.execute(
            "SELECT * FROM sections WHERE parent_id IS NULL ORDER BY sort_order"
        )
    else:
        cursor.execute(
            "SELECT * FROM sections WHERE parent_id = ? ORDER BY sort_order",
            (parent_id,),
        )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_section(section_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sections WHERE id = ?", (section_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_papers_by_section(section_id: int, limit=20):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM papers WHERE section_id = ? ORDER BY year DESC LIMIT ?",
        (section_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def add_section(name_ar: str, name_en: str, parent_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sections (name_ar, name_en, parent_id) VALUES (?, ?, ?)",
        (name_ar, name_en, parent_id),
    )
    conn.commit()
    conn.close()


def add_paper(section_id: int, title: str, authors="", year="", doi="",
              url="", abstract="", source="", pdf_url="", is_open_access=0):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO papers
           (section_id, title, authors, year, doi, url, abstract, source, pdf_url, is_open_access)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (section_id, title, authors, year, doi, url, abstract, source, pdf_url, is_open_access),
    )
    conn.commit()
    conn.close()


def paper_exists_by_doi(doi: str) -> bool:
    if not doi:
        return False
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM papers WHERE doi = ?", (doi,))
    row = cursor.fetchone()
    conn.close()
    return row is not None


def count_papers_in_section(section_id: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as cnt FROM papers WHERE section_id = ?", (section_id,))
    row = cursor.fetchone()
    conn.close()
    return row["cnt"] if row else 0
