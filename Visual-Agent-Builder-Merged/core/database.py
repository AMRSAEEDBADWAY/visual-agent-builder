import sqlite3
import os
from contextlib import contextmanager

# Base directory setup
# نحفظ قاعدة البيانات في مجلد داخل حساب المستخدم لضمان صلاحيات الكتابة على ويندوز ولينكس
USER_BASE_DIR = os.path.expanduser("~")
APP_DATA_DIR = os.path.join(USER_BASE_DIR, ".visual_agent_builder")
os.makedirs(APP_DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(APP_DATA_DIR, "projects.db")

@contextmanager
def get_db_connection():
    """Context manager for SQLite database connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    # Enable foreign key support in SQLite
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.commit()
        conn.close()

def init_db():
    """Initialize the database with required tables if they don't exist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 1. Users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Add new columns for User Management safely
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
        except sqlite3.OperationalError:
            pass # Column already exists
            
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN security_question TEXT")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN security_answer_hash TEXT")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN session_token TEXT")
        except sqlite3.OperationalError:
            pass


        # 2. Projects table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        ''')

        # 3. Nodes (Agents/Tools) table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS nodes (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL, -- e.g., 'agent', 'tool', 'input', 'output'
            x_position REAL NOT NULL,
            y_position REAL NOT NULL,
            data_json TEXT, -- JSON string storing instructions, prompt, model settings
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
        ''')

        # 4. Edges (Connections between nodes) table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS edges (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            source_node_id TEXT NOT NULL,
            target_node_id TEXT NOT NULL,
            source_handle TEXT,
            target_handle TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (source_node_id) REFERENCES nodes(id) ON DELETE CASCADE,
            FOREIGN KEY (target_node_id) REFERENCES nodes(id) ON DELETE CASCADE
        )
        ''')

        # 5. Chat History table for AI memory
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            sender TEXT NOT NULL, -- 'user' or 'agent'
            message TEXT NOT NULL,
            agent_id TEXT, -- ID of the specific agent if sender is 'agent'
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
        ''')
        
        # 6. Activity Logs for auditing
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            action TEXT NOT NULL,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
    print(f"Database initialized successfully at {DB_PATH}")



def create_user(user_id: str, username: str, email: str, password_hash: str, security_question: str = None, security_answer_hash: str = None):
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO users (id, username, email, password_hash, security_question, security_answer_hash) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, username, email, password_hash, security_question, security_answer_hash)
        )
        return user_id

def get_user_by_username(username: str):
    with get_db_connection() as conn:
        return conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

def update_user_password(username: str, new_password_hash: str):
    with get_db_connection() as conn:
        conn.execute("UPDATE users SET password_hash = ? WHERE username = ?", (new_password_hash, username))

def get_user_by_session_token(token: str):
    if token is None:
        return None
    with get_db_connection() as conn:
        return conn.execute("SELECT * FROM users WHERE session_token = ?", (token,)).fetchone()

def update_session_token(user_id: str, token: str):
    with get_db_connection() as conn:
        conn.execute("UPDATE users SET session_token = ? WHERE id = ?", (token, user_id))

def get_all_users():
    with get_db_connection() as conn:
        return conn.execute("SELECT id, username, email, role, created_at FROM users ORDER BY created_at DESC").fetchall()

def create_project(project_id: str, user_id: str, name: str, description: str = ""):
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO projects (id, user_id, name, description) VALUES (?, ?, ?, ?)",
            (project_id, user_id, name, description)
        )
        return project_id

def get_projects_by_user(user_id: str):
    with get_db_connection() as conn:
        return conn.execute("SELECT * FROM projects WHERE user_id = ? ORDER BY updated_at DESC", (user_id,)).fetchall()

def get_project(project_id: str):
    with get_db_connection() as conn:
        return conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()

def delete_project(project_id: str):
    with get_db_connection() as conn:
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        
def save_node(node_id: str, project_id: str, name: str, node_type: str, x: float, y: float, data_json: str):
    with get_db_connection() as conn:
        conn.execute(
            """INSERT INTO nodes (id, project_id, name, type, x_position, y_position, data_json) 
               VALUES (?, ?, ?, ?, ?, ?, ?) 
               ON CONFLICT(id) DO UPDATE SET 
               name=excluded.name, type=excluded.type, x_position=excluded.x_position, 
               y_position=excluded.y_position, data_json=excluded.data_json""",
            (node_id, project_id, name, node_type, x, y, data_json)
        )

def get_nodes(project_id: str):
    with get_db_connection() as conn:
        return conn.execute("SELECT * FROM nodes WHERE project_id = ?", (project_id,)).fetchall()

def save_edge(edge_id: str, project_id: str, source: str, target: str, source_handle: str = "", target_handle: str = ""):
    with get_db_connection() as conn:
        conn.execute(
            """INSERT INTO edges (id, project_id, source_node_id, target_node_id, source_handle, target_handle) 
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO NOTHING""",
            (edge_id, project_id, source, target, source_handle, target_handle)
        )

def get_edges(project_id: str):
    with get_db_connection() as conn:
        return conn.execute("SELECT * FROM edges WHERE project_id = ?", (project_id,)).fetchall()

# Security & Audit Functions
def log_activity(username: str, action: str, details: str = ""):
    """Logs user actions (login, logout, failed attempts)."""
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO activity_logs (username, action, details) VALUES (?, ?, ?)",
            (username, action, details)
        )

def get_recent_activity(limit: int = 100):
    """Fetches recent activity logs."""
    with get_db_connection() as conn:
        return conn.execute("SELECT * FROM activity_logs ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()

if __name__ == "__main__":
    init_db()
