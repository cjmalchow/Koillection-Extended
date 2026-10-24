import io
import math
from datetime import datetime
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    PageBreak,
    KeepTogether
)
from reportlab.pdfgen import canvas

from icons import (
    get_type_icon_image,
    get_finish_icon_image,
    generate_opacity_dots_image,
    generate_star_rating_image,
    generate_color_swatch_image,
    compute_effective_secondary_hex
)

PAGE_WIDTH, PAGE_HEIGHT = letter
MARGIN = 36.0
USABLE_WIDTH = PAGE_WIDTH - (2 * MARGIN)  # 540 points

TYPE_DISPLAY_NAMES = {
    "regular nail lacquer": "Regular Lacquer",
    "uv gel nail lacquer": "UV Gel Lacquer",
    "top coat": "Top Coat",
    "base coat": "Base Coat",
    "baee coat": "Base Coat",
    "cuticle oil": "Cuticle Oil",
    "nail treatment": "Nail Treatment",
    "liquid latex": "Liquid Latex",
    "drying drops": "Drying Drops",
    "stamping air dry lacquer": "Stamping Lacquer",
    "press on glue/releaser": "Nail Glue / Releaser",
}

FINISH_DISPLAY_NAMES = {
    "creme": "Creme",
    "cream": "Creme",
    "confetti": "Confetti",
    "party": "Confetti",
    "shimmer": "Shimmer",
    "glitter": "Glitter",
    "holo": "Holo",
    "flake": "Flake",
    "flakies": "Flakies",
    "metallic": "Metallic",
    "chrome": "Metallic",
    "pearl": "Pearl",
    "matte": "Matte",
    "jelly": "Jelly",
    "thermal": "Thermal",
    "magnetic": "Magnetic",
    "solar": "Solar",
    "neon": "Neon",
    "foil": "Foil",
    "satin": "Satin",
    "iridescent": "Iridescent",
    "sheer": "Sheer",
    "glow": "Glow",
    "glass fleck": "Glass Fleck",
    "multichrome": "Multichrome",
    "duochrome": "Duochrome",
    "crackle": "Crackle",
    "textured": "Textured",
}


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        self.start_page_offset = kwargs.pop("start_page_offset", 1)
        self.doc_title_tag = kwargs.pop("doc_title_tag", "Koillection Archival Directory")
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, total_pages: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#555555"))
        self.setStrokeColor(colors.HexColor("#CCCCCC"))
        self.setLineWidth(0.6)
        self.line(MARGIN, 30, PAGE_WIDTH - MARGIN, 30)
        
        actual_page_num = (self._pageNumber - 1) + self.start_page_offset
        footer_text = f"Page {actual_page_num}"
        self.drawRightString(PAGE_WIDTH - MARGIN, 20, footer_text)
        self.drawString(MARGIN, 20, f"Polish & Storage Directory • {self.doc_title_tag}")
        self.restoreState()


def _pil_to_flowable(pil_img, width_pt: float, height_pt: float) -> RLImage:
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    buf.seek(0)
    return RLImage(buf, width=width_pt, height=height_pt)


def _format_group_banner_text(group_key_name: str, group_value: str, count: int) -> str:
    labels = {
        "brand": "BRAND",
        "location": "STORAGE LOCATION",
        "nail_type": "FORMULATION TYPE",
        "color_family": "COLOR SPECTRUM",
        "finish": "FINISH / EFFECT",
        "rating_group": "RATING TIER",
        "acquisition_year": "ACQUISITION YEAR",
        "tags": "SET / COLLECTION",
        "collection": "COLLECTION"
    }
    prefix = labels.get(group_key_name, str(group_key_name).upper())
    return f"{prefix}: {group_value} ({count} polishes)"


