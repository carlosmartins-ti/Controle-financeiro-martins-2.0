from database import get_connection
from datetime import datetime

# ================= DEFAULT CATEGORIES =================

DEFAULT_CATEGORIES = [
    "Aluguel",
    "Condomínio",
    "Água",
    "Luz",
    "Internet",
    "Plano celular",
    "Mercado",
    "Cartão de crédito",
    "Outros"
]


# ================= USERS (REMEMBER ME) =================

def get_user_by_token(token):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, username FROM users WHERE remember_token = %s",
        (token,)
    )

    row = cur.fetchone()

    cur.close()
    conn.close()

    return row


def save_remember_token(user_id, token):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "UPDATE users SET remember_token = %s WHERE id = %s",
        (token, user_id)
    )

    conn.commit()
    cur.close()
    conn.close()


def clear_remember_token(user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "UPDATE users SET remember_token = NULL WHERE id = %s",
        (user_id,)
    )

    conn.commit()
    cur.close()
    conn.close()


# ================= CATEGORIES =================

def seed_default_categories(user_id):
    conn = get_connection()
    cur = conn.cursor()

    for name in DEFAULT_CATEGORIES:
        cur.execute(
            """
            INSERT INTO categories (user_id, name, created_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, name) DO NOTHING
            """,
            (user_id, name, datetime.now())
        )

    conn.commit()
    cur.close()
    conn.close()


def list_categories(user_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT id, name FROM categories WHERE user_id = %s ORDER BY name",
        (user_id,)
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows


def create_category(user_id, name):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO categories (user_id, name, created_at) VALUES (%s, %s, %s)",
        (user_id, name, datetime.now())
    )

    conn.commit()
    cur.close()
    conn.close()


def delete_category(user_id, category_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM categories WHERE id = %s AND user_id = %s",
        (category_id, user_id)
    )

    conn.commit()
    cur.close()
    conn.close()


# ================= PAYMENTS =================

def add_payment(
    user_id,
    description,
    amount,
    purchase_date,
    due_date,
    month,
    year,
    category_id=None,
    is_credit=False,
    installments=1,
    parcel_type="total"
):

    conn = get_connection()
    cur = conn.cursor()

    amount = float(amount)
    installments = int(installments)

    credit_group = int(datetime.now().timestamp())

    if is_credit and installments > 1:

        if parcel_type == "total":
            parcel_value = round(amount / installments, 2)
        else:
            parcel_value = round(amount, 2)

    else:
        parcel_value = round(amount, 2)

    base_date = datetime.fromisoformat(str(due_date))
    purchase_dt = datetime.fromisoformat(str(purchase_date)).date() if purchase_date else None

    for i in range(installments):

        parcel_month = month + i
        parcel_year = year

        while parcel_month > 12:
            parcel_month -= 12
            parcel_year += 1

        parcel_due = base_date.replace(month=parcel_month, year=parcel_year)

        cur.execute(
            """
            INSERT INTO payments (
                user_id,
                description,
                category_id,
                amount,
                purchase_date,
                due_date,
                month,
                year,
                paid,
                paid_date,
                created_at,
                is_credit,
                installments,
                installment_index,
                credit_group
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),%s,%s,%s,%s)
            """,
            (
                user_id,
                f"{description} ({i+1}/{installments})" if installments > 1 else description,
                category_id,
                parcel_value,
                purchase_dt,
                parcel_due.date(),
                parcel_month,
                parcel_year,
                False,
                None,
                bool(is_credit),
                installments,
                i + 1,
                credit_group
            )
        )

    conn.commit()
    cur.close()
    conn.close()


def list_payments(user_id, month, year):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            p.id,
            p.description,
            p.amount,
            p.purchase_date,
            p.due_date,
            p.paid,
            p.paid_date,
            p.category_id,
            c.name AS category,
            p.is_credit,
            p.installments,
            p.installment_index,
            p.credit_group
        FROM payments p
        LEFT JOIN categories c ON c.id = p.category_id
        WHERE p.user_id = %s
        AND p.month = %s
        AND p.year = %s
        ORDER BY p.due_date
        """,
        (user_id, month, year)
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows


def mark_paid(user_id, payment_id, paid):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "UPDATE payments SET paid = %s, paid_date = %s WHERE id = %s AND user_id = %s",
        (bool(paid), datetime.now() if paid else None, payment_id, user_id)
    )

    conn.commit()
    cur.close()
    conn.close()


def update_payment(user_id, payment_id, description, amount, purchase_date, due_date, category_id):
    conn = get_connection()
    cur = conn.cursor()

    purchase_dt = datetime.fromisoformat(str(purchase_date)).date() if purchase_date else None

    cur.execute(
        """
        UPDATE payments
        SET description = %s,
            amount = %s,
            purchase_date = %s,
            due_date = %s,
            category_id = %s
        WHERE id = %s
        AND user_id = %s
        """,
        (description, amount, purchase_dt, due_date, category_id, payment_id, user_id)
    )

    conn.commit()
    cur.close()
    conn.close()


def delete_payment(user_id, payment_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM payments WHERE id = %s AND user_id = %s",
        (payment_id, user_id)
    )

    conn.commit()
    cur.close()
    conn.close()


# ================= BUDGET =================

def get_budget(user_id, month, year):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT income, expense_goal FROM budgets WHERE user_id = %s AND month = %s AND year = %s",
        (user_id, month, year)
    )

    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return {"income": 0.0, "expense_goal": 0.0}

    return {
        "income": float(row["income"]),
        "expense_goal": float(row["expense_goal"])
    }


def upsert_budget(user_id, month, year, income, expense_goal):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO budgets (user_id, month, year, income, expense_goal, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (user_id, month, year)
        DO UPDATE SET income = %s, expense_goal = %s
        """,
        (user_id, month, year, income, expense_goal, datetime.now(), income, expense_goal)
    )

    conn.commit()
    cur.close()
    conn.close()


