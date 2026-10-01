import io
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
    Image as RLImage
)
from reportlab.pdfgen import canvas

from icons import (
    get_finish_icon_image,
    generate_opacity_dots_image,
    generate_star_rating_image,
    generate_color_swatch_image
)

PAGE_WIDTH, PAGE_HEIGHT = letter
MARGIN = 36.0
USABLE_WIDTH = PAGE_WIDTH - (2 * MARGIN)  # 540 points


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
        "location": 50,
        "color_swatch": 26,
        "brand": 75,
        "shade_name": 140,
        "finish": 80,
        "coats": 42,
        "rating": 72,
        "size_acq": 55,
        "item_id": 45,
    }
    total_requested = sum(base_weights.get(c, 50) for c in active_cols)
    if total_requested == 0:
        return [USABLE_WIDTH / max(1, len(active_cols))] * len(active_cols)
    scale = USABLE_WIDTH / float(total_requested)
    return [round(base_weights.get(c, 50) * scale, 1) for c in active_cols]


def _format_group_banner_text(group_key_name: str, group_value: str, count: int) -> str:
    """Formats distinct, publication-quality group banner titles."""
    labels = {
        "brand": "BRAND",
        "location": "STORAGE LOCATION",
        "color_family": "COLOR SPECTRUM",
        "finish": "FINISH / EFFECT",
        "rating_group": "RATING TIER",
        "acquisition_year": "ACQUISITION YEAR",
        "collection": "COLLECTION"
    }
    prefix = labels.get(group_key_name, str(group_key_name).upper())
    return f"{prefix}: {group_value} ({count} polishes)"


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
    header_subtitle: str = None
) -> bytes:
    if active_columns is None or len(active_columns) == 0:
        active_columns = ["location", "color_swatch", "brand", "shade_name", "finish", "coats", "rating", "size_acq"]

    pdf_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=letter,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=42
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

    story = []

    now_str = datetime.now().strftime("%B %d, %Y • %I:%M %p")
    story.append(Paragraph(collection_title, title_style))
    
    sub = header_subtitle or f"Generated: {now_str} &nbsp;|&nbsp; Total Polishes: <b>{len(df)}</b> &nbsp;|&nbsp; Grouped by: <b>{group_by.replace('_', ' ').capitalize()}</b>"
    story.append(Paragraph(sub, meta_style))
    story.append(Spacer(1, 10))

    col_widths = _compute_column_widths(active_columns)

    header_titles = {
        "location": "Location",
        "color_swatch": "Color",
        "brand": "Brand",
        "shade_name": "Shade Name",
        "finish": "Finish",
        "coats": "Coats",
        "rating": "Rating",
        "size_acq": "Size / Acq",
        "item_id": "Item ID"
    }

    headers = [Paragraph(f"<b>{header_titles.get(col, col.capitalize())}</b>", header_cell_style) for col in active_columns]

    def make_rows_for_df(subset_df):
        table_rows = [headers]
        for _, row in subset_df.iterrows():
            row_cells = []
            for col in active_columns:
                if col == "location":
                    row_cells.append(Paragraph(str(row.get("location", "—")), cell_bold))
                elif col == "color_swatch":
                    swatch_pil = generate_color_swatch_image(row.get("color_hex", ""), size=18)
                    row_cells.append(_pil_to_flowable(swatch_pil, 11, 11))
                elif col == "brand":
                    row_cells.append(Paragraph(str(row.get("brand", "—")), cell_normal))
                elif col == "shade_name":
                    row_cells.append(Paragraph(str(row.get("shade_name", "—")), cell_bold))
                elif col == "finish":
                    f_str = str(row.get("finish", "Creme"))
                    f_pil = get_finish_icon_image(f_str, size=16)
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
                    pips_pil = generate_opacity_dots_image(str(row.get("coats", "2")), max_coats=3, width=38, height=12)
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
                    
            table_rows.append(row_cells)
        return table_rows

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

    # Dynamic Section Banners
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

            rows = make_rows_for_df(group_df)
            t = Table(rows, colWidths=col_widths, repeatRows=1)
            t.setStyle(get_table_style())
            story.append(t)
            story.append(Spacer(1, 6))
    else:
        # Flat Directory
        rows = make_rows_for_df(df)
        t = Table(rows, colWidths=col_widths, repeatRows=1)
        t.setStyle(get_table_style())
        story.append(t)

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