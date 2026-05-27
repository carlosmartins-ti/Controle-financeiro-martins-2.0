import os
from datetime import date, datetime
from io import BytesIO

import pandas as pd
from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from database import init_db, get_connection
from auth import (
    authenticate,
    authenticate_full,
    create_user,
    get_security_question,
    reset_password,
    admin_list_users,
    admin_create_user,
    admin_delete_user,
    admin_reset_password
)
import repos
from export_utils import export_pdf_bytes, export_excel_bytes

ADMIN_USERNAME = "carlos.martins"
MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
]
SECURITY_QUESTIONS = [
    "Qual o nome do seu primeiro pet?",
    "Qual o nome da sua mãe?",
    "Qual sua cidade de nascimento?",
    "Qual seu filme favorito?",
]

app = FastAPI(title="Controle Financeiro")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "troque-essa-chave-em-producao"),
    same_site="lax",
    https_only=False,
)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def fmt_brl(v):
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def format_date_br(s):
    if not s:
        return ""
    try:
        return datetime.fromisoformat(str(s)).strftime("%d/%m/%Y")
    except Exception:
        try:
            return s.strftime("%d/%m/%Y")
        except Exception:
            return str(s)


templates.env.filters["brl"] = fmt_brl
templates.env.filters["datebr"] = format_date_br


def parse_bool(value):
    return str(value).lower() in {"true", "t", "1", "sim", "yes", "on"}


def current_user(request: Request):
    uid = request.session.get("user_id")
    username = request.session.get("username")
    is_superuser = request.session.get("is_superuser", False)

    if not uid or not username:
        return None

    return {
        "id": int(uid),
        "username": username,
        "is_admin": username == ADMIN_USERNAME,
        "is_superuser": bool(is_superuser)
    }


def require_login(request: Request):
    user = current_user(request)
    if not user:
        return None
    return user


def require_superuser(request: Request):
    user = current_user(request)

    if not user:
        return None

    if not bool(user.get("is_superuser")):
        return None

    return user


def redirect(path: str):
    return RedirectResponse(path, status_code=303)


def month_year_defaults(month: int | None, year: int | None):
    today = date.today()
    return month or today.month, year or today.year


def base_context(request: Request, user: dict, month: int, year: int, page: str):
    rows = repos.list_payments(user["id"], month, year) or []
    total = sum(float(r.get("amount") or 0) for r in rows)
    pago = sum(float(r.get("amount") or 0) for r in rows if parse_bool(r.get("paid")))
    aberto = total - pago
    budget = repos.get_budget(user["id"], month, year)
    renda = float(budget.get("income") or 0)
    saldo = renda - total
    return {
        "request": request,
        "user": user,
        "page": page,
        "month": month,
        "year": year,
        "month_label": MESES[month - 1],
        "meses": list(enumerate(MESES, start=1)),
        "years": list(range(date.today().year - 2, date.today().year + 3)),
        "rows": rows,
        "total": total,
        "pago": pago,
        "aberto": aberto,
        "budget": budget,
        "renda": renda,
        "saldo": saldo,
        "msg": request.query_params.get("msg"),
        "err": request.query_params.get("err"),
    }


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def login_page(request: Request):
    user = current_user(request)

    if user:
        if bool(user.get("is_superuser")):
            return redirect("/admin/usuarios")
        return redirect("/dashboard")

    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "request": request,
            "tab": request.query_params.get("tab", "entrar"),
            "err": request.query_params.get("err"),
            "msg": request.query_params.get("msg"),
            "security_questions": SECURITY_QUESTIONS,
        },
    )


@app.post("/login")
def login(request: Request, username: str = Form(""), password: str = Form("")):
    user = authenticate_full(username, password)

    if not user:
        return redirect("/?err=Usuário ou senha inválidos.")

    request.session["user_id"] = int(user["id"])
    request.session["username"] = user["username"]
    request.session["is_superuser"] = bool(user["is_superuser"])

    repos.seed_default_categories(int(user["id"]))

    if bool(user["is_superuser"]):
        return redirect("/admin/usuarios")

    return redirect("/dashboard?msg=Login realizado com sucesso.")


@app.post("/signup")
def signup(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
    security_question: str = Form(""),
    security_answer: str = Form(""),
):
    try:
        create_user(username, password, security_question, security_answer)
        uid = authenticate(username, password)
        request.session["user_id"] = int(uid)
        request.session["username"] = username.strip().lower()
        request.session["is_superuser"] = False
        repos.seed_default_categories(int(uid))
        return redirect("/dashboard?msg=Conta criada com sucesso.")
    except Exception as e:
        return redirect(f"/?tab=criar&err={str(e)}")