# ================= FATURA DO CARTÃO =================

def _get_card_category_ids(conn, user_id):

    cur = conn.cursor()

    cur.execute(
        """
        SELECT id
        FROM categories
        WHERE user_id = %s
        AND LOWER(name) LIKE %s
        """,
        (user_id, '%cart%')
    )

    rows = cur.fetchall()

    cur.close()

    return [r["id"] for r in rows] if rows else []


def mark_credit_invoice_paid(user_id, month, year):

    conn = get_connection()
    conn.autocommit = False

    try:

        card_ids = _get_card_category_ids(conn, user_id)

        if not card_ids:
            conn.commit()
            return

        cur = conn.cursor()

        cur.execute(
            """
            UPDATE payments
            SET paid = TRUE,
                paid_date = CURRENT_DATE
            WHERE user_id = %s
            AND month = %s
            AND year = %s
            AND category_id = ANY(%s)
            AND paid = FALSE
            """,
            (user_id, month, year, card_ids)
        )

        cur.close()
        conn.commit()

    finally:
        conn.close()


def unmark_credit_invoice_paid(user_id, month, year):

    conn = get_connection()
    conn.autocommit = False

    try:

        card_ids = _get_card_category_ids(conn, user_id)

        if not card_ids:
            conn.commit()
            return

        cur = conn.cursor()

        cur.execute(
            """
            UPDATE payments
            SET paid = FALSE,
                paid_date = NULL
            WHERE user_id = %s
            AND month = %s
            AND year = %s
            AND category_id = ANY(%s)
            AND paid = TRUE
            """,
            (user_id, month, year, card_ids)
        )

        cur.close()
        conn.commit()

    finally:
        conn.close()


# ================= EXCLUIR COMPRA PARCELADA =================

def delete_credit_group(user_id, credit_group, only_open=True):

    conn = get_connection()
    cur = conn.cursor()

    if only_open:

        cur.execute(
            """
            DELETE FROM payments
            WHERE user_id = %s
            AND credit_group = %s
            AND paid = FALSE
            """,
            (user_id, credit_group)
        )

    else:

        cur.execute(
            """
            DELETE FROM payments
            WHERE user_id = %s
            AND credit_group = %s
            """,
            (user_id, credit_group)
        )

    conn.commit()
    cur.close()
    conn.close()


# ================= EDITAR COMPRA PARCELADA =================

def _clean_installment_description(description):
    """
    Remove o final da descrição quando estiver assim:
    Nome da compra (1/3)
    Nome da compra (2/3)
    """
    import re

    return re.sub(r"\s*\(\d+\/\d+\)\s*$", "", str(description or "")).strip()


def _add_months_safe(dt, months_to_add):
    """
    Soma meses sem quebrar quando o mês não tem o mesmo dia.
    Exemplo:
    31/01 + 1 mês vira 28/02 ou 29/02.
    """
    import calendar

    month = dt.month - 1 + int(months_to_add)
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])

    return dt.replace(year=year, month=month, day=day)


