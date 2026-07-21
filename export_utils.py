import io
from collections.abc import Mapping

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _records_list(records):
    return [dict(row) if isinstance(row, Mapping) else dict(row) for row in (records or [])]


def export_excel_bytes(records, sheet_name: str = "Pagamentos") -> bytes:
    """Gera Excel diretamente, sem carregar a biblioteca pandas."""
    rows = _records_list(records)
    output = io.BytesIO()

    workbook = Workbook(write_only=True)
    sheet = workbook.create_sheet(title=sheet_name[:31] or "Pagamentos")

    if rows:
        headers = list(rows[0].keys())
        sheet.append(headers)

        for row in rows:
            sheet.append([row.get(header) for header in headers])

    workbook.save(output)
    return output.getvalue()


def export_pdf_bytes(records, title: str = "Pagamentos") -> bytes:
    """Gera PDF a partir de uma lista de registros."""
    rows = _records_list(records)
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

    story = [
        Paragraph(title, title_style),
        Paragraph("Relatório profissional de despesas por período", subtitle_style),
    ]

    if not rows:
        story.append(Paragraph("Sem registros no filtro atual.", styles["Normal"]))
        doc.build(story)
        return output.getvalue()

    def order_key(row):
        status = str(row.get("Status") or "")
        description = str(row.get("Descrição") or "")
        category = str(row.get("Categoria") or "")
        status_order = 1 if status == "Pago" else 0
        installment_order = 0 if "(" in description and "/" in description and ")" in description else 1
        return status_order, category.casefold(), installment_order, description.casefold()

    rows.sort(key=order_key)
    headers = list(rows[0].keys())

    story.append(Paragraph(f"Total de registros: {len(rows)}", subtitle_style))

    data = [[Paragraph(str(column), header_style) for column in headers]]
    for row in rows:
        data.append([
            Paragraph(str(row.get(column, "") if row.get(column, "") is not None else ""), cell_style)
            for column in headers
        ])

    col_widths = []
    for column in headers:
        if column == "Descrição":
            col_widths.append(235)
        elif column == "Categoria":
            col_widths.append(155)
        elif column == "Valor":
            col_widths.append(75)
        elif column in ["Compra", "Vencimento"]:
            col_widths.append(80)
        elif column == "Status":
            col_widths.append(75)
        else:
            col_widths.append(90)

    table = Table(data, colWidths=col_widths, repeatRows=1, hAlign="CENTER")
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

    for index in range(1, len(data)):
        background = colors.HexColor("#f8fafc") if index % 2 == 0 else colors.white
        style.add("BACKGROUND", (0, index), (-1, index), background)

    if "Status" in headers:
        status_column = headers.index("Status")
        for index, row in enumerate(rows, start=1):
            text_color = colors.HexColor("#15803d") if "Pago" in str(row.get("Status")) else colors.HexColor("#b45309")
            style.add("TEXTCOLOR", (status_column, index), (status_column, index), text_color)

    table.setStyle(style)
    story.append(table)
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