@app.post("/reset-password")
def reset_pass(username: str = Form(""), answer: str = Form(""), new_password: str = Form("")):
    try:
        ok = reset_password(username, answer, new_password)
        if ok:
            return redirect("/?msg=Senha alterada com sucesso.")
        return redirect("/?tab=recuperar&err=Resposta incorreta ou usuário não encontrado.")
    except Exception as e:
        return redirect(f"/?tab=recuperar&err={str(e)}")


@app.post("/security-question")
def security_question(username: str = Form("")):
    q = get_security_question(username) if username else None
    if not q:
        return redirect("/?tab=recuperar&err=Usuário não encontrado.")
    return redirect(f"/?tab=recuperar&msg={q}")


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return redirect("/?msg=Você saiu do sistema.")


@app.get("/admin/usuarios")
def admin_usuarios(request: Request):
    user = require_superuser(request)

    if not user:
        return redirect("/")

    users = admin_list_users()

    return templates.TemplateResponse(
        request,
        "admin_usuarios.html",
        {
            "request": request,
            "user": user,
            "users": users,
            "msg": request.query_params.get("msg"),
            "err": request.query_params.get("err"),
        }
    )


@app.post("/admin/usuarios/criar")
def admin_create(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    user = require_superuser(request)

    if not user:
        return redirect("/")

    try:
        admin_create_user(
            username=username,
            password=password,
            is_superuser=False
        )

        return redirect("/admin/usuarios?msg=Usuário criado com sucesso.")

    except Exception as e:
        return redirect(f"/admin/usuarios?err={str(e)}")


@app.post("/admin/usuarios/excluir")
def admin_delete(
    request: Request,
    user_id: int = Form(...),
):
    user = require_superuser(request)

    if not user:
        return redirect("/")

    if int(user_id) == int(user["id"]):
        return redirect("/admin/usuarios?err=Você não pode excluir seu próprio usuário.")

    admin_delete_user(user_id)

    return redirect("/admin/usuarios?msg=Usuário excluído.")


@app.post("/admin/usuarios/resetar")
def admin_reset(
    request: Request,
    user_id: int = Form(...),
    new_password: str = Form(...),
):
    user = require_superuser(request)

    if not user:
        return redirect("/")

    try:
        admin_reset_password(user_id, new_password)
        return redirect("/admin/usuarios?msg=Senha redefinida.")

    except Exception as e:
        return redirect(f"/admin/usuarios?err={str(e)}")


@app.get("/dashboard")
def dashboard(request: Request, month: int | None = Query(None), year: int | None = Query(None)):
    user = require_login(request)
    if not user:
        return redirect("/")

    if bool(user.get("is_superuser")):
        return redirect("/admin/usuarios")

    month, year = month_year_defaults(month, year)
    ctx = base_context(request, user, month, year, "dashboard")
    report = repos.get_expenses_report(user["id"], month, year) or []
    max_total = max([float(r.get("total") or 0) for r in report], default=0)
    ctx.update({"report": report, "max_total": max_total})

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        ctx
    )


@app.get("/despesas")
def despesas(
    request: Request,
    month: int | None = Query(None),
    year: int | None = Query(None),
    hide_paid: int = Query(0),
):
    user = require_login(request)
    if not user:
        return redirect("/")

    if bool(user.get("is_superuser")):
        return redirect("/admin/usuarios")

    month, year = month_year_defaults(month, year)
    ctx = base_context(request, user, month, year, "despesas")
    cats = repos.list_categories(user["id"]) or []
    card_cat_ids = [r["id"] for r in cats if r.get("name") and "cart" in str(r.get("name")).lower()]
    credit_rows = [r for r in ctx["rows"] if r.get("category_id") in card_cat_ids]
    open_credit = [r for r in credit_rows if not parse_bool(r.get("paid"))]
    total_fatura = sum(float(r.get("amount") or 0) for r in open_credit)
    visible_rows = sorted(ctx["rows"], key=lambda r: (1 if parse_bool(r.get("paid")) else 0, str(r.get("due_date") or "")))
    if hide_paid:
        visible_rows = [r for r in visible_rows if not parse_bool(r.get("paid"))]
    ctx.update({
        "categories": cats,
        "hide_paid": hide_paid,
        "visible_rows": visible_rows,
        "credit_rows": credit_rows,
        "open_credit": open_credit,
        "total_fatura": total_fatura,
    })
    return templates.TemplateResponse(request, "despesas.html", ctx)


