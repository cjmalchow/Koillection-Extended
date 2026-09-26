"""
Color Swatch Creator - Standalone Micro-frontend for Koillection
Designed for nail polish swatch albums with physical spreads, multi-book persistence,
chromometric rainbow sorting, color group buffer spacing, PDF generation, mail-merge CSV export, 
printable swatch sheets, label printing, and instant swatch removal.
"""

import os
import re
import io
import csv
import json
import uuid
import colorsys
import urllib.request
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import create_engine, text

# ---------------------------------------------------------
# Page Configuration & Styling
# ---------------------------------------------------------
st.set_page_config(
    page_title="Color Swatch Creator",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for UI polish, cards, and printable views with forced color retention
st.markdown("""
<style>
    /* Global layout */
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 98%;
    }
    
    /* Instructions Box */
    .guide-box {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 15px;
        font-size: 0.92rem;
        color: #334155;
        line-height: 1.5;
    }
    .guide-step {
        font-weight: 700;
        color: #0f172a;
    }
    
    /* Stats & Chips */
    .filter-chip {
        display: inline-block;
        background: #fee2e2;
        border: 1px solid #fca5a5;
        color: #991b1b;
        border-radius: 9999px;
        padding: 3px 10px;
        font-size: 0.8rem;
        font-weight: 500;
        margin: 2px 4px 4px 0;
    }
    
    /* Swatch Grid & Cards */
    .spread-container {
        display: flex;
        flex-direction: row;
        gap: 20px;
        margin-top: 15px;
        margin-bottom: 25px;
    }
    .book-page {
        flex: 1;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        padding: 16px;
    }
    .page-header {
        font-size: 1.1rem;
        font-weight: 700;
        color: #1e293b;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 8px;
        margin-bottom: 14px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .swatch-grid {
        display: grid;
        gap: 8px;
    }
    .swatch-card {
        position: relative;
        background: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 8px 4px 6px 4px;
        text-align: center;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
        display: flex;
        flex-direction: column;
        align-items: center;
        min-height: 104px;
        justify-content: flex-start;
    }
    .swatch-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.12);
        border-color: #94a3b8;
    }
    .swatch-color {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        margin-bottom: 5px;
        border: 2px solid #ffffff;
        box-shadow: 0 1px 3px rgba(0,0,0,0.3);
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
    }
    .swatch-num {
        font-size: 0.72rem;
        font-weight: 700;
        color: #0f172a;
        line-height: 1.1;
    }
    .swatch-name {
        font-size: 0.68rem;
        color: #334155;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 100%;
        line-height: 1.1;
        margin-top: 2px;
    }
    .swatch-meta {
        font-size: 0.62rem;
        color: #64748b;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 100%;
        line-height: 1.1;
    }
    .swatch-card.empty-slot {
        background: #f8fafc;
        border: 1px dashed #cbd5e1;
        opacity: 0.75;
    }
    
    /* In-Card Removal '✕' */
    .remove-btn {
        position: absolute;
        top: 3px;
        right: 3px;
        width: 20px;
        height: 20px;
        background-color: #ef4444 !important;
        color: #ffffff !important;
        border-radius: 50%;
        font-size: 13px;
        font-weight: 900;
        line-height: 19px;
        text-align: center;
        text-decoration: none !important;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.35);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 30;
        cursor: pointer;
        opacity: 0.95;
        transition: transform 0.15s ease, background-color 0.15s ease, opacity 0.15s ease;
    }
    .remove-btn:hover {
        background-color: #b91c1c !important;
        color: #ffffff !important;
        opacity: 1.0 !important;
        transform: scale(1.22);
    }
    
    /* Force Browser Color Printing */
    @media print {
        * {
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
            color-adjust: exact !important;
        }
        body { font-size: 9pt; background: #fff; }
        .no-print { display: none !important; }
        .page-break { page-break-after: always; break-after: page; }
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Database Connection & Schema Management
# ---------------------------------------------------------
DB_USER = os.getenv("DB_USER", "koillection_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "local_polish_vault_2026")
DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "koillection")

DEFAULT_DB_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

@st.cache_resource
def get_db_engine():
    return create_engine(DATABASE_URL, pool_pre_ping=True)

engine = get_db_engine()

def init_tables():
    """Ensure custom tables exist with self-healing migrations including buffer options."""
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS custom_swatch_book (
                id VARCHAR(64) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                prefix VARCHAR(32) NOT NULL,
                collection_id VARCHAR(64),
                total_pages INT NOT NULL DEFAULT 2,
                slots_per_page INT NOT NULL DEFAULT 108,
                columns_per_row INT NOT NULL DEFAULT 12,
                distribution_mode VARCHAR(64) NOT NULL DEFAULT 'Sequential Chromatic Fill',
                buffer_slots INT NOT NULL DEFAULT 2,
                snap_to_row BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.execute(text("""
            ALTER TABLE custom_swatch_book ADD COLUMN IF NOT EXISTS total_pages INT NOT NULL DEFAULT 2;
            ALTER TABLE custom_swatch_book ADD COLUMN IF NOT EXISTS slots_per_page INT NOT NULL DEFAULT 108;
            ALTER TABLE custom_swatch_book ADD COLUMN IF NOT EXISTS columns_per_row INT NOT NULL DEFAULT 12;
            ALTER TABLE custom_swatch_book ADD COLUMN IF NOT EXISTS distribution_mode VARCHAR(64) NOT NULL DEFAULT 'Sequential Chromatic Fill';
            ALTER TABLE custom_swatch_book ADD COLUMN IF NOT EXISTS buffer_slots INT NOT NULL DEFAULT 2;
            ALTER TABLE custom_swatch_book ADD COLUMN IF NOT EXISTS snap_to_row BOOLEAN NOT NULL DEFAULT FALSE;
            ALTER TABLE custom_swatch_book ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            ALTER TABLE custom_swatch_book ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        """))

        has_legacy_swatch_code = conn.execute(text("""
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'custom_swatch_book_item' AND column_name = 'swatch_code'
        """)).scalar()

        if has_legacy_swatch_code:
            conn.execute(text("DROP TABLE custom_swatch_book_item CASCADE;"))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS custom_swatch_book_item (
                id VARCHAR(64) PRIMARY KEY,
                book_id VARCHAR(64) NOT NULL REFERENCES custom_swatch_book(id) ON DELETE CASCADE,
                item_id VARCHAR(64) NOT NULL,
                slot_number INT NOT NULL,
                swatch_number VARCHAR(64) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        conn.execute(text("""
            ALTER TABLE custom_swatch_book_item ADD COLUMN IF NOT EXISTS id VARCHAR(64);
            ALTER TABLE custom_swatch_book_item ADD COLUMN IF NOT EXISTS book_id VARCHAR(64);
            ALTER TABLE custom_swatch_book_item ADD COLUMN IF NOT EXISTS item_id VARCHAR(64);
            ALTER TABLE custom_swatch_book_item ADD COLUMN IF NOT EXISTS slot_number INT NOT NULL DEFAULT 1;
            ALTER TABLE custom_swatch_book_item ADD COLUMN IF NOT EXISTS swatch_number VARCHAR(64) NOT NULL DEFAULT '';
            ALTER TABLE custom_swatch_book_item ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS custom_swatch_app_state (
                key VARCHAR(64) PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))

init_tables()

# ---------------------------------------------------------
# Helper Functions (Brand Sanitizer & Persistent State)
# ---------------------------------------------------------
def clean_brand_name(brand_val, default=""):
    """Strips JSON/Python array brackets like ['ORLY'] into clean brand strings."""
    if not brand_val:
        return default
    cleaned = re.sub(r"[\[\]\'\"]", "", str(brand_val)).strip()
    return cleaned if cleaned else default

def get_app_state(key, default=None):
    try:
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT value FROM custom_swatch_app_state WHERE key = CAST(:k AS text)"),
                {"k": key}
            ).scalar()
            return result if result is not None else default
    except Exception:
        return default