def _build_page_mini_legend(subset_df: pd.DataFrame, font_family: str, banner_bg: str) -> Table:
    styles = getSampleStyleSheet()
    font_bold = f"{font_family}-Bold" if font_family != "Times-Roman" else "Times-Bold"

    label_style = ParagraphStyle(
        "MiniLegendHeader",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=6.5,
        leading=8,
        textColor=colors.HexColor("#2C3E50")
    )

    item_style = ParagraphStyle(
        "MiniLegendItem",
        parent=styles["Normal"],
        fontName=font_family,
        fontSize=6.5,
        leading=8,
        textColor=colors.HexColor("#333333")
    )

    LABEL_COL_W = 75.0
    CONTENT_COL_W = USABLE_WIDTH - LABEL_COL_W

    # 1. Formulation Types
    raw_types = [t for t in subset_df["nail_type"].dropna().unique() if str(t).strip()]
    seen_types = set()
    type_flowables = []
    
    num_t = max(1, min(len(raw_types), 5))
    chunk_w_type = CONTENT_COL_W / num_t

    for t_str in raw_types:
        t_clean = str(t_str).strip()
        disp_name = TYPE_DISPLAY_NAMES.get(t_clean.lower(), t_clean)
        if disp_name.lower() in seen_types:
            continue
        seen_types.add(disp_name.lower())

        icon_flow = _pil_to_flowable(get_type_icon_image(t_clean, size=14), 8, 8)
        micro_table = Table([[icon_flow, Paragraph(disp_name, item_style)]], colWidths=[10, max(20, chunk_w_type - 12)])
        micro_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        type_flowables.append(micro_table)

    # 2. Aesthetic Finishes
    seen_finishes = set()
    finish_flowables = []
    for raw_finish in subset_df["finish"].dropna():
        for part in str(raw_finish).split(","):
            p = part.strip()
            disp_finish = FINISH_DISPLAY_NAMES.get(p.lower(), p)
            if disp_finish and disp_finish.lower() not in seen_finishes:
                seen_finishes.add(disp_finish.lower())
                f_flow = _pil_to_flowable(get_finish_icon_image(p, size=14), 8, 8)
                chunk_w_fin = CONTENT_COL_W / 6.0
                micro_table = Table([[f_flow, Paragraph(disp_finish, item_style)]], colWidths=[10, max(20, chunk_w_fin - 12)])
                micro_table.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]))
                finish_flowables.append(micro_table)

    legend_rows = []
    if type_flowables:
        t_row = [Paragraph("<b>FORMULATION:</b>", label_style)]
        sub_t = Table([type_flowables[:5]], colWidths=[chunk_w_type] * min(len(type_flowables), 5))
        sub_t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        t_row.append(sub_t)
        legend_rows.append(t_row)

    if finish_flowables:
        for idx in range(0, len(finish_flowables), 6):
            batch = finish_flowables[idx:idx + 6]
            f_hdr = Paragraph("<b>FINISHES:</b>" if idx == 0 else "", label_style)
            chunk_w = CONTENT_COL_W / len(batch)
            sub_f = Table([batch], colWidths=[chunk_w] * len(batch))
            sub_f.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))
            legend_rows.append([f_hdr, sub_f])

    if not legend_rows:
        return Spacer(1, 1)

    legend_table = Table(legend_rows, colWidths=[LABEL_COL_W, CONTENT_COL_W])
    legend_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8F9FA")),
        ("LINEABOVE", (0, 0), (-1, 0), 0.75, colors.HexColor("#D0D7DE")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    legend_table.splitByRow = 0
    return legend_table


def render_polish_2line_block(
    row: pd.Series,
    styles: dict,
    finish_icon_only: bool = False,
    default_coats: int = 3
) -> tuple:
    """
    Renders a single polish into 2 table sub-rows across a 4-column master grid:
    Col 0 (46pt):  Swatch (Pill, Dual-Split if Multichrome / Secondary Hex)
    Col 1 (340pt): Line 1 = Brand • Shade (Set) [Color Family • Size • #]
                   Line 2 = Formulation • Finishes (Spelled Out) • [Acq • From • Fill]
    Col 2 (68pt):  Line 1 = Location | Line 2 = Coats (Pips + Count)
    Col 3 (86pt):  Line 1 = Rating   | Line 2 = Dual Hex (#HEX1 / #HEX2)
    """
    primary_hex = str(row.get("color_hex", "")).strip().upper()
    raw_sec_hex = str(row.get("secondary_hex", "")).strip().upper()
    f_str = str(row.get("finish", "Creme")).strip()
    
    # 1. Effective Secondary Hex (Explicit or Smart Chromatic Shift)
    effective_sec = compute_effective_secondary_hex(primary_hex, raw_sec_hex, f_str)
    
    # Swatch Flowable (Maximized 42pt x 30pt pill)
    swatch_pil = generate_color_swatch_image(
        hex_code=primary_hex,
        secondary_hex=effective_sec,
        width=42,
        height=30,
        radius=5,
        finish=f_str
    )
    swatch_flow = _pil_to_flowable(swatch_pil, 42, 30)

    # -------------------------------------------------------------------------
    # LINE 1 - COL 1: Identity & Rich Metadata Badges
    # -------------------------------------------------------------------------
    brand = str(row.get("brand", "Unknown")).strip()
    shade = str(row.get("shade_name", "Untitled")).strip()
    tags = str(row.get("tags", "")).strip()
    family = str(row.get("color_family", "")).strip()
    size_oz = str(row.get("size_oz", "")).strip()
    bottle_num = str(row.get("bottle_number", "")).strip()
    is_dc = bool(row.get("is_discontinued", False))

    tag_html = f' &nbsp; <font color="#55606E" size="7.5"><i>(Set: {tags})</i></font>' if tags else ''

    line1_meta_parts = []
    if family and family != "No Color Set":
        line1_meta_parts.append(f'<font color="#4B5563"><i>{family}</i></font>')
    if size_oz:
        line1_meta_parts.append(f'<font color="#6B7280">{size_oz} oz</font>')
    if bottle_num:
        line1_meta_parts.append(f'<font color="#6B7280">#{bottle_num}</font>')
    if is_dc:
        line1_meta_parts.append('<font color="#DC2626"><b>[DISCONTINUED]</b></font>')

    badge_html = f' &nbsp;&nbsp; <font color="#9CA3AF" size="7.5">[{ " • ".join(line1_meta_parts) }]</font>' if line1_meta_parts else ''
    line1_desc_html = f'<b><font color="#111827" size="9">{brand}</font></b> &nbsp;•&nbsp; <font color="#1F2937" size="9"><b>{shade}</b></font>{tag_html}{badge_html}'
    line1_desc = Paragraph(line1_desc_html, styles["CellNormal"])

    # LINE 1 - COL 2: Location
    loc_str = str(row.get("location", "—")).strip()
    line1_loc = Paragraph(f'<b><font size="8.5" color="#111827">{loc_str}</font></b>', styles["CellCenter"])

    # LINE 1 - COL 3: Star Rating (0-5 stars)
    r_score = float(row.get("rating_5", 0.0))
    stars_pil = generate_star_rating_image(r_score, width=58, height=11)
    line1_rating = _pil_to_flowable(stars_pil, 54, 10)

    # -------------------------------------------------------------------------
    # LINE 2 - COL 1: Formulation, Spelled-Out Finishes & Acquisition/Fill Meta
    # -------------------------------------------------------------------------
    t_str = str(row.get("nail_type", "Regular Nail Lacquer")).strip()
    t_disp = TYPE_DISPLAY_NAMES.get(t_str.lower(), t_str)
    t_pil = get_type_icon_image(t_str, size=14)
    t_flow = _pil_to_flowable(t_pil, 9, 9)

    finish_parts = [piece.strip() for piece in f_str.split(",") if piece.strip()]
    if not finish_parts:
        finish_parts = ["Creme"]

    if finish_icon_only:
        fin_icon_flowables = []
        for f_name in finish_parts[:4]:
            f_pil = get_finish_icon_image(f_name, size=14)
            fin_icon_flowables.append(_pil_to_flowable(f_pil, 9, 9))
        fin_table = Table([fin_icon_flowables], colWidths=[12.0] * len(fin_icon_flowables))
        fin_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        fin_cell = fin_table
        fin_col_w = 55
    else:
        primary_finish = finish_parts[0]
        f_pil = get_finish_icon_image(primary_finish, size=14)
        f_flow = _pil_to_flowable(f_pil, 9, 9)
        fin_label = ", ".join(finish_parts[:3])
        fin_cell = Table([[f_flow, Paragraph(f"<font color='#4B5563' size='7.5'>{fin_label}</font>", styles["CellNormal"])]], colWidths=[11, 134])
        fin_cell.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        fin_col_w = 145

    acq_date = str(row.get("purchase_date", "")).strip()
    purchased_from = str(row.get("purchased_from", "")).strip()
    fill_level = str(row.get("fill_level", "")).strip()

    line2_meta_parts = []
    if acq_date:
        acq_yr = acq_date[:4] if len(acq_date) >= 4 and acq_date[:4].isdigit() else acq_date
        line2_meta_parts.append(f"Acq: {acq_yr}")
    if purchased_from:
        line2_meta_parts.append(f"From: {purchased_from[:14]}")
    if fill_level:
        line2_meta_parts.append(f"Fill: {fill_level}")

    meta2_str = " • ".join(line2_meta_parts)
    line2_meta_p = Paragraph(f"<font color='#6B7280' size='7'>{meta2_str}</font>", styles["CellNormal"])

    type_cell = Table([[t_flow, Paragraph(f"<font color='#1F2937' size='7.5'><b>{t_disp}</b></font>", styles["CellNormal"])]], colWidths=[11, 74])
    type_cell.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    rem_meta_w = max(40, 340 - 85 - fin_col_w)
    meta_table = Table(
        [[type_cell, fin_cell, line2_meta_p]],
        colWidths=[85, fin_col_w, rem_meta_w]
    )
    meta_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    # LINE 2 - COL 2: Required Coats (Opacity Pips + Numeric Count)
    raw_coats = str(row.get("coats", "")).strip()
    coats_val = raw_coats if raw_coats and raw_coats not in ["", "None", "nan", "0"] else str(default_coats)
    pips_pil = generate_opacity_dots_image(coats_val, max_coats=3, width=34, height=10)
    pips_flow = _pil_to_flowable(pips_pil, 30, 9)
    line2_coats = Table(
        [[pips_flow, Paragraph(f'<font size="7" color="#4B5563">{coats_val}c</font>', styles["CellNormal"])]],
        colWidths=[32, 22]
    )
    line2_coats.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    # LINE 2 - COL 3: Hex Code Monospace (Displays both hex codes if secondary exists)
    if primary_hex:
        if effective_sec and effective_sec != primary_hex:
            hex_markup = f'<font color="#111827" size="6.5" face="Courier"><b>{primary_hex}</b></font> <font color="#9CA3AF" size="6">/</font> <font color="#4B5563" size="6.5" face="Courier"><b>{effective_sec}</b></font>'
        else:
            hex_markup = f'<font color="#374151" size="7" face="Courier"><b>{primary_hex}</b></font>'
        line2_hex = Paragraph(hex_markup, styles["CellCenter"])
    else:
        line2_hex = Paragraph('<font color="#AAAAAA" size="7">No Hex</font>', styles["CellCenter"])

    row_top = [swatch_flow, line1_desc, line1_loc, line1_rating]
    row_bot = ["", meta_table, line2_coats, line2_hex]

    return row_top, row_bot


def build_2line_catalog_table(
    polish_blocks: list,
    headers: list,
    col_widths: list,
    header_bg: str = "#ECEFF1",
    zebra_bg: str = "#F8F9FA",
    compact_mode: bool = True,
    repeat_rows: int = 0
) -> Table:
    table_data = [headers]
    for top_r, bot_r in polish_blocks:
        table_data.append(top_r)
        table_data.append(bot_r)

    pad_top = 2.0 if compact_mode else 3.5
    pad_bot = 2.0 if compact_mode else 3.5

    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_bg)),
        ("LINEBELOW", (0, 0), (-1, 0), 1.0, colors.HexColor("#B0BEC5")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (3, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, 0), 3.0),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 3.0),
    ]

    for idx in range(len(polish_blocks)):
        row_top = 1 + idx * 2
        row_bot = row_top + 1

        style_cmds.append(("SPAN", (0, row_top), (0, row_bot)))

        if idx % 2 == 1:
            style_cmds.append(("BACKGROUND", (0, row_top), (-1, row_bot), colors.HexColor(zebra_bg)))

        style_cmds.append(("TOPPADDING", (0, row_top), (-1, row_top), pad_top))
        style_cmds.append(("BOTTOMPADDING", (0, row_top), (-1, row_top), 0.5))
        style_cmds.append(("TOPPADDING", (0, row_bot), (-1, row_bot), 0.5))
        style_cmds.append(("BOTTOMPADDING", (0, row_bot), (-1, row_bot), pad_bot))

        style_cmds.append(("LINEBELOW", (0, row_bot), (-1, row_bot), 0.5, colors.HexColor("#E0E0E0")))

    t = Table(table_data, colWidths=col_widths, repeatRows=repeat_rows)
    t.setStyle(TableStyle(style_cmds))
    return t


