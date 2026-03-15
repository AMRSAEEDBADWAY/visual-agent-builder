import secrets
import bcrypt
from typing import Optional
from core.database import get_db_connection, log_activity

def hash_password(password: str) -> str:
    """Hashes a password using bcrypt (industry standard)."""
    # bcrypt requires bytes, so we encode the password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    # Return as a string to store in DB
    return hashed.decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """Verifies a password against its bcrypt hash."""
    try:
        # Check if the password matches the hash
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        # Fallback for old SHA-256 hashes if any (optional, usually returns False)
        return False

def generate_session_token() -> str:
    """Generates a secure random token for sessions."""
    return secrets.token_hex(32)

def verify_security_answer(answer: str, hashed_answer: str) -> bool:
    """Verifies a security answer against its hash. Ignoring case and surrounding whitespace."""
    if not answer or not hashed_answer:
        return False
    normalized_answer = answer.strip().lower()
    return verify_password(normalized_answer, hashed_answer)

def authenticate_user(username: str, password: str) -> Optional[dict]:
    """
    Authenticates a user and returns their data if successful.
    Returns None if authentication fails.
    """
    with get_db_connection() as conn:
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        
        if user and verify_password(password, user['password_hash']):
            log_activity(username, "LOGIN", "Successful login")
            return dict(user)
            
        # Log failure
        log_activity(username, "FAILED_LOGIN", "Invalid password or non-existent user")
        return None
