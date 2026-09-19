# -*- coding: utf-8 -*-
"""
pdf_reports.py
---------------
توليد تقارير PDF احترافية بالعربي لبرنامج Horria Lab
يحتاج خط عربي TTF موضوع في مجلد fonts/ (راجع README.md)
"""

import os
from datetime import datetime

import arabic_reshaper
from bidi.algorithm import get_display

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

APP_NAME = "Horria Lab"
DEVELOPER = "Developed By Eng. Ahmed Adel"

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
FONT_REGULAR_NAME = "ArabicRegular"
FONT_BOLD_NAME = "ArabicBold"

_FONTS_READY = False


def _find_font_file(preferred_names):
    if not os.path.isdir(FONT_DIR):
        return None
    files = os.listdir(FONT_DIR)
    for name in preferred_names:
        for f in files:
            if name.lower() in f.lower() and f.lower().endswith(".ttf"):
                return os.path.join(FONT_DIR, f)
    ttfs = [f for f in files if f.lower().endswith(".ttf")]
    return os.path.join(FONT_DIR, ttfs[0]) if ttfs else None


def setup_fonts():
    """يسجل الخط العربي في reportlab. لازم يتنفذ مرة قبل أي تقرير."""
    global _FONTS_READY
    if _FONTS_READY:
        return

    regular = _find_font_file(["regular", "amiri-regular", "notonaskharabic-regular", "cairo-regular"])
    bold = _find_font_file(["bold", "amiri-bold", "notonaskharabic-bold", "cairo-bold"]) or regular

    if not regular:
        raise FileNotFoundError(
            "لم يتم العثور على خط عربي TTF داخل مجلد fonts/\n"
            "من فضلك حمّل خط عربي (مثلاً Amiri أو Noto Naskh Arabic أو Cairo) "
            "وضع ملف .ttf داخل مجلد fonts بجانب البرنامج. راجع README.md."
        )

    pdfmetrics.registerFont(TTFont(FONT_REGULAR_NAME, regular))
    pdfmetrics.registerFont(TTFont(FONT_BOLD_NAME, bold))
    _FONTS_READY = True


def ar(text):
    """يجهز النص العربي للعرض الصحيح (اتجاه ولصق الحروف) داخل PDF."""
    if text is None:
        return ""
    text = str(text)
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def _styles():
    title_style = ParagraphStyle(
        "TitleAr", fontName=FONT_BOLD_NAME, fontSize=20, alignment=TA_CENTER,
        textColor=colors.HexColor("#1B4332"), spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "SubtitleAr", fontName=FONT_REGULAR_NAME, fontSize=11, alignment=TA_CENTER,
        textColor=colors.HexColor("#555555"), spaceAfter=2,
    )
    section_style = ParagraphStyle(
        "SectionAr", fontName=FONT_BOLD_NAME, fontSize=13, alignment=TA_RIGHT,
        textColor=colors.HexColor("#1B4332"), spaceBefore=10, spaceAfter=6,
    )
    normal_style = ParagraphStyle(
        "NormalAr", fontName=FONT_REGULAR_NAME, fontSize=10, alignment=TA_RIGHT,
    )
    return title_style, subtitle_style, section_style, normal_style


def _header_flowables(report_title, extra_line=""):
    setup_fonts()
    title_style, subtitle_style, section_style, normal_style = _styles()
    flow = []
    flow.append(Paragraph(ar(APP_NAME), title_style))
    flow.append(Paragraph(ar(DEVELOPER), subtitle_style))
    flow.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1B4332"), spaceBefore=6, spaceAfter=10))
    flow.append(Paragraph(ar(report_title), section_style))
    if extra_line:
        flow.append(Paragraph(ar(extra_line), subtitle_style))
    flow.append(Spacer(1, 8))
    return flow


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONT_REGULAR_NAME if _FONTS_READY else "Helvetica", 8)
    canvas.setFillColor(colors.grey)
    footer_text = get_display(arabic_reshaper.reshape(
        f"{APP_NAME} | {DEVELOPER} | صفحة {doc.page}"
    ))
    canvas.drawCentredString(A4[0] / 2, 1.2 * cm, footer_text)
    canvas.restoreState()