def build_tabular_directory_pdf(
    df: pd.DataFrame,
    group_by: str = "location",
    collection_title: str = "Nail Polish & Storage Location Directory",
    active_columns: list = None,
    font_family: str = "Helvetica",
    banner_bg: str = "#2C3E50",
    banner_text: str = "#FFFFFF",
    header_bg: str = "#ECEFF1",
    header_text: str = "#111111",
    zebra_bg: str = "#F8F9FA",
    compact_mode: bool = True,
    start_page_num: int = 1,
    header_subtitle: str = None,
    finish_icon_only: bool = False,
    default_coats: int = 3,
    legend_mode: str = "per_page",
    rows_per_page: int = 0,
    **kwargs
) -> bytes:
    TOP_MARGIN = 32.0
    BOTTOM_MARGIN = 34.0

    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=letter,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN
    )

    styles = getSampleStyleSheet()
    font_bold = f"{font_family}-Bold" if font_family != "Times-Roman" else "Times-Bold"

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1A252C")
    )
    
    meta_style = ParagraphStyle(
        "DocMeta",
        parent=styles["Normal"],
        fontName=font_family,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#666666")
    )

    section_style = ParagraphStyle(
        "SectionBanner",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=10.5,
        leading=13,
        textColor=colors.HexColor(banner_text)
    )

    header_cell_style = ParagraphStyle(
        "HeaderCell",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor(header_text)
    )

    header_cell_center = ParagraphStyle(
        "HeaderCellCenter",
        parent=header_cell_style,
        alignment=1
    )

    cell_normal = ParagraphStyle(
        "CellNormal",
        parent=styles["Normal"],
        fontName=font_family,
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#222222")
    )

    cell_center = ParagraphStyle(
        "CellCenter",
        parent=cell_normal,
        alignment=1
    )

    render_styles = {
        "CellNormal": cell_normal,
        "CellCenter": cell_center
    }

    # 4-Column Balanced Grid: Sum = 540.0 pt (US Letter Width)
    col_widths = [46.0, 340.0, 68.0, 86.0]

    headers = [
        Paragraph("<b>Swatch</b>", header_cell_center),
        Paragraph("<b>Polish & Formulation Details</b>", header_cell_style),
        Paragraph("<b>Location / Coats</b>", header_cell_center),
        Paragraph("<b>Rating / Hex</b>", header_cell_center),
    ]

    story = []

    if legend_mode == "first_page":
        story.extend(get_legend_flowables(font_family=font_family, banner_bg=banner_bg, banner_text=banner_text))
        story.append(PageBreak())

    now_str = datetime.now().strftime("%B %d, %Y • %I:%M %p")
    title_p = Paragraph(collection_title, title_style)
    sub = header_subtitle or f"Generated: {now_str} &nbsp;|&nbsp; Total Polishes: <b>{len(df)}</b> &nbsp;|&nbsp; Grouped by: <b>{group_by.replace('_', ' ').capitalize()}</b>"
    sub_p = Paragraph(sub, meta_style)

    _, h_title = title_p.wrap(USABLE_WIDTH, 100)
    _, h_sub = sub_p.wrap(USABLE_WIDTH, 100)
    page_1_header_overhead = h_title + h_sub + 18.0

    story.append(title_p)
    story.append(sub_p)
    story.append(Spacer(1, 8))

    FRAME_HEIGHT = PAGE_HEIGHT - TOP_MARGIN - BOTTOM_MARGIN  # 726.0 pt
    SHOCK_BUFFER = 20.0

    all_polish_blocks = [
        render_polish_2line_block(row, render_styles, finish_icon_only=finish_icon_only, default_coats=default_coats)
        for _, row in df.iterrows()
    ]

    # -------------------------------------------------------------------------
    # REAL-TIME DYNAMIC SWEET-SPOT PAGINATION ENGINE
    # -------------------------------------------------------------------------
    if legend_mode == "per_page" and not df.empty:
        current_idx = 0
        is_page_one = True
        pages_to_render = []

        while current_idx < len(df):
            if is_page_one:
                page_budget = FRAME_HEIGHT - page_1_header_overhead - SHOCK_BUFFER
            else:
                page_budget = FRAME_HEIGHT - SHOCK_BUFFER
            
            best_k = 1
            max_possible_k = len(df) - current_idx

            for test_k in range(1, max_possible_k + 1):
                candidate_blocks = all_polish_blocks[current_idx : current_idx + test_k]
                test_table = build_2line_catalog_table(
                    candidate_blocks, headers, col_widths,
                    header_bg=header_bg, zebra_bg=zebra_bg, compact_mode=compact_mode
                )
                _, h_table = test_table.wrap(USABLE_WIDTH, 2000)

                candidate_df = df.iloc[current_idx : current_idx + test_k]
                test_legend = _build_page_mini_legend(candidate_df, font_family=font_family, banner_bg=banner_bg)
                
                h_legend = 0.0
                if isinstance(test_legend, Table):
                    _, h_legend = test_legend.wrap(USABLE_WIDTH, 2000)

                total_consumed = h_table + 4.0 + h_legend

                if total_consumed <= page_budget:
                    best_k = test_k
                else:
                    break

            if rows_per_page > 0:
                manual_cap = max(6, (rows_per_page // 2) - 1) if is_page_one else max(6, rows_per_page // 2)
                best_k = min(best_k, manual_cap)

            final_blocks = all_polish_blocks[current_idx : current_idx + best_k]
            final_table = build_2line_catalog_table(
                final_blocks, headers, col_widths,
                header_bg=header_bg, zebra_bg=zebra_bg, compact_mode=compact_mode
            )

            final_legend = _build_page_mini_legend(
                df.iloc[current_idx : current_idx + best_k],
                font_family=font_family, banner_bg=banner_bg
            )

            pages_to_render.append((final_table, final_legend))

            current_idx += best_k
            is_page_one = False

        for p_idx, (p_table, p_legend) in enumerate(pages_to_render):
            story.append(KeepTogether([p_table, Spacer(1, 4), p_legend]))
            if p_idx < len(pages_to_render) - 1:
                story.append(PageBreak())

    else:
        if group_by != "none" and not df.empty and group_by in df.columns:
            groups = df.groupby(group_by, sort=False)
            group_offset = 0
            for group_key, group_df in groups:
                group_len = len(group_df)
                group_label = _format_group_banner_text(group_by, str(group_key), group_len)
                banner_table = Table([[Paragraph(group_label, section_style)]], colWidths=[USABLE_WIDTH])
                banner_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(banner_bg)),
                    ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ]))
                story.append(Spacer(1, 5))
                story.append(banner_table)

                group_blocks = all_polish_blocks[group_offset : group_offset + group_len]
                t = build_2line_catalog_table(
                    group_blocks, headers, col_widths,
                    header_bg=header_bg, zebra_bg=zebra_bg, compact_mode=compact_mode, repeat_rows=1
                )
                story.append(t)
                story.append(Spacer(1, 6))
                group_offset += group_len
        else:
            t = build_2line_catalog_table(
                all_polish_blocks, headers, col_widths,
                header_bg=header_bg, zebra_bg=zebra_bg, compact_mode=compact_mode, repeat_rows=1
            )
            story.append(t)

    if legend_mode == "last_page":
        story.append(PageBreak())
        story.extend(get_legend_flowables(font_family=font_family, banner_bg=banner_bg, banner_text=banner_text))

    def make_canvas(filename, **kwargs):
        return NumberedCanvas(
            filename,
            start_page_offset=start_page_num,
            doc_title_tag=collection_title,
            **kwargs
        )

    doc.build(story, canvasmaker=make_canvas)
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()