def set_app_state(key, value):
    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO custom_swatch_app_state (key, value, updated_at)
                    VALUES (CAST(:k AS text), CAST(:v AS text), CURRENT_TIMESTAMP)
                    ON CONFLICT (key) DO UPDATE 
                    SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP;
                """),
                {"k": key, "v": str(value)}
            )
    except Exception as e:
        print(f"Error saving app state {key}: {e}")

# ---------------------------------------------------------
# Color Science & Chromometric Rainbow Sorting
# ---------------------------------------------------------
def hex_to_rgb(hex_str):
    if not hex_str or not isinstance(hex_str, str):
        return (0.5, 0.5, 0.5)
    h = hex_str.strip().lstrip('#')
    if len(h) == 3:
        h = ''.join([c*2 for c in h])
    if len(h) != 6:
        return (0.5, 0.5, 0.5)
    try:
        r = int(h[0:2], 16) / 255.0
        g = int(h[2:4], 16) / 255.0
        b = int(h[4:6], 16) / 255.0
        return (r, g, b)
    except ValueError:
        return (0.5, 0.5, 0.5)

def hex_to_rgb_255(hex_str):
    r, g, b = hex_to_rgb(hex_str)
    return (int(r * 255), int(g * 255), int(b * 255))

def classify_color(hex_str):
    r, g, b = hex_to_rgb(hex_str)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    h_deg = h * 360.0

    if v < 0.14:
        family, order = 'Blacks', 14
    elif s < 0.08 and v > 0.88:
        family, order = 'Whites', 15
    elif s < 0.12:
        family, order = 'Grays & Silvers', 13
    elif 10 <= h_deg < 48 and v < 0.55 and s > 0.18:
        family, order = 'Browns & Mochas', 11
    elif 15 <= h_deg < 50 and s < 0.35 and 0.50 <= v <= 0.90:
        family, order = 'Nudes & Beiges', 12
    elif 320 <= h_deg < 350 or (h_deg >= 350 and lum > 0.55 and s < 0.70):
        family, order = 'Pinks & Magentas', 2
    elif h_deg >= 345 or h_deg < 12:
        family, order = 'Reds', 1
    elif 12 <= h_deg < 25:
        family, order = 'Corals & Peaches', 3
    elif 25 <= h_deg < 45:
        family, order = 'Oranges', 4
    elif 45 <= h_deg < 70:
        family, order = 'Yellows & Golds', 5
    elif 70 <= h_deg < 165:
        family, order = 'Greens', 6
    elif 165 <= h_deg < 195:
        family, order = 'Teals & Turquoises', 7
    elif 195 <= h_deg < 255:
        family, order = 'Blues', 8
    elif 255 <= h_deg < 285:
        family, order = 'Indigos & Navies', 9
    elif 285 <= h_deg < 320:
        family, order = 'Purples & Violets', 10
    else:
        family, order = 'Reds', 1

    return {
        'h': h, 'h_deg': h_deg,
        's': s, 'v': v,
        'lum': lum,
        'family': family,
        'fam_order': order
    }

# ---------------------------------------------------------
# Buffer-Aware Chromatic Placement Algorithm
# ---------------------------------------------------------
def assign_swatches_with_buffers(items, cols_per_row, total_capacity, prefix, buffer_slots=0, snap_to_row=False):
    """
    Sorts polishes chromatically into 15 color families and leaves intentional buffer gaps
    between color groups to give physical albums room for future additions.
    """
    if not items:
        return [], 0
        
    clean_prefix = str(prefix).replace("–", "-").replace("—", "-")
    
    families_order = [
        'Reds', 'Pinks & Magentas', 'Corals & Peaches', 'Oranges', 'Yellows & Golds',
        'Greens', 'Teals & Turquoises', 'Blues', 'Indigos & Navies', 'Purples & Violets',
        'Browns & Mochas', 'Nudes & Beiges', 'Grays & Silvers', 'Blacks', 'Whites'
    ]
    
    enriched = []
    for it in items:
        m = classify_color(it.get('hex_code', '#888888'))
        d = dict(it)
        d.update(m)
        enriched.append(d)
        
    family_groups = []
    for fam_name in families_order:
        fam_items = [it for it in enriched if it['family'] == fam_name]
        if fam_items:
            fam_items.sort(key=lambda x: (-x['lum'], x['h_deg'], x.get('name', '')))
            family_groups.append((fam_name, fam_items))
            
    other_items = [it for it in enriched if it['family'] not in families_order]
    if other_items:
        other_items.sort(key=lambda x: (-x['lum'], x['h_deg'], x.get('name', '')))
        family_groups.append(('Other', other_items))
        
    assigned = []
    current_slot = 1
    overflow_count = 0
    total_groups = len(family_groups)
    
    for g_idx, (fam_name, f_items) in enumerate(family_groups):
        for item in f_items:
            if current_slot <= total_capacity:
                d = dict(item)
                d['slot_number'] = current_slot
                d['swatch_number'] = f"{clean_prefix}-{current_slot:03d}"
                assigned.append(d)
                current_slot += 1
            else:
                overflow_count += 1
                
        # Insert growth buffers between color families (skip if last group or full)
        if g_idx < total_groups - 1 and current_slot <= total_capacity:
            if buffer_slots > 0:
                current_slot += buffer_slots
                
            if snap_to_row and cols_per_row > 0:
                remainder = (current_slot - 1) % cols_per_row
                if remainder != 0:
                    current_slot += (cols_per_row - remainder)
                    
    return assigned, overflow_count

# ---------------------------------------------------------
# Robust Typography & Font Provider (Guarantees Huge Text)
# ---------------------------------------------------------
@st.cache_resource
def get_guaranteed_font_path(bold=False):
    target_path = f"/tmp/Roboto-{'Bold' if bold else 'Regular'}.ttf"
    if os.path.exists(target_path):
        return target_path

    search_dirs = ["/usr/share/fonts", "/usr/local/share/fonts"]
    for d in search_dirs:
        if os.path.exists(d):
            for root, _, files in os.walk(d):
                for f in files:
                    if f.lower().endswith(".ttf"):
                        if bold and ("bold" in f.lower() or "b.ttf" in f.lower()):
                            return os.path.join(root, f)
                        elif not bold and ("regular" in f.lower() or "r.ttf" in f.lower()):
                            return os.path.join(root, f)

    try:
        url = "https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-Bold.ttf" if bold else "https://raw.githubusercontent.com/googlefonts/roboto/main/src/hinted/Roboto-Regular.ttf"
        urllib.request.urlretrieve(url, target_path)
        if os.path.exists(target_path):
            return target_path
    except Exception:
        pass

    return None

def get_font_handle(size, bold=False):
    font_path = get_guaranteed_font_path(bold=bold)
    if font_path:
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            pass

    try:
        return ImageFont.load_default(size=size)
    except Exception:
        pass

    return ImageFont.load_default()

def draw_text_robust(draw, img, xy, text_str, font, fill, size, anchor="la"):
    if hasattr(font, "size") and font.size > 12:
        try:
            draw.text(xy, text_str, fill=fill, font=font, anchor=anchor)
            return
        except Exception:
            pass

    scale = max(1, int(round(size / 10.0)))
    if scale <= 1:
        draw.text(xy, text_str, fill=fill, font=font, anchor=anchor)
        return

    bbox = draw.textbbox((0, 0), text_str, font=font) if hasattr(draw, "textbbox") else (0, 0, len(text_str) * 6, 11)
    tw = max(1, bbox[2] - bbox[0])
    th = max(1, bbox[3] - bbox[1])

    txt_img = Image.new("RGBA", (tw + 4, th + 4), (0, 0, 0, 0))
    txt_draw = ImageDraw.Draw(txt_img)
    txt_draw.text((0, 0), text_str, fill=fill, font=font)

    scaled_img = txt_img.resize((txt_img.width * scale, txt_img.height * scale), Image.NEAREST)

    px, py = xy
    if "m" in anchor:
        px -= scaled_img.width // 2
    elif "r" in anchor:
        px -= scaled_img.width

    if "m" in anchor:
        py -= scaled_img.height // 2
    elif "b" in anchor:
        py -= scaled_img.height

    img.paste(scaled_img, (int(px), int(py)), scaled_img)

# ---------------------------------------------------------
# Native PDF Generator (Guaranteed Colors & Huge Clear Headers)
# ---------------------------------------------------------
def generate_swatch_book_pdf(book, swatches):
    total_pages = book['total_pages']
    slots_per_page = book['slots_per_page']
    cols_per_row = book['columns_per_row']
    total_capacity = total_pages * slots_per_page
    
    prefix = str(book['prefix']).replace("–", "-").replace("—", "-")
    book_name = str(book['name']).replace("–", "-").replace("—", "-")
    
    swatch_by_slot = {sw['slot_number']: sw for sw in swatches}
    
    page_w = 1700
    page_h = 2200
    margin_x = 70
    margin_y = 60
    header_h = 160
    
    usable_w = page_w - (margin_x * 2)
    usable_h = page_h - margin_y - header_h - 40
    
    num_rows = int(np.ceil(slots_per_page / cols_per_row))
    col_w = usable_w / cols_per_row
    row_h = usable_h / num_rows
    
    font_title = get_font_handle(58, bold=True)
    font_sub = get_font_handle(28, bold=True)
    font_num = get_font_handle(18, bold=True)
    font_name = get_font_handle(13, bold=False)
    font_brand = get_font_handle(11, bold=False)

    pil_pages = []
    
    for p_num in range(1, total_pages + 1):
        img = Image.new("RGB", (page_w, page_h), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        
        p_start = (p_num - 1) * slots_per_page + 1
        p_end = p_num * slots_per_page
        
        header_title = f"{book_name} - Page {p_num} of {total_pages}"
        draw_text_robust(draw, img, (margin_x, margin_y), header_title, font_title, (15, 23, 42), size=58)
        
        header_meta = f"Slots {p_start:03d} - {p_end:03d}   |   Prefix: {prefix}   |   Capacity: {total_capacity} Slots"
        draw_text_robust(draw, img, (margin_x, margin_y + 75), header_meta, font_sub, (71, 85, 105), size=28)
        
        draw.line([(margin_x, margin_y + 125), (page_w - margin_x, margin_y + 125)], fill=(148, 163, 184), width=4)
        
        grid_top = margin_y + header_h
        
        for slot_idx in range(p_start, p_end + 1):
            slot_in_page = slot_idx - p_start
            r = slot_in_page // cols_per_row
            c = slot_in_page % cols_per_row
            
            x0 = margin_x + (c * col_w) + 3
            y0 = grid_top + (r * row_h) + 3
            x1 = x0 + col_w - 6
            y1 = y0 + row_h - 6
            
            cx = (x0 + x1) / 2
            circle_r = 28
            circle_y = y0 + 38
            
            if slot_idx in swatch_by_slot:
                sw = swatch_by_slot[slot_idx]
                rgb = hex_to_rgb_255(sw.get('hex_code', '#ffffff'))
                s_num = str(sw['swatch_number']).replace("–", "-").replace("—", "-")
                s_name = sw.get('name') or ''
                s_brand = clean_brand_name(sw.get('brand'))
                
                draw.rectangle([x0, y0, x1, y1], fill=(255, 255, 255), outline=(203, 213, 225), width=1)
                draw.ellipse([cx - circle_r, circle_y - circle_r, cx + circle_r, circle_y + circle_r], fill=rgb, outline=(0, 0, 0), width=2)
                
                draw_text_robust(draw, img, (cx, y0 + 78), s_num, font_num, (15, 23, 42), size=18, anchor="mm")
                trunc_name = s_name[:14] + '..' if len(s_name) > 15 else s_name
                draw_text_robust(draw, img, (cx, y0 + 102), trunc_name, font_name, (51, 65, 85), size=14, anchor="mm")
                trunc_brand = s_brand[:15] if s_brand else ""
                draw_text_robust(draw, img, (cx, y0 + 124), trunc_brand, font_brand, (100, 116, 139), size=12, anchor="mm")
            else:
                draw.rectangle([x0, y0, x1, y1], fill=(248, 250, 252), outline=(226, 232, 240), width=1)
                draw.ellipse([cx - circle_r, circle_y - circle_r, cx + circle_r, circle_y + circle_r], fill=(255, 255, 255), outline=(148, 163, 184), width=1)
                draw_text_robust(draw, img, (cx, y0 + 78), f"{slot_idx:03d}", font_num, (148, 163, 184), size=16, anchor="mm")
                draw_text_robust(draw, img, (cx, y0 + 102), "Available", font_name, (203, 213, 225), size=13, anchor="mm")
                
        pil_pages.append(img)
        
    pdf_buffer = io.BytesIO()
    if pil_pages:
        pil_pages[0].save(pdf_buffer, format="PDF", save_all=True, append_images=pil_pages[1:], resolution=200.0)
    return pdf_buffer.getvalue()

# ---------------------------------------------------------
# Database Query Functions
# ---------------------------------------------------------
def get_collections():
    with engine.connect() as conn:
        res = conn.execute(text("SELECT id, title FROM koi_collection ORDER BY title ASC")).mappings().all()
        return [dict(r) for r in res]

def get_items_for_collection(collection_id):
    sql = """
    SELECT 
        i.id,
        i.name,
        i.collection_id,
        i.owner_id,
        c.title AS collection_title,
        MAX(CASE WHEN d.label ILIKE 'Colo%r%(Hex)%' OR d.label ILIKE 'Colour (Hex)' THEN d.value END) AS hex_code,
        MAX(CASE WHEN d.label ILIKE 'Finish%' THEN d.value END) AS finish,
        MAX(CASE WHEN d.label ILIKE 'Brand' THEN d.value END) AS brand,
        MAX(CASE WHEN d.label ILIKE 'Lacquer Type' THEN d.value END) AS lacquer_type,
        MAX(CASE WHEN d.label ILIKE 'Location' OR d.label ILIKE 'Other Location%' THEN d.value END) AS location,
        MAX(CASE WHEN d.label ILIKE 'Swatch Number' THEN d.value END) AS swatch_number,
        MAX(CASE WHEN d.label ILIKE 'Swatch Book' THEN d.value END) AS swatch_book
    FROM koi_item i
    JOIN koi_collection c ON c.id = i.collection_id
    LEFT JOIN koi_datum d ON d.item_id = i.id
    WHERE (:col_id IS NULL OR i.collection_id = CAST(:col_id AS text))
    GROUP BY i.id, i.name, i.collection_id, i.owner_id, c.title
    ORDER BY i.name ASC;
    """
    with engine.connect() as conn:
        res = conn.execute(text(sql), {"col_id": collection_id}).mappings().all()
        return [dict(r) for r in res]

def get_books_for_collection(collection_id):
    with engine.connect() as conn:
        sql = """
        SELECT id, name, prefix, collection_id, total_pages, slots_per_page, 
               columns_per_row, distribution_mode, buffer_slots, snap_to_row, created_at, updated_at
        FROM custom_swatch_book
        WHERE (:col_id IS NULL OR collection_id = CAST(:col_id AS text))
        ORDER BY name ASC;
        """
        res = conn.execute(text(sql), {"col_id": collection_id}).mappings().all()
        return [dict(r) for r in res]

def get_book_by_id(book_id):
    with engine.connect() as conn:
        sql = "SELECT * FROM custom_swatch_book WHERE id = CAST(:bid AS text)"
        row = conn.execute(text(sql), {"bid": book_id}).mappings().first()
        return dict(row) if row else None

def get_book_items(book_id):
    with engine.connect() as conn:
        sql = """
        SELECT sbi.slot_number, sbi.swatch_number, sbi.item_id,
               i.name, i.owner_id,
               MAX(CASE WHEN d.label ILIKE 'Colo%r%(Hex)%' OR d.label ILIKE 'Colour (Hex)' THEN d.value END) AS hex_code,
               MAX(CASE WHEN d.label ILIKE 'Finish%' THEN d.value END) AS finish,
               MAX(CASE WHEN d.label ILIKE 'Brand' THEN d.value END) AS brand,
               MAX(CASE WHEN d.label ILIKE 'Lacquer Type' THEN d.value END) AS lacquer_type
        FROM custom_swatch_book_item sbi
        JOIN koi_item i ON i.id = sbi.item_id
        LEFT JOIN koi_datum d ON d.item_id = i.id
        WHERE sbi.book_id = CAST(:bid AS text)
        GROUP BY sbi.slot_number, sbi.swatch_number, sbi.item_id, i.name, i.owner_id
        ORDER BY sbi.slot_number ASC;
        """
        res = conn.execute(text(sql), {"bid": book_id}).mappings().all()
        return [dict(r) for r in res]

def save_book_items(book_id, prefix, items_to_assign):
    """Saves swatch assignments respecting custom slot coordinates and buffers."""
    clean_prefix = str(prefix).replace("–", "-").replace("—", "-")
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM custom_swatch_book_item WHERE book_id = CAST(:bid AS text)"), {"bid": book_id})
        for idx, item in enumerate(items_to_assign):
            slot_num = item.get('slot_number', idx + 1)
            swatch_num = item.get('swatch_number', f"{clean_prefix}-{slot_num:03d}")
            conn.execute(
                text("""
                    INSERT INTO custom_swatch_book_item (id, book_id, item_id, slot_number, swatch_number)
                    VALUES (CAST(:id AS text), CAST(:bid AS text), CAST(:item_id AS text), :slot, CAST(:swatch AS text))
                """),
                {
                    "id": str(uuid.uuid4()),
                    "bid": book_id,
                    "item_id": item['id'],
                    "slot": slot_num,
                    "swatch": swatch_num
                }
            )

def remove_swatch_from_book(book_id, item_id):
    book = get_book_by_id(book_id)
    if not book:
        return
    prefix = str(book['prefix']).replace("–", "-").replace("—", "-")
    
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM custom_swatch_book_item WHERE book_id = CAST(:bid AS text) AND item_id = CAST(:iid AS text)"),
            {"bid": book_id, "iid": item_id}
        )
        rem_res = conn.execute(
            text("SELECT id, item_id FROM custom_swatch_book_item WHERE book_id = CAST(:bid AS text) ORDER BY slot_number ASC"),
            {"bid": book_id}
        ).mappings().all()
        
        for new_slot, row in enumerate(rem_res, start=1):
            new_swatch = f"{prefix}-{new_slot:03d}"
            conn.execute(
                text("UPDATE custom_swatch_book_item SET slot_number = :slot, swatch_number = CAST(:snum AS text) WHERE id = CAST(:row_id AS text)"),
                {"slot": new_slot, "snum": new_swatch, "row_id": row['id']}
            )

def commit_swatches_to_koillection(book_id):
    book = get_book_by_id(book_id)
    if not book:
        return 0
    book_items = get_book_items(book_id)
    book_name = book['name']
    
    count = 0
    with engine.begin() as conn:
        for it in book_items:
            item_id = it['item_id']
            swatch_number = it['swatch_number']
            owner_id = it.get('owner_id')
            if not owner_id:
                owner_id = conn.execute(
                    text("SELECT owner_id FROM koi_item WHERE id = CAST(:iid AS text)"),
                    {"iid": item_id}
                ).scalar()

            existing_num = conn.execute(
                text("SELECT id FROM koi_datum WHERE item_id = CAST(:iid AS text) AND label = 'Swatch Number'"),
                {"iid": item_id}
            ).scalar()
            if existing_num:
                conn.execute(
                    text("UPDATE koi_datum SET value = CAST(:val AS text), updated_at = CURRENT_TIMESTAMP WHERE id = CAST(:id AS text)"),
                    {"val": swatch_number, "id": existing_num}
                )
            else:
                conn.execute(
                    text("""
                        INSERT INTO koi_datum (id, item_id, type, label, value, position, created_at, updated_at, visibility, final_visibility, owner_id)
                        VALUES (CAST(:id AS text), CAST(:iid AS text), 'text', 'Swatch Number', CAST(:val AS text), 10, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'public', 'public', CAST(:owner_id AS text))
                    """),
                    {"id": str(uuid.uuid4()), "iid": item_id, "val": swatch_number, "owner_id": owner_id}
                )
                
            existing_book = conn.execute(
                text("SELECT id FROM koi_datum WHERE item_id = CAST(:iid AS text) AND label = 'Swatch Book'"),
                {"iid": item_id}
            ).scalar()
            if existing_book:
                conn.execute(
                    text("UPDATE koi_datum SET value = CAST(:val AS text), updated_at = CURRENT_TIMESTAMP WHERE id = CAST(:id AS text)"),
                    {"val": book_name, "id": existing_book}
                )
            else:
                conn.execute(
                    text("""
                        INSERT INTO koi_datum (id, item_id, type, label, value, position, created_at, updated_at, visibility, final_visibility, owner_id)
                        VALUES (CAST(:id AS text), CAST(:iid AS text), 'text', 'Swatch Book', CAST(:val AS text), 11, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'public', 'public', CAST(:owner_id AS text))
                    """),
                    {"id": str(uuid.uuid4()), "iid": item_id, "val": book_name, "owner_id": owner_id}
                )
            count += 1
    return count

# ---------------------------------------------------------
# Intercept In-Card '✕' Clicks
# ---------------------------------------------------------
q_params = st.query_params
if "remove_item_id" in q_params:
    to_remove = q_params.get("remove_item_id")
    target_book = q_params.get("book_id")
    target_col = q_params.get("collection_id")
    
    if target_book and to_remove:
        remove_swatch_from_book(target_book, to_remove)
        if target_col:
            set_app_state("active_collection_id", target_col)
            st.session_state["sel_col_widget"] = target_col
        set_app_state("active_book_id", target_book)
        st.session_state["sel_book_widget"] = target_book

    st.query_params.clear()
    if target_col:
        st.query_params["collection_id"] = target_col
    if target_book:
        st.query_params["book_id"] = target_book
    st.rerun()

# ---------------------------------------------------------
# Sidebar: Library & Book Selection
# ---------------------------------------------------------
st.sidebar.title("🎨 Color Swatch Creator")

all_collections = get_collections()
col_dict = {c['id']: c['title'] for c in all_collections}
col_ids = list(col_dict.keys())

persisted_col = get_app_state("active_collection_id")
active_col_id = None
if "collection_id" in st.query_params and st.query_params["collection_id"] in col_ids:
    active_col_id = st.query_params["collection_id"]
elif persisted_col in col_ids:
    active_col_id = persisted_col
elif col_ids:
    active_col_id = col_ids[0]

if "sel_col_widget" not in st.session_state or st.session_state["sel_col_widget"] not in col_ids:
    st.session_state["sel_col_widget"] = active_col_id

def on_col_change():
    new_c = st.session_state["sel_col_widget"]
    set_app_state("active_collection_id", new_c)
    st.query_params["collection_id"] = new_c
    new_books = get_books_for_collection(new_c)
    if new_books:
        first_b = new_books[0]['id']
        st.session_state["sel_book_widget"] = first_b
        set_app_state("active_book_id", first_b)
        st.query_params["book_id"] = first_b
    else:
        st.session_state["sel_book_widget"] = None
        set_app_state("active_book_id", "")
        if "book_id" in st.query_params:
            del st.query_params["book_id"]

selected_col_id = st.sidebar.selectbox(
    "📁 Select Library / Collection",
    options=col_ids,
    format_func=lambda cid: col_dict.get(cid, "Default Library"),
    key="sel_col_widget",
    on_change=on_col_change
)

books = get_books_for_collection(selected_col_id)
book_dict = {b['id']: b for b in books}
book_ids = list(book_dict.keys())

persisted_book = get_app_state("active_book_id")
active_book_id = None
if "book_id" in st.query_params and st.query_params["book_id"] in book_ids:
    active_book_id = st.query_params["book_id"]
elif persisted_book in book_ids:
    active_book_id = persisted_book
elif book_ids:
    active_book_id = book_ids[0]

if "sel_book_widget" not in st.session_state or st.session_state["sel_book_widget"] not in book_ids:
    st.session_state["sel_book_widget"] = active_book_id

def on_book_change():
    new_b = st.session_state["sel_book_widget"]
    set_app_state("active_book_id", new_b)
    st.query_params["book_id"] = new_b
    for k in ["flt_brands", "flt_finishes", "flt_lacquers", "flt_families", "flt_search", "flt_unswatched"]:
        if k in st.session_state:
            del st.session_state[k]

if book_ids:
    selected_book_id = st.sidebar.selectbox(
        "📖 Select Swatch Book",
        options=book_ids,
        format_func=lambda bid: f"{book_dict[bid]['name']} (Prefix: {book_dict[bid]['prefix']})",
        key="sel_book_widget",
        on_change=on_book_change
    )
    current_book = book_dict.get(selected_book_id)
else:
    current_book = None
    st.sidebar.info("No swatch books found for this collection. Create one below!")

# ---------------------------------------------------------
# Sidebar: Book Management (Create / Edit)
# ---------------------------------------------------------
st.sidebar.markdown("---")
with st.sidebar.expander("➕ Create New Swatch Book", expanded=not bool(book_ids)):
    with st.form("create_book_form"):
        new_b_name = st.text_input("Book Name", value=f"Swatch Book {len(books) + 1}")
        new_b_prefix = st.text_input("Prefix (e.g. 1, 2, B1)", value=str(len(books) + 1))
        new_b_pages = st.number_input("Total Pages in Album", min_value=1, max_value=20, value=2, step=1)
        new_b_slots = st.number_input("Slots Per Page", min_value=12, max_value=300, value=108, step=12)
        new_b_cols = st.number_input("Columns Per Row", min_value=4, max_value=24, value=12, step=1)
        new_b_mode = st.selectbox("Distribution Strategy", ["Sequential Chromatic Fill", "Visually Balanced Gamut"])
        new_b_buffer = st.number_input("Buffer Slots Between Color Groups", min_value=0, max_value=24, value=2, step=1, help="Empty slots left after each color family.")
        new_b_snap = st.checkbox("Snap Color Groups to New Row", value=False, help="Always start each new color group at the beginning of a fresh row.")
        
        create_btn = st.form_submit_button("✨ Create Swatch Book", use_container_width=True)
        if create_btn:
            new_id = str(uuid.uuid4())
            with engine.begin() as conn:
                conn.execute(
                    text("""
                        INSERT INTO custom_swatch_book (id, name, prefix, collection_id, total_pages, slots_per_page, columns_per_row, distribution_mode, buffer_slots, snap_to_row)
                        VALUES (CAST(:id AS text), CAST(:name AS text), CAST(:pref AS text), CAST(:cid AS text), :p, :s, :c, CAST(:m AS text), :b, :snap)
                    """),
                    {
                        "id": new_id, "name": new_b_name, "pref": new_b_prefix,
                        "cid": selected_col_id, "p": new_b_pages, "s": new_b_slots,
                        "c": new_b_cols, "m": new_b_mode, "b": new_b_buffer, "snap": new_b_snap
                    }
                )
            set_app_state("active_book_id", new_id)
            st.query_params["book_id"] = new_id
            st.session_state["sel_book_widget"] = new_id
            st.rerun()

if current_book:
    with st.sidebar.expander("⚙️ Edit Current Book Settings"):
        with st.form("edit_book_form"):
            edit_b_name = st.text_input("Book Name", value=current_book['name'])
            edit_b_prefix = st.text_input("Prefix", value=current_book['prefix'])
            edit_b_pages = st.number_input("Total Pages", min_value=1, max_value=20, value=current_book['total_pages'], step=1)
            edit_b_slots = st.number_input("Slots Per Page", min_value=12, max_value=300, value=current_book['slots_per_page'], step=12)
            edit_b_cols = st.number_input("Columns Per Row", min_value=4, max_value=24, value=current_book['columns_per_row'], step=1)
            edit_b_mode = st.selectbox(
                "Distribution Strategy",
                ["Sequential Chromatic Fill", "Visually Balanced Gamut"],
                index=0 if current_book['distribution_mode'] == 'Sequential Chromatic Fill' else 1
            )
            edit_b_buffer = st.number_input("Buffer Slots Between Color Groups", min_value=0, max_value=24, value=int(current_book.get('buffer_slots', 2)), step=1)
            edit_b_snap = st.checkbox("Snap Color Groups to New Row", value=bool(current_book.get('snap_to_row', False)))
            
            save_edit_btn = st.form_submit_button("💾 Save Book Changes", use_container_width=True)
            if save_edit_btn:
                with engine.begin() as conn:
                    conn.execute(
                        text("""
                            UPDATE custom_swatch_book
                            SET name = CAST(:name AS text), prefix = CAST(:pref AS text),
                                total_pages = :p, slots_per_page = :s, columns_per_row = :c,
                                distribution_mode = CAST(:m AS text), buffer_slots = :b, snap_to_row = :snap, updated_at = CURRENT_TIMESTAMP
                            WHERE id = CAST(:bid AS text)
                        """),
                        {
                            "name": edit_b_name, "pref": edit_b_prefix,
                            "p": edit_b_pages, "s": edit_b_slots, "c": edit_b_cols,
                            "m": edit_b_mode, "b": edit_b_buffer, "snap": edit_b_snap, "bid": current_book['id']
                        }
                    )
                st.rerun()
                
        st.write("")
        confirm_del = st.checkbox("Confirm deletion of this book", key="confirm_del_book")
        if st.button("🗑️ Delete This Book", type="secondary", disabled=not confirm_del, use_container_width=True):
            with engine.begin() as conn:
                conn.execute(text("DELETE FROM custom_swatch_book WHERE id = CAST(:bid AS text)"), {"bid": current_book['id']})
            set_app_state("active_book_id", "")
            if "book_id" in st.query_params:
                del st.query_params["book_id"]
            st.rerun()

# ---------------------------------------------------------
# Main Panel: Instructions, Filters, Metrics, and Actions
# ---------------------------------------------------------
if not current_book:
    st.info("👈 Please select or create a Swatch Book in the sidebar to begin.")
    st.stop()

# Instructions & User Guide Dropdown (Matching Sibling Apps)
with st.expander("ℹ️ Instructions & User Guide (Click to expand)", expanded=False):
    st.markdown("""
    <div class="guide-box">
        <h4 style="margin-top: 0; margin-bottom: 10px; color: #1e293b;">🎨 How to Use the Color Swatch Creator</h4>
        <p><span class="guide-step">1. Select or Create a Swatch Book:</span> Choose your physical album from the sidebar or click <i>"➕ Create New Swatch Book"</i>. Match your physical album's layout (Total Pages, Slots Per Page, Columns Per Row).</p>
        <p><span class="guide-step">2. Color Growth Buffers:</span> Prevent the <i>"avalanche effect"</i> where buying 1 new red polish forces you to shift 100 sticks! Use the <b>Buffer Slider</b> to leave empty slots after each color group, or check <b>"Snap to New Row"</b> to ensure each color starts cleanly on a fresh line.</p>
        <p><span class="guide-step">3. Filter Your Library:</span> Use the <i>"🔍 Simplified Exclusion Filters"</i> to exclude brands, finishes, formulas, or colors you don't want swatched into this album. All exclusion filters are automatically saved to the database and will survive swatch deletions.</p>
        <p><span class="guide-step">4. Auto-Populate & Instant ✕ Removal:</span> Click <b>"🔄 Auto-Populate"</b> to sort polishes chromometrically (Red → Violet → Browns → Neutrals, light to dark). If a polish doesn't belong, click the red <b>✕</b> on its card to instantly remove it and smoothly re-sequence the remaining slots.</p>
        <p><span class="guide-step">5. Print & Export Hub:</span>
            <ul>
                <li><b>📕 Generated PDF:</b> Creates a high-res vector multi-page PDF with true RGB color fills and bold headers ready to print on cardstock or slide behind swatch sleeves.</li>
                <li><b>🏷️ Mail-Merge CSV:</b> Formatted for Avery, Brother P-touch, and Dymo label printing software.</li>
                <li><b>🎯 Swatch Dot Labels:</b> Circular stickers formatted for 0.5"–0.75" swatch stick caps and bottle tops.</li>
                <li><b>📋 Directory Insert:</b> A binder index table map to slip inside the front/back cover of your album.</li>
            </ul>
        </p>
        <p><span class="guide-step">6. Commit to Database:</span> Click <b>"📥 Commit to Koillection DB"</b> to permanently write the assigned <code>Swatch Number</code> (e.g., <code>1-001</code>) and <code>Swatch Book</code> name to each item in Koillection.</p>
    </div>
    """, unsafe_allow_html=True)

raw_items = get_items_for_collection(selected_col_id)
total_library_items = len(raw_items)

valid_hex_items = [it for it in raw_items if it.get('hex_code') and str(it.get('hex_code')).strip().startswith('#')]
missing_hex_count = total_library_items - len(valid_hex_items)

all_brands = sorted(list({clean_brand_name(it.get('brand')) for it in valid_hex_items if it.get('brand')}))
all_brands = [b for b in all_brands if b]
all_finishes = sorted(list({it['finish'] for it in valid_hex_items if it.get('finish')}))
all_lacquers = sorted(list({it['lacquer_type'] for it in valid_hex_items if it.get('lacquer_type')}))
all_families = [
    'Reds', 'Pinks & Magentas', 'Corals & Peaches', 'Oranges', 'Yellows & Golds',
    'Greens', 'Teals & Turquoises', 'Blues', 'Indigos & Navies', 'Purples & Violets',
    'Browns & Mochas', 'Nudes & Beiges', 'Grays & Silvers', 'Blacks', 'Whites'
]

# Persistent Exclusions
filter_state_key = f"filters_{current_book['id']}"
saved_filters_raw = get_app_state(filter_state_key, "{}")
try:
    saved_filters = json.loads(saved_filters_raw)
except Exception:
    saved_filters = {}

if "vault" not in st.session_state:
    st.session_state.vault = {}

for fk, default_val in [
    ("flt_brands", []),
    ("flt_finishes", []),
    ("flt_lacquers", []),
    ("flt_families", []),
    ("flt_search", ""),
    ("flt_unswatched", False)
]:
    if fk not in st.session_state.vault:
        st.session_state.vault[fk] = saved_filters.get(fk, default_val)
    if fk not in st.session_state:
        st.session_state[fk] = st.session_state.vault[fk]

st.session_state["flt_brands"] = [x for x in st.session_state["flt_brands"] if x in all_brands]
st.session_state["flt_finishes"] = [x for x in st.session_state["flt_finishes"] if x in all_finishes]
st.session_state["flt_lacquers"] = [x for x in st.session_state["flt_lacquers"] if x in all_lacquers]
st.session_state["flt_families"] = [x for x in st.session_state["flt_families"] if x in all_families]

st.subheader(f"📖 {current_book['name']} (Prefix: {current_book['prefix']})")

with st.expander("🔍 Simplified Exclusion Filters & Polish Selection", expanded=False):
    st.caption("Select items to exclude from the swatch book. Items not excluded will be available for swatching.")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        excluded_brands = st.multiselect("Exclude Brands:", options=all_brands, key="flt_brands")
        excluded_finishes = st.multiselect("Exclude Finishes:", options=all_finishes, key="flt_finishes")
    with col_f2:
        excluded_lacquers = st.multiselect("Exclude Lacquer Types:", options=all_lacquers, key="flt_lacquers")
        excluded_families = st.multiselect("Exclude Color Families:", options=all_families, key="flt_families")
        
    col_f3, col_f4 = st.columns([2, 1])
    with col_f3:
        search_query = st.text_input("Search polish name or brand:", placeholder="e.g. OPI, Glitter, Ruby...", key="flt_search").strip().lower()
    with col_f4:
        st.write("")
        st.write("")
        unswatched_only = st.checkbox("Only unswatched polishes", key="flt_unswatched", help="Exclude polishes that already have a Swatch Number in Koillection.")

current_flt_state = {
    "flt_brands": excluded_brands,
    "flt_finishes": excluded_finishes,
    "flt_lacquers": excluded_lacquers,
    "flt_families": excluded_families,
    "flt_search": search_query,
    "flt_unswatched": unswatched_only
}
if current_flt_state != saved_filters:
    st.session_state.vault.update(current_flt_state)
    set_app_state(filter_state_key, json.dumps(current_flt_state))

filtered_items = []
for it in valid_hex_items:
    clean_b = clean_brand_name(it.get('brand'))
    if clean_b in excluded_brands:
        continue
    if it.get('finish') in excluded_finishes:
        continue
    if it.get('lacquer_type') in excluded_lacquers:
        continue
    if unswatched_only and it.get('swatch_number'):
        continue
    if search_query:
        name_match = search_query in it.get('name', '').lower()
        brand_match = search_query in clean_b.lower()
        if not (name_match or brand_match):
            continue
    cat = classify_color(it['hex_code'])
    if cat['family'] in excluded_families:
        continue
    filtered_items.append(it)

active_filter_tags = []
if excluded_brands:
    active_filter_tags.append(f"Excluded {len(excluded_brands)} Brands")
if excluded_finishes:
    active_filter_tags.append(f"Excluded {len(excluded_finishes)} Finishes")
if excluded_lacquers:
    active_filter_tags.append(f"Excluded {len(excluded_lacquers)} Types")
if excluded_families:
    active_filter_tags.append(f"Excluded {len(excluded_families)} Colors")
if unswatched_only:
    active_filter_tags.append("Unswatched Only")
if search_query:
    active_filter_tags.append(f"Search: '{search_query}'")

if active_filter_tags:
    st.markdown("".join([f"<span class='filter-chip'>🚫 {t}</span>" for t in active_filter_tags]), unsafe_allow_html=True)

# ---------------------------------------------------------
# Book Capacity & Swatch Calculation with Buffers
# ---------------------------------------------------------
total_pages = current_book['total_pages']
slots_per_page = current_book['slots_per_page']
cols_per_row = current_book['columns_per_row']
total_capacity = total_pages * slots_per_page

current_buffer_slots = int(current_book.get('buffer_slots', 2))
current_snap_row = bool(current_book.get('snap_to_row', False))

current_swatches = get_book_items(current_book['id'])

if not current_swatches and filtered_items:
    chosen, _ = assign_swatches_with_buffers(
        filtered_items, cols_per_row, total_capacity, current_book['prefix'],
        buffer_slots=current_buffer_slots, snap_to_row=current_snap_row
    )
    save_book_items(current_book['id'], current_book['prefix'], chosen)
    current_swatches = get_book_items(current_book['id'])

col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)
col_m1.metric("Book Capacity", f"{total_capacity} slots", f"{total_pages} pages × {slots_per_page}")
col_m2.metric("Library Polishes", f"{total_library_items} total", f"{len(valid_hex_items)} with Hex")
col_m3.metric("Passed Filters", f"{len(filtered_items)} polishes")
col_m4.metric("Assigned Swatches", f"{len(current_swatches)} in Book")
empty_slots_count = max(0, total_capacity - len(current_swatches))
col_m5.metric("Available Gaps", f"{empty_slots_count} slots", f"{current_buffer_slots} buf / {'Row-Snap ON' if current_snap_row else 'Linear'}")

if missing_hex_count > 0:
    st.info(f"ℹ️ Note: **{missing_hex_count}** polishes in this library do not have a hex code (`Colour (Hex)`) entered in Koillection and were skipped. Enter hex codes in Koillection to include them.")

# ---------------------------------------------------------
# Quick Buffer Tuning & Action Toolbar
# ---------------------------------------------------------
with st.expander("⚙️ Quick Buffer Tuning & Growth Settings (Room for Future Polishes)", expanded=False):
    col_buf1, col_buf2, col_buf3 = st.columns([2.5, 2.5, 2])
    with col_buf1:
        quick_buffer = st.slider(
            "Buffer empty slots between color groups:",
            min_value=0, max_value=12,
            value=current_buffer_slots,
            help="Leaves unassigned slots after each color group so you can insert future bottles without shifting physical swatches."
        )
    with col_buf2:
        st.write("")
        quick_snap = st.checkbox(
            "Snap each color group to a new row",
            value=current_snap_row,
            help="Rounds up empty slots so every new color family begins at Column 1 of a fresh row."
        )
    with col_buf3:
        st.write("")
        if st.button("💾 Apply & Re-Populate Layout", type="primary", use_container_width=True):
            with engine.begin() as conn:
                conn.execute(
                    text("UPDATE custom_swatch_book SET buffer_slots = :b, snap_to_row = :snap, updated_at = CURRENT_TIMESTAMP WHERE id = CAST(:bid AS text)"),
                    {"b": quick_buffer, "snap": quick_snap, "bid": current_book['id']}
                )
            chosen, overflow = assign_swatches_with_buffers(
                filtered_items, cols_per_row, total_capacity, current_book['prefix'],
                buffer_slots=quick_buffer, snap_to_row=quick_snap
            )
            save_book_items(current_book['id'], current_book['prefix'], chosen)
            if overflow > 0:
                st.warning(f"⚠️ Notice: Buffers pushed {overflow} polishes beyond the {total_capacity}-slot album capacity. Consider increasing total pages in sidebar settings.")
            st.toast(f"✅ Layout re-populated with buffers! {len(chosen)} swatches assigned.", icon="✨")
            st.rerun()

st.markdown("---")
col_tb1, col_tb2 = st.columns([1, 1])

with col_tb1:
    if st.button("🔄 Auto-Populate / Reset Book", type="primary", use_container_width=True, help="Sorts matching polishes chromometrically, applies growth buffers, and re-populates all slots."):
        chosen, overflow = assign_swatches_with_buffers(
            filtered_items, cols_per_row, total_capacity, current_book['prefix'],
            buffer_slots=current_buffer_slots, snap_to_row=current_snap_row
        )
        save_book_items(current_book['id'], current_book['prefix'], chosen)
        if overflow > 0:
            st.warning(f"⚠️ Notice: Buffers pushed {overflow} polishes beyond the {total_capacity}-slot album capacity. Consider increasing total pages in sidebar settings.")
        st.toast(f"✅ Assigned {len(chosen)} swatches into Book '{current_book['name']}'!", icon="🎉")
        st.rerun()

with col_tb2:
    if st.button("📥 Commit to Koillection DB", use_container_width=True, help="Writes 'Swatch Number' (e.g. 1-001) and 'Swatch Book' into Koillection items."):
        with st.spinner("Writing swatch numbers to database..."):
            written = commit_swatches_to_koillection(current_book['id'])
            st.toast(f"✅ Successfully updated {written} items in Koillection!", icon="💾")

# ---------------------------------------------------------
# Comprehensive Export & Print Hub (ALWAYS VISIBLE)
# ---------------------------------------------------------
with st.expander("📦 Print & Export Hub (PDF Generation, CSVs, Swatch Sheets, Labels & Directory)", expanded=True):
    tab_pdf, tab_csv, tab_labels, tab_directory = st.tabs([
        "📕 Generated PDF Swatch Book",
        "🏷️ CSV Exports", 
        "🎯 Printable Swatch Dot Labels", 
        "📋 Directory Insert"
    ])
    
    # TAB 1: Native PDF Generator with Huge Clear Headers & True Colors
    with tab_pdf:
        st.markdown("#### 📕 High-Resolution Swatch Book PDF")
        st.caption("Generates a multi-page PDF document with large, bold, high-visibility headers, true hyphens, and baked-in RGB colors.")
        if current_swatches:
            with st.spinner("Rendering vector-quality PDF swatch book with bold typography..."):
                pdf_bytes = generate_swatch_book_pdf(current_book, current_swatches)
            
            st.download_button(
                label="📥 Download Swatch Book PDF (Large Headers & True Colors)",
                data=pdf_bytes,
                file_name=f"{current_book['name'].replace(' ', '_')}_Swatch_Album.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
                help="Download high-resolution PDF for printing on paper, cardstock, or binder sleeves."
            )
            st.success("✅ PDF rendered with large bold headers, true ASCII hyphens, clean brand text, and exact RGB color fills.")
        else:
            st.info("💡 Click '🔄 Auto-Populate / Reset Book' above to generate swatches before creating the PDF.")

    # TAB 2: CSV Exports
    with tab_csv:
        st.markdown("#### 📥 CSV Downloads")
        c_csv1, c_csv2 = st.columns(2)
        with c_csv1:
            if current_swatches:
                csv_buffer = io.StringIO()
                writer = csv.writer(csv_buffer)
                writer.writerow(["Label", "Book", "Swatch", "Name", "Brand", "Color", "Finish", "Page", "Row", "Column"])
                for sw in current_swatches:
                    slot = sw['slot_number']
                    page = ((slot - 1) // slots_per_page) + 1
                    page_slot = ((slot - 1) % slots_per_page)
                    row = (page_slot // cols_per_row) + 1
                    col = (page_slot % cols_per_row) + 1
                    clean_b = clean_brand_name(sw.get('brand'))
                    writer.writerow([
                        sw['swatch_number'],
                        current_book['prefix'],
                        f"{slot:03d}",
                        sw['name'],
                        clean_b,
                        sw.get('hex_code') or '',
                        sw.get('finish') or '',
                        page, row, col
                    ])
                st.download_button(
                    "🏷️ Download Mail-Merge CSV (Avery / Label Printers)",
                    data=csv_buffer.getvalue(),
                    file_name=f"swatch_labels_{current_book['prefix']}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    help="Strictly formatted CSV ready for Avery, Brother P-touch, and Dymo software."
                )
            else:
                st.info("💡 Click '🔄 Auto-Populate / Reset Book' above to generate swatches for CSV export.")
        
        with c_csv2:
            if current_swatches:
                inv_df = pd.DataFrame([
                    {
                        "Slot": sw['slot_number'],
                        "Swatch Number": sw['swatch_number'],
                        "Name": sw['name'],
                        "Brand": clean_brand_name(sw.get('brand')),
                        "Hex": sw.get('hex_code') or '',
                        "Finish": sw.get('finish') or '',
                        "Page": ((sw['slot_number'] - 1) // slots_per_page) + 1
                    }
                    for sw in current_swatches
                ])
                st.download_button(
                    "📊 Download Complete Book Inventory CSV",
                    data=inv_df.to_csv(index=False),
                    file_name=f"swatch_inventory_{current_book['prefix']}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    help="Spreadsheet-friendly CSV of all items in this swatch book."
                )

    # TAB 3: Printable Swatch Dot Labels
    with tab_labels:
        st.markdown("#### 🎯 Printable Swatch Dot Labels")
        st.caption("Circular swatch sticker dots formatted for bottle caps or swatch sticks. Ready to print on sticker paper.")
        if current_swatches:
            labels_html = f"""
            <style>
                * {{
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                    color-adjust: exact !important;
                }}
                @media print {{
                    body {{ margin: 0; background: #fff !important; font-family: sans-serif; }}
                    .no-print {{ display: none !important; }}
                }}
                .label-sheet {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
                    gap: 8px;
                    padding: 10px;
                }}
                .swatch-dot-label {{
                    width: 80px;
                    height: 80px;
                    border-radius: 50%;
                    border: 1px dashed #64748b;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    text-align: center;
                    padding: 4px;
                    box-sizing: border-box;
                    background: #ffffff;
                }}
                .dot-color-preview {{
                    width: 22px;
                    height: 22px;
                    border-radius: 50%;
                    border: 1px solid #000;
                    margin-bottom: 2px;
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                }}
            </style>
            <div style="margin-bottom: 12px;" class="no-print">
                <button onclick="window.print()" style="padding: 10px 20px; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 14px;">🖨️ Print Labels Now</button>
            </div>
            <div class="label-sheet">
            """
            for sw in current_swatches:
                hex_val = sw.get('hex_code') or '#ffffff'
                clean_snum = str(sw['swatch_number']).replace("–", "-").replace("—", "-")
                clean_b = clean_brand_name(sw.get('brand'))
                labels_html += f"""
                <div class="swatch-dot-label">
                    <div class="dot-color-preview" style="background-color: {hex_val}; background: {hex_val};"></div>
                    <div style="font-size: 9px; font-weight: 900; line-height: 1;">{clean_snum}</div>
                    <div style="font-size: 7px; max-width: 72px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; line-height: 1.1; margin-top: 2px;">{sw['name']}</div>
                    <div style="font-size: 6px; color: #64748b;">{clean_b}</div>
                </div>
                """
            labels_html += "</div>"
            st.components.v1.html(labels_html, height=450, scrolling=True)
        else:
            st.info("Populate swatches to generate labels.")

    # TAB 4: Directory Insert
    with tab_directory:
        st.markdown("#### 📋 Swatch Book Directory Insert")
        st.caption("A paper directory map to slip into the front or back cover of your swatch album.")
        if current_swatches:
            clean_bname = str(current_book['name']).replace("–", "-").replace("—", "-")
            clean_bpref = str(current_book['prefix']).replace("–", "-").replace("—", "-")
            dir_html = f"""
            <style>
                * {{
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                    color-adjust: exact !important;
                }}
            </style>
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 15px;">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #000; padding-bottom: 8px;">
                    <h2 style="margin: 0; font-size: 18px;">{clean_bname} - Swatch Directory</h2>
                    <button onclick="window.print()" style="padding: 6px 14px; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold;">🖨️ Print Now</button>
                </div>
                <p style="color: #555; margin-top: 6px; font-size: 12px;">Total Swatches: {len(current_swatches)} | Prefix: {clean_bpref} | Format: Book-Slot</p>
                <table style="width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 11px;">
                    <thead>
                        <tr style="background: #f1f5f9; border-bottom: 2px solid #cbd5e1; text-align: left;">
                            <th style="padding: 6px;">Slot</th>
                            <th style="padding: 6px;">Swatch ID</th>
                            <th style="padding: 6px;">Color</th>
                            <th style="padding: 6px;">Polish Name</th>
                            <th style="padding: 6px;">Brand</th>
                            <th style="padding: 6px;">Finish</th>
                            <th style="padding: 6px;">Page : Row : Col</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            for sw in current_swatches:
                slot = sw['slot_number']
                page = ((slot - 1) // slots_per_page) + 1
                page_slot = ((slot - 1) % slots_per_page)
                row = (page_slot // cols_per_row) + 1
                col = (page_slot % cols_per_row) + 1
                hex_c = sw.get('hex_code') or '#ffffff'
                clean_snum = str(sw['swatch_number']).replace("–", "-").replace("—", "-")
                clean_b = clean_brand_name(sw.get('brand'))
                dir_html += f"""
                        <tr style="border-bottom: 1px solid #e2e8f0;">
                            <td style="padding: 4px; font-weight: bold;">{slot:03d}</td>
                            <td style="padding: 4px; font-family: monospace; font-weight: bold;">{clean_snum}</td>
                            <td style="padding: 4px;"><div style="width: 16px; height: 16px; border-radius: 50%; background: {hex_c}; background-color: {hex_c}; border: 1px solid #000;"></div></td>
                            <td style="padding: 4px; font-weight: 500;">{sw['name']}</td>
                            <td style="padding: 4px;">{clean_b}</td>
                            <td style="padding: 4px;">{sw.get('finish') or ''}</td>
                            <td style="padding: 4px; color: #475569;">P{page} : R{row} : C{col}</td>
                        </tr>
                """
            dir_html += """
                    </tbody>
                </table>
            </div>
            """
            st.components.v1.html(dir_html, height=450, scrolling=True)
        else:
            st.info("Populate swatches to view the printable directory.")

# ---------------------------------------------------------
# Swatch Removal Dropdown Toolbar
# ---------------------------------------------------------
if current_swatches:
    with st.expander("✂️ Quick Swatch Removal Dropdown (Alternative to clicking ✕)", expanded=False):
        c_rem1, c_rem2 = st.columns([3, 1])
        with c_rem1:
            rem_options = []
            for sw in current_swatches:
                b_display = clean_brand_name(sw.get('brand'), default='No Brand')
                s_display = str(sw['swatch_number']).replace("–", "-").replace("—", "-")
                rem_options.append((
                    sw['item_id'],
                    f"Slot {sw['slot_number']:03d} [{s_display}]: {sw['name']} ({b_display})"
                ))
            
            selected_rem_id = st.selectbox(
                "Select a swatch to remove and automatically redistribute:",
                options=[ro[0] for ro in rem_options],
                format_func=lambda x: dict(rem_options).get(x, x),
                key="direct_remove_select"
            )
        with c_rem2:
            st.write("")
            st.write("")
            if st.button("🗑️ Remove Swatch", type="primary", use_container_width=True):
                if selected_rem_id:
                    remove_swatch_from_book(current_book['id'], selected_rem_id)
                    st.toast("✅ Swatch removed! Remaining swatches redistributed seamlessly.", icon="✨")
                    st.rerun()

# ---------------------------------------------------------
# Album Visualizer: Two-Page Spread & Single Page Views
# ---------------------------------------------------------
st.markdown("---")
st.markdown("### 📖 Album View")

if not current_swatches:
    st.warning("⚠️ No swatches currently populated in this book. Click '🔄 Auto-Populate / Reset Book' above to generate the layout!")
else:
    col_layout1, col_layout2 = st.columns([1.5, 3.5])
    with col_layout1:
        view_layout_mode = st.radio("Display Layout:", ["Two-Page Spread", "Single Page View"], horizontal=True)

    swatch_by_slot = {sw['slot_number']: sw for sw in current_swatches}

    def render_page_html(page_num):
        if page_num > total_pages:
            return ""
        start_slot = (page_num - 1) * slots_per_page + 1
        end_slot = page_num * slots_per_page
        
        cards_html = []
        for slot in range(start_slot, end_slot + 1):
            if slot in swatch_by_slot:
                sw = swatch_by_slot[slot]
                hex_c = sw.get('hex_code') or '#888888'
                name = sw.get('name') or 'Unnamed'
                brand = clean_brand_name(sw.get('brand'))
                snum = str(sw.get('swatch_number') or f"{current_book['prefix']}-{slot:03d}").replace("–", "-").replace("—", "-")
                item_id = sw['item_id']
                remove_url = f"?book_id={current_book['id']}&collection_id={selected_col_id}&remove_item_id={item_id}"
                card = f"""<div class="swatch-card">
<a href="{remove_url}" class="remove-btn" title="Remove {name} from book" target="_self">&#x2715;</a>
<div class="swatch-color" style="background: {hex_c};"></div>
<div class="swatch-num">{snum}</div>
<div class="swatch-name" title="{name}">{name}</div>
<div class="swatch-meta">{brand}</div>
</div>"""
                cards_html.append(card)
            else:
                card = f"""<div class="swatch-card empty-slot">
<div class="swatch-color" style="background: #e2e8f0; border: 2px dashed #94a3b8;"></div>
<div class="swatch-num" style="color: #94a3b8;">Slot {slot:03d}</div>
<div class="swatch-name" style="color: #94a3b8; font-style: italic;">Available</div>
<div class="swatch-meta" style="color: #cbd5e1;">Empty / Buffer</div>
</div>"""
                cards_html.append(card)

        grid_content = "\n".join(cards_html)
        page_html = f"""<div class="book-page">
<div class="page-header">
<span>📄 Page {page_num}</span>
<span style="font-size: 0.8rem; font-weight: normal; color: #64748b;">Slots {start_slot:03d} - {end_slot:03d}</span>
</div>
<div class="swatch-grid" style="grid-template-columns: repeat({cols_per_row}, minmax(0, 1fr));">
{grid_content}
</div>
</div>"""
        return page_html

    if view_layout_mode == "Two-Page Spread":
        num_spreads = (total_pages + 1) // 2
        if num_spreads > 1:
            spread_labels = [f"Spread {sp+1} (Pages {sp*2+1} & {min(sp*2+2, total_pages)})" for sp in range(num_spreads)]
            selected_spread_idx = st.radio("Album Spread Selection:", options=list(range(num_spreads)), format_func=lambda i: spread_labels[i], horizontal=True)
        else:
            selected_spread_idx = 0

        left_page_num = selected_spread_idx * 2 + 1
        right_page_num = selected_spread_idx * 2 + 2

        left_html = render_page_html(left_page_num)
        right_html = render_page_html(right_page_num) if right_page_num <= total_pages else ""

        spread_html = f"""<div class="spread-container">
{left_html}
{right_html}
</div>"""
        st.markdown(spread_html, unsafe_allow_html=True)

    else:
        if total_pages > 1:
            selected_page_num = st.radio(
                "Select Page to View:",
                options=list(range(1, total_pages + 1)),
                format_func=lambda p: f"Page {p}",
                horizontal=True
            )
        else:
            selected_page_num = 1

        page_html = render_page_html(selected_page_num)
        single_html = f"""<div class="spread-container" style="max-width: 900px; margin: 0 auto;">
{page_html}
</div>"""
        st.markdown(single_html, unsafe_allow_html=True)

# ---------------------------------------------------------
# Smart Gap Finder
# ---------------------------------------------------------
if empty_slots_count > 0:
    with st.expander(f"📍 Smart Gap Finder ({empty_slots_count} Empty / Buffer Slots Found)", expanded=False):
        st.write("Physical coordinates for empty slots and growth buffers in this book:")
        gap_rows = []
        for slot in range(1, total_capacity + 1):
            if slot not in swatch_by_slot:
                page = ((slot - 1) // slots_per_page) + 1
                page_slot = ((slot - 1) % slots_per_page)
                row = (page_slot // cols_per_row) + 1
                col = (page_slot % cols_per_row) + 1
                gap_rows.append({
                    "Slot Number": f"{slot:03d}",
                    "Page": f"Page {page}",
                    "Row": f"Row {row}",
                    "Column": f"Col {col}",
                    "Suggested Label": f"{current_book['prefix']}-{slot:03d}"
                })
        st.dataframe(pd.DataFrame(gap_rows), use_container_width=True, hide_index=True)