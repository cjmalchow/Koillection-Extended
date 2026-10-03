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
    PageBreak
)
from reportlab.pdfgen import canvas

from icons import (
    get_type_icon_image,
    get_finish_icon_image,
    generate_opacity_dots_image,
    generate_star_rating_image,
    generate_color_swatch_image
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
    "shimmer": "Shimmer",
    "glitter": "Glitter",
    "holo": "Holo",
    "flake": "Flake",
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


def _compute_column_widths(active_cols: list) -> list:
    base_weights = {
        "location": 46,
        "color_swatch": 32,
        "nail_type": 28,
        "brand": 72,
        "shade_name": 132,
        "finish": 74,
        "coats": 38,
        "rating": 68,
        "size_acq": 50,
        "item_id": 45,
    }
    total_requested = sum(base_weights.get(c, 50) for c in active_cols)
    if total_requested == 0:
        return [USABLE_WIDTH / max(1, len(active_cols))] * len(active_cols)
    scale = USABLE_WIDTH / float(total_requested)
    return [round(base_weights.get(c, 50) * scale, 1) for c in active_cols]


def _format_group_banner_text(group_key_name: str, group_value: str, count: int) -> str:
    labels = {
        "brand": "BRAND",
        "location": "STORAGE LOCATION",
        "nail_type": "FORMULATION TYPE",
        "color_family": "COLOR SPECTRUM",
        "finish": "FINISH / EFFECT",
        "rating_group": "RATING TIER",
        "acquisition_year": "ACQUISITION YEAR",
        "collection": "COLLECTION"
    }
    prefix = labels.get(group_key_name, str(group_key_name).upper())
    return f"{prefix}: {group_value} ({count} polishes)"


def _build_page_mini_legend(subset_df: pd.DataFrame, font_family: str, banner_bg: str) -> Table:
    """Builds a compact horizontal key showing ONLY icons on this page."""
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

    raw_types = [t for t in subset_df["nail_type"].dropna().unique() if str(t).strip()]
    seen_types = set()
    type_flowables = []
    for t_str in raw_types:
        t_clean = str(t_str).strip()
        disp_name = TYPE_DISPLAY_NAMES.get(t_clean.lower(), t_clean)
        if disp_name.lower() in seen_types:
            continue
        seen_types.add(disp_name.lower())

        icon_flow = _pil_to_flowable(get_type_icon_image(t_clean, size=14), 8, 8)
        micro_table = Table([[icon_flow, Paragraph(disp_name, item_style)]], colWidths=[10, None])
        micro_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        type_flowables.append(micro_table)

    seen_finishes = set()
    finish_flowables = []
    for raw_finish in subset_df["finish"].dropna():
        for part in str(raw_finish).split(","):
            p = part.strip()
            disp_finish = FINISH_DISPLAY_NAMES.get(p.lower(), p)
            if disp_finish and disp_finish.lower() not in seen_finishes:
                seen_finishes.add(disp_finish.lower())
                f_flow = _pil_to_flowable(get_finish_icon_image(p, size=14), 8, 8)
                micro_table = Table([[f_flow, Paragraph(disp_finish, item_style)]], colWidths=[10, None])
                micro_table.setStyle(TableStyle([
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]))
                finish_flowables.append(micro_table)

    LABEL_COL_W = 70.0
    CONTENT_COL_W = USABLE_WIDTH - LABEL_COL_W

    legend_rows = []
    # 1. Formulation Row
    if type_flowables:
        t_row = [Paragraph("<b>FORMULATION:</b>", label_style)]
        chunk_w = CONTENT_COL_W / max(1, min(len(type_flowables), 5))
        sub_t = Table([type_flowables[:5]], colWidths=[chunk_w] * min(len(type_flowables), 5))
        sub_t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ]))
        t_row.append(sub_t)
        legend_rows.append(t_row)

    # 2. Finishes Row
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
    # PREVENT SPLITTING TYPES AND FINISHES ACROSS PAGES
    legend_table.splitByRow = 0
    return legend_table


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
    if active_columns is None or len(active_columns) == 0:
        active_columns = ["location", "color_swatch", "nail_type", "brand", "shade_name", "finish", "coats", "rating", "size_acq"]

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

    cell_bold = ParagraphStyle(
        "CellBold",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#111111")
    )

    cell_normal = ParagraphStyle(
        "CellNormal",
        parent=styles["Normal"],
        fontName=font_family,
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#222222")
    )

    cell_muted = ParagraphStyle(
        "CellMuted",
        parent=styles["Normal"],
        fontName=font_family,
        fontSize=7,
        leading=9,
        textColor=colors.HexColor("#666666")
    )

    col_widths = _compute_column_widths(active_columns)

    header_titles = {
        "location": "Location",
        "color_swatch": "Color",
        "nail_type": "Type",
        "brand": "Brand",
        "shade_name": "Shade Name",
        "finish": "Finish" if not finish_icon_only else "Finishes",
        "coats": "Coats",
        "rating": "Rating",
        "size_acq": "Size / Acq",
        "item_id": "Item ID"
    }

    headers = [Paragraph(f"<b>{header_titles.get(col, col.capitalize())}</b>", header_cell_style) for col in active_columns]

    padding_v = 2.5 if compact_mode else 4.5

    def get_table_style():
        return TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_bg)),
            ("LINEBELOW", (0, 0), (-1, 0), 1.0, colors.HexColor("#B0BEC5")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(zebra_bg)]),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), padding_v),
            ("BOTTOMPADDING", (0, 0), (-1, -1), padding_v),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("LINEBELOW", (0, 1), (-1, -1), 0.5, colors.HexColor("#EEEEEE")),
        ])

    def render_single_row_cells(row):
        row_cells = []
        for col in active_columns:
            if col == "location":
                row_cells.append(Paragraph(str(row.get("location", "—")), cell_bold))
            elif col == "color_swatch":
                swatch_pil = generate_color_swatch_image(row.get("color_hex", ""), size=18)
                row_cells.append(_pil_to_flowable(swatch_pil, 11, 11))
            elif col == "nail_type":
                t_str = str(row.get("nail_type", "Regular Nail Lacquer"))
                t_pil = get_type_icon_image(t_str, size=18)
                row_cells.append(_pil_to_flowable(t_pil, 11, 11))
            elif col == "brand":
                row_cells.append(Paragraph(str(row.get("brand", "—")), cell_normal))
            elif col == "shade_name":
                row_cells.append(Paragraph(str(row.get("shade_name", "—")), cell_bold))
            elif col == "finish":
                f_str = str(row.get("finish", "Creme"))
                finish_parts = [piece.strip() for piece in f_str.split(",") if piece.strip()]
                if not finish_parts:
                    finish_parts = ["Creme"]

                if finish_icon_only:
                    icon_flowables = []
                    for f_name in finish_parts[:4]:
                        f_pil = get_finish_icon_image(f_name, size=16)
                        icon_flowables.append(_pil_to_flowable(f_pil, 11, 11))
                    
                    col_w_list = [14.0] * len(icon_flowables)
                    multi_icon_table = Table([icon_flowables], colWidths=col_w_list)
                    multi_icon_table.setStyle(TableStyle([
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ]))
                    row_cells.append(multi_icon_table)
                else:
                    primary_finish = finish_parts[0]
                    f_pil = get_finish_icon_image(primary_finish, size=16)
                    f_flow = _pil_to_flowable(f_pil, 10, 10)
                    finish_table = Table([[f_flow, Paragraph(f_str[:16], cell_normal)]], colWidths=[12, None])
                    finish_table.setStyle(TableStyle([
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ]))
                    row_cells.append(finish_table)
            elif col == "coats":
                raw_coats = str(row.get("coats", "")).strip()
                coats_val = raw_coats if raw_coats and raw_coats not in ["", "None", "nan", "0"] else str(default_coats)
                pips_pil = generate_opacity_dots_image(coats_val, max_coats=3, width=38, height=12)
                row_cells.append(_pil_to_flowable(pips_pil, 32, 9))
            elif col == "rating":
                r_score = float(row.get("rating_5", 0.0))
                stars_pil = generate_star_rating_image(r_score, width=70, height=13)
                row_cells.append(_pil_to_flowable(stars_pil, 58, 10))
            elif col == "size_acq":
                s_val = row.get("size_oz", "")
                a_val = row.get("purchase_date", "")
                parts = [str(x) for x in [s_val, a_val] if x]
                row_cells.append(Paragraph(" • ".join(parts) if parts else "-", cell_muted))
            elif col == "item_id":
                row_cells.append(Paragraph(str(row.get("item_id", ""))[:8], cell_muted))
            else:
                row_cells.append(Paragraph(str(row.get(col, "")), cell_normal))
        return row_cells

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
    
    # 18pt buffer prevents Page 1 header collisions
    PAGE_1_BUFFER = 18.0
    OTHER_PAGES_BUFFER = 8.0

    # -------------------------------------------------------------------------
    # SWEET-SPOT EXACT PAGINATION
    # -------------------------------------------------------------------------
    if legend_mode == "per_page" and not df.empty:
        all_data_row_cells = [render_single_row_cells(row) for _, row in df.iterrows()]

        current_idx = 0
        is_page_one = True
        pages_to_render = []

        while current_idx < len(df):
            if is_page_one:
                page_budget = FRAME_HEIGHT - page_1_header_overhead - PAGE_1_BUFFER
            else:
                page_budget = FRAME_HEIGHT - OTHER_PAGES_BUFFER
            
            best_k = 1
            max_possible_k = len(df) - current_idx

            for test_k in range(1, max_possible_k + 1):
                candidate_rows = [headers] + all_data_row_cells[current_idx : current_idx + test_k]
                test_table = Table(candidate_rows, colWidths=col_widths)
                test_table.setStyle(get_table_style())
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
                manual_cap = max(10, rows_per_page - 3) if is_page_one else rows_per_page
                best_k = min(best_k, manual_cap)

            final_rows = [headers] + all_data_row_cells[current_idx : current_idx + best_k]
            final_table = Table(final_rows, colWidths=col_widths)
            final_table.setStyle(get_table_style())

            final_legend = _build_page_mini_legend(df.iloc[current_idx : current_idx + best_k], font_family=font_family, banner_bg=banner_bg)

            pages_to_render.append((final_table, final_legend))

            current_idx += best_k
            is_page_one = False

        for p_idx, (p_table, p_legend) in enumerate(pages_to_render):
            story.append(p_table)
            story.append(Spacer(1, 4))
            story.append(p_legend)
            if p_idx < len(pages_to_render) - 1:
                story.append(PageBreak())

    else:
        if group_by != "none" and not df.empty and group_by in df.columns:
            groups = df.groupby(group_by, sort=False)
            for group_key, group_df in groups:
                group_label = _format_group_banner_text(group_by, str(group_key), len(group_df))
                banner_table = Table([[Paragraph(group_label, section_style)]], colWidths=[USABLE_WIDTH])
                banner_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(banner_bg)),
                    ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ]))
                story.append(Spacer(1, 5))
                story.append(banner_table)

                rows = [headers] + [render_single_row_cells(row) for _, row in group_df.iterrows()]
                t = Table(rows, colWidths=col_widths, repeatRows=1)
                t.setStyle(get_table_style())
                story.append(t)
                story.append(Spacer(1, 6))
        else:
            rows = [headers] + [render_single_row_cells(row) for _, row in df.iterrows()]
            t = Table(rows, colWidths=col_widths, repeatRows=1)
            t.setStyle(get_table_style())
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

    indicator_banner = Table([[Paragraph("DIRECTORY RATINGS, OPACITY & SWATCHES", sec_banner_style)]], colWidths=[col_w])
    indicator_banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(banner_bg)),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))

    swatch_flow = _pil_to_flowable(generate_color_swatch_image("#7B1FA2", size=18), 12, 12)
    pips_flow = _pil_to_flowable(generate_opacity_dots_image("2", max_coats=3, width=38, height=12), 34, 10)
    stars_flow = _pil_to_flowable(generate_star_rating_image(4.5, width=70, height=13), 58, 11)

    indicators_rows = [
        [
            swatch_flow,
            [Paragraph("<b>Color Swatch Pip</b>", item_title_style), Paragraph("Filled circle shows true hex color. Dashed ring indicates unswatched.", item_desc_style)]
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

    right_rows = [
        [Table([[Paragraph("AESTHETIC FINISHES & SPECIAL EFFECTS", sec_banner_style)]], colWidths=[col_w])]
    ]

    finishes_data = [
        ("creme", "Creme", "Classic smooth, opaque color with glossy non-sparkle finish."),
        ("shimmer", "Shimmer", "Fine micro-particles creating luminous depth and glow."),
        ("glitter", "Glitter", "Reflective multi-sized hexagonal, square, or star sequins."),
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
        ("TOPPADDING", (0, 0), (-1, -1), 2.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
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