# -----------------------------------------------------------------------------
# REUSABLE MASTER LEGEND FLOWABLE GENERATOR
# -----------------------------------------------------------------------------
def get_legend_flowables(
    font_family: str = "Helvetica",
    banner_bg: str = "#2C3E50",
    banner_text: str = "#FFFFFF"
) -> list:
    styles = getSampleStyleSheet()
    font_bold = f"{font_family}-Bold" if font_family != "Times-Roman" else "Times-Bold"

    title_style = ParagraphStyle(
        "LegendTitle",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#1A252C")
    )

    meta_style = ParagraphStyle(
        "LegendMeta",
        parent=styles["Normal"],
        fontName=font_family,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#555555")
    )

    sec_banner_style = ParagraphStyle(
        "SecBanner",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=9.5,
        leading=12,
        textColor=colors.HexColor(banner_text)
    )

    item_title_style = ParagraphStyle(
        "ItemTitle",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#111111")
    )

    item_desc_style = ParagraphStyle(
        "ItemDesc",
        parent=styles["Normal"],
        fontName=font_family,
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#555555")
    )

    flowables = []
    flowables.append(Paragraph("NAIL POLISH DIRECTORY • VISUAL ICON & FORMULATION KEY", title_style))
    flowables.append(Paragraph("Archival reference guide for physical binders, quick-reference desk sheets, and drawer walk-throughs.", meta_style))
    flowables.append(Spacer(1, 10))

    col_w = 264.0

    # LEFT COLUMN: 1. FORMULATION TYPES (10 items)
    types_rows = [
        [Table([[Paragraph("FORMULATION TYPES & SYSTEMS", sec_banner_style)]], colWidths=[col_w])]
    ]

    types_data = [
        ("regular nail lacquer", "Regular Nail Lacquer", "Standard nitrocellulose air-dry lacquer formula."),
        ("uv gel nail lacquer", "UV Gel Nail Lacquer", "Cured under UV/LED lamp; high-durability gel polish."),
        ("top coat", "Top Coat", "Protective high-gloss or matte quick-dry sealing layer."),
        ("base coat", "Base Coat", "Foundation layer; ridge-filling, adhesive, or peel-off."),
        ("cuticle oil", "Cuticle Oil", "Nourishing hydration treatment for nail bed & skin."),
        ("nail treatment", "Nail Treatment", "Strengthener, hardener, or therapeutic repair base."),
        ("liquid latex", "Liquid Latex / Tape", "Peelable cuticle barrier guard for clean nail art stamping."),
        ("drying drops", "Drying Drops", "Volatile solvent evaporative drops for rapid touch-dry speed."),
        ("stamping air dry lacquer", "Stamping Air Dry Lacquer", "Highly opaque, high-viscosity stamping plate formula."),
        ("press on glue/releaser", "Press-On Glue / Releaser", "Adhesive bonding resin or debonding dissolver solution.")
    ]

    for key, name, desc in types_data:
        icon_flow = _pil_to_flowable(get_type_icon_image(key, size=18), 12, 12)
        content = [Paragraph(f"<b>{name}</b>", item_title_style), Paragraph(desc, item_desc_style)]
        types_rows.append([icon_flow, content])

    types_table = Table(types_rows, colWidths=[22, col_w - 22])
    types_table.setStyle(TableStyle([
        ("SPAN", (0, 0), (1, 0)),
        ("BACKGROUND", (0, 0), (1, 0), colors.HexColor(banner_bg)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("LINEBELOW", (0, 1), (-1, -1), 0.5, colors.HexColor("#EEEEEE")),
    ]))

    # LEFT COLUMN: 2. DIRECTORY INDICATORS
    indicator_banner = Table([[Paragraph("DIRECTORY RATINGS, OPACITY & SWATCHES", sec_banner_style)]], colWidths=[col_w])
    indicator_banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(banner_bg)),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))

    swatch_flow = _pil_to_flowable(generate_color_swatch_image("#7B1FA2", width=36, height=22, radius=4), 28, 16)
    pips_flow = _pil_to_flowable(generate_opacity_dots_image("2", max_coats=3, width=38, height=12), 34, 10)
    stars_flow = _pil_to_flowable(generate_star_rating_image(4.5, width=70, height=13), 58, 11)

    indicators_rows = [
        [
            swatch_flow,
            [Paragraph("<b>Color Swatch Pill</b>", item_title_style), Paragraph("Large true hex preview with dual-split support for multichromes.", item_desc_style)]
        ],
        [
            pips_flow,
            [Paragraph("<b>Coat Opacity Indicator</b>", item_title_style), Paragraph("Recommended coat count (1, 2, or 3) to achieve full bottle opacity.", item_desc_style)]
        ],
        [
            stars_flow,
            [Paragraph("<b>Star Rating (0.0 – 5.0)</b>", item_title_style), Paragraph("Vector half-star rating based on longevity, opacity, and formula.", item_desc_style)]
        ]
    ]

    indicators_table = Table(indicators_rows, colWidths=[65, col_w - 65])
    indicators_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("LINEBELOW", (0, 1), (-1, -1), 0.5, colors.HexColor("#EEEEEE")),
    ]))

    left_column_elements = [types_table, Spacer(1, 8), indicator_banner, Spacer(1, 4), indicators_table]
    left_column_table = Table([[el] for el in left_column_elements], colWidths=[col_w])
    left_column_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    # RIGHT COLUMN: ALL 23 AESTHETIC FINISHES
    right_rows = [
        [Table([[Paragraph("AESTHETIC FINISHES & SPECIAL EFFECTS", sec_banner_style)]], colWidths=[col_w])]
    ]

    finishes_data = [
        ("creme", "Creme", "Classic smooth, opaque color with glossy non-sparkle finish."),
        ("shimmer", "Shimmer", "Fine micro-particles creating luminous depth and glow."),
        ("glitter", "Glitter", "Reflective multi-sized hexagonal, square, or star sequins."),
        ("confetti", "Confetti", "Suspended multi-colored matte sequins, dots, or streamer glitters."),
        ("holo", "Holo (Holographic)", "Prismatic rainbow diffraction (linear or scattered)."),
        ("flake", "Flake / Flakies", "Irregular iridescent, metallic, or chameleon foil shards."),
        ("metallic", "Metallic / Chrome", "High-contrast mirror or brushed reflective liquid metal."),
        ("pearl", "Pearl", "Soft luminous luster with satiny mineral pearl glow."),
        ("matte", "Matte", "Non-reflective frosted finish with velvety surface."),
        ("jelly", "Jelly", "Translucent, squishy, buildable glass-tint color base."),
        ("thermal", "Thermal", "Temperature-reactive color shift between warm and cool."),
        ("magnetic", "Magnetic", "Velvet or cat-eye effect activated by a magnetic wand."),
        ("solar", "Solar / Photochromic", "Changes shade when exposed to direct natural sunlight."),
        ("neon", "Neon", "Fluorescent, vibrant pigments glowing under UV blacklight."),
        ("foil", "Foil", "Crinkled metallic leaf effect with micro-faceted sparkle."),
        ("satin", "Satin", "Low-sheen demi-matte finish with gentle silk reflection."),
        ("iridescent", "Iridescent", "Translucent color shift reflecting rainbow highlights."),
        ("sheer", "Sheer", "Delicate wash of tint for natural or French manicures."),
        ("glow", "Glow-in-the-Dark", "Phosphorescent pigments that radiate light in dark rooms."),
        ("glass fleck", "Glass Fleck", "Glass-flecked mica flakes creating brilliant smooth sparkle."),
        ("multichrome", "Multichrome", "Shifts across 3+ distinct colors depending on light angle."),
        ("crackle", "Crackle", "Top layer fractures and shatters into mosaic cracks as it dries."),
        ("textured", "Textured / Sand", "Dries with physical sand-like matte grit texture.")
    ]

    for key, name, desc in finishes_data:
        icon_flow = _pil_to_flowable(get_finish_icon_image(key, size=16), 11, 11)
        content = [Paragraph(f"<b>{name}</b>", item_title_style), Paragraph(desc, item_desc_style)]
        right_rows.append([icon_flow, content])

    right_table = Table(right_rows, colWidths=[20, col_w - 20])
    right_table.setStyle(TableStyle([
        ("SPAN", (0, 0), (1, 0)),
        ("BACKGROUND", (0, 0), (1, 0), colors.HexColor(banner_bg)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ("LINEBELOW", (0, 1), (-1, -1), 0.5, colors.HexColor("#EEEEEE")),
    ]))

    master_table = Table([[left_column_table, right_table]], colWidths=[col_w + 3, col_w + 3])
    master_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    flowables.append(master_table)
    return flowables


def build_legend_pdf(
    font_family: str = "Helvetica",
    banner_bg: str = "#2C3E50",
    banner_text: str = "#FFFFFF"
) -> bytes:
    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=letter,
        leftMargin=36.0,
        rightMargin=36.0,
        topMargin=32.0,
        bottomMargin=32.0
    )
    story = get_legend_flowables(font_family=font_family, banner_bg=banner_bg, banner_text=banner_text)
    doc.build(story)
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()