@app.post("/despesas/add")
def add_despesa(
    request: Request,
    description: str = Form(""),
    amount: float = Form(0),
    purchase_date: str = Form(""),
    due_date: str = Form(""),
    category_id: str = Form(""),
    installments: int = Form(1),
    parcel_type: str = Form("total"),
):
    user = require_login(request)
    if not user:
        return redirect("/")

    if bool(user.get("is_superuser")):
        return redirect("/admin/usuarios")

    try:
        due = datetime.fromisoformat(due_date).date()
        cid = int(category_id) if category_id else None
        repos.add_payment(
            user["id"], description.strip(), float(amount), purchase_date, due_date,
            due.month, due.year, cid,
            is_credit=True if installments > 1 else False,
            installments=int(installments), parcel_type=parcel_type,
        )
        return redirect(f"/despesas?month={due.month}&year={due.year}&msg=Despesa cadastrada com sucesso.")
    except Exception as e:
        return redirect(f"/despesas?err={str(e)}")


@app.post("/despesas/{payment_id}/paid")
def toggle_paid(request: Request, payment_id: int, paid: int = Form(1), month: int = Form(...), year: int = Form(...)):
    user = require_login(request)
    if not user:
        return redirect("/")

    if bool(user.get("is_superuser")):
        return redirect("/admin/usuarios")

    repos.mark_paid(user["id"], payment_id, bool(paid))
    return redirect(f"/despesas?month={month}&year={year}&msg=Despesa atualizada.")


@app.post("/despesas/{payment_id}/delete")
def delete_despesa(request: Request, payment_id: int, month: int = Form(...), year: int = Form(...)):
    user = require_login(request)
    if not user:
        return redirect("/")

    if bool(user.get("is_superuser")):
        return redirect("/admin/usuarios")

    repos.delete_payment(user["id"], payment_id)
    return redirect(f"/despesas?month={month}&year={year}&msg=Despesa excluída.")


@app.post("/despesas/{payment_id}/edit")
def edit_despesa(
    request: Request,
    payment_id: int,
    month: int = Form(...),
    year: int = Form(...),
    description: str = Form(""),
    amount: float = Form(0),
    purchase_date: str = Form(""),
    due_date: str = Form(""),
    category_id: str = Form(""),
):
    user = require_login(request)
    if not user:
        return redirect("/")

    if bool(user.get("is_superuser")):
        return redirect("/admin/usuarios")

    cid = int(category_id) if category_id else None
    repos.update_payment(user["id"], payment_id, description.strip(), float(amount), purchase_date, due_date, cid)
    return redirect(f"/despesas?month={month}&year={year}&msg=Despesa atualizada com sucesso.")


@app.post("/despesas/credit/pay")
def pay_credit(request: Request, month: int = Form(...), year: int = Form(...)):
    user = require_login(request)
    if not user:
        return redirect("/")

    if bool(user.get("is_superuser")):
        return redirect("/admin/usuarios")

    repos.mark_credit_invoice_paid(user["id"], month, year)
    return redirect(f"/despesas?month={month}&year={year}&msg=Fatura marcada como paga.")


@app.post("/despesas/credit/unpay")
def unpay_credit(request: Request, month: int = Form(...), year: int = Form(...)):
    user = require_login(request)
    if not user:
        return redirect("/")

    if bool(user.get("is_superuser")):
        return redirect("/admin/usuarios")

    repos.unmark_credit_invoice_paid(user["id"], month, year)
    return redirect(f"/despesas?month={month}&year={year}&msg=Pagamento da fatura desfeito.")


@app.post("/despesas/credit/delete-group")
def delete_credit_group(
    request: Request,
    credit_group: int = Form(...),
    only_open: int = Form(1),
    month: int = Form(...),
    year: int = Form(...),
):
    user = require_login(request)
    if not user:
        return redirect("/")

    if bool(user.get("is_superuser")):
        return redirect("/admin/usuarios")

    repos.delete_credit_group(user["id"], credit_group, only_open=bool(only_open))
    return redirect(f"/despesas?month={month}&year={year}&msg=Compra parcelada excluída.")


@app.post("/despesas/credit/update-installments")
def update_credit_installments(
    request: Request,
    credit_group: int = Form(...),
    new_installments: int = Form(...),
    month: int = Form(...),
    year: int = Form(...),
):
    user = require_login(request)
    if not user:
        return redirect("/")

    if bool(user.get("is_superuser")):
        return redirect("/admin/usuarios")

    try:
        repos.update_credit_group_installments(
            user["id"],
            credit_group,
            new_installments
        )

        return redirect(
            f"/despesas?month={month}&year={year}&msg=Parcelas atualizadas com sucesso."
        )

    except Exception as e:
        return redirect(
            f"/despesas?month={month}&year={year}&err={str(e)}"
        )


