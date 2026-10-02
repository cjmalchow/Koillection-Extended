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
    get_type_icon_image,
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
        "location": 48,
        "color_swatch": 24,
        "nail_type": 28,
        "brand": 75,
        "shade_name": 135,
        "finish": 75,
        "coats": 40,
        "rating": 68,
        "size_acq": 52,
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
    default_coats: int = 3
) -> bytes:
    if active_columns is None or len(active_columns) == 0:
        active_columns = ["location", "color_swatch", "nail_type", "brand", "shade_name", "finish", "coats", "rating", "size_acq"]

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


# -----------------------------------------------------------------------------
# 1-PAGE DEDICATED LEGEND GENERATOR (Balanced & Full-Color)
# -----------------------------------------------------------------------------
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

    story = []

    story.append(Paragraph("NAIL POLISH DIRECTORY • VISUAL ICON & FORMULATION KEY", title_style))
    story.append(Paragraph("Archival reference guide for physical binders, quick-reference desk sheets, and drawer walk-throughs.", meta_style))
    story.append(Spacer(1, 10))

    col_w = 264.0

    def make_entry(flowable_icon, title_text, desc_text):
        content = [
            Paragraph(f"<b>{title_text}</b>", item_title_style),
            Paragraph(desc_text, item_desc_style)
        ]
        return [flowable_icon, content]

    # --- LEFT COLUMN: 1. FORMULATION TYPES ---
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

    # --- LEFT COLUMN: 2. DIRECTORY INDICATORS (Width 65 pt avoids collision) ---
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

    # --- RIGHT COLUMN: ALL 22 AESTHETIC FINISHES ---
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

    story.append(master_table)
    doc.build(story)
    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()