def _status_color(status):
    if "مقبول" in status:
        return colors.HexColor("#2E7D32")
    if "مرفوض" in status:
        return colors.HexColor("#C62828")
    return colors.black


def _build_table(rows, col_headers, col_widths):
    """rows: list of lists (بترتيب من اليمين لليسار كما ستُعرض)."""
    setup_fonts()
    data = [[ar(h) for h in col_headers]] + rows
    table = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("FONTNAME", (0, 0), (-1, -1), FONT_REGULAR_NAME),
        ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD_NAME),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B4332")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F6F5")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    table.setStyle(TableStyle(style))
    return table


def daily_report(records, date_str, out_path):
    """
    records: قائمة dict بالأعمدة (التاريخ, نوع الوارد, اسم المورد, اسم المنتج, الحالة, ملاحظات)
    date_str: التاريخ المطلوب بصيغة YYYY-MM-DD
    """
    day_rows = [r for r in records if str(r.get("التاريخ", "")).strip() == date_str]

    doc = SimpleDocTemplate(
        out_path, pagesize=A4,
        rightMargin=1.5 * cm, leftMargin=1.5 * cm, topMargin=1.3 * cm, bottomMargin=1.5 * cm,
    )

    flow = _header_flowables("التقرير اليومي للتوريدات", f"التاريخ: {date_str}")

    accepted = [r for r in day_rows if "مقبول" in str(r.get("الحالة", ""))]
    rejected = [r for r in day_rows if "مرفوض" in str(r.get("الحالة", ""))]

    _, _, section_style, normal_style = _styles()
    summary_text = (
        f"إجمالي عدد التوريدات: {len(day_rows)}   |   "
        f"مقبول: {len(accepted)}   |   مرفوض: {len(rejected)}"
    )
    flow.append(Paragraph(ar(summary_text), normal_style))
    flow.append(Spacer(1, 12))

    if day_rows:
        col_headers = ["ملاحظات", "الحالة", "الكمية", "اسم المنتج", "اسم المورد", "نوع الوارد"]
        rows = []
        for r in day_rows:
            qty = str(r.get("الكمية", "") or "").strip()
            unit = str(r.get("الوحدة", "") or "").strip()
            qty_str = f"{qty} {unit}".strip() or "-"
            rows.append([
                ar(r.get("ملاحظات", "") or "-"),
                ar(r.get("الحالة", "")),
                ar(qty_str),
                ar(r.get("اسم المنتج", "")),
                ar(r.get("اسم المورد", "")),
                ar(r.get("نوع الوارد", "")),
            ])
        widths = [3.2 * cm, 2 * cm, 2.3 * cm, 3.2 * cm, 3.2 * cm, 3.6 * cm]
        flow.append(_build_table(rows, col_headers, widths))
    else:
        flow.append(Paragraph(ar("لا توجد توريدات مسجلة في هذا اليوم."), normal_style))

    flow.append(Spacer(1, 16))
    flow.append(Paragraph(
        ar(f"تم إصدار التقرير بتاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}"),
        ParagraphStyle("small", fontName=FONT_REGULAR_NAME, fontSize=8, alignment=TA_CENTER, textColor=colors.grey),
    ))

    doc.build(flow, onFirstPage=_footer, onLaterPages=_footer)
    return out_path