@app.get("/despesas/pdf")
def download_pdf(request: Request, month: int, year: int):
    user = require_login(request)
    if not user:
        return redirect("/")

    if bool(user.get("is_superuser")):
        return redirect("/admin/usuarios")

    rows = repos.list_payments(user["id"], month, year) or []

    df = pd.DataFrame([
        {
            "Descrição": r.get("description"),
            "Categoria": r.get("category") or "",
            "Valor": fmt_brl(r.get("amount") or 0),
            "Compra": format_date_br(r.get("purchase_date")),
            "Vencimento": format_date_br(r.get("due_date")),
            "Status": "Pago" if parse_bool(r.get("paid")) else "Em aberto",
        }
        for r in rows
    ])

    if not df.empty:
        df["_status_ordem"] = df["Status"].apply(lambda x: 1 if x == "Pago" else 0)

        df["_parcelada_ordem"] = df["Descrição"].astype(str).apply(
            lambda x: 0 if "(" in x and "/" in x and ")" in x else 1
        )

        df = df.sort_values(
            by=["_status_ordem", "Categoria", "_parcelada_ordem", "Descrição"],
            ascending=[True, True, True, True],
            kind="mergesort"
        )

        df = df.drop(
            columns=["_status_ordem", "_parcelada_ordem"],
            errors="ignore"
        )

    pdf = export_pdf_bytes(df, f"Despesas - {MESES[month - 1]}/{year}")

    return StreamingResponse(
        BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=despesas_{month}_{year}.pdf"},
    )
    


@app.get("/despesas/excel")
def download_excel(request: Request, month: int, year: int):
    user = require_login(request)
    if not user:
        return redirect("/")

    if bool(user.get("is_superuser")):
        return redirect("/admin/usuarios")

    rows = repos.list_payments(user["id"], month, year) or []
    df = pd.DataFrame(rows)
    data = export_excel_bytes(df, "Pagamentos")
    return StreamingResponse(
        BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=despesas_{month}_{year}.xlsx"},
    )


@app.get("/categorias")
def categorias(request: Request, month: int | None = Query(None), year: int | None = Query(None)):
    user = require_login(request)
    if not user:
        return redirect("/")

    if bool(user.get("is_superuser")):
        return redirect("/admin/usuarios")

    month, year = month_year_defaults(month, year)
    ctx = base_context(request, user, month, year, "categorias")
    ctx.update({"categories": repos.list_categories(user["id"]) or []})
    return templates.TemplateResponse(request, "categorias.html", ctx)


@app.post("/categorias/add")
def add_categoria(request: Request, name: str = Form(""), month: int = Form(...), year: int = Form(...)):
    user = require_login(request)
    if not user:
        return redirect("/")

    if bool(user.get("is_superuser")):
        return redirect("/admin/usuarios")

    if name.strip():
        repos.create_category(user["id"], name.strip())
    return redirect(f"/categorias?month={month}&year={year}&msg=Categoria cadastrada.")


@app.post("/categorias/{category_id}/delete")
def delete_categoria(request: Request, category_id: int, month: int = Form(...), year: int = Form(...)):
    user = require_login(request)
    if not user:
        return redirect("/")

    if bool(user.get("is_superuser")):
        return redirect("/admin/usuarios")

    repos.delete_category(user["id"], category_id)
    return redirect(f"/categorias?month={month}&year={year}&msg=Categoria excluída.")


@app.get("/planejamento")
def planejamento(request: Request, month: int | None = Query(None), year: int | None = Query(None)):
    user = require_login(request)
    if not user:
        return redirect("/")

    if bool(user.get("is_superuser")):
        return redirect("/admin/usuarios")

    month, year = month_year_defaults(month, year)
    ctx = base_context(request, user, month, year, "planejamento")
    return templates.TemplateResponse(request, "planejamento.html", ctx)


@app.post("/planejamento/save")
def save_planejamento(
    request: Request,
    month: int = Form(...),
    year: int = Form(...),
    income: float = Form(0),
    expense_goal: float = Form(0),
):
    user = require_login(request)
    if not user:
        return redirect("/")

    if bool(user.get("is_superuser")):
        return redirect("/admin/usuarios")

    repos.upsert_budget(user["id"], month, year, income, expense_goal)
    return redirect(f"/planejamento?month={month}&year={year}&msg=Planejamento salvo com sucesso.")
