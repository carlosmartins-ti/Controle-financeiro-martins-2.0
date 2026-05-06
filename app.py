import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import streamlit.components.v1 as components

from database import init_db
from auth import authenticate, create_user, get_security_question, reset_password
import repos

# ================= SETUP =================
st.set_page_config(
    page_title="Controle Financeiro",
    page_icon="💳",
    layout="wide"
)

with open("style.css", "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

init_db()

ADMIN_USERNAME = "carlos.martins"

MESES = [
    "Janeiro","Fevereiro","Março","Abril","Maio","Junho",
    "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"
]

# ================= UTILS =================
def fmt_brl(v):
    return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def format_date_br(s):
    if not s:
        return ""
    try:
        return datetime.fromisoformat(str(s)).strftime("%d/%m/%Y")
    except:
        return str(s)

def is_admin():
    return st.session_state.username == ADMIN_USERNAME

# ================= SESSION =================
for k in ["user_id", "username", "edit_id", "msg_ok"]:
    if k not in st.session_state:
        st.session_state[k] = None

if "hide_paid" not in st.session_state:
    st.session_state.hide_paid = False

# ================= COMPLEMENTO (APENAS ADICIONADO) =================
# Estado para controlar "voltar ao app" após gerar PDF
if "pdf_relatorio_path" not in st.session_state:
    st.session_state.pdf_relatorio_path = None

if "pdf_relatorio_nome" not in st.session_state:
    st.session_state.pdf_relatorio_nome = None

# ================= AUTH =================
def screen_auth():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700&family=DM+Sans:wght@400;500&display=swap');

    [data-testid="stAppViewContainer"] > .main {
        background: #f8fafc !important;
    }

    [data-testid="stHeader"] {
        background: transparent !important;
    }

    .block-container {
        max-width: 980px !important;
        padding-top: 42px !important;
    }

    .login-card-wrap {
        background: #ffffff;
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 30px 80px rgba(15, 23, 42, 0.25);
        min-height: 520px;
    }

    .login-left-panel {
        background: #080e1c;
        min-height: 520px;
        padding: 34px 28px;
        position: relative;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .login-left-panel::before {
        content: "";
        position: absolute;
        width: 300px;
        height: 300px;
        border-radius: 50%;
        background: #1d9e75;
        opacity: 0.07;
        top: -100px;
        right: -120px;
    }

    .login-left-panel::after {
        content: "";
        position: absolute;
        width: 160px;
        height: 160px;
        border-radius: 50%;
        background: #1d9e75;
        opacity: 0.05;
        bottom: -40px;
        left: -50px;
    }

    .login-brand-icon {
        width: 46px;
        height: 46px;
        background: #1d9e75;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
        margin-bottom: 12px;
        position: relative;
        z-index: 1;
    }

    .login-brand-name {
        font-family: "Sora", sans-serif;
        font-size: 21px;
        font-weight: 700;
        color: #f1f5f9;
        line-height: 1.25;
        position: relative;
        z-index: 1;
    }

    .login-brand-desc {
        font-size: 12px;
        color: #4b5e78;
        margin-top: 6px;
        position: relative;
        z-index: 1;
    }

    .login-stats {
        display: flex;
        flex-direction: column;
        gap: 12px;
        position: relative;
        z-index: 1;
        margin-top: 34px;
    }

    .login-stat {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 10px;
        padding: 12px 14px;
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .login-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #1d9e75;
        flex-shrink: 0;
    }

    .login-stat-label {
        font-size: 10px;
        color: #4b5e78;
    }

    .login-stat-value {
        font-family: "Sora", sans-serif;
        font-size: 13px;
        font-weight: 600;
        color: #cbd5e1;
    }

    .login-author {
        font-size: 10px;
        color: #253245;
        position: relative;
        z-index: 1;
        line-height: 1.6;
        margin-top: 30px;
    }

    .login-header-only {
        background: #ffffff;
        padding: 28px 26px 8px;
    }

    .login-title {
        font-family: "Sora", sans-serif;
        font-size: 22px;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 4px;
    }

    .login-subtitle {
        font-size: 13px;
        color: #94a3b8;
        margin-bottom: 26px;
    }

    div[data-testid="stTabs"] button[data-baseweb="tab"] {
        color: #94a3b8 !important;
        font-family: "Sora", sans-serif !important;
        font-size: 13px !important;
        font-weight: 600 !important;
    }

    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: #1d9e75 !important;
    }

    div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
        background-color: #1d9e75 !important;
    }

    .stTextInput label,
    .stSelectbox label {
        color: #64748b !important;
        font-size: 12px !important;
        font-weight: 700 !important;
        text-transform: uppercase;
    }

    .stTextInput input {
        background: #f8fafc !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 9px !important;
        color: #0f172a !important;
        height: 44px !important;
    }

    .stButton > button {
        background: #1d9e75 !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        font-family: "Sora", sans-serif !important;
        font-weight: 700 !important;
        height: 44px !important;
        width: 100% !important;
    }

    .stButton > button:hover {
        background: #0f6e56 !important;
        color: #ffffff !important;
    }

    .mobile-login-header {
        display: none;
    }

    @media (max-width: 768px) {
        .block-container {
            padding: 0 !important;
            max-width: 100% !important;
        }

        .login-left-panel {
            display: none;
        }

        .login-header-only {
            padding: 20px 18px 8px;
        }

        .mobile-login-header {
            display: block;
            background: #080e1c;
            border-radius: 14px;
            padding: 18px 18px;
            margin-bottom: 22px;
            position: relative;
            overflow: hidden;
        }

        .mobile-login-header::before {
            content: "";
            position: absolute;
            width: 200px;
            height: 200px;
            border-radius: 50%;
            background: #1d9e75;
            opacity: 0.07;
            top: -80px;
            right: -60px;
        }

        .mobile-login-top {
            display: flex;
            align-items: center;
            gap: 12px;
            position: relative;
            z-index: 1;
        }

        .mobile-login-icon {
            width: 40px;
            height: 40px;
            background: #1d9e75;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }

        .mobile-login-name {
            font-family: "Sora", sans-serif;
            font-size: 17px;
            font-weight: 700;
            color: #f1f5f9;
        }

        .mobile-login-desc {
            font-size: 11px;
            color: #4b5e78;
        }
    }
    </style>
    """, unsafe_allow_html=True)

    col_left, col_right = st.columns([0.42, 0.58], gap="small")

    with col_left:
        html_left = (
            '<div class="login-left-panel">'
            '<div>'
            '<div class="login-brand-icon">💳</div>'
            '<div class="login-brand-name">Controle<br>Financeiro</div>'
            '<div class="login-brand-desc">Gestão inteligente das suas finanças</div>'
            '<div class="login-stats">'
            '<div class="login-stat">'
            '<div class="login-dot"></div>'
            '<div><div class="login-stat-label">Despesas por categoria</div>'
            '<div class="login-stat-value">Organizado e visual</div></div>'
            '</div>'
            '<div class="login-stat">'
            '<div class="login-dot"></div>'
            '<div><div class="login-stat-label">Planejamento mensal</div>'
            '<div class="login-stat-value">Renda vs. gastos</div></div>'
            '</div>'
            '<div class="login-stat">'
            '<div class="login-dot"></div>'
            '<div><div class="login-stat-label">Controle de parcelas</div>'
            '<div class="login-stat-value">Cartão e compras</div></div>'
            '</div>'
            '</div>'
            '</div>'
            '<div class="login-author">'
            'Desenvolvido por <strong style="color:#3d5470">Carlos Martins</strong><br>'
            'cr954479@gmail.com'
            '</div>'
            '</div>'
        )
        st.markdown(html_left, unsafe_allow_html=True)

    with col_right:
        html_right = (
            '<div class="login-header-only">'
            '<div class="mobile-login-header">'
            '<div class="mobile-login-top">'
            '<div class="mobile-login-icon">💳</div>'
            '<div>'
            '<div class="mobile-login-name">Controle Financeiro</div>'
            '<div class="mobile-login-desc">Gestão inteligente das suas finanças</div>'
            '</div>'
            '</div>'
            '</div>'
            '<div class="login-title">Bem-vindo de volta</div>'
            '<div class="login-subtitle">Faça login para acessar sua conta</div>'
            '</div>'
        )
        st.markdown(html_right, unsafe_allow_html=True)

        t1, t2, t3 = st.tabs(["Entrar", "Criar conta", "Recuperar senha"])

        with t1:
            u = st.text_input("Usuário", key="login_user")
            p = st.text_input("Senha", type="password", key="login_pass")

            if st.button("Entrar", key="btn_login", use_container_width=True):
                uid = authenticate(u, p)
                if uid:
                    st.session_state.user_id = uid
                    st.session_state.username = u.strip().lower()
                    st.rerun()
                else:
                    st.error("Usuário ou senha inválidos.")

        with t2:
            u = st.text_input("Novo usuário", key="signup_user")
            p = st.text_input("Nova senha", type="password", key="signup_pass")
            q = st.selectbox(
                "Pergunta de segurança",
                [
                    "Qual o nome do seu primeiro pet?",
                    "Qual o nome da sua mãe?",
                    "Qual sua cidade de nascimento?",
                    "Qual seu filme favorito?"
                ],
                key="signup_q"
            )
            a = st.text_input("Resposta", key="signup_answer")

            if st.button("Criar conta", key="btn_signup", use_container_width=True):
                create_user(u, p, q, a)
                uid = authenticate(u, p)
                st.session_state.user_id = uid
                st.session_state.username = u.strip().lower()
                repos.seed_default_categories(uid)
                st.success("Conta criada com sucesso.")
                st.rerun()

        with t3:
            u = st.text_input("Usuário", key="reset_user")
            q = get_security_question(u) if u else None

            if q:
                st.info(q)
                a = st.text_input("Resposta", key="reset_answer")
                np = st.text_input("Nova senha", type="password", key="reset_pass")

                if st.button("Redefinir senha", key="btn_reset", use_container_width=True):
                    if reset_password(u, a, np):
                        st.success("Senha alterada!")
                    else:
                        st.error("Resposta incorreta.")
# ================= APP =================
def screen_app():
    try:
        if not st.session_state.user_id:
            st.error("Usuário não autenticado.")
            return

        with st.sidebar:
            st.markdown(f"**Usuário:** {st.session_state.username}")
            if is_admin():
                st.caption("🔑 Administrador")


            today = date.today()
            month_label = st.selectbox("Mês", MESES, index=today.month - 1)
            year = st.selectbox("Ano", list(range(today.year - 2, today.year + 3)), index=2)
            month = MESES.index(month_label) + 1

            st.divider()
            page = st.radio(
                "Menu",
                ["📊 Dashboard", "🧾 Despesas", "🏷️ Categorias", "💰 Planejamento"]
            )


            if st.button("Sair", use_container_width=True):
                st.session_state.user_id = None
                st.session_state.username = None
                st.rerun()


        if st.session_state.msg_ok:
            st.toast(st.session_state.msg_ok, icon="✅", duration=15)
            st.session_state.msg_ok = None


        repos.seed_default_categories(st.session_state.user_id)


        rows = repos.list_payments(st.session_state.user_id, month, year)
        df = pd.DataFrame(rows)


        total = float(df["amount"].sum()) if not df.empty else 0.0
        pago = float(df[df["paid"] == True]["amount"].sum()) if not df.empty else 0.0
        aberto = total - pago

        budget = repos.get_budget(st.session_state.user_id, month, year)
        renda = float(budget["income"])

        saldo = float(renda) - float(total)

        st.title("💳 Controle Financeiro")
        st.caption(f"Período: **{month_label}/{year}**")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total do mês", fmt_brl(total))
        c2.metric("Pago", fmt_brl(pago))
        c3.metric("Em aberto", fmt_brl(aberto))
        c4.metric("Saldo", fmt_brl(saldo))

        st.divider()

        # ================= DESPESAS =================
        if page == "🧾 Despesas":
            st.subheader("🧾 Despesas")


            # ===== RELATÓRIO PDF =====
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            import tempfile

            # ================= COMPLEMENTO (APENAS ADICIONADO) =================
            # PDF em formato de TABELA + botão "Voltar ao app"
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
            from reportlab.lib import colors

            col_pdf1, col_pdf2 = st.columns([1.2, 1.2])

            if col_pdf1.button("📄 Gerar PDF (Tabela)"):

                data = repos.list_payments(
                    st.session_state.user_id, month, year
                )

                tmp_tbl = tempfile.NamedTemporaryFile(
                    delete=False, suffix=".pdf"
                )

                doc = SimpleDocTemplate(
                    tmp_tbl.name,
                    pagesize=A4,
                    rightMargin=36,
                    leftMargin=36,
                    topMargin=36,
                    bottomMargin=36,
                )

                table_data = []
                table_data.append(
                    [f"Despesas - {month_label}/{year}", "", ""]
                )
                table_data.append(
                    ["Descrição", "Valor (R$)", "Status"]
                )

                total_tbl = 0.0

                for r in data:
                    nome = (r.get("description") or "").strip()
                    valor = float(r.get("amount") or 0)
                    pago = r.get("paid")

                    total_tbl += valor

                    status = (
                        "Pago"
                        if str(pago).lower() in ["true", "t", "1"]
                        else "Em aberto"
                    )

                    table_data.append(
                        [nome, fmt_brl(valor), status]
                    )

                table_data.append(
                    ["TOTAL", fmt_brl(total_tbl), ""]
                )

                table = Table(
                    table_data, colWidths=[260, 100, 100]
                )

                table.setStyle(
                    TableStyle(
                        [
                            ("SPAN", (0, 0), (-1, 0)),
                            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                            ("FONTSIZE", (0, 0), (-1, 0), 14),
                            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                            ("BACKGROUND", (0, 1), (-1, 1), colors.lightgrey),
                            ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                            ("GRID", (0, 1), (-1, -1), 0.6, colors.grey),
                            ("ALIGN", (1, 2), (1, -1), "RIGHT"),
                            ("ALIGN", (2, 2), (2, -2), "CENTER"),
                            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                            ("BACKGROUND", (0, -1), (-1, -1), colors.whitesmoke),
                        ]
                    )
                )

                doc.build([table])

                st.session_state.pdf_relatorio_path = tmp_tbl.name
                st.session_state.pdf_relatorio_nome = (
                    f"despesas_tabela_{month}_{year}.pdf"
                )

                st.success("PDF gerado com sucesso!")
                st.rerun()



            if st.session_state.pdf_relatorio_path:
                with open(st.session_state.pdf_relatorio_path, "rb") as f:
                    st.download_button(
                        "⬇️ Baixar PDF (Tabela)",
                        f,
                        file_name=st.session_state.pdf_relatorio_nome or f"despesas_tabela_{month}_{year}.pdf",
                        mime="application/pdf"
                    )

                if col_pdf2.button("⬅️ Voltar ao app"):
                    st.session_state.pdf_relatorio_path = None
                    st.session_state.pdf_relatorio_nome = None
                    st.rerun()

            # ===== RESTANTE DO CÓDIGO ORIGINAL =====

            cats = repos.list_categories(st.session_state.user_id)
            cat_map = {r["name"]: r["id"] for r in cats}
            cat_names = ["(Sem categoria)"] + list(cat_map.keys())

            card_cat_ids = [r["id"] for r in cats if r.get("name") and "cart" in str(r.get("name")).lower()]
            credit_rows = [r for r in rows if (r.get("category_id") in card_cat_ids)]

            if credit_rows:
                open_credit = [r for r in credit_rows if not r.get("paid")]
                total_fatura = sum(float(r.get("amount") or 0) for r in open_credit)

                st.divider()
                st.subheader("💳 Fatura do cartão")


                cA, cB = st.columns([2.2, 1.2])
                cA.metric("Total em aberto", fmt_brl(total_fatura))

                if open_credit:
                    if cB.button("💰 Pagar fatura do cartão", key="pay_card"):
                        repos.mark_credit_invoice_paid(st.session_state.user_id, month, year)
                        st.session_state.msg_ok = "Fatura do cartão marcada como paga!"
                        st.rerun()
                else:
                    if cB.button("🔄 Desfazer pagamento da fatura", key="unpay_card"):
                        repos.unmark_credit_invoice_paid(st.session_state.user_id, month, year)
                        st.session_state.msg_ok = "Pagamento da fatura desfeito!"
                        st.rerun()

            with st.expander("➕ Adicionar despesa", expanded=True):
                with st.form("form_add_despesa", clear_on_submit=True):
                    a1, a2, a3, a4, a5, a6 = st.columns([3, 1, 1.3, 1.3, 2, 1])

                    desc = a1.text_input("Descrição")
                    val = a2.number_input("Valor (R$)", min_value=0.0, step=10.0)

                    compra = a3.date_input(
                        "Data da compra",
                        value=date.today(),
                        format="DD/MM/YYYY"
                    )

                    venc = a4.date_input(
                        "Vencimento",
                        value=date.today(),
                        format="DD/MM/YYYY"
                    )

                    cat_name = a5.selectbox("Categoria", cat_names)
                    parcelas = a6.number_input("Parcelas", min_value=1, step=1, value=1)
                    tipo_parcela = st.radio(
                         "Tipo de valor",
                         ["Valor total da compra", "Valor já é por parcela"],
                         horizontal=True
                    )

                    submitted = st.form_submit_button("Adicionar")


            if submitted:
                if not desc.strip():
                    st.warning("Informe a descrição da despesa.")
                elif val <= 0:
                    st.warning("Informe um valor maior que zero.")
                else:
                    cid = None if cat_name == "(Sem categoria)" else cat_map[cat_name]

                    repos.add_payment(
                        st.session_state.user_id,
                        desc.strip(),
                        float(val),
                        str(compra),   # 👈 NOVO
                        str(venc),
                        venc.month,    # 👈 mês baseado no vencimento
                        venc.year, 
                        cid,
                        is_credit=True if parcelas > 1 else False,
                        installments=int(parcelas),
                        parcel_type="total"
                            if tipo_parcela == "Valor total da compra"
                            else "unit"
                    )

                    st.session_state.msg_ok = "Despesa cadastrada com sucesso!"
                    st.rerun()

            st.divider()

            if df.empty:
                st.info("Nenhuma despesa cadastrada.")
            else:
                # Botão ocultar/mostrar pagos
                btn_label = "👁️ Mostrar pagos" if st.session_state.hide_paid else "🙈 Ocultar pagos"
                if st.button(btn_label, key="toggle_paid"):
                    st.session_state.hide_paid = not st.session_state.hide_paid
                    st.rerun()

                # Ordenar: em aberto primeiro, pagos depois
                rows_ordenados = sorted(rows, key=lambda r: (1 if r.get("paid") else 0))

                # Filtrar se ocultar pagos estiver ativo
                rows_visiveis = [r for r in rows_ordenados if not r.get("paid")] \
                    if st.session_state.hide_paid else rows_ordenados

                for r in rows_visiveis:
                    pid = r.get("id")
                    desc_r = r.get("description")
                    amount = r.get("amount")
                    due = r.get("due_date")
                    purchase = r.get("purchase_date")
                    paid = r.get("paid")
                    cat_name_r = r.get("category")

                    is_credit = r.get("is_credit")
                    installments = r.get("installments") or 1
                    credit_group = r.get("credit_group")
                    
                    status_color = "#16a34a" if paid else "#dc2626"
                    status_text = "✅ Pago" if paid else "🕓 Em aberto"
                    
                    with st.container(border=True):
                        
                        st.markdown(
                            f'<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;">'
                            f'<div>'
                            f'<div style="font-size:18px;font-weight:600;">🧾 {desc_r}</div>'
                            f'<div style="opacity:0.7;font-size:13px;">🏷️ {cat_name_r if cat_name_r else ""}</div>'
                            f'</div>'
                            f'<div style="background:{status_color};padding:6px 14px;border-radius:20px;font-size:13px;font-weight:500;white-space:nowrap;">'
                            f'{status_text}'
                            f'</div>'
                            f'</div>',
                            unsafe_allow_html=True
                        )

                        st.markdown(
                            f'<div style="display:flex;justify-content:space-between;align-items:center;margin-top:10px;">'
                            f'<div style="font-size:22px;font-weight:700;">{fmt_brl(amount)}</div>'
                            f'<div style="opacity:0.7;font-size:14px;">Venc: {format_date_br(due)}</div>'
                            f'<div style="opacity:0.7;font-size:12px;">Compra: {format_date_br(purchase)}</div>'
                            f'</div>',
                            unsafe_allow_html=True
                        )

                        col_btn1, col_btn2, col_btn3 = st.columns([1,1,1], gap="small")

                        with col_btn1:
                            if not paid:
                                if st.button("Pagar", key=f"pay_{pid}", use_container_width=True):
                                    repos.mark_paid(st.session_state.user_id, pid, True)
                                    st.session_state.msg_ok = "Despesa marcada como paga!"
                                    st.rerun()
                            else:
                                if st.button("Desfazer", key=f"unpay_{pid}", use_container_width=True):
                                    repos.mark_paid(st.session_state.user_id, pid, False)
                                    st.session_state.msg_ok = "Pagamento desfeito!"
                                    st.rerun()

                        with col_btn2:
                            if st.button("Editar", key=f"edit_{pid}", use_container_width=True):
                                st.session_state.edit_id = pid
                                st.rerun()

                        with col_btn3:
                            if st.button("Excluir", key=f"del_{pid}", use_container_width=True):
                                repos.delete_payment(st.session_state.user_id, pid)
                                st.session_state.msg_ok = "Despesa excluída!"
                                st.rerun()
                                
                    if is_credit and int(installments) > 1 and credit_group:
                        with st.expander("🧩 Compra parcelada"):
                            if st.button("🗑️ Excluir parcelas em aberto", key=f"del_open_{credit_group}_{pid}"):
                                repos.delete_credit_group(
                                    st.session_state.user_id,
                                    credit_group,
                                    only_open=True
                                )
                                st.session_state.msg_ok = "Parcelas em aberto excluídas!"
                                st.rerun()


                            if st.button("❌ Excluir TODA a compra parcelada", key=f"del_all_{credit_group}_{pid}"):
                                repos.delete_credit_group(
                                    st.session_state.user_id,
                                    credit_group,
                                    only_open=False
                                )
                                st.session_state.msg_ok = "Compra parcelada excluída!"
                                st.rerun()


                    if st.session_state.edit_id == pid:
                        with st.form(f"edit_form_{pid}", clear_on_submit=False):
                            n_desc = st.text_input("Descrição", value=str(desc_r or ""))
                            n_val = st.number_input("Valor", value=float(amount or 0), step=10.0)
                            n_compra = st.date_input(
                                "Data da compra",
                                value=datetime.fromisoformat(str(purchase)).date() if purchase else date.today()
                            )
                            n_venc = st.date_input(
                                "Vencimento",
                                value=datetime.fromisoformat(str(due)).date() if due else date.today()
                            )

                            cats2 = repos.list_categories(st.session_state.user_id)
                            cat_map2 = {rr["name"]: rr["id"] for rr in cats2}
                            cat_names2 = ["(Sem categoria)"] + list(cat_map2.keys())
                            current_cat = cat_name_r if cat_name_r in cat_map2 else "(Sem categoria)"


                            n_cat_name = st.selectbox(
                                "Categoria",
                                cat_names2,
                                index=cat_names2.index(current_cat)
                            )

                            col1, col2 = st.columns(2)
                            salvar = col1.form_submit_button("Salvar")
                            cancelar = col2.form_submit_button("Cancelar")


                        if salvar:
                            cid2 = None if n_cat_name == "(Sem categoria)" else cat_map2[n_cat_name]
                            repos.update_payment(
                                st.session_state.user_id,
                                pid,
                                n_desc.strip(),
                                float(n_val),
                                str(n_compra),
                                str(n_venc),
                                cid2
                            )
                            st.session_state.edit_id = None
                            st.session_state.msg_ok = "Despesa atualizada com sucesso!"
                            st.rerun()


                        if cancelar:
                            st.session_state.edit_id = None
                            st.rerun()
                            
        if page == "📊 Dashboard":
            st.subheader("📊 Dashboard")
            if not df.empty:
                fig = px.pie(df, names="category", values="amount")
                st.plotly_chart(fig, use_container_width=True)

        if page == "🏷️ Categorias":
            st.subheader("🏷️ Categorias")

            with st.form("form_categoria", clear_on_submit=True):
                new_cat = st.text_input("Nova categoria")
                submitted_cat = st.form_submit_button("Adicionar")

            if submitted_cat and new_cat.strip():
                repos.create_category(st.session_state.user_id, new_cat.strip())
                st.session_state.msg_ok = "Categoria cadastrada com sucesso!"
                st.rerun()

            for r in repos.list_categories(st.session_state.user_id):
                cid = r.get("id")
                name = r.get("name")

                a, b = st.columns([4, 1])
                a.write(name)

                if b.button("Excluir", key=f"cat_del_{cid}"):
                    repos.delete_category(st.session_state.user_id, cid)
                    st.session_state.msg_ok = "Categoria excluída!"
                    st.rerun()

        if page == "💰 Planejamento":
            st.subheader("💰 Planejamento")
            renda_v = st.number_input("Renda", value=float(renda))
            meta_v = st.number_input("Meta de gastos", value=float(budget["expense_goal"]))
            if st.button("Salvar"):
                repos.upsert_budget(st.session_state.user_id, month, year, renda_v, meta_v)
                st.session_state.msg_ok = "Planejamento salvo com sucesso!"
                st.rerun()


    except Exception as e:
        st.exception(e)
        st.stop()


# ================= ROUTER =================
if st.session_state.user_id is None:
    screen_auth()
else:
    screen_app()
