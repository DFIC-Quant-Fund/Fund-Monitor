import hashlib
import os
import uuid
from datetime import datetime

from dotenv import load_dotenv

from database.connection import get_db_connection

load_dotenv()


def generate_salt() -> str:
    salt = os.urandom(16).hex()
    return salt


def hash_password(password: str, salt: str) -> str:
    try:
        password = password.strip()
        salt = salt.strip()

        hash = hashlib.scrypt(
            password.encode(), salt=salt.encode(), n=16384, r=8, p=1, dklen=64
        )

        return hash.hex()
    except Exception as error:
        raise error


def verify_password(email: str, password: str) -> bool:
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT salt FROM Users WHERE email = %s", (email,))
    result = cursor.fetchone()

    if result is None:
        print("No user found with the provided email.")
        cursor.close()
        connection.close()
        return

    salt = result[0]
    input_hashed_password = hash_password(password, salt)

    cursor.execute("SELECT password FROM Users WHERE email = %s", (email,))

    db_result = cursor.fetchone()

    if db_result is None:
        print("Error: No password found for the provided email.")
        cursor.close()
        connection.close()
        return

    db_hashed_password = db_result[0]

    if db_hashed_password == input_hashed_password:
        return True
    else:
        return False


def session_exists(session_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM Sessions WHERE session_id = ?", (session_id,))
    result = cur.fetchone()
    conn.close()
    return result is not None


def generate_session():
    session_id = str(uuid.uuid4())
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO Sessions (session_id, expires_at) VALUES (%s, %s)",
        (session_id, datetime.utcnow()),
    )
    conn.commit()
    conn.close()
    return session_id

