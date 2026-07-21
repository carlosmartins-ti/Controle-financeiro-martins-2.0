import atexit
import os
import threading

import psycopg2
from psycopg2 import extensions
from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL não definida")

_POOL = None
_POOL_LOCK = threading.Lock()


def _pool_max_connections():
    try:
        return max(1, min(int(os.getenv("DB_POOL_MAX", "3")), 10))
    except (TypeError, ValueError):
        return 3


def _get_pool():
    """Cria o pool somente no primeiro acesso ao banco."""
    global _POOL

    if _POOL is None:
        with _POOL_LOCK:
            if _POOL is None:
                _POOL = ThreadedConnectionPool(
                    minconn=1,
                    maxconn=_pool_max_connections(),
                    dsn=DATABASE_URL,
                    sslmode="require",
                    cursor_factory=RealDictCursor,
                    connect_timeout=int(os.getenv("DB_CONNECT_TIMEOUT", "8")),
                    application_name="controle-financeiro-martins",
                    keepalives=1,
                    keepalives_idle=30,
                    keepalives_interval=10,
                    keepalives_count=3,
                )

    return _POOL


class _PooledConnection:
    """
    Mantém compatibilidade com o código atual.
    Quando o repositório chama close(), a conexão volta para o pool em vez de
    abrir um novo handshake SSL na próxima consulta.
    """

    def __init__(self, pool, connection):
        self._pool = pool
        self._connection = connection
        self._returned = False

    def __getattr__(self, name):
        return getattr(self._connection, name)

    @property
    def autocommit(self):
        return self._connection.autocommit

    @autocommit.setter
    def autocommit(self, value):
        self._connection.autocommit = value

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def close(self):
        if self._returned:
            return

        self._returned = True
        discard = bool(self._connection.closed)

        if not discard:
            try:
                status = self._connection.get_transaction_status()
                if status != extensions.TRANSACTION_STATUS_IDLE:
                    self._connection.rollback()
            except Exception:
                discard = True

        self._pool.putconn(self._connection, close=discard)


def get_connection():
    pool = _get_pool()
    connection = pool.getconn()

    if connection.closed:
        pool.putconn(connection, close=True)
        connection = pool.getconn()

    return _PooledConnection(pool, connection)


def close_pool():
    global _POOL

    with _POOL_LOCK:
        if _POOL is not None:
            _POOL.closeall()
            _POOL = None


atexit.register(close_pool)


def init_db():
    """Cria/atualiza a estrutura. Execute em migração, não em todo cold start."""
    conn = get_connection()
    conn.autocommit = False
    cur = conn.cursor()

    try:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                security_question TEXT NOT NULL,
                security_answer_hash TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                telegram_id BIGINT,
                remember_token TEXT,
                is_superuser BOOLEAN NOT NULL DEFAULT FALSE
            )
            """
        )

        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS telegram_id BIGINT")
        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS remember_token TEXT")
        cur.execute(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_superuser BOOLEAN NOT NULL DEFAULT FALSE"
        )
        cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS users_telegram_id_uq ON users (telegram_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS users_remember_token_idx ON users (remember_token)"
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                UNIQUE(user_id, name)
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS payments (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                category_id INTEGER,
                amount NUMERIC(10,2) NOT NULL,
                purchase_date DATE,
                due_date DATE NOT NULL,
                month INTEGER NOT NULL,
                year INTEGER NOT NULL,
                paid BOOLEAN NOT NULL DEFAULT FALSE,
                paid_date DATE,
                created_at TIMESTAMP NOT NULL,
                is_credit BOOLEAN NOT NULL DEFAULT FALSE,
                installments INTEGER NOT NULL DEFAULT 1,
                installment_index INTEGER NOT NULL DEFAULT 1,
                credit_group INTEGER
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS budgets (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                month INTEGER NOT NULL,
                year INTEGER NOT NULL,
                income NUMERIC(10,2) NOT NULL DEFAULT 0,
                expense_goal NUMERIC(10,2) NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL,
                UNIQUE(user_id, month, year)
            )
            """
        )

        # Índices usados nas telas, filtros mensais e operações de parcelamento.
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS payments_user_period_due_idx
            ON payments (user_id, year, month, due_date)
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS payments_user_credit_group_idx
            ON payments (user_id, credit_group)
            WHERE credit_group IS NOT NULL
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS payments_user_period_paid_idx
            ON payments (user_id, year, month, paid)
            """
        )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()
