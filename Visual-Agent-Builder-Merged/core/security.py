import os
from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken

# The ideal path for the encryption key
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY_PATH = os.path.join(BASE_DIR, "secret.key")

# Cache the key in memory to avoid repeated disk reads
_cached_key = None

def generate_key():
    """
    Generates a key and save it into a file
    """
    key = Fernet.generate_key()
    with open(KEY_PATH, "wb") as key_file:
        key_file.write(key)
    print(f"Encryption key generated and saved to {KEY_PATH}. KEEP THIS SAFE!")

def load_key():
    """
    Loads the key from disk or from memory cache if already loaded.
    """
    global _cached_key
    
    if _cached_key is not None:
        return _cached_key
        
    if not os.path.exists(KEY_PATH):
        generate_key()
        
    with open(KEY_PATH, "rb") as key_file:
        _cached_key = key_file.read()
        
    return _cached_key

def encrypt_text(message: str) -> str:
    """
    Encrypts a string message.
    """
    if not message:
        return message
        
    key = load_key()
    fernet = Fernet(key)
    encoded_message = message.encode()
    encrypted_message = fernet.encrypt(encoded_message)
    return encrypted_message.decode()

def decrypt_text(encrypted_message: str) -> str:
    """
    Decrypts an encrypted string message.
    """
    if not encrypted_message:
        return encrypted_message
        
    try:
        key = load_key()
        fernet = Fernet(key)
        decrypted_message = fernet.decrypt(encrypted_message.encode())
        return decrypted_message.decode()
    except (InvalidToken, ValueError):
        # Fallback if decryption fails (e.g. data was saved in plain text before encryption was added)
        return encrypted_message