def update_credit_group_installments(user_id, credit_group, new_installments):
    """
    Atualiza a quantidade de parcelas de uma compra parcelada.

    Funcionamento:
    - Se aumentar, cria novas parcelas nos meses seguintes.
    - Se diminuir, exclui somente parcelas futuras/em aberto.
    - Não deixa diminuir abaixo da última parcela já paga.
    - Atualiza o texto da descrição para (1/N), (2/N), etc.
    """

    new_installments = int(new_installments)

    if new_installments < 1:
        raise ValueError("Quantidade de parcelas inválida.")

    conn = get_connection()
    conn.autocommit = False
    cur = conn.cursor()

    try:
        cur.execute(
            """
            SELECT
                id,
                description,
                category_id,
                amount,
                purchase_date,
                due_date,
                month,
                year,
                paid,
                installments,
                installment_index,
                credit_group
            FROM payments
            WHERE user_id = %s
              AND credit_group = %s
            ORDER BY installment_index ASC, due_date ASC, id ASC
            """,
            (user_id, credit_group)
        )

        rows = cur.fetchall()

        if not rows:
            raise ValueError("Compra parcelada não encontrada.")

        rows = sorted(
            rows,
            key=lambda r: (
                int(r.get("installment_index") or 999999),
                str(r.get("due_date") or ""),
                int(r.get("id") or 0)
            )
        )

        paid_indexes = [
            int(r.get("installment_index") or 0)
            for r in rows
            if bool(r.get("paid"))
        ]

        max_paid_index = max(paid_indexes) if paid_indexes else 0

        if new_installments < max_paid_index:
            raise ValueError(
                f"Não é possível reduzir para {new_installments} parcelas, "
                f"pois já existe parcela paga até a {max_paid_index}ª."
            )

        first = rows[0]

        base_description = _clean_installment_description(first.get("description"))
        category_id = first.get("category_id")
        purchase_date = first.get("purchase_date")
        credit_group_value = first.get("credit_group")
        parcel_value = float(first.get("amount") or 0)

        base_due = first.get("due_date")

        if not base_due:
            raise ValueError("A compra parcelada não possui data de vencimento base.")

        if isinstance(base_due, str):
            base_due = datetime.fromisoformat(base_due).date()

        existing_by_index = {
            int(r.get("installment_index") or 0): r
            for r in rows
            if int(r.get("installment_index") or 0) > 0
        }

        # Atualiza as parcelas que devem existir
        for idx in range(1, new_installments + 1):
            new_due = _add_months_safe(base_due, idx - 1)

            if new_installments > 1:
                new_description = f"{base_description} ({idx}/{new_installments})"
            else:
                new_description = base_description

            if idx in existing_by_index:
                r = existing_by_index[idx]

                cur.execute(
                    """
                    UPDATE payments
                    SET description = %s,
                        due_date = %s,
                        month = %s,
                        year = %s,
                        installments = %s,
                        installment_index = %s,
                        is_credit = %s
                    WHERE id = %s
                      AND user_id = %s
                    """,
                    (
                        new_description,
                        new_due,
                        new_due.month,
                        new_due.year,
                        new_installments,
                        idx,
                        True if new_installments > 1 else False,
                        r.get("id"),
                        user_id
                    )
                )

            else:
                cur.execute(
                    """
                    INSERT INTO payments (
                        user_id,
                        description,
                        category_id,
                        amount,
                        purchase_date,
                        due_date,
                        month,
                        year,
                        paid,
                        paid_date,
                        created_at,
                        is_credit,
                        installments,
                        installment_index,
                        credit_group
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),%s,%s,%s,%s)
                    """,
                    (
                        user_id,
                        new_description,
                        category_id,
                        parcel_value,
                        purchase_date,
                        new_due,
                        new_due.month,
                        new_due.year,
                        False,
                        None,
                        True if new_installments > 1 else False,
                        new_installments,
                        idx,
                        credit_group_value
                    )
                )

        # Remove parcelas acima do novo limite, mas somente se estiverem em aberto
        cur.execute(
            """
            DELETE FROM payments
            WHERE user_id = %s
              AND credit_group = %s
              AND installment_index > %s
              AND paid = FALSE
            """,
            (user_id, credit_group, new_installments)
        )

        # Segurança: se existir parcela paga acima do novo limite, bloqueia
        cur.execute(
            """
            SELECT COUNT(*) AS total
            FROM payments
            WHERE user_id = %s
              AND credit_group = %s
              AND installment_index > %s
              AND paid = TRUE
            """,
            (user_id, credit_group, new_installments)
        )

        check = cur.fetchone()

        if check and int(check.get("total") or 0) > 0:
            raise ValueError(
                "Não foi possível reduzir: existem parcelas pagas acima do novo limite."
            )

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()


# ================= RELATÓRIO DE DESPESAS =================

def get_expenses_report(user_id, month, year):

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            COALESCE(c.name, p.description) AS name,
            SUM(p.amount) AS total,
            SUM(CASE WHEN p.paid = TRUE THEN p.amount ELSE 0 END) AS paid_total,
            SUM(CASE WHEN p.paid = FALSE THEN p.amount ELSE 0 END) AS open_total
        FROM payments p
        LEFT JOIN categories c ON c.id = p.category_id
        WHERE p.user_id = %s
        AND p.month = %s
        AND p.year = %s
        GROUP BY COALESCE(c.name, p.description)
        ORDER BY COALESCE(c.name, p.description)
        """,
        (user_id, month, year)
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows
