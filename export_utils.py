import io
import pandas as pd

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer


def export_excel_bytes(df: pd.DataFrame, sheet_name: str = "Pagamentos") -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return output.getvalue()


def export_pdf_bytes(df: pd.DataFrame, title: str = "Pagamentos") -> bytes:
    output = io.BytesIO()

    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=24,
        leftMargin=24,
        topMargin=24,
        bottomMargin=24,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "TituloPDF",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#07142d"),
        spaceAfter=6,
    )

    subtitle_style = ParagraphStyle(
        "SubtituloPDF",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=14,
    )

    cell_style = ParagraphStyle(
        "CelulaPDF",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        alignment=TA_LEFT,
    )

    header_style = ParagraphStyle(
        "CabecalhoPDF",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=TA_LEFT,
    )

    story = []

    story.append(Paragraph(title, title_style))
    story.append(Paragraph("Relatório profissional de despesas por período", subtitle_style))

    if df.empty:
        story.append(Paragraph("Sem registros no filtro atual.", styles["Normal"]))
        doc.build(story)
        return output.getvalue()

    df = df.copy()

    # Ordenação profissional
    if "Status" in df.columns and "Categoria" in df.columns and "Descrição" in df.columns:
        df["_status_ordem"] = df["Status"].apply(lambda x: 1 if x == "Pago" else 0)

        df["_tipo_ordem"] = df["Descrição"].astype(str).apply(
            lambda x: 0 if "(" in x and "/" in x and ")" in x else 1
        )

        df = df.sort_values(
            by=["_status_ordem", "Categoria", "_tipo_ordem", "Descrição"],
            ascending=[True, True, True, True],
            kind="mergesort"
        )

        df = df.drop(columns=["_status_ordem", "_tipo_ordem"], errors="ignore")

    total_registros = len(df)

    if "Valor" in df.columns:
        story.append(Paragraph(f"Total de registros: {total_registros}", subtitle_style))
    else:
        story.append(Paragraph(f"Total de registros: {total_registros}", subtitle_style))

    data = []

    data.append([Paragraph(str(col), header_style) for col in df.columns])

    for _, row in df.iterrows():
        data.append([
            Paragraph(str(value), cell_style)
            for value in row.tolist()
        ])

    col_widths = []

    for col in df.columns:
        if col == "Descrição":
            col_widths.append(235)
        elif col == "Categoria":
            col_widths.append(155)
        elif col == "Valor":
            col_widths.append(75)
        elif col in ["Compra", "Vencimento"]:
            col_widths.append(80)
        elif col == "Status":
            col_widths.append(75)
        else:
            col_widths.append(90)

    tbl = Table(
        data,
        colWidths=col_widths,
        repeatRows=1,
        hAlign="CENTER"
    )

    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#07142d")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 8),

        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("TOPPADDING", (0, 1), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
    ])

    for i in range(1, len(data)):
        if i % 2 == 0:
            style.add("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f8fafc"))
        else:
            style.add("BACKGROUND", (0, i), (-1, i), colors.white)

    if "Status" in df.columns:
        status_col = list(df.columns).index("Status")

        for i, value in enumerate(df["Status"].astype(str).tolist(), start=1):
            if "Pago" in value:
                style.add("TEXTCOLOR", (status_col, i), (status_col, i), colors.HexColor("#15803d"))
            else:
                style.add("TEXTCOLOR", (status_col, i), (status_col, i), colors.HexColor("#b45309"))

    tbl.setStyle(style)

    story.append(tbl)
    story.append(Spacer(1, 12))

    footer_style = ParagraphStyle(
        "RodapePDF",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#64748b"),
    )

    story.append(Paragraph("Desenvolvido por Carlos Martins", footer_style))

    doc.build(story)
    return output.getvalue()
