import bcrypt
import datetime
import secrets
from psycopg2.extras import RealDictCursor
from database import get_connection


def _now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def hash_text(text: str) -> str:
    return bcrypt.hashpw(text.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_text(text: str, hashed: str) -> bool:
    return bcrypt.checkpw(text.encode("utf-8"), hashed.encode("utf-8"))


def generate_remember_token():
    return secrets.token_urlsafe(32)


# -------------------- CREATE USER --------------------
def create_user(username, password, security_question, security_answer):
    username = username.strip().lower()
    password = password or ""
    security_answer = security_answer or ""

    if not username or not password:
        raise ValueError("Usuário e senha são obrigatórios.")

    if len(password) < 4:
        raise ValueError("Senha muito curta (mínimo 4).")

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        """
        INSERT INTO users
            (username, password_hash, security_question, security_answer_hash, created_at, is_superuser)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            username,
            hash_text(password),
            security_question.strip(),
            hash_text(security_answer.strip()),
            _now(),
            False
        )
    )

    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return int(row["id"])


# -------------------- AUTHENTICATE NORMAL --------------------
def authenticate(username, password):
    username = username.strip().lower()

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        "SELECT id, password_hash FROM users WHERE username = %s",
        (username,)
    )
    row = cur.fetchone()

    cur.close()
    conn.close()

    if row and verify_text(password, row["password_hash"]):
        return row["id"]

    return None


# -------------------- AUTHENTICATE COMPLETO --------------------
def authenticate_full(username, password):
    username = username.strip().lower()

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        """
        SELECT id, username, password_hash, COALESCE(is_superuser, false) AS is_superuser
        FROM users
        WHERE username = %s
        """,
        (username,)
    )

    row = cur.fetchone()

    cur.close()
    conn.close()

    if row and verify_text(password, row["password_hash"]):
        return {
            "id": row["id"],
            "username": row["username"],
            "is_superuser": bool(row["is_superuser"])
        }

    return None


# -------------------- SECURITY QUESTION --------------------
def get_security_question(username: str):
    username = (username or "").strip().lower()

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        "SELECT security_question FROM users WHERE username = %s",
        (username,)
    )
    row = cur.fetchone()

    cur.close()
    conn.close()

    return row["security_question"] if row else None


# -------------------- RESET PASSWORD NORMAL --------------------
def reset_password(username: str, security_answer: str, new_password: str) -> bool:
    username = (username or "").strip().lower()
    security_answer = security_answer or ""

    if len(new_password) < 4:
        raise ValueError("Senha muito curta (mínimo 4).")

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        "SELECT id, security_answer_hash FROM users WHERE username = %s",
        (username,)
    )
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        return False

    user_id = row["id"]
    answer_hash = row["security_answer_hash"]

    if not verify_text(security_answer.strip(), answer_hash):
        cur.close()
        conn.close()
        return False

    cur.execute(
        "UPDATE users SET password_hash = %s WHERE id = %s",
        (hash_text(new_password), user_id)
    )

    conn.commit()
    cur.close()
    conn.close()
    return True


# -------------------- ADMIN: LISTAR USUÁRIOS --------------------
def admin_list_users():
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        """
        SELECT
            id,
            username,
            created_at,
            COALESCE(is_superuser, false) AS is_superuser
        FROM users
        ORDER BY username
        """
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows


# -------------------- ADMIN: CRIAR USUÁRIO --------------------
def admin_create_user(username, password, is_superuser=False):
    username = (username or "").strip().lower()
    password = password or ""

    if not username or not password:
        raise ValueError("Usuário e senha são obrigatórios.")

    if len(password) < 4:
        raise ValueError("Senha muito curta (mínimo 4).")

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        "SELECT id FROM users WHERE username = %s",
        (username,)
    )

    exists = cur.fetchone()

    if exists:
        cur.close()
        conn.close()
        raise ValueError("Este usuário já existe.")

    cur.execute(
        """
        INSERT INTO users
            (username, password_hash, security_question, security_answer_hash, created_at, is_superuser)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            username,
            hash_text(password),
            "Criado pelo administrador",
            hash_text("admin"),
            _now(),
            bool(is_superuser)
        )
    )

    conn.commit()
    cur.close()
    conn.close()


# -------------------- ADMIN: RESETAR SENHA --------------------
def admin_reset_password(user_id, new_password):
    if not new_password or len(new_password) < 4:
        raise ValueError("Senha muito curta (mínimo 4).")

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        """
        UPDATE users
        SET password_hash = %s
        WHERE id = %s
        """,
        (hash_text(new_password), user_id)
    )

    conn.commit()
    cur.close()
    conn.close()


# -------------------- ADMIN: EXCLUIR USUÁRIO --------------------
def admin_delete_user(user_id):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        "DELETE FROM users WHERE id = %s",
        (user_id,)
    )

    conn.commit()
    cur.close()
    conn.close()


# -------------------- ADMIN: ALTERAR SUPERUSER --------------------
def admin_set_superuser(user_id, is_superuser):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute(
        """
        UPDATE users
        SET is_superuser = %s
        WHERE id = %s
        """,
        (bool(is_superuser), user_id)
    )

    conn.commit()
    cur.close()
    conn.close()
