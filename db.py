# db.py
import sqlite3
from config import DB_PATH

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                name TEXT,
                username TEXT,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # التأكد من وجود الأعمدة المطلوبة
        cur = conn.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cur.fetchall()]
        if 'name' not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN name TEXT")
        if 'username' not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN username TEXT")
        if 'title' not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN title TEXT")
        if 'created_at' not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

        conn.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                description TEXT,
                file_id TEXT,
                status TEXT DEFAULT 'pending',
                reply_text TEXT,
                reply_file_id TEXT,
                reply_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        ''')
        conn.commit()

def add_user(user_id, name, username, title):
    with get_db() as conn:
        conn.execute(
            'INSERT OR REPLACE INTO users (user_id, name, username, title) VALUES (?, ?, ?, ?)',
            (user_id, name, username, title)
        )
        conn.commit()

def user_exists(user_id):
    with get_db() as conn:
        cur = conn.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
        return cur.fetchone() is not None

def get_user_title(user_id):
    with get_db() as conn:
        cur = conn.execute('SELECT title FROM users WHERE user_id = ?', (user_id,))
        row = cur.fetchone()
        return row['title'] if row else None

def get_all_users():
    with get_db() as conn:
        cur = conn.execute('SELECT user_id, name, username, title FROM users')
        return cur.fetchall()

def get_users_by_title(title):
    with get_db() as conn:
        cur = conn.execute('SELECT user_id FROM users WHERE title = ?', (title,))
        return [row['user_id'] for row in cur.fetchall()]

def get_all_titles():
    with get_db() as conn:
        cur = conn.execute('SELECT DISTINCT title FROM users')
        return [row['title'] for row in cur.fetchall()]

def delete_user(user_id):
    with get_db() as conn:
        conn.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        conn.commit()

def add_task(user_id, description, file_id=None):
    with get_db() as conn:
        cur = conn.execute(
            'INSERT INTO tasks (user_id, description, file_id) VALUES (?, ?, ?)',
            (user_id, description, file_id)
        )
        conn.commit()
        return cur.lastrowid

def get_user_pending_tasks(user_id):
    with get_db() as conn:
        cur = conn.execute(
            'SELECT task_id, description, file_id FROM tasks WHERE user_id = ? AND status = "pending"',
            (user_id,)
        )
        return cur.fetchall()

def get_task_stats(user_id):
    with get_db() as conn:
        cur = conn.execute('SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = "pending"', (user_id,))
        pending = cur.fetchone()[0]
        cur = conn.execute('SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = "done"', (user_id,))
        done = cur.fetchone()[0]
        return pending, done

def get_all_tasks_stats():
    with get_db() as conn:
        cur = conn.execute('SELECT COUNT(*) FROM tasks WHERE status = "pending"')
        pending = cur.fetchone()[0]
        cur = conn.execute('SELECT COUNT(*) FROM tasks WHERE status = "done"')
        done = cur.fetchone()[0]
        return pending, done

def get_task(task_id):
    with get_db() as conn:
        cur = conn.execute('SELECT * FROM tasks WHERE task_id = ?', (task_id,))
        return cur.fetchone()

def complete_task(task_id, reply_text, reply_file_id=None, reply_type=None):
    with get_db() as conn:
        conn.execute(
            'UPDATE tasks SET status = "done", reply_text = ?, reply_file_id = ?, reply_type = ?, completed_at = CURRENT_TIMESTAMP WHERE task_id = ?',
            (reply_text, reply_file_id, reply_type, task_id)
        )
        conn.commit()

# ========== الدالة الجديدة لعرض جميع المهام المعلقة مع تفاصيل المستخدم ==========
def get_all_pending_tasks():
    """الحصول على جميع المهام المعلقة مع معلومات المستخدم"""
    with get_db() as conn:
        cur = conn.execute('''
            SELECT t.task_id, t.description, u.title, u.name, u.user_id
            FROM tasks t
            JOIN users u ON t.user_id = u.user_id
            WHERE t.status = 'pending'
            ORDER BY t.created_at DESC
        ''')
        return cur.fetchall()