def monthly_rejected_report(records, year, month, out_path):
    month_str = f"{year:04d}-{month:02d}"
    month_rows = [r for r in records if str(r.get("التاريخ", "")).strip().startswith(month_str)]
    rejected = [r for r in month_rows if "مرفوض" in str(r.get("الحالة", ""))]

    doc = SimpleDocTemplate(
        out_path, pagesize=A4,
        rightMargin=1.5 * cm, leftMargin=1.5 * cm, topMargin=1.3 * cm, bottomMargin=1.5 * cm,
    )
    flow = _header_flowables("التقرير الشهري - حالات الرفض", f"الشهر: {month_str}")

    _, _, section_style, normal_style = _styles()
    flow.append(Paragraph(ar(f"إجمالي عدد حالات الرفض هذا الشهر: {len(rejected)}"), normal_style))
    flow.append(Spacer(1, 12))

    if rejected:
        col_headers = ["ملاحظات", "الكمية", "اسم المنتج", "اسم المورد", "نوع الوارد", "التاريخ"]
        rows = []
        for r in rejected:
            qty = str(r.get("الكمية", "") or "").strip()
            unit = str(r.get("الوحدة", "") or "").strip()
            qty_str = f"{qty} {unit}".strip() or "-"
            rows.append([
                ar(r.get("ملاحظات", "") or "-"),
                ar(qty_str),
                ar(r.get("اسم المنتج", "")),
                ar(r.get("اسم المورد", "")),
                ar(r.get("نوع الوارد", "")),
                ar(r.get("التاريخ", "")),
            ])
        widths = [3.2 * cm, 2.2 * cm, 3 * cm, 3 * cm, 3 * cm, 2.4 * cm]
        flow.append(_build_table(rows, col_headers, widths))

        flow.append(Spacer(1, 16))
        flow.append(Paragraph(ar("عدد حالات الرفض حسب المورد:"), section_style))

        counts = {}
        for r in rejected:
            s = r.get("اسم المورد", "غير محدد")
            counts[s] = counts.get(s, 0) + 1
        counts_sorted = sorted(counts.items(), key=lambda x: -x[1])

        rows2 = [[ar(str(c)), ar(s)] for s, c in counts_sorted]
        flow.append(_build_table(rows2, ["عدد مرات الرفض", "اسم المورد"], [4 * cm, 6 * cm]))
    else:
        flow.append(Paragraph(ar("لا توجد حالات رفض مسجلة هذا الشهر."), normal_style))

    doc.build(flow, onFirstPage=_footer, onLaterPages=_footer)
    return out_path


def supplier_report(records, supplier_query, out_path):
    """تقرير عن مورد معين: كل توريداته وعدد مرات الرفض."""
    supplier_rows = [
        r for r in records
        if supplier_query.strip() in str(r.get("اسم المورد", "")).strip()
    ]
    rejected = [r for r in supplier_rows if "مرفوض" in str(r.get("الحالة", ""))]
    accepted = [r for r in supplier_rows if "مقبول" in str(r.get("الحالة", ""))]

    doc = SimpleDocTemplate(
        out_path, pagesize=A4,
        rightMargin=1.5 * cm, leftMargin=1.5 * cm, topMargin=1.3 * cm, bottomMargin=1.5 * cm,
    )
    flow = _header_flowables("تقرير مورد", f"بحث عن: {supplier_query}")

    _, _, section_style, normal_style = _styles()
    summary = (
        f"إجمالي التوريدات: {len(supplier_rows)}   |   "
        f"مقبول: {len(accepted)}   |   مرفوض: {len(rejected)}"
    )
    flow.append(Paragraph(ar(summary), normal_style))
    flow.append(Spacer(1, 12))

    if supplier_rows:
        col_headers = ["ملاحظات", "الحالة", "الكمية", "اسم المنتج", "نوع الوارد", "التاريخ"]
        rows = []
        for r in supplier_rows:
            qty = str(r.get("الكمية", "") or "").strip()
            unit = str(r.get("الوحدة", "") or "").strip()
            qty_str = f"{qty} {unit}".strip() or "-"
            rows.append([
                ar(r.get("ملاحظات", "") or "-"),
                ar(r.get("الحالة", "")),
                ar(qty_str),
                ar(r.get("اسم المنتج", "")),
                ar(r.get("نوع الوارد", "")),
                ar(r.get("التاريخ", "")),
            ])
        widths = [2.8 * cm, 2 * cm, 2.2 * cm, 3 * cm, 3 * cm, 2.3 * cm]
        flow.append(_build_table(rows, col_headers, widths))
    else:
        flow.append(Paragraph(ar("لا توجد سجلات لهذا المورد."), normal_style))

    doc.build(flow, onFirstPage=_footer, onLaterPages=_footer)
    return